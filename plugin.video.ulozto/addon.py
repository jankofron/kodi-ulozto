import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmc
import sys
import requests
from urllib.parse import parse_qsl
from requests import HTTPError
import socket

API_HOST = 'apis.uloz.to'
PLUGIN_ID = 'plugin.video.ulozto'

CHUNK_SIZE = 134217728  # = 128MB
RETRIES = 5
REQUEST_TIMEOUT = 30  # seconds
UPLOAD_TIMEOUT = 600  # seconds

should_verify = True
global addon_handle
global session
global plugin_url

global LOGIN
global AUTH_TOKEN
global RECS_FOLDER_SLUG
global ROOT_FOLDER_SLUG
global API_TOKEN
global DEVICE_ID


def show_notification(text):
    dialog = xbmcgui.Dialog()
    dialog.notification('UložTo přehrávač', text, xbmcgui.NOTIFICATION_INFO, 3000)


def show_error(text):
    dialog = xbmcgui.Dialog()
    dialog.notification('UložTo přehrávač', text, xbmcgui.NOTIFICATION_ERROR, 3000)


def authenticate():
    global session
    global ROOT_FOLDER_SLUG

    # print(f"User {LOGIN} authentication")
    login = {"login": LOGIN, "token": AUTH_TOKEN, "device_id": DEVICE_ID}
    try:
        user_token_response = session.post(url=f'https://{API_HOST}/v6/auth/token', json=login, verify=should_verify)
        if user_token_response.status_code == 400:
            show_error('Chybné přihlašovací údaje!')
            session = None
        user_token_response.raise_for_status()

        session.headers["X-User-Token"] = user_token_response.json()['token_id']
        ROOT_FOLDER_SLUG = user_token_response.json()['session']['user']['root_folder_slug']
        xbmc.log('UlozTo: Login Successful', xbmc.LOGINFO)

        # show_notification('Příhlášení úspěšné.')

    except HTTPError:
        show_error('Přihlášení selhalo.')
        session = None


def get_subfolders(parent_folder_slug):
    # print('Fetching upload root folder content')
    global session
    global plugin_url

    user = {'userLogin': LOGIN, 'folderSlug': parent_folder_slug}
    q_params = {'limit': 500, 'sort': 'name'}
    root_folder_content = session.get(url=f"https://{API_HOST}/v9/user/{LOGIN}/folder/{parent_folder_slug}/folder-list",
                                      json=user,
                                      params=q_params,
                                      verify=should_verify)
    root_folder_content.raise_for_status()
    subfolders = root_folder_content.json()['subfolders']
    return [[i['name'], f'{plugin_url}?user-token={session.headers["X-User-Token"]}&action=listing&folder={i["slug"]}']
            for i in subfolders]


def get_download_link(slug):
    global session
    global plugin_url

    payload = {'user_login': LOGIN, 'device_id': DEVICE_ID, 'file_slug': slug}

    link = session.post(url=f"https://{API_HOST}/v5/file/download-link/vipdata", json=payload, verify=should_verify)
    if link.status_code == 401:  # we need to process captcha
        show_error('Nemohu získat odkaz k přehrání.')
        return None

    return link.json()['link']


def get_remote_files(folderslug):
    global session
    global plugin_url

    user = {"userLogin": LOGIN, 'folderSlug': folderslug}
    q_params = {'limit': 1000}
    files = session.get(url=f"https://{API_HOST}/v8/user/{LOGIN}/folder/{folderslug}/file-list",
                        json=user,
                        params=q_params,
                        verify=should_verify)

    files.raise_for_status()

    filelist = list()

    for file in files.json()['items']:
        filelist.append([file['name'][:-len(file['extension']) - 1], file['slug']])

    return filelist


def list_videos(folderslug):
    global plugin_url
    global session

    # first list folders
    folders = get_subfolders(folderslug)
    for folder in folders:
        li = xbmcgui.ListItem(label=folder[0])
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=folder[1], listitem=li, isFolder=True)
    # now add the movies

    movies = get_remote_files(folderslug)
    for item in movies:
        li = xbmcgui.ListItem(item[0])
        url = item[1]
        xbmcplugin.addDirectoryItem(handle=addon_handle,
                                    url=f'{plugin_url}?user-token={session.headers["X-User-Token"]}&action=play&video={url}&name={item[0]}',
                                    listitem=li, isFolder=False)

    xbmcplugin.endOfDirectory(addon_handle)


def play_video(name, fileslug):
    global session
    # Create a playable item with a path to play.
    link = get_download_link(fileslug)

    play_item = xbmcgui.ListItem(path=link)
    play_item.getVideoInfoTag().setTitle(name)
    # play_item.setArt({'poster': 'uloto.png'})

    # Pass the item to the Kodi player.
    # xbmcplugin.setResolvedUrl(addon_handle, True, listitem=play_item)

    xbmc.log('UlozTo: Trying to play: ' + link, xbmc.LOGINFO)
    xbmc.Player().play(link, play_item)


def router(params):
    """
    Router function that calls other functions
    depending on the provided paramstring
    """

    global session
    global RECS_FOLDER_SLUG

    # Parse a URL-encoded paramstring to the dictionary of
    # {<parameter>: <value>} elements

    # Check the parameters passed to the plugin
    if params:
        if params['action'] == 'listing':
            # Display the list of videos in a provided category.
            list_videos(params['folder'])
        elif params['action'] == 'play':
            # Play a video from a provided URL.
            play_video(params['name'], params['video'])
    else:
        if session is not None:
            list_videos(RECS_FOLDER_SLUG)


def get_remote_slug(path: str):
    global ROOT_FOLDER_SLUG
    global session

    path = path.strip('/')

    elements = path.split('/')
    parent_folder_slug = ROOT_FOLDER_SLUG

    for element in elements:
        user = {'userLogin': LOGIN, 'folderSlug': parent_folder_slug}
        q_params = {'limit': 500, 'sort': 'name'}
        root_folder_content = session.get(
            url=f"https://{API_HOST}/v9/user/{LOGIN}/folder/{parent_folder_slug}/folder-list",
            json=user,
            params=q_params,
            verify=should_verify)
        root_folder_content.raise_for_status()

        try:
            parent_folder_slug = [i['slug'] for i in root_folder_content.json()['subfolders'] if i['name'] == element][
                0]

        except IndexError:
            show_error('Vzdálená složka nenalezena – upravte nastavení')
            return None

    return parent_folder_slug


### Main ###
if __name__ == '__main__':
    # initialize plugin
    plugin_url = sys.argv[0]
    addon_handle = int(sys.argv[1])
    xbmcplugin.setContent(addon_handle, 'movies')

    # initialize plugin settings
    settings = xbmcaddon.Addon(id=PLUGIN_ID).getSettings()
    LOGIN = settings.getString('username')
    AUTH_TOKEN = settings.getString('auth-token')
    API_TOKEN = settings.getString('api-token')
    DEVICE_ID = socket.gethostname()

    # setting up the session parameters
    session = requests.Session()

    session.headers = {
        "X-Auth-Token": API_TOKEN,
        "Content-type": "application/json",
        "Accept": "application/json",
    }

    # parsing parameters from Kodi
    params = dict(parse_qsl(sys.argv[2][1:]))

    if 'user-token' in params.keys():
        session.headers['X-User-Token'] = params['user-token']

    else:
        authenticate()
        if session is None:
            sys.exit(0)

        RECS_FOLDER_SLUG = get_remote_slug(settings.getString('root-folder'))

        if RECS_FOLDER_SLUG is None:
            exit(0)

    router(params)

