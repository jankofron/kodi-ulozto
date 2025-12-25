import xbmcgui
import xbmcplugin
import sys
from urllib.parse import parse_qsl
import ulozto as ulozto_api

### Main ###
if __name__ == '__main__':
    # initialize plugin
    ulozto_api.plugin_url = sys.argv[0]
    ulozto_api.addon_handle = int(sys.argv[1])
    xbmcplugin.setContent(ulozto_api.addon_handle, 'movies')

    # parsing parameters from Kodi
    params = dict(parse_qsl(sys.argv[2][1:]))

    win = xbmcgui.Window(10000)
    if ulozto_api.addon_handle != -1:
        win.setProperty('ulozto-plugin-handle', str(ulozto_api.addon_handle))

    user_token = None
    if win.getProperty('ulozto-plugin-user-token') != '':
        ulozto_api.initialize(win.getProperty('ulozto-plugin-user-token'))

    else:
        ulozto_api.initialize()
        ulozto_api.authenticate()

        if ulozto_api.RECS_FOLDER_SLUG is None:
            exit(0)

    ulozto_api.router(params)
