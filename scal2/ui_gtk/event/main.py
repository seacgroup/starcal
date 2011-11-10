# -*- coding: utf-8 -*-
# 
# Copyright (C) 2009-2011 Saeed Rasooli <saeed.gnu@gmail.com> (ilius)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License,    or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, 
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.    See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program. If not, see <http://www.gnu.org/licenses/gpl.txt>.
# Or on Debian systems, from /usr/share/common-licenses/GPL

import os, sys, shlex
from os.path import join, dirname

from scal2 import core
from scal2.core import pixDir, convert, numLocale, myRaise

from scal2.locale_man import tr as _
from scal2.locale_man import rtl

from scal2 import event_man
#from scal2.event import dateEncode, timeEncode, dateDecode, timeDecode

from scal2 import ui
from scal2.ui_gtk.utils import imageFromFile, pixbufFromFile, rectangleContainsPoint, \
                               labelStockMenuItem, labelImageMenuItem, confirm
from scal2.ui_gtk.color_utils import gdkColorToRgb
from scal2.ui_gtk.drawing import newOutlineSquarePixbuf
#from scal2.ui_gtk.mywidgets.multi_spin_box import DateBox, TimeBox

from scal2.ui_gtk.event.occurrence_view import *

import gtk
from gtk import gdk

#print 'Testing translator', __file__, _('About')


class EventEditorDialog(gtk.Dialog):
    def __init__(self, event=None, eventType='', title=None):## don't give both event a eventType
        gtk.Dialog.__init__(self)
        if title:
            self.set_title(title)
        #self.connect('delete-event', lambda obj, e: self.destroy())
        #self.resize(800, 600)
        ###
        cancelB = self.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
        okB = self.add_button(gtk.STOCK_OK, gtk.RESPONSE_OK)
        if ui.autoLocale:
            cancelB.set_label(_('_Cancel'))
            cancelB.set_image(gtk.image_new_from_stock(gtk.STOCK_CANCEL,gtk.ICON_SIZE_BUTTON))
            okB.set_label(_('_OK'))
            okB.set_image(gtk.image_new_from_stock(gtk.STOCK_OK,gtk.ICON_SIZE_BUTTON))
        self.connect('response', lambda w, e: self.hide())
        #######
        self.event = event
        self.activeEventWidget = None
        #######
        #print 'eventType = %r'%eventType
        if eventType:
            cls = event_man.eventsClassDict[eventType]
            self.event = cls()
            self.activeEventWidget = self.event.makeWidget()
        else:
            hbox = gtk.HBox()
            combo = gtk.combo_box_new_text()
            for cls in event_man.eventsClassList:
                combo.append_text(cls.desc)
            hbox.pack_start(gtk.Label(_('Event Type')), 0, 0)
            hbox.pack_start(combo, 0, 0)
            hbox.pack_start(gtk.Label(''), 1, 1)
            self.vbox.pack_start(hbox, 0, 0)
            ####
            if self.event:
                combo.set_active(event_man.eventsClassNameList.index(self.event.name))
            else:
                combo.set_active(event_man.defaultEventTypeIndex)
                self.event = event_man.eventsClassList[event_man.defaultEventTypeIndex]()
            self.activeEventWidget = self.event.makeWidget()
            combo.connect('changed', self.eventTypeChanged)
            self.comboEventType = combo
        self.vbox.pack_start(self.activeEventWidget, 0, 0)
        self.vbox.show_all()
    def dateModeChanged(self, combo):
        pass
    def eventTypeChanged(self, combo):
        if self.activeEventWidget:
            self.activeEventWidget.destroy()
        event = event_man.eventsClassList[combo.get_active()]()
        if self.event:
            event.copyFrom(self.event)
            event.setId(self.event.eid)
            del self.event
        self.event = event
        self.activeEventWidget = event.makeWidget()
        self.vbox.pack_start(self.activeEventWidget, 0, 0)
        self.activeEventWidget.show_all()
    def run(self):
        if not self.activeEventWidget or not self.event:
            return None
        if gtk.Dialog.run(self)!=gtk.RESPONSE_OK:
            try:
                filesBox = self.activeEventWidget.filesBox
            except AttributeError:
                pass
            else:
                filesBox.removeNewFiles()
            return None
        self.activeEventWidget.updateVars()
        self.destroy()
        return self.event


