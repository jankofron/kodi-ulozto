import socket

import requests
import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs
from requests import HTTPError

import update_library as tmdb

API_HOST = 'apis.uloz.to'
PLUGIN_ID = 'plugin.video.ulozto'

CHUNK_SIZE = 134217728  # = 128MB
RETRIES = 5
REQUEST_TIMEOUT = 30  # seconds
UPLOAD_TIMEOUT = 600  # seconds

should_verify = True
session = None
plugin_url = None
addon_handle = -1
addon = None

LOGIN = None
AUTH_TOKEN = None
RECS_FOLDER_SLUG = None
ROOT_FOLDER_SLUG = None
API_TOKEN = None
DEVICE_ID = None


def show_notification(text):
    dialog = xbmcgui.Dialog()
    dialog.notification('UložTo Disk', text, xbmcgui.NOTIFICATION_INFO, 3000)


def show_error(text):
    dialog = xbmcgui.Dialog()
    dialog.notification('UložTo Disk', text, xbmcgui.NOTIFICATION_ERROR, 3000)


def authenticate():
    global session
    global ROOT_FOLDER_SLUG
    global RECS_FOLDER_SLUG

    # print(f"User {LOGIN} authentication")
    login = {"login": LOGIN, "token": AUTH_TOKEN, "device_id": DEVICE_ID}
    try:
        user_token_response = session.post(url=f'https://{API_HOST}/v6/auth/token', json=login, verify=should_verify)
        if user_token_response.status_code == 400:
            show_error(addon.getLocalizedString(30005))
            session = None
        user_token_response.raise_for_status()

        session.headers["X-User-Token"] = user_token_response.json()['token_id']
        xbmcgui.Window(10000).setProperty('ulozto-plugin-user-token', session.headers["X-User-Token"])
        ROOT_FOLDER_SLUG = user_token_response.json()['session']['user']['root_folder_slug']
        settings = xbmcaddon.Addon().getSettings()
        RECS_FOLDER_SLUG = get_remote_slug(settings.getString('root-folder'))
        win = xbmcgui.Window(10000)
        win.setProperty('ulozto-plugin-root-folder-slug', ROOT_FOLDER_SLUG or '')
        win.setProperty('ulozto-plugin-recs-folder-slug', RECS_FOLDER_SLUG or '')

        xbmc.log('UlozTo: Login Successful', xbmc.LOGDEBUG)

        # show_notification('Příhlášení úspěšné.')

    except HTTPError:
        show_error(addon.getLocalizedString(30006))
        session = None


def get_subfolders(parent_folder_slug, plugin_url=''):
    user = {'userLogin': LOGIN, 'folderSlug': parent_folder_slug}
    q_params = {'limit': 500, 'sort': 'name'}
    root_folder_content = session.get(url=f"https://{API_HOST}/v9/user/{LOGIN}/folder/{parent_folder_slug}/folder-list",
                                      json=user,
                                      params=q_params,
                                      verify=should_verify)
    root_folder_content.raise_for_status()
    subfolders = root_folder_content.json()['subfolders']
    return [[i['name'], f'{plugin_url}?action=listing&folder={i["slug"]}',
             i['slug']]
            for i in subfolders]


def get_download_link(slug):
    payload = {'user_login': LOGIN, 'device_id': DEVICE_ID, 'file_slug': slug}

    link = session.post(url=f"https://{API_HOST}/v5/file/download-link/vipdata", json=payload, verify=should_verify)
    if link.status_code == 401:  # we need to process captcha
        show_error(addon.getLocalizedString(30007))
        return None

    return link.json()['link']


def get_remote_files(folderslug):
    user = {"userLogin": LOGIN, 'folderSlug': folderslug}
    q_params = {'limit': 1000}
    files = session.get(url=f"https://{API_HOST}/v8/user/{LOGIN}/folder/{folderslug}/file-list",
                        json=user,
                        params=q_params,
                        verify=should_verify)

    files.raise_for_status()

    filelist = list()

    for file in files.json()['items']:
        try:
            if not file['is_in_trash']:
                filelist.append([file['name'][:-len(file['extension']) - 1], file['slug']])
            else:
                pass
        except IndexError:
            pass

    return filelist


def list_videos(folderslug):
    # first list folders
    folders = get_subfolders(folderslug, plugin_url)
    for idx in range(len(folders)):
        folder = folders[idx]
        li = xbmcgui.ListItem(label=folder[0])
        li.setProperties({'item-index': idx})
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=folder[1], listitem=li, isFolder=True)

    folder_cnt = len(folders)

    # now add the movies
    movies = get_remote_files(folderslug)
    for idx in range(len(movies)):
        item = movies[idx]
        li = xbmcgui.ListItem(item[0])
        li.setProperties({'file-slug': item[1],
                          'parent-folder-slug': folderslug,
                          'item-index': idx + folder_cnt})
        li.setProperty('IsPlayable', 'true')

        tmdb.set_li_data(li)

        xbmcplugin.addDirectoryItem(handle=addon_handle,
                                    url=f'{plugin_url}?action=play&video={item[1]}&name={item[0]}',
                                    listitem=li, isFolder=False)

    # Use normal navigation so Kodi maintains the container stack (needed for ".." to work)
    xbmcplugin.endOfDirectory(addon_handle, updateListing=False, cacheToDisc=True)


