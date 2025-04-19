import json
import requests
import xbmcaddon
import xbmcgui
import xbmcvfs
import xbmc
import sqlite3
import ulozto as ulozto_api

URL = 'https://api.themoviedb.org/3/search/movie?query={}&include_adult=false&language={}'
URL_ID = 'https://api.themoviedb.org/3/{}/{}?language={}'
MOVIE = 'movie'
SERIES = 'tv'
IMAGE_URL = 'https://image.tmdb.org/t/p/w1280/{}'
DB_FILE = 'movies.sqlite'
DB_TABLE = 'movies'
TMDB_REQUEST_HEADERS = {
    "accept": "application/json",
    "Authorization": "Key required"
}

global pd
global ROOT_FOLDER_SLUG
global SESSION_KEY
global COVERART_FOLDER
global DB_FILENAME
global DATA_FOLDER
global API_KEY
global addon
global lang


class CancelException(Exception):
    pass


def get_movie_details_by_id(id: str) -> dict:
    url_movie = URL_ID.format(MOVIE, id, lang)
    url_series = URL_ID.format(SERIES, id, lang)

    xbmc.log('Getting movie details for {}'.format(id), xbmc.LOGINFO)
    response = requests.get(url_movie, headers=TMDB_REQUEST_HEADERS)

    if response.status_code == 200:
        data = response.json()
        xbmc.log('Movie details obtained: {}'.format(data), xbmc.LOGINFO)

        if 'poster_path' in data.keys() and data['poster_path'] is not None:
            get_art(data['poster_path'])

        if 'backdrop_path' in data.keys() and data['backdrop_path'] is not None:
            get_art(data['backdrop_path'])

        return data

    else:
        # we try series
        response = requests.get(url_series, headers=TMDB_REQUEST_HEADERS)
        xbmc.log('Session headers: {}'.format(str(TMDB_REQUEST_HEADERS)), xbmc.LOGINFO)

        if response.status_code == 200:
            data = response.json()
            xbmc.log('Series details obtained: {}'.format(data), xbmc.LOGINFO)

            if 'poster_path' in data.keys() and data['poster_path'] is not None:
                get_art(data['poster_path'])

            return data

        else:
            # xbmc.log('No data found for {}'.format(id), xbmc.LOGDEBUG)
            return None


def get_movie_info(title: str) -> dict:
    url = URL.format(title, lang)

    xbmc.log('Getting movie details for {}'.format(title), xbmc.LOGDEBUG)
    response = requests.get(url, headers=TMDB_REQUEST_HEADERS)
    # xbmc.log('Session headers: {}'.format(str(TMDB_REQUEST_HEADERS)), xbmc.LOGDEBUG)
    data = response.json()
    xbmc.log('Movie details obtained: {}'.format(data), xbmc.LOGDEBUG)
    results = data.get('results')
    return results[0] if results is not None and len(results) > 0 else None


def save_data(key: str, data: dict):
    db_path = xbmcvfs.translatePath(DB_FILENAME)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('insert or replace into movies values (?, ?)', (key, json.dumps(data)))
    conn.commit()
    conn.close()


def get_data(key: str) -> dict:
    """
    Retrieves the date stored previously in the local movie database
    :param key: the filename is used as key – might be not unique, but we can assume this
    :return: JSON structure if there is such record, None otherwise
    """
    DB_FILENAME = DATA_FOLDER + DB_FILE

    db_path = xbmcvfs.translatePath(DB_FILENAME)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('select data from movies where key=?', (key,))
    details = c.fetchone()
    conn.close()
    # xbmc.log('Data retrieved: {}'.format(details), xbmc.LOGDEBUG)
    if details is not None:
        return json.loads(details[0])
    else:
        return None

def reset_item(name: str) -> bool:
    db_path = xbmcvfs.translatePath(DB_FILENAME)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('delete from movies where key=?', (name,))
    conn.commit()
    conn.close()
    return True


def update_listitem(li: xbmcgui.ListItem, data: dict):
    try:
        tag = li.getVideoInfoTag()
        try:
            tag.setTitle(data['title'])
        except KeyError:
            pass
        try:
            tag.setPlot(data['overview'])
        except KeyError:
            pass
        try:
            tag.setRating(data['vote_average'])
        except KeyError:
            pass
        try:
            tag.setOriginalTitle(data['original_title'])
        except KeyError:
            pass
        try:
            tag.setYear(int(data['release_date'][:4]))
        except KeyError:
            pass
        try:
            tag.setDuration(int(data['runtime']) * 60)
        except KeyError:
            pass
        try:
            tag.setTagLine(data['tagline'])
        except KeyError:
            pass

        if 'poster_path' in data.keys() and data['poster_path'] is not None and data['poster_path'] != '':
            local_path = COVERART_FOLDER + data['poster_path']
            xbmc.log('Poster path: {}'.format(local_path), xbmc.LOGDEBUG)
            li.setArt({"poster": local_path})

        if 'backdrop_path' in data.keys() and data['backdrop_path'] is not None and data['backdrop_path'] != '':
            local_path = COVERART_FOLDER + data['backdrop_path']
            xbmc.log('Fanart path: {}'.format(local_path), xbmc.LOGDEBUG)
            li.setArt({"fanart": local_path})



    except Exception as e:
        xbmc.log(e.__str__(), xbmc.LOGDEBUG)