class GroupEditorDialog(gtk.Dialog):
    def __init__(self, group=None):
        gtk.Dialog.__init__(self)
        self.set_title(_('Edit Group') if group else _('Add Group'))
        #self.connect('delete-event', lambda obj, e: self.destroy())
        #self.resize(800, 600)
        ###
        cancelB = self.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
        okB = self.add_button(gtk.STOCK_OK, gtk.RESPONSE_OK)
        if ui.autoLocale:
            cancelB.set_label(_('_Cancel'))
            cancelB.set_image(gtk.image_new_from_stock(gtk.STOCK_CANCEL,gtk.ICON_SIZE_BUTTON))
            okB.set_label(_('_OK'))
            okB.set_image(gtk.image_new_from_stock(gtk.STOCK_OK,gtk.ICON_SIZE_BUTTON))
        self.connect('response', lambda w, e: self.hide())
        #######
        self._group = group
        self.activeGroupWidget = None
        #######
        hbox = gtk.HBox()
        combo = gtk.combo_box_new_text()
        for cls in event_man.eventGroupsClassList:
            combo.append_text(cls.desc)
        hbox.pack_start(gtk.Label(_('Group Type')), 0, 0)
        hbox.pack_start(combo, 0, 0)
        hbox.pack_start(gtk.Label(''), 1, 1)
        self.vbox.pack_start(hbox, 0, 0)
        ####
        if self._group:
            combo.set_active(event_man.eventGroupsClassNameList.index(self._group.name))
        else:
            combo.set_active(event_man.defaultGroupTypeIndex)
            self._group = event_man.eventGroupsClassList[event_man.defaultGroupTypeIndex]()
        self.activeGroupWidget = self._group.makeWidget()## FIXME
        combo.connect('changed', self.groupTypeChanged)
        self.comboGroupType = combo
        self.vbox.pack_start(self.activeGroupWidget, 0, 0)
        self.vbox.show_all()
    def dateModeChanged(self, combo):
        pass
    def groupTypeChanged(self, combo):
        if self.activeGroupWidget:
            self.activeGroupWidget.destroy()
        group = event_man.eventGroupsClassList[combo.get_active()]()
        if self._group:
            group.copyFrom(self._group)
            group.setId(self._group.gid)
            del self._group
        self._group = group
        self.activeGroupWidget = group.makeWidget()
        self.vbox.pack_start(self.activeGroupWidget, 0, 0)
        self.activeGroupWidget.show_all()
    def run(self):
        if self.activeGroupWidget is None or self._group is None:
            return None
        if gtk.Dialog.run(self)!=gtk.RESPONSE_OK:
            return None
        self.activeGroupWidget.updateVars()
        self.destroy()
        return self._group




