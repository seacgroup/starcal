# -*- coding: utf-8 -*-
#
# Copyright (C) 2009-2011 Saeed Rasooli <saeed.gnu@gmail.com> (ilius)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program. If not, see <http://www.gnu.org/licenses/gpl.txt>.
# Also avalable in /usr/share/common-licenses/GPL on Debian systems
# or /usr/share/licenses/common/GPL3/license.txt on ArchLinux
from time import time
#print time(), __file__ ## FIXME

import sys, os, os.path, shutil
from os import listdir
from os.path import dirname, join, isfile, isdir, splitext, isabs
from xml.dom.minidom import parse## remove FIXME
from subprocess import Popen

from scal2.utils import NullObj, toStr, cleanCacheDict, escape
from scal2.os_utils import makeDir
from scal2.path import *

from scal2.cal_types import calTypes

from scal2 import locale_man
from scal2.locale_man import tr as _

from scal2 import core
from scal2.core import APP_NAME, myRaise, myRaiseTback, getMonthLen, osName

from scal2 import event_lib

uiName = ''
null = NullObj()

def parseDroppedDate(text):
    part = text.split('/')
    if len(part)==3:
        try:
            part[0] = int(part[0])
            part[1] = int(part[1])
            part[2] = int(part[2])
        except:
            myRaise(__file__)
            return None
        minMax = ((1300, 2100), (1, 12), (1, 31))
        formats=(
                [0, 1, 2],
                [1, 2, 0],
                [2, 1, 0],
        )
        for format in formats:
            for i in range(3):
                valid = True
                f = format[i]
                if not (minMax[f][0] <= part[i] <= minMax[f][1]):
                    valid = False
                    #print 'format %s was not valid, part[%s]=%s'%(format, i, part[i])
                    break
            if valid:
                year = part[format.index(0)] ## "format" must be list because of method "index"
                month = part[format.index(1)]
                day = part[format.index(2)]
                break
        if not valid:
            return None
    else:
        return None
    ##??????????? when drag from a persian GtkCalendar with format %y/%m/%d
    #if year < 100:
    #    year += 2000
    return (year, month, day)

def dictsTupleConfStr(data):
    n = len(data)
    st = '('
    for i in range(n):
        d = data[i].copy()
        st += '\n{'
        for k in d.keys():
            v = d[k]
            if type(k)==str:
                ks = '\'%s\''%k
            else:
                ks = str(k)
            if type(v)==str:
                vs = '\'%s\''%v
            else:
                vs = str(v)
            st += '%s:%s, '%(ks,vs)
        if i==n-1:
            st = st[:-2] + '})'
        else:
            st = st[:-2] + '},'
    return st

def saveLiveConf():
    text = ''
    for key in (
        'winX', 'winY', 'winWidth',
        'winKeepAbove', 'winSticky',
        'pluginsTextIsExpanded', 'eventViewMaxHeight', 'bgColor',
        'eventManShowDescription',## FIXME
    ):
        text += '%s=%r\n'%(key, eval(key))
    open(confPathLive, 'w').write(text)

def saveLiveConfLoop():
    tm = time()
    if tm-lastLiveConfChangeTime > saveLiveConfDelay:
        saveLiveConf()
        return False ## Finish loop
    return True ## Continue loop

def checkNeedRestart():
    for key in needRestartPref.keys():
        if needRestartPref[key] != eval(key):
            print '"%s", "%s", "%s"'%(key, needRestartPref[key], eval(key))
            return True
    return False

getPywPath = lambda: join(rootDir, APP_NAME + ('-qt' if uiName=='qt' else '') + '.pyw')

def winMakeShortcut(srcPath, dstPath, iconPath=None):
    from win32com.client import Dispatch
    shell = Dispatch('WScript.Shell')
    shortcut = shell.CreateShortCut(dstPath)
    shortcut.Targetpath = srcPath
    #shortcut.WorkingDirectory = ...
    shortcut.save()



