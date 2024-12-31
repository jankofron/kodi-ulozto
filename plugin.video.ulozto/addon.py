import xbmc
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

    user_token = None
    if 'user-token' in params.keys():
        user_token = params['user-token']
        ulozto_api.initialize(user_token)

    else:
        ulozto_api.initialize()
        ulozto_api.authenticate()

        if ulozto_api.RECS_FOLDER_SLUG is None:
            exit(0)

    # xbmc.log(str(ulozto_api.session.headers), xbmc.LOGINFO)

    ulozto_api.router(params)