class EventManagerDialog(gtk.Dialog):## FIXME
    def __init__(self, mainWin=None):## mainWin is needed? FIXME
        gtk.Dialog.__init__(self)
        self.set_title(_('Event Manager'))
        self.resize(600, 300)
        self.connect('delete-event', self.onDeleteEvent)
        ###
        treeBox = gtk.HBox()
        #####
        self.treeview = gtk.TreeView()
        #self.treeview.set_headers_visible(False)## FIXME
        #self.treeview.get_selection().set_mode(gtk.SELECTION_MULTIPLE)## FIXME
        #self.treeview.set_rubber_banding(gtk.SELECTION_MULTIPLE)## FIXME
        self.treeview.connect('realize', self.onTreeviewRealize)
        self.treeview.connect('cursor-changed', self.treeviewCursorChanged)## FIXME
        self.treeview.connect('button-press-event', self.treeviewButtonPress)
        ###
        swin = gtk.ScrolledWindow()
        swin.add(self.treeview)
        swin.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        treeBox.pack_start(swin, 1, 1)
        self.vbox.pack_start(treeBox)
        #####
        self.treestore = gtk.TreeStore(int, gdk.Pixbuf, str, str)
        ## event: event_id,  event_icon,   event_summary, event_description
        ## group: group_id,  group_pixbuf, group_title,   ?description     ## -group_id-2 ? FIXME
        ## trash: -1,        trash_icon,   _('Trash'),    ''
        self.treeview.set_model(self.treestore)
        ###
        col = gtk.TreeViewColumn()
        cell = gtk.CellRendererPixbuf()
        col.pack_start(cell)
        col.add_attribute(cell, 'pixbuf', 1)
        self.treeview.append_column(col)
        ###
        col = gtk.TreeViewColumn(_('Summary'), gtk.CellRendererText(), text=2)
        col.set_resizable(True)
        self.treeview.append_column(col)
        ###
        col = gtk.TreeViewColumn(_('Description'), gtk.CellRendererText(), text=3)
        self.treeview.append_column(col)
        ###
        #self.treeview.set_search_column(2)## or 3
        ###
        #self.clipboard = gtk.clipboard_get(gtk.gdk.SELECTION_CLIPBOARD)
        #self.clipboard = gtk.clipboard_get()
        self.toPasteEvent = None ## (path, bool move)
        #####
        self.vbox.show_all()
        #self.reloadEvents()## FIXME
    def canPasteToGroup(self, group):
        if self.toPasteEvent is None:
            return False
        ## check event type here? FIXME
        return True
    def openRightClickMenu(self, path, etime=None):
        ## how about multi-selection? FIXME
        ## and Select _All menu item
        #cur = self.treeview.get_cursor()
        #if not cur:
        #    return None
        #(path, col) = cur
        obj_list = self.getObjsByPath(path)
        #print len(obj_list)
        menu = gtk.Menu()
        if len(obj_list)==1:
            group = obj_list[0]
            if group.name == 'trash':
                #print 'right click on trash', group.title
                menu.add(labelStockMenuItem('_Edit', gtk.STOCK_EDIT, self.editTrash))
                menu.add(labelStockMenuItem('_Clear', gtk.STOCK_EDIT, self.clearTrash))
            else:
                #print 'right click on group', group.title
                menu.add(labelStockMenuItem('_Edit', gtk.STOCK_EDIT, self.editGroup, path, group))
                eventTypes = group.acceptsEventTypes
                if eventTypes is None:
                    eventTypes = event_man.eventsClassNameList
                for eventType in eventTypes:
                    if eventType == 'custom':## FIXME
                        eventType = ''
                        desc = _('Event')
                    else:
                        desc = event_man.eventsClassDict[eventType].desc
                    menu.add(labelStockMenuItem(
                        _('_Add ') + ' ' + desc,
                        gtk.STOCK_ADD,
                        self.addEventToGroupFromMenu,
                        path,
                        group,
                        eventType,
                        _('Add') + ' ' + desc,
                    ))
                pasteItem = labelStockMenuItem('_Paste Event', gtk.STOCK_PASTE, self.pasteEventIntoGroup, path)
                pasteItem.set_sensitive(self.canPasteToGroup(group))
                menu.add(pasteItem)
                ##
                menu.add(gtk.SeparatorMenuItem())
                menu.add(labelStockMenuItem('_Add New Group', gtk.STOCK_NEW, self.addGroupAfterGroup, path))
                menu.add(gtk.SeparatorMenuItem())
                menu.add(labelStockMenuItem('_Delete Group', gtk.STOCK_NEW, self.deleteGroup, path))
                ##
                menu.add(labelStockMenuItem('Move _Up', gtk.STOCK_EDIT, self.moveGroupUp, group))
                menu.add(labelStockMenuItem('Move _Down', gtk.STOCK_EDIT, self.moveGroupDown, group))
                for (actionName, actionFuncName) in group.actions:
                    menu.add(labelStockMenuItem(_(actionName), None, self.groupActionClicked, group, actionFuncName))
        elif len(obj_list)==2:
            (group, event) = obj_list
            #print 'right click on event', event.summary
            if group.name != 'trash':
                menu.add(labelStockMenuItem('_Edit', gtk.STOCK_EDIT, self.editEventFromMenu))
                menu.add(gtk.SeparatorMenuItem())
            menu.add(labelStockMenuItem('Cu_t', gtk.STOCK_CUT, self.cutEvent, path))
            menu.add(labelStockMenuItem('_Copy', gtk.STOCK_COPY, self.copyEvent, path))
            ##
            if group.name == 'trash':
                menu.add(gtk.SeparatorMenuItem())
                menu.add(labelStockMenuItem('_Delete', gtk.STOCK_DELETE, self.deleteEventFromTrash, path))
            else:
                pasteItem = labelStockMenuItem('_Paste', gtk.STOCK_PASTE, self.pasteEventAfterEvent, path)
                pasteItem.set_sensitive(self.canPasteToGroup(group))
                menu.add(pasteItem)
                ##
                menu.add(gtk.SeparatorMenuItem())
                menu.add(labelImageMenuItem('_Move to Trash', ui.eventTrash.icon, self.moveEventToTrash, path))
        else:
            return
        menu.show_all()
        if etime is None:
            pass ## FIXME
        menu.popup(None, None, None, 3, etime)
    def onTreeviewRealize(self, event):
        self.reloadEvents()## FIXME
    getRowBgColor = lambda self: gdkColorToRgb(self.treeview.style.base[gtk.STATE_NORMAL])## bg color of non-selected rows
    getEventRow = lambda self, event: (
        event.eid,
        pixbufFromFile(event.icon),
        event.summary,
        event.description,
    )
    getGroupRow = lambda self, group, rowBgColor: (
        group.gid,
        newOutlineSquarePixbuf(
            group.color,
            20,
            0 if group.enable else 15,
            rowBgColor,
        ),
        group.title,
        '',
    )
    def reloadEvents(self):
        self.treestore.clear()
        rowBgColor = self.getRowBgColor()
        for group in ui.eventGroups:
            groupIter = self.treestore.append(None, self.getGroupRow(group, rowBgColor))
            for event in group:
                self.treestore.append(groupIter, self.getEventRow(event))
        self.trashIter = self.treestore.append(None, (
            -1,
            pixbufFromFile(ui.eventTrash.icon),
            ui.eventTrash.title,
            '',
        ))
        for event in ui.eventTrash:
            self.treestore.append(self.trashIter, self.getEventRow(event))
        self.treeviewCursorChanged()
    def onDeleteEvent(self, obj, event):
        self.hide()
        return True
    def getObjsByPath(self, path):
        obj_list = []
        for i in range(len(path)):
            it = self.treestore.get_iter(path[:i+1])
            obj_id = self.treestore.get_value(it, 0)
            if i==0:
                if obj_id==-1:
                    obj_list.append(ui.eventTrash)
                else:
                    obj_list.append(ui.eventGroups[obj_id])
            else:
                obj_list.append(obj_list[i-1].getEvent(obj_id))
        return obj_list
    def treeviewCursorChanged(self, treev=None):
        cur = self.treeview.get_cursor()
        if not cur:
            return
        (path, col) = cur
        ## update eventInfoBox
        return True
    def treeviewButtonPress(self, treev, g_event):
        pos_t = treev.get_path_at_pos(int(g_event.x), int(g_event.y))
        if not pos_t:
            return
        (path, col, xRel, yRel) = pos_t
        if not path:
            return
        if not col:
            return
        rect = treev.get_cell_area(path, col)
        if not rectangleContainsPoint(rect, g_event.x, g_event.y):
            return
        if g_event.button == 1:
            obj_list = self.getObjsByPath(path)
            node_iter = self.treestore.get_iter(path)
            if len(obj_list) == 1:## group, not event
                group = obj_list[0]
                if group.name != 'trash':
                    cell = col.get_cell_renderers()[0]
                    try:
                        cell.get_property('pixbuf')
                    except:
                        pass
                    else:
                        group.enable = not group.enable
                        group.saveConfig()
                        self.treestore.set_value(
                            node_iter,
                            1,
                            newOutlineSquarePixbuf(
                                group.color,
                                20,
                                0 if group.enable else 15,
                                self.getRowBgColor(),
                            ),
                        )
        elif g_event.button == 3:
            self.openRightClickMenu(path, g_event.time)
    def addGroupAfterGroup(self, menu, path):
        (index,) = path
        group = GroupEditorDialog().run()
        if group is None:
            return
        group.saveConfig()
        ui.eventGroups.insert(index+1, group)
        ui.eventGroups.saveConfig()
        afterGroupIter = self.treestore.get_iter(path)
        self.treestore.insert_after(
            #self.treestore.get_iter_root(),## parent
            self.treestore.iter_parent(afterGroupIter),
            afterGroupIter,## sibling
            self.getGroupRow(group, self.getRowBgColor()), ## row
        )
    def editGroup(self, menu, path, group):
        print 'editGroup'
        group = GroupEditorDialog(group).run()
        if group is None:
            return
        group.saveConfig()## FIXME
        #self.reloadEvents()## perfomance FIXME
        groupIter = self.treestore.get_iter(path)
        for i, value in enumerate(self.getGroupRow(group)):
            self.treestore.set_value(
                groupIter,
                i,
                value,
            )
    def deleteGroup(self, menu, path):
        (index,) = path
        (group,) = self.getObjsByPath(path)
        if not confirm(_('Press OK if you are sure to delete group "%s"')%group.title):
            return
        ui.deleteEventGroup(group)
        self.treestore.remove(self.treestore.get_iter(path))
    def addEventToGroupFromMenu(self, menu, path, group, eventType, title):
        event = EventEditorDialog(eventType=eventType, title=title).run()
        if event is None:
            return
        group.append(event)
        self.treestore.append(
            self.treestore.get_iter(path),## parent
            self.getEventRow(event), ## row
        )
    def editTrash(self, menu):
        pass
    def clearTrash(self, menu):
        pass
    def moveGroupUp(self, menu, path):
        pass
    def moveGroupDown(self, menu, path):
        pass
    def groupActionClicked(self, menu, group, actionFuncName):
        getattr(group, actionFuncName)()
    def editEventFromMenu(self, menu):
        pass
    def cutEvent(self, menu, path):
        self.toPasteEvent = (path, True)
    def copyEvent(self, menu, path):
        self.toPasteEvent = (path, False)
    def pasteEventAfterEvent(self, menu, tarPath):## tarPath is a 2-lengthed tuple
        if not self.toPasteEvent:
            return
        (srcPath, move) = self.toPasteEvent
        (srcGroup, srcEvent) = self.getObjsByPath(srcPath)
        (tarGroup, tarEvent) = self.getObjsByPath(tarPath)
        # tarEvent is not used
        ###
        if move:
            srcGroup.excludeEvent(srcEvent.eid)
            srcGroup.saveConfig()
            tarGroup.insert(tarPath[1], srcEvent)
            tarGroup.saveConfig()
            self.treestore.move_after(
                self.treestore.get_iter(srcPath),
                self.treestore.get_iter(tarPath),
            )
        else:
            newEvent = srcEvent.copy()
            newEvent.saveConfig()
            tarGroup.insert(tarPath[1], newEvent)
            tarGroup.saveConfig()
            self.treestore.insert_after(
                self.treestore.get_iter(tarPath[:1]),## parent
                self.treestore.get_iter(tarPath),## sibling
                self.getEventRow(newEvent), ## row
            )
        self.toPasteEvent = None
    def pasteEventIntoGroup(self, menu, tarPath):## tarPath is a 1-lengthed tuple
        if not self.toPasteEvent:
            return
        (srcPath, move) = self.toPasteEvent
        (srcGroup, srcEvent) = self.getObjsByPath(srcPath)
        (tarGroup,) = self.getObjsByPath(tarPath)
        tarGroupIter = self.treestore.get_iter(tarPath)
        ###
        if move:
            srcGroup.excludeEvent(srcEvent.eid)
            srcGroup.saveConfig()
            tarGroup.append(srcEvent)
            tarGroup.saveConfig()
            tarGroupCount = self.treestore.iter_n_children(tarGroupIter)
            self.treestore.move_after(
                self.treestore.get_iter(srcPath),
                self.treestore.get_iter((tarPath[0], tarGroupCount-1)),
            )
        else:
            newEvent = srcEvent.copy()
            newEvent.saveConfig()
            tarGroup.append(newEvent)
            tarGroup.saveConfig()
            self.treestore.append(
                tarGroupIter,## parent
                self.getEventRow(newEvent), ## row
            )
        self.toPasteEvent = None
    def moveEventToTrash(self, menu, path):
        (group, event) = self.getObjsByPath(path)
        group.excludeEvent(event.eid)
        group.saveConfig()
        ui.eventTrash.append(event)
        ui.eventTrash.saveConfig()
        self.treestore.move_before(
            self.treestore.get_iter(path),
            self.treestore.iter_nth_child(self.trashIter, 0),## GtkWarning: Given children are not in the same level
        )
    def deleteEventFromTrash(self, menu, path):
        pass
    #def selectAllEventInGroup(self, menu):## FIXME
    #    pass
    #def selectAllEventInTrash(self, menu):## FIXME
    #    pass