def play_video(handle, name, fileslug):
    # Build the real (dynamic) stream URL
    stream_url = get_download_link(fileslug)
    if not stream_url:
        xbmc.log("UlozTo: no stream URL", xbmc.LOGERROR)
        xbmcplugin.setResolvedUrl(handle, False, xbmcgui.ListItem())
        return

    li = xbmcgui.ListItem(path=stream_url)
    li.setProperty('IsPlayable', 'true')

    # (Optional) add metadata/art so it shows in OSD/history
    details = tmdb.get_data(name) or {'title': name}
    tmdb.update_listitem(li, details)

    # (Optional) If you know duration, help Kodi’s resume logic:
    # tag = li.getVideoInfoTag()
    # tag.setDuration(runtime_seconds)  # Kodi 20+

    xbmc.log('UlozTo: Trying to play: ' + stream_url, xbmc.LOGINFO)
    xbmcplugin.setResolvedUrl(handle, True, li)
    # IMPORTANT: return immediately after resolving
    return


def delete_file(file_slug: str) -> bool:
    res = session.delete(url=f"https://{API_HOST}/v6/file/{file_slug}/private")
    if res.status_code == 204:
        return True
    else:
        return False


def router(params):
    """
    Router function that calls other functions
    depending on the provided paramstring
    """

    global RECS_FOLDER_SLUG

    # Parse a URL-encoded paramstring to the dictionary of
    # {<parameter>: <value>} elements

    # Check the parameters passed to the plugin
    if params:
        if params['action'] == 'listing':
            # Display the list of videos in a provided category.
            tmdb.ensure_db()

            list_videos(params['folder'])

        elif params['action'] == 'play':
            # Play a video from a provided URL.
            play_video(int(xbmcgui.Window(10000).getProperty('ulozto-plugin-handle')), params['name'], params['video'])

    else:
        if session is not None:
            # RECS_FOLDER_SLUG may be missing when we restore from cached session; recompute if needed
            if RECS_FOLDER_SLUG is None:
                settings = xbmcaddon.Addon().getSettings()
                # If we don't know the root, re-authenticate to get it
                if ROOT_FOLDER_SLUG is None:
                    authenticate()
                if ROOT_FOLDER_SLUG is not None:
                    RECS_FOLDER_SLUG = get_remote_slug(settings.getString('root-folder'))
                    xbmcgui.Window(10000).setProperty('ulozto-plugin-recs-folder-slug', RECS_FOLDER_SLUG or '')

            if RECS_FOLDER_SLUG is None:
                show_error(addon.getLocalizedString(30008))
                return

            tmdb.ensure_db()
            list_videos(RECS_FOLDER_SLUG)


def get_remote_slug(path: str):
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
            show_error(addon.getLocalizedString(30008))
            return None

    return parent_folder_slug


def initialize(user_token: str = None):
    global LOGIN
    global AUTH_TOKEN
    global API_TOKEN
    global DEVICE_ID
    global session
    global RECS_FOLDER_SLUG
    global ROOT_FOLDER_SLUG
    global addon

    win = xbmcgui.Window(10000)
    # Restore cached slugs (may be empty strings if not set)
    root_prop = win.getProperty('ulozto-plugin-root-folder-slug')
    recs_prop = win.getProperty('ulozto-plugin-recs-folder-slug')
    ROOT_FOLDER_SLUG = root_prop if root_prop != '' else None
    RECS_FOLDER_SLUG = recs_prop if recs_prop != '' else None

    # initialize plugin settings
    addon = xbmcaddon.Addon()
    settings = xbmcaddon.Addon().getSettings()
    LOGIN = settings.getString('username')
    AUTH_TOKEN = settings.getString('auth-token')
    API_TOKEN = settings.getString('api-token')
    DEVICE_ID = socket.gethostname()
    tmdb.DATA_FOLDER = xbmcvfs.translatePath(addon.getAddonInfo('profile'))
    tmdb.COVERART_FOLDER = tmdb.DATA_FOLDER + 'coverart'
    tmdb.DB_FILENAME = tmdb.DATA_FOLDER + tmdb.DB_FILE

    # setting up the session parameters
    session = requests.Session()

    session.headers = {
        "X-Auth-Token": API_TOKEN,
        "Content-type": "application/json",
        "Accept": "application/json",
    }

    if user_token is not None:
        session.headers["X-User-Token"] = user_token
