import xbmc
import xbmcgui
import sys
import update_library as tmdb
import xbmcvfs
import xbmcaddon

if __name__ == "__main__":

    addon = xbmcaddon.Addon()

    res = xbmcgui.Dialog().numeric(0, addon.getLocalizedString(30009), defaultt='')

    if res != '':  # cancel not pressed
        tmdb.DATA_FOLDER = xbmcvfs.translatePath(addon.getAddonInfo('profile'))
        tmdb.COVERART_FOLDER = tmdb.DATA_FOLDER + 'coverart'
        tmdb.DB_FILENAME = tmdb.DATA_FOLDER + tmdb.DB_FILE
        settings = xbmcaddon.Addon().getSettings()
        tmdb.lang = settings.getString('language')
        if not tmdb.set_tmdb_key(addon):
            sys.exit(0)

        success = tmdb.update_details_tmdb_by_id(sys.listitem.getLabel(), res)

        if success:
            tmdb.set_li_data(sys.listitem)
            # xbmcgui.Dialog().notification('UložTo Disk', addon.getLocalizedString(30019), xbmcgui.NOTIFICATION_INFO,
            #                              3000)
            plugin_url = 'plugin://' + sys.argv[0].strip('/')
            item: xbmcgui.ListItem = sys.listitem
            url = f"{plugin_url}?user-token={item.getProperty('session-key')}&action=listing&folder={item.getProperty('parent-folder-slug')}"
            # xbmcgui.Dialog().notification('UložTo Disk', url, xbmcgui.NOTIFICATION_INFO, 3000)
            xbmc.executebuiltin(f'Container.Update({url})')
            # xbmc.executebuiltin(f'Control.SetFocus({item.getProperty("item-index")})')
        else:
            xbmcgui.Dialog().notification('UložTo Disk', addon.getLocalizedString(30015), xbmcgui.NOTIFICATION_ERROR,
                                          3000)
