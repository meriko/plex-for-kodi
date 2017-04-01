import xbmc
import xbmcgui
import kodigui

import busy
import playlist
import windowutils
import search

import opener

from lib import util
from lib import player
from lib import colors

from plexnet import plexapp
from plexnet import playqueue

import library
from plexnet import plexobjects

class ChannelWindow(kodigui.ControlledWindow, windowutils.UtilMixin):
    xmlFile = 'script-plex-channel.xml'
    path = util.ADDON.getAddonInfo('path')
    theme = 'Main'
    res = '1080i'
    width = 1920
    height = 1080

    ITEM_ID = 101

    OPTIONS_GROUP_ID = 200

    HOME_BUTTON_ID = 201
    SEARCH_BUTTON_ID = 202
    PLAYER_STATUS_BUTTON_ID = 204

    def __init__(self, *args, **kwargs):
        kodigui.ControlledWindow.__init__(self, *args, **kwargs)
        self.exitCommand = None
        self.item = kwargs.get('item')
        self.parent = kwargs.get('parent')

    def onFirstInit(self):
        self.itemControl = kodigui.ManagedControlList(self, self.ITEM_ID, 5)

        if not self.item:
            title = 'Channels'
        else:
            title = self.item.title        
            try: title =  title + ' / ' + self.parent.title
            except: pass
        
        self.setProperty('title', title)

        is_directory = self.fill()
        
        self.setFocusId(self.ITEM_ID)

        if is_directory:
            self.setProperty('is.directory', '1')
        else:
            self.clearProperty('is.directory')

        try: 
            thumb = self.item.thumb
        except:
            try:
                thumb = self.parent.thumb
            except:
                thumb = None

        try: 
            art = self.item.art
        except:
            try:
                if self.parent.art != '':
                    art = self.parent.art
                else:
                    art = thumb
            except:
                art = thumb

        if thumb:
            thumb = self.buildImageUrl(path=thumb, transcode=False)
            self.setProperty('thumb', thumb)

        if art:
            art = self.buildImageUrl(path=art)
            self.setProperty('background', art)  

    def onAction(self, action):
        try:
            if action == xbmcgui.ACTION_CONTEXT_MENU:
                if not xbmc.getCondVisibility('ControlGroup({0}).HasFocus(0)'.format(self.OPTIONS_GROUP_ID)):
                    self.setFocusId(self.OPTIONS_GROUP_ID)
                    return
            # elif action in(xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_CONTEXT_MENU):
            #     if not xbmc.getCondVisibility('ControlGroup({0}).HasFocus(0)'.format(self.OPTIONS_GROUP_ID)):
            #         self.setFocusId(self.OPTIONS_GROUP_ID)
            #         return

        except:
            util.ERROR()

        kodigui.ControlledWindow.onAction(self, action)
        
    def onClick(self, controlID):
        if controlID == self.HOME_BUTTON_ID:
            self.goHome()
        elif controlID == self.ITEM_ID:
            self.itemClicked(self.itemControl)
        elif controlID == self.PLAYER_STATUS_BUTTON_ID:
            self.showAudioPlayer()
        elif controlID == self.SEARCH_BUTTON_ID:
            self.searchButtonClicked()

    def searchButtonClicked(self):
        self.processCommand(search.dialog(self))

    def itemClicked(self, list_control):
        mli = list_control.getSelectedItem()
        if not mli:
            return

        if mli.dataSource.media:
            if mli.dataSource.type == 'track':
                player.PLAYER.stop()
                import musicplayer
                self.openWindow(musicplayer.MusicPlayerWindow, track=mli.dataSource)
            else:
                import videoplayer
                self.processCommand(videoplayer.play(video=mli.dataSource, resume=False))
        elif mli.dataSource.search == '1':
            # TODO: Add search
            pass
        else:
            self.openWindow(ChannelWindow, item=mli.dataSource, parent=self.item)

    def createListItem(self, obj):
        try: thumb = obj.get('thumb')
        except: thumb = None

        try: art = obj.get('art')
        except: art = None

        if art:
            art = self.buildImageUrl(path=art)
        else:
            art = self.buildImageUrl(path=thumb)

        if thumb and not thumb.startswith("http"):
            thumb = plexapp.SERVERMANAGER.selectedServer.buildUrl(thumb)

        mli = kodigui.ManagedListItem(
            label=obj.get('title') or '',
            label2=obj.get('grandparentTitle') or '',
            iconImage=thumb,
            thumbnailImage=thumb,
            data_source=obj
        )

        mli.setProperty('summary', obj.get('summary'))
        mli.setProperty('thumb', thumb)
        mli.setProperty('art', art)

        date = obj.get('originallyAvailableAt')
        if date != '':
            mli.setProperty('date', date)

        duration = obj.get('duration')
        if duration:
            duration = util.durationToText(int(duration))
            mli.setProperty('duration', duration)

        season = obj.get('season')
        if season:
            mli.setProperty('season', season)
            
        episode = obj.get('index')
        if episode:
            mli.setProperty('episode', episode)

        return mli

    @busy.dialog()
    def fill(self):
        items = []
        
        if self.item:
            path = self.item.get('key')
        else:
            path = plexapp.SERVERMANAGER.selectedServer.buildUrl('/channels/all')
        
        try:    
            objs = plexobjects.listItems(server=plexapp.SERVERMANAGER.selectedServer, path=path)
        except:
            util.messageDialog(heading="No Content", msg="This channel is not responding")
            self.doClose()
            return

        is_directory = True

        for obj in objs:
            mli = self.createListItem(obj)
            if mli:
                items.append(mli)

                if mli.dataSource.type not in ['Directory', 'channel']: 
                    is_directory = False

        self.itemControl.addItems(items)

        if self.item and not items:
            container = plexapp.SERVERMANAGER.selectedServer.query(self.item.get('key'))

            heading = container.attrib.get('header')
            if heading is None:
                heading = "No content"

            msg = container.attrib.get('message')
            if msg is None:
                try:
                    code = int(container.attrib.get('code'))

                    if code == 2000:
                        msg = 'This channel is not responding.'
                    else:
                        msg = container.attrib.get('status')
                except:
                    pass

                if msg is None:
                    msg = "No content found"

            util.messageDialog(heading=heading, msg=msg)

            self.doClose()

        return is_directory

    def buildImageUrl(self, path, transcode=True, width=None, height=None, blur=None, opacity=None, background=None):
        if not path:
            return ''

        if not path.startswith('http'):
            path = plexapp.SERVERMANAGER.selectedServer.buildUrl(path)

        if transcode:
            return plexapp.SERVERMANAGER.selectedServer.getImageTranscodeURL(path=path, width=1920, height=1080, blur=5, opacity=10, background=colors.noAlpha.Background)
        else:
            return path