class EventManagerDialog0(gtk.Dialog):## FIXME
    def __init__(self, mainWin=None):## mainWin is needed? FIXME
        gtk.Dialog.__init__(self)
        self.set_title(_('Event Manager'))
        self.resize(600, 300)
        self.connect('delete-event', self.onDeleteEvent)
        ###
        vpan = gtk.VPaned()
        headerBox = gtk.HBox()
        treeBox = gtk.HBox()
        vpan.add1(headerBox)
        vpan.add2(treeBox)
        infoBox = gtk.VBox()
        infoBox.set_border_width(1)
        self.filesVbox = gtk.VBox()
        infoTextvew = gtk.TextView()
        infoTextvew.set_editable(False)
        infoTextvew.set_cursor_visible(False)
        #infoTextvew.set_state(gtk.STATE_ACTIVE)## FIXME
        self.infoText = infoTextvew.get_buffer()
        infoBox.pack_start(infoTextvew, 1, 1)
        #self.infoText = gtk.Label()
        #self.infoText.set_selectable(True)
        #self.infoText.set_line_wrap(True)
        #self.infoText.set_alignment(0, 0.5)
        #infoBox.pack_start(self.infoText, 1, 1)
        #swin = gtk.ScrolledWindow()
        #swin.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        #swin.add_with_viewport(self.infoText)
        #swin.add(self.infoText)
        #infoBox.pack_start(swin, 1, 1)
        #####
        infoBox.pack_start(self.filesVbox, 0, 0)
        headerBox.pack_start(infoBox, 1, 1)
        headerButtonBox = gtk.VButtonBox()
        headerButtonBox.set_layout(gtk.BUTTONBOX_END)
        ####
        addButton = gtk.Button(stock=gtk.STOCK_ADD)
        #addButton = gtk.OptionMenu(stock=gtk.STOCK_ADD)
        #menu = gtk.Menu()
        #menu.set_border_width(0)
        ##for eventType in ('custom', 'yearly', 'dailyNote', 'task'):## FIXME
        #for cls in eventsClassList:## order? FIXME
        #    item = gtk.MenuItem(cls.desc)## ImageMenuItem
        #    #item.set_image(imageFromFile(...))
        #    item.connect('activate', self.addCustomEvent, cls)
        ####
        editButton = gtk.Button(stock=gtk.STOCK_EDIT)
        delButton = gtk.Button(stock=gtk.STOCK_DELETE)
        if ui.autoLocale:
            addButton.set_label(_('_Add'))
            addButton.set_use_underline(True)
            addButton.set_image(gtk.image_new_from_stock(gtk.STOCK_ADD, gtk.ICON_SIZE_BUTTON))
            ##########
            editButton.set_label(_('_Edit'))
            editButton.set_use_underline(True)
            editButton.set_image(gtk.image_new_from_stock(gtk.STOCK_EDIT, gtk.ICON_SIZE_BUTTON))
            ##########
            delButton.set_label(_('_Delete'))
            delButton.set_use_underline(True)
            delButton.set_image(gtk.image_new_from_stock(gtk.STOCK_DELETE, gtk.ICON_SIZE_BUTTON))
        headerButtonBox.add(addButton)
        headerButtonBox.add(editButton)
        headerButtonBox.add(delButton)
        #####
        addButton.connect('clicked', self.addCustomEvent)
        editButton.connect('clicked', self.editClicked)
        delButton.connect('clicked', self.delClicked)
        #####
        headerBox.pack_start(headerButtonBox, 0, 0)
        self.treeview = gtk.TreeView()
        swin = gtk.ScrolledWindow()
        swin.add(self.treeview)
        swin.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        treeBox.pack_start(swin, 1, 1)
        self.vbox.pack_start(vpan)
        #####
        self.treestore = gtk.ListStore(int, gdk.Pixbuf, str, str)## eid, icon, summary, description
        self.treeview.set_model(self.treestore)
        ###      
        col = gtk.TreeViewColumn('', gtk.CellRendererPixbuf(), pixbuf=1)
        col.set_resizable(True)
        self.treeview.append_column(col)
        ###
        col = gtk.TreeViewColumn(_('Summary'), gtk.CellRendererText(), text=2)
        col.set_resizable(True)
        self.treeview.append_column(col)
        self.treeview.set_search_column(1)
        ###
        col = gtk.TreeViewColumn(_('Description'), gtk.CellRendererText(), text=3)
        self.treeview.append_column(col)
        #self.treeview.set_search_column(2)
        ###
        self.treeview.connect('cursor-changed', self.treeviewCursorChanged)
        #####
        self.vbox.show_all()
        self.reloadEvents()
    def onDeleteEvent(self, obj, event):
        self.hide()
        return True
    def reloadEvents(self):
        self.treestore.clear()
        for event in ui.events:
            self.treestore.append((
                event.eid,
                pixbufFromFile(event.icon),
                event.summary,
                event.description,
            ))
        self.treeviewCursorChanged()
    def getSelectedEvent(self):
        cur = self.treeview.get_cursor()[0]
        if not cur:
            return None
        return ui.eventsById[self.treestore[cur[0]][0]]
    def treeviewCursorChanged(self, treev=None):
        event = self.getSelectedEvent()
        self.infoText.set_text(event.getInfo() if event else '')
        for hbox in self.filesVbox.get_children():
            hbox.destroy()
        if event is not None:
            for url, fname in event.getFilesUrls():
                hbox = gtk.HBox()
                hbox.pack_start(gtk.LinkButton(url, fname), 0, 0)
                hbox.pack_start(gtk.Label(''), 1, 1) 
                self.filesVbox.pack_start(hbox, 0, 0)
            self.filesVbox.show_all()
    def addEvent(self, eventType):
        if eventType:
            title = _('Add') + ' ' + event_man.eventsClassDict[eventType].desc
        else:
            title = _('Add') + ' ' + _('Event')
        event = EventEditorDialog(eventType=eventType, title=title).run()
        #print 'event =', event
        if event is not None:
            ui.addEvent(event)
            self.reloadEvents()## perfomance FIXME
    def addCustomEvent(self, obj=None):
        self.addEvent('')
    def addYearlyEvent(self, obj=None):
        self.addEvent('yearly')
    def addDailyNote(self, obj=None):
        self.addEvent('dailyNote')
    def editClicked(self, obj=None):
        event = self.getSelectedEvent()
        if not event:
            return
        event = EventEditorDialog(event=event, title=_('Edit Event')).run()
        #print 'event =', event
        if event is not None:
            event.saveConfig()## FIXME
            self.reloadEvents()## perfomance FIXME
    def delClicked(self, obj=None):
        event = self.getSelectedEvent()
        print 'delClicked', event, bool(event)
        if event is not None:
            ui.deleteEvent(event)
            self.reloadEvents()## perfomance FIXME