def addStartup():
    if osName=='win':
        makeDir(winStartupDir)
        #fname = APP_NAME + ('-qt' if uiName=='qt' else '') + '.pyw'
        fname = core.COMMAND + '.pyw'
        fpath = join(rootDir, fname)
        #open(winStartupFile, 'w').write('execfile(%r, {"__file__":%r})'%(fpath, fpath))
        try:
            winMakeShortcut(fpath, winStartupFile)
        except:
            return False
        else:
            return True
    elif isdir('%s/.config'%homeDir):## osName in ('linux', 'mac') ## maybe Gnome/KDE on Solaris, *BSD, ...
        text = '''[Desktop Entry]
Type=Application
Name=%s %s
Icon=%s
Exec=%s'''%(core.APP_DESC, core.VERSION, APP_NAME, core.COMMAND)## double quotes needed when the exec path has space
        makeDir(comDeskDir)
        try:
            fp = open(comDesk, 'w')
        except:
            core.myRaise(__file__)
            return False
        else:
            fp.write(text)
            return True
    elif osName=='mac':## FIXME
        pass
    return False

def removeStartup():
    if osName=='win':## FIXME
        if isfile(winStartupFile):
            os.remove(winStartupFile)
    elif isfile(comDesk):
        os.remove(comDesk)

def checkStartup():
    if osName=='win':
        return isfile(winStartupFile)
    elif isfile(comDesk):
        return True
    return False

def dayOpenEvolution(arg=None):
    ##y, m, d = core.jd_to(cell.jd-1, core.DATE_GREG) ## in gnome-cal opens prev day! why??
    y, m, d = cell.dates[core.DATE_GREG]
    Popen('LANG=en_US.UTF-8 evolution calendar:///?startdate=%.4d%.2d%.2d'%(y, m, d), shell=True)## FIXME
    ## 'calendar:///?startdate=%.4d%.2d%.2dT120000Z'%(y, m, d)
    ## What "Time" pass to evolution? like gnome-clock: T193000Z (19:30:00) / Or ignore "Time"
    ## evolution calendar:///?startdate=$(date +"%Y%m%dT%H%M%SZ")

def dayOpenSunbird(arg=None):
    ## does not work on latest version of Sunbird ## FIXME
    ## and Sunbird seems to be a dead project
    ## Opens previous day in older version
    y, m, d = cell.dates[core.DATE_GREG]
    Popen('LANG=en_US.UTF-8 sunbird -showdate %.4d/%.2d/%.2d'%(y, m, d), shell=True)

## How do this with KOrginizer? FIXME

#######################################################################


class Cell:## status and information of a cell
    def __init__(self, jd):
        self.eventsData = []
        self.eventsDataIsSet = False
        self.pluginsText = ''
        ###
        self.jd = jd
        date = core.jd_to(jd, core.primaryMode)
        self.year, self.month, self.day = date
        self.weekDay = core.jwday(jd)
        self.weekNum = core.getWeekNumber(self.year, self.month, self.day)
        self.holiday = (self.weekDay in core.holidayWeekDays)
        ###################
        self.dates = []
        for mode in range(len(calTypes)):
            if mode==core.primaryMode:
                self.dates.append((self.year, self.month, self.day))
            else:
                self.dates.append(core.jd_to(jd, mode))
        ###################
        for k in core.plugIndex:
            plug = core.allPlugList[k]
            if plug.enable:
                try:
                    plug.update_cell(self)
                except:
                    myRaiseTback()
        ###################
        self.eventsData = event_lib.getDayOccurrenceData(jd, eventGroups)
    def format(self, binFmt, mode=None, tm=null):## FIXME
        if mode is None:
            mode = core.primaryMode
        pyFmt, funcs = binFmt
        return pyFmt%tuple(f(self, mode, tm) for f in funcs)
    def inSameMonth(self, other):
        return self.dates[core.primaryMode][:2] == other.dates[core.primaryMode][:2]
    def getEventIcons(self):
        iconList = []
        for item in self.eventsData:
            icon = item['icon']
            if icon and not icon in iconList:
                iconList.append(icon)
        return iconList
    def getEventText(self, showDesc=True, colorizeFunc=None, xmlEscape=False):
        lines = []
        for item in self.eventsData:
            line = ''.join(item['text']) if showDesc else item['text'][0]
            if xmlEscape:
               line = escape(line)
            if item['time']:
                line = item['time'] + ' ' + line
            if colorizeFunc:
                line = colorizeFunc(line, item['color'])
            lines.append(line)
        return '\n'.join(lines)


