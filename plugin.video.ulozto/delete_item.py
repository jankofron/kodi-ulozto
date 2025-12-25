import xbmc
import xbmcgui
import sys
import xbmcaddon
import ulozto

if __name__ == "__main__":

    addon = xbmcaddon.Addon()
    item: xbmcgui.ListItem = sys.listitem

    res = xbmcgui.Dialog().yesno(addon.getLocalizedString(30020),
                                 addon.getLocalizedString(30021).format(sys.listitem.getLabel()))

    if res:
        session_key = item.getProperty('session-key') or xbmcgui.Window(10000).getProperty('ulozto-plugin-user-token')
        ulozto.initialize(session_key or None)
        if not session_key:
            ulozto.authenticate()
            session_key = ulozto.session.headers.get("X-User-Token", "") if ulozto.session else ''
        res = ulozto.delete_file(item.getProperty('file-slug'))

        if res:
            item.setLabel(addon.getLocalizedString(30034).format(item.getLabel()))
            xbmcgui.Dialog().notification('UložTo Disk', addon.getLocalizedString(30022), xbmcgui.NOTIFICATION_INFO,
                                          3000)
            # Refresh the container with the new URL
            plugin_url = 'plugin://' + sys.argv[0].strip('/')
            url = f"{plugin_url}?user-token={session_key}&action=listing&folder={item.getProperty('parent-folder-slug')}"
            xbmc.executebuiltin(f'Container.Update({url})')
        else:
            xbmcgui.Dialog().notification('UložTo Disk', addon.getLocalizedString(30023), xbmcgui.NOTIFICATION_ERROR,
                                          3000)

    else:
        pass
