from typing import Optional, Union
import xbmc

import update_library as db

class ResumablePlayer(xbmc.Player):
    def __init__(self, *args):
        super().__init__()
        self.details = args[0]
        self.full_name = args[1]
        self.last_position = 0

    def onPlayBackStarted(self):
        xbmc.log("##### TEST - playback started", level=xbmc.LOGINFO)
        xbmc.log("##### Last_position seek: " + str(self.last_position), level=xbmc.LOGINFO)
        if self.last_position is not 0:
            super().seekTime(self.last_position)


    def onPlayBackEnded(self):
        xbmc.log("##### TEST - playback ended", level=xbmc.LOGINFO)

    def onPlayBackStopped(self):
        xbmc.log("##### TEST - playback stopped", level=xbmc.LOGINFO)

    def play(self, item: Union[str,  'PlayList'] = "",
             listitem: Optional['xbmcgui.ListItem'] = None,
             windowed: bool = False,
             startpos: int = -1) -> None:
        if 'last_position' in self.details:
            self.last_position = self.details['last_position']
            xbmc.log("##### Last_position found: " + str(self.details['last_position']), level=xbmc.LOGINFO)


        super().play(item, listitem=listitem)

        xbmc.sleep(1000)

        # Wait until playback starts
        while self.isPlaying():
            self.details['last_position'] = super().getTime()
            db.save_data(self.full_name, self.details)
            xbmc.sleep(5000)