class CellCache:
    def __init__(self):
        self.jdCells = {} ## a mapping from julan_day to Cell instance
        self.plugins = {}
        self.weekEvents = {}
    def clear(self):
        global cell, todayCell
        self.jdCells = {}
        self.weekEvents = {}
        cell = self.getCell(cell.jd)
        todayCell = self.getCell(todayCell.jd)
    def registerPlugin(self, name, setParamsCallable, getCellGroupCallable):
        """
            setParamsCallable(cell): cell.attr1 = value1 ....
            getCellGroupCallable(cellCache, *args): return cell_group
                call cellCache.getCell(jd) inside getCellGroupFunc
        """
        self.plugins[name] = (
            setParamsCallable,
            getCellGroupCallable,
        )
        for localCell in self.jdCells.values():
            setParamsCallable(localCell)
    def getCell(self, jd):
        try:
            return self.jdCells[jd]
        except KeyError:
            return self.buildCell(jd)
    def getTmpCell(self, jd):## don't keep, no eventsData, no plugin params
        try:
            return self.jdCells[jd]
        except KeyError:
            return Cell(jd)
    getCellByDate = lambda self, y, m, d: self.getCell(core.to_jd(y, m, d, core.primaryMode))
    getTodayCell = lambda self: self.getCell(core.getCurrentJd())
    def buildCell(self, jd):
        localCell = Cell(jd)
        for pluginData in self.plugins.values():
            pluginData[0](localCell)
        self.jdCells[jd] = localCell
        cleanCacheDict(self.jdCells, maxDayCacheSize, jd)
        return localCell
    getCellGroup = lambda self, pluginName, *args:\
        self.plugins[pluginName][1](self, *args)
    def getWeekData(self, absWeekNumber):
        cells = self.getCellGroup('WeekCal', absWeekNumber)
        try:
            wEventData = self.weekEvents[absWeekNumber]
        except KeyError:
            wEventData = event_lib.getWeekOccurrenceData(absWeekNumber, eventGroups)
            cleanCacheDict(self.weekEvents, maxWeekCacheSize, absWeekNumber)
            self.weekEvents[absWeekNumber] = wEventData
        return (cells, wEventData)
    #def getMonthData(self, year, month):## needed? FIXME


def changeDate(year, month, day, mode=None):
    global cell
    if mode is None:
        mode = core.primaryMode
    cell = cellCache.getCell(core.to_jd(year, month, day, mode))

def gotoJd(jd):
    global cell
    cell = cellCache.getCell(jd)

def jdPlus(plus=1):
    global cell
    cell = cellCache.getCell(cell.jd + plus)

def monthPlus(plus=1):
    global cell
    year, month = core.monthPlus(cell.year, cell.month, plus)
    day = min(cell.day, getMonthLen(year, month, core.primaryMode))
    cell = cellCache.getCellByDate(year, month, day)

def yearPlus(plus=1):
    global cell
    year = cell.year + plus
    month = cell.month
    day = min(cell.day, getMonthLen(year, month, core.primaryMode))
    cell = cellCache.getCellByDate(year, month, day)

getFont = lambda: list(fontCustom if fontCustomEnable else fontDefault)

def getFontSmall():
    name, bold, underline, size = getFont()
    return (name, bold, underline, int(size*0.6))

def initFonts(fontDefaultNew):
    global fontDefault, fontCustom, mcalTypeParams
    fontDefault = fontDefaultNew
    if not fontCustom:
        fontCustom = fontDefault
    ###
    if mcalTypeParams[0]['font']==None:
        mcalTypeParams[0]['font'] = getFont()
    ###
    smallFont = getFontSmall()
    for item in mcalTypeParams[1:]:
        if item['font']==None:
            item['font'] = smallFont[:]


def getHolidaysJdList(startJd, endJd):
    jdList = []
    for jd in range(startJd, endJd):
        tmpCell = cellCache.getTmpCell(jd)
        if tmpCell.holiday:
            jdList.append(jd)
    return jdList


######################################################################

def checkMainWinItems():
    global mainWinItems
    #print mainWinItems
    ## cleaning and updating mainWinItems
    names = set([name for (name, i) in mainWinItems])
    defaultNames = set([name for (name, i) in mainWinItemsDefault])
    #print mainWinItems
    #print sorted(list(names))
    #print sorted(list(defaultNames))
    #####
    ## removing items that are no longer supported
    mainWinItems, mainWinItemsTmp = [], mainWinItems
    for name, enable in mainWinItemsTmp:
        if name in defaultNames:
            mainWinItems.append((name, enable))
    #####
    ## adding items newly added in this version, this is for user's convenience
    newNames = defaultNames.difference(names)
    #print 'mainWinItems: newNames =', newNames
    ##
    name = 'winContronller'
    if name in newNames:
        mainWinItems.insert(0, (name, True))
        newNames.remove(name)
    ##
    for name in newNames:
        mainWinItems.append((name, False))## FIXME