def get_art(m_id: str):
    if not xbmcvfs.exists(COVERART_FOLDER):
        xbmcvfs.mkdir(COVERART_FOLDER)
        xbmc.log('Coverart folder created', xbmc.LOGDEBUG)

    local_path = COVERART_FOLDER + m_id
    if not xbmcvfs.exists(local_path):
        image_path = IMAGE_URL.format(m_id)
        image = requests.get(image_path).content
        # xbmc.log('Getting the coverart', xbmc.LOGDEBUG)
        with open(local_path, 'wb') as f:
            f.write(image)

        xbmc.log('Coverart image saved', xbmc.LOGDEBUG)


def update_details_tmdb(filename: str):
    # xbmc.log('Update library called', xbmc.LOGDEBUG)

    query = filename.split(',')[0].split('(')[0]
    data = get_movie_info(query)

    if data is not None:
        update_details_tmdb_by_id(filename, data['id'])


def update_details_tmdb_by_id(filename: str, tmdb_id: str) -> bool:
    ensure_db()

    data = get_movie_details_by_id(tmdb_id)

    if data is not None:
        # xbmc.log('Textual info set: {}, {}'.format(data['title'], data['overview']), xbmc.LOGDEBUG)

        if 'poster_path' in data.keys() and data['poster_path'] is not None:
            get_art(data['poster_path'])

        save_data(filename, data)
        # xbmc.log('Poster image set', xbmc.LOGDEBUG)
        return True
    else:
        return False


def ensure_db():
    db_path = xbmcvfs.translatePath(DB_FILENAME)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('create table if not exists movies ( key text primary key, data text );')
    conn.commit()
    conn.close()


def update_library(slug: str):
    ensure_db()

    # First, update the files
    files = ulozto_api.get_remote_files(slug)
    for i in range(len(files)):
        if pd.iscanceled():
            raise CancelException()
        if get_data(files[i][0]) is None:
            update_details_tmdb(files[i][0])
        pd.update(i * 100 // len(files), files[i][0])

    # update the subfolders
    folders = ulozto_api.get_subfolders(slug)
    for i in range(len(folders)):
        pd.update(0, '')
        update_library(folders[i][2])


def set_li_data(li: xbmcgui.ListItem):
    movie_details = get_data(li.getLabel())
    if movie_details is not None:
        update_listitem(li, movie_details)


def set_tmdb_key(addon):
    settings = addon.getSettings()
    tmdb_key = settings.getString('tmdb-api-key')
    if len(tmdb_key) == 0:
        key_file = settings.getString('tmdb-key-file')
        with open(key_file) as f:
            tmdb_key = f.read().strip()

        if len(tmdb_key) == 0:
            xbmcgui.Dialog().notification('UložTo Disk', addon.getLocalizedString(30017), xbmcgui.NOTIFICATION_ERROR,
                                          3000)
            exit(0)
        else:
            TMDB_REQUEST_HEADERS['Authorization'] = 'Bearer ' + tmdb_key
            settings.setString(id='tmdb-api-key', value=tmdb_key)
    else:
        TMDB_REQUEST_HEADERS['Authorization'] = 'Bearer ' + tmdb_key


if __name__ == "__main__":
    # initialize plugin settings

    ulozto_api.initialize()
    ulozto_api.authenticate()

    if ulozto_api.RECS_FOLDER_SLUG is None:
        exit(0)

    addon = xbmcaddon.Addon()
    DATA_FOLDER = xbmcvfs.translatePath(addon.getAddonInfo('profile'))
    COVERART_FOLDER = DATA_FOLDER + 'coverart'
    DB_FILENAME = DATA_FOLDER + DB_FILE
    settings = addon.getSettings()
    lang = settings.getString('language')
    set_tmdb_key(addon)

    pd = xbmcgui.DialogProgress()
    pd.create(addon.getLocalizedString(30010), addon.getLocalizedString(30011))

    try:
        update_library(ulozto_api.RECS_FOLDER_SLUG)
    except CancelException:
        pass

    pd.close()
    xbmc.executebuiltin("Container.Refresh")
