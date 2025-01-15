import xbmc
import xbmcgui
import sys
import xbmcaddon
import ulozto

if __name__ == "__main__":

    addon = xbmcaddon.Addon()

    res = xbmcgui.Dialog().yesno(addon.getLocalizedString(30020),
                                 addon.getLocalizedString(30021).format(sys.listitem.getLabel()))

    if res:
        item: xbmcgui.ListItem = sys.listitem
        ulozto.initialize(item.getProperty('session-key'))
        res = ulozto.delete_file(item.getProperty('file-slug'))

        if res:
            item.setLabel(addon.getLocalizedString(30034).format(item.getLabel()))
            xbmcgui.Dialog().notification('UložTo Disk', addon.getLocalizedString(30022), xbmcgui.NOTIFICATION_INFO,
                                          3000)
            # Refresh the container with the new URL
            plugin_url = 'plugin://' + sys.argv[0].strip('/')
            item: xbmcgui.ListItem = sys.listitem
            url = f"{plugin_url}?user-token={item.getProperty('session-key')}&action=listing&folder={item.getProperty('parent-folder-slug')}"
            xbmc.executebuiltin(f'Container.Update({url})')
        else:
            xbmcgui.Dialog().notification('UložTo Disk', addon.getLocalizedString(30023), xbmcgui.NOTIFICATION_ERROR,
                                          3000)


    else:
        pass