def deleteEventGroup(group):
    eventGroups.moveToTrash(group, eventTrash)

def moveEventToTrash(group, event):
    eventIndex = group.remove(event)
    group.save()
    eventTrash.insert(0, event)## or append? FIXME
    eventTrash.save()
    return eventIndex

def moveEventToTrashFromOutside(group, event):
    global trashedEvents
    eventIndex = moveEventToTrash(group, event)
    trashedEvents.append((group.id, event.id, eventIndex))

getEvent = lambda groupId, eventId: eventGroups[groupId][eventId]

def duplicateGroupTitle(group):
    title = toStr(group.title)
    titleList = [toStr(g.title) for g in eventGroups]
    parts = title.split('#')
    try:
        index = int(parts[-1])
        title = '#'.join(parts[:-1])
    except:
        #myRaise()
        index = 1
    index += 1
    while True:
        newTitle = title + '#%d'%index
        if newTitle not in titleList:
            group.title = newTitle
            return
        index += 1

def init():
    core.init()
    #### Load accounts, groups and trash? FIXME
    eventAccounts.load()
    eventGroups.load()
    eventTrash.load()
    ####
    event_lib.saveLastIds()


######################################################################
shownCals = [] ## FIXME
mcalTypeParams = [
    {'pos':(0, -2), 'font':None, 'color':(220, 220, 220)},
    {'pos':(18, 5), 'font':None, 'color':(165, 255, 114)},
    {'pos':(-18, 4), 'font':None, 'color':(0, 200, 205)},
]

wcalTypeParams = [
    {'font':None},
    {'font':None},
    {'font':None},
]



def getMcalMinorTypeParams():
    ls = []
    for i, mode in enumerate(calTypes.active):
        try:
            params = mcalTypeParams[i]
        except IndexError:
            break
        else:
            ls.append((mode, params))
    return ls

################################
tagsDir = join(pixDir, 'event')

class TagIconItem:
    def __init__(self, name, desc='', icon='', eventTypes=()):
        self.name = name
        if not desc:
            desc = name.capitalize()
        self.desc = _(desc)
        if icon:
            if not isabs(icon):
                icon = join(tagsDir, icon)
        else:
            iconTmp = join(tagsDir, name)+'.png'
            if isfile(iconTmp):
                icon = iconTmp
        self.icon = icon
        self.eventTypes = eventTypes
        self.usage = 0
    __repr__ = lambda self: 'TagIconItem(%r, desc=%r, icon=%r, eventTypes=%r)'%(self.name, self.desc, self.icon, self.eventTypes)


eventTags = (
    TagIconItem('birthday', eventTypes=('yearly',)),
    TagIconItem('marriage', desc=_('Marriage'), eventTypes=('yearly',)),
    TagIconItem('obituary', eventTypes=('yearly',)),
    TagIconItem('note', eventTypes=('dailyNote',)),
    TagIconItem('task', eventTypes=('task',)),
    TagIconItem('alarm'),
    TagIconItem('business'),
    TagIconItem('personal'),
    TagIconItem('favorite'),
    TagIconItem('important'),
    TagIconItem('appointment', eventTypes=('task',)),
    TagIconItem('meeting', eventTypes=('task',)),
    TagIconItem('phone_call', desc='Phone Call', eventTypes=('task',)),
    TagIconItem('university', eventTypes=('task',)),## FIXME
    TagIconItem('education'),
    TagIconItem('holiday'),
    TagIconItem('travel'),
)

getEventTagsDict = lambda: dict([(tagObj.name, tagObj) for tagObj in eventTags])
eventTagsDesc = dict([(t.name, t.desc) for t in eventTags])

###################
for fname in os.listdir(join(srcDir, 'accounts')):
    name, ext = splitext(fname)
    if ext == '.py' and name != '__init__':
        try:
            __import__('scal2.accounts.%s'%name)
        except:
            core.myRaiseTback()
#print 'accounts', event_lib.classes.account.names
###########
eventAccounts = event_lib.EventAccountsHolder()
eventGroups = event_lib.EventGroupsHolder()
eventTrash = event_lib.EventTrash()



#try:
#    event_lib.checkAndStartDaemon()## FIXME here or in ui_*/event/main.py
#except:
#    print 'Error while starting daemon'
#    myRaise()


newGroups = []## list of groupId's
changedGroups = []## list of groupId's
newEvents = []## a list of (groupId, eventId) 's
changedEvents = []## a list of (groupId, eventId) 's
trashedEvents = []## a list of (groupId, eventId) 's