def makeWidget(obj):## obj is an instance of Event or EventRule or EventNotifier
    if hasattr(obj, 'WidgetClass'):
        return obj.WidgetClass(obj)
    else:
        return None

##############################################################################





##############################################################################

if rtl:
    gtk.widget_set_default_direction(gtk.TEXT_DIR_RTL)


modPrefix = 'scal2.ui_gtk.event.'

for cls in event_man.eventsClassList:
    try:
        module = __import__(modPrefix + cls.name, fromlist=['EventWidget'])
        cls.WidgetClass = module.EventWidget
    except:
        myRaise()

for cls in event_man.eventRulesClassList:
    try:
        module = __import__(modPrefix + 'rules.' + cls.name, fromlist=['RuleWidget'])
    except:
        myRaise()
        continue
    try:
        cls.WidgetClass = module.RuleWidget
    except AttributeError:
        print 'no class RuleWidget defined in module "%s"'%cls.name

for cls in event_man.eventNotifiersClassList:
    try:
        module = __import__(modPrefix + 'notifiers.' + cls.name, fromlist=['NotifierWidget', 'notify'])
        cls.WidgetClass = module.NotifierWidget
        cls.notify = module.notify
    except:
        myRaise()

for cls in event_man.eventGroupsClassList:
    try:
        module = __import__(modPrefix + 'groups.' + cls.name, fromlist=['GroupWidget'])
    except:
        myRaise()
        continue
    try:
        cls.WidgetClass = module.GroupWidget
    except AttributeError:
        print 'no class GroupWidget defined in module "%s"'%cls.name


event_man.Event.makeWidget = makeWidget
event_man.EventRule.makeWidget = makeWidget
event_man.EventNotifier.makeWidget = makeWidget
event_man.EventGroup.makeWidget = makeWidget

ui.eventGroups.loadConfig()
ui.eventTrash.loadConfig()

def testCustomEventEditor():
    from pprint import pprint, pformat
    dialog = gtk.Dialog()
    #dialog.vbox.pack_start(IconSelectButton('/usr/share/starcal2/pixmaps/starcal2.png'))
    event = event_man.Event(1)
    event.loadConfig()
    widget = event.makeWidget()
    dialog.vbox.pack_start(widget)
    dialog.vbox.show_all()
    dialog.add_button('OK', 0)
    def on_response(d, e):
        widget.updateVars()
        widget.event.saveConfig()
        pprint(widget.event.getData())
    dialog.connect('response', on_response)
    #dialog.run()
    dialog.present()
    gtk.main()

if __name__=='__main__':
    testCustomEventEditor()


