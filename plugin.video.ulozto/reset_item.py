import xbmc
import xbmcgui
import sys
import update_library as tmdb
import xbmcvfs
import xbmcaddon

if __name__ == "__main__":

    addon = xbmcaddon.Addon()

    res = xbmcgui.Dialog().yesno('UložTo Disk', addon.getLocalizedString(30025))

    if res != '':  # yes pressed
        tmdb.DATA_FOLDER = xbmcvfs.translatePath(addon.getAddonInfo('profile'))
        tmdb.COVERART_FOLDER = tmdb.DATA_FOLDER + 'coverart'
        tmdb.DB_FILENAME = tmdb.DATA_FOLDER + tmdb.DB_FILE

        success = tmdb.reset_item(sys.listitem.getLabel())

        if success:
            tmdb.set_li_data(sys.listitem)
            plugin_url = 'plugin://' + sys.argv[0].strip('/')
            item: xbmcgui.ListItem = sys.listitem
            url = f"{plugin_url}?user-token={item.getProperty('session-key')}&action=listing&folder={item.getProperty('parent-folder-slug')}"
            xbmc.executebuiltin(f'Container.Update({url})')
        else:
            xbmcgui.Dialog().notification('UložTo Disk', addon.getLocalizedString(30015), xbmcgui.NOTIFICATION_ERROR,
                                          3000)