#def updateEventTagsUsage():## FIXME where to use?
#    tagsDict = getEventTagsDict()
#    for tagObj in eventTags:
#        tagObj.usage = 0
#    for event in events:## FIXME
#        for tag in event.tags:
#            try:
#                tagsDict[tag].usage += 1
#            except KeyError:
#                pass


###################
core.loadAllPlugins()## FIXME
###################
## BUILD CACHE AFTER SETTING core.primaryMode
maxDayCacheSize = 100 ## maximum size of cellCache (days number)
maxWeekCacheSize = 12

cellCache = CellCache()
todayCell = cell = cellCache.getTodayCell() ## FIXME
###########################
autoLocale = True
logo = '%s/starcal2.png'%pixDir
comDeskDir = '%s/.config/autostart'%homeDir
comDesk = '%s/%s.desktop'%(comDeskDir, APP_NAME)
#kdeDesk='%s/.kde/Autostart/%s.desktop'%(homeDir, APP_NAME)
###########################
#themeDir = join(rootDir, 'themes')
#theme = None
########################### Options ###########################
winWidth = 480
mcalHeight = 250
winTaskbar = False
useAppIndicator = True
showDigClockTb = True ## On Toolbar ## FIXME
showDigClockTr = True ## On Tray
####
toolbarIconSizePixel = 24 ## used in pyqt ui
####
bgColor = (26, 0, 1, 255)## or None
bgUseDesk = False
borderColor = (123, 40, 0, 255)
borderTextColor = (255, 255, 255, 255) ## text of weekDays and weekNumbers
#menuBgColor = borderColor ##???????????????
textColor = (255, 255, 255, 255)
menuTextColor = None##borderTextColor##???????????????
holidayColor = (255, 160, 0, 255)
inactiveColor = (255, 255, 255, 115)
todayCellColor  = (0, 255, 0, 50)
##########
cursorOutColor = (213, 207, 0, 255)
cursorBgColor = (41, 41, 41, 255)
cursorDiaFactor = 0.15
cursorRoundingFactor = 0.50
mcalGrid = False
mcalGridColor = (255, 252, 0, 82)
##########
mcalLeftMargin = 30
mcalTopMargin = 30
####################
wcalHeight = 200
wcalTextSizeScale = 0.6 ## between 0 and 1
#wcalTextColor = (255, 255, 255) ## FIXME
wcalPadding = 10
wcalGrid = False
wcalGridColor = (255, 252, 0, 82)

wcal_weekDays_width = 80
wcal_eventsCount_width = 80
wcal_eventsCount_expand = False
wcal_eventsIcon_width = 50
wcal_eventsText_showDesc = True
wcal_eventsText_colorize = True
wcal_daysOfMonth_width = 30
wcal_daysOfMonth_dir = 'ltr' ## ltr/rtl/auto



##### just for compatibility
try:
    wcal_weekDays_width = wcalWeekDaysWidth
except NameError:
    pass
try:
    wcal_eventsCount_width = wcalEventsCountColWidth
except NameError:
    pass
try:
    wcal_eventsCount_expand = wcalEventsCountExpand
except NameError:
    pass
try:
    wcal_eventsIcon_width = wcalEventsIconColWidth
except NameError:
    pass
try:
    wcal_eventsText_showDesc = wcalEventsTextShowDesc
except NameError:
    pass
try:
    wcal_eventsText_colorize = wcalEventsTextColorize
except NameError:
    pass
try:
    wcal_daysOfMonth_width = wcalDaysOfMonthColWidth
except NameError:
    pass
try:
    wcal_daysOfMonth_dir = wcalDaysOfMonthColDir
except NameError:
    pass

####################
boldYmLabel = True ## apply in Pref FIXME
showYmArrows = True ## apply in Pref FIXME
labelMenuDelay = 0.1 ## delay for shift up/down items of menu for right click on YearLabel
####################
trayImage = join(pixDir, 'tray-green.png')
trayImageHoli = join(pixDir, 'tray-red.png')
trayBgColor = (-1, -1, -1, 0) ## how to get bg color of gnome panel ????????????
trayTextColor = (0, 0, 0)
traySize = 22
trayFont = None
trayY0 = None

'''
trayImage = join(pixDir, 'tray-dark.png')
trayImageHoli = join(pixDir, 'tray-dark.png')
trayBgColor = (0, 0, 0, 0) ## how to get bg color of gnome panel ????????????
trayTextColor = (255, 255, 255)
traySize = 21
trayFont = None
trayY0 = 4
'''

