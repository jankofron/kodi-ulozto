import xbmcgui
import xbmc
import sys
import update_library as tmdb
import xbmcvfs
import xbmcaddon

if __name__ == "__main__":

    addon = xbmcaddon.Addon()

    res = xbmcgui.Dialog().numeric(0, addon.getLocalizedString(30009))

    addon = xbmcaddon.Addon()
    tmdb.DATA_FOLDER = xbmcvfs.translatePath(addon.getAddonInfo('profile'))

    success = tmdb.update_details_tmdb_by_id(sys.listitem.getLabel(), res)

    if success:
        tmdb.set_li_data(sys.listitem)
        xbmc.executebuiltin("Container.Refresh")
