import os
import socket
import sys
import tempfile
import threading
import requests
import xbmc
import xbmcaddon
import xbmcgui

import ulozto
import update_library as tmdb

global LOGIN
global AUTH_TOKEN
global API_TOKEN
global DEVICE_ID


class CachingPlayer(xbmc.Player):
    def __init__(self, *args):
        super().__init__()
        self.thread: threading.Thread = None
        self.playback_stopped = False
        self.local_file = None

    def download_to_file(self, url, local_path):
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(local_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=1048576):
                    if chunk:
                        f.write(chunk)
                    if self.playback_stopped:
                        break

    def start_async_download(self, url):
        temp_dir = tempfile.gettempdir()
        self.local_file = os.path.join(temp_dir, os.path.basename(url))

        self.thread = threading.Thread(target=self.download_to_file, args=(url, self.local_file), daemon=True)
        self.thread.start()


    def play_video_cached(self, name, fileslug):
        url = ulozto.get_download_link(fileslug)
        if not url:
            xbmcgui.Dialog().notification('Error', 'Could not get video link.', xbmcgui.NOTIFICATION_ERROR)
            return

        self.start_async_download(url)

        # Wait for some initial buffer (e.g. 2MB or timeout)
        min_size = 10 * 1024 * 1024
        max_wait_time = 10 * 1000  # 10 seconds
        waited = 0
        while waited < max_wait_time:
            if os.path.exists(self.local_file) and os.path.getsize(self.local_file) >= min_size:
                break
            xbmc.sleep(500)
            waited += 500

        play_item = xbmcgui.ListItem(path=self.local_file)
        details = tmdb.get_data(name) or {'title': name}
        tmdb.update_listitem(play_item, details)

        xbmc.log('UlozTo: Playing local temp file: ' + self.local_file, xbmc.LOGDEBUG)
        xbmc.Player().play(self.local_file, play_item)

        xbmc.sleep(1000)

        while self.isPlaying():
            xbmc.sleep(5000)

        self.playback_stopped = True
        if self.local_file is not None:
            os.remove(self.local_file)


if __name__ == "__main__":
    item: xbmcgui.ListItem = sys.listitem
    ulozto.initialize(item.getProperty('session-key'))
    settings = xbmcaddon.Addon().getSettings()
    LOGIN = settings.getString('username')
    AUTH_TOKEN = settings.getString('auth-token')
    API_TOKEN = settings.getString('api-token')
    DEVICE_ID = socket.gethostname()

    player = CachingPlayer()
    player.play_video_cached(item.getLabel(), item.getProperty('file-slug'))