####################
menuActiveLabelColor = "#ff0000"
pluginsTextTray = False
pluginsTextInsideExpander = True
pluginsTextIsExpanded = True ## affect only if pluginsTextInsideExpander
eventViewMaxHeight = 200
####################
dragGetMode = core.DATE_GREG  ## apply in Pref FIXME
#dragGetDateFormat = '%Y/%m/%d'
dragRecMode = core.DATE_GREG  ## apply in Pref FIXME
####################
monthRMenuNum = True
#monthRMenu
prefPagesOrder = tuple(range(5))
winControllerButtons = (
    ('sep', True),
    ('min', True),
    ('max', False),
    ('close', True),
    ('sep', False),
    ('sep', False),
    ('sep', False),
)
winControllerSpacing = 0
####################
winKeepAbove = True
winSticky = True
winX = 0
winY = 0
###
fontDefault = ['Sans', False, False, 12]
fontCustom = None
fontCustomEnable = False
#####################
showMain = True ## Show main window on start (or only goto tray)
#####################
mainWinItems = (
    ('winContronller', True),
    ('toolbar', True),
    ('labelBox', True),
    ('monthCal', False),
    ('weekCal', True),
    ('statusBar', True),
    ('pluginsText', True),
    ('eventDayView', True),
)

mainWinItemsDefault = mainWinItems[:]

wcalItems = (
    ('toolbar', True),
    ('weekDays', True),
    ('pluginsText', True),
    ('eventsIcon', True),
    ('eventsText', True),
    ('daysOfMonth', True),
)

wcalItemsDefault = wcalItems[:]

####################

ntpServers = (
    'pool.ntp.org',
    'asia.pool.ntp.org',
    'europe.pool.ntp.org',
    'north-america.pool.ntp.org',
    'oceania.pool.ntp.org',
    'south-america.pool.ntp.org',
    'ntp.ubuntu.com',
)


#####################
#dailyNoteChDateOnEdit = True ## change date of a dailyNoteEvent when editing it
eventManShowDescription = True
#####################
focusTime = 0
lastLiveConfChangeTime = 0


saveLiveConfDelay = 0.5 ## seconds
timeout_initial = 200
timeout_repeat = 50


def updateFocusTime(*args):
    global focusTime
    focusTime = time()


sysConfPath = join(sysConfDir, 'ui.conf') ## also includes LIVE config
if os.path.isfile(sysConfPath):
    try:
        exec(open(sysConfPath).read())
    except:
        myRaise(__file__)

confPath = join(confDir, 'ui.conf')
if os.path.isfile(confPath):
    try:
        exec(open(confPath).read())
    except:
        myRaise(__file__)

confPathLive = join(confDir, 'ui-live.conf')
if os.path.isfile(confPathLive):
    try:
        exec(open(confPathLive).read())
    except:
        myRaise(__file__)
################################

try:
    mcalGridColor = wcalGridColor = gridColor
except NameError:
    pass

try:
    fontUseDefault
except NameError:
    pass
else:
    fontCustomEnable = not fontUseDefault ## for compatibilty
    del fontUseDefault

try:
    version
except NameError:
    prefVersion = ''
else:
    prefVersion = version
    del version


if shownCals:## just for compatibility
    mcalTypeParams = []
    wcalTypeParams = []
    calTypes.activeNames = []
    for item in shownCals:
        mcalTypeParams.append({
            'pos': (item['x'], item['y']),
            'font': list(item['font']),
            'color': item['color'],
        })
        wcalTypeParams.append({
            'font': list(item['font']),
        })
        calTypes.activeNames.append(calTypes.names[item['mode']])
    core.primaryMode = calTypes.update()

## FIXME
#newPrimaryMode = shownCals[0]['mode']
#if newPrimaryMode!= core.primaryMode:
#    core.primaryMode = newPrimaryMode
#    cellCache.clear()
#del newPrimaryMode

## monthcal:


needRestartPref = {} ### Right place ????????
for key in (
    'locale_man.lang',
    'locale_man.enableNumLocale',
    'winTaskbar',
    'showYmArrows',
    'useAppIndicator',
):
    needRestartPref[key] = eval(key)

if menuTextColor is None:
    menuTextColor = borderTextColor

##################################

## move to gtk_ud ? FIXME
mainWin = None
prefDialog = None
eventManDialog = None
timeLineWin = None
weekCalWin = None






