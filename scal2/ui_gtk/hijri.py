# -*- coding: utf-8 -*-
#
# Copyright (C) 2011 Saeed Rasooli <saeed.gnu@gmail.com> (ilius)
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

## Islamic (Hijri) calendar: http://en.wikipedia.org/wiki/Islamic_calendar

import os
from os.path import isfile

from scal2.cal_types import calTypes
from scal2.cal_types.hijri import monthDb, monthName

from scal2 import core
from scal2.core import jd_to, to_jd
from scal2.locale_man import rtl, dateLocale
from scal2.locale_man import tr as _

from scal2 import ui

import gtk
from gtk import gdk

from scal2.ui_gtk.mywidgets.multi_spin_button import DateButton
from scal2.ui_gtk.utils import dialog_add_button

from scal2.ui_gtk import gtk_ud as ud

hijriMode = calTypes.names.index('hijri')

def getCurrentYm():
    y, m, d = ui.todayCell.dates[hijriMode]
    return y*12 + m-1

class EditDbDialog(gtk.Dialog):
    def __init__(self):## parent FIXME
        gtk.Dialog.__init__(self)
        self.set_title(_('Tune Hijri Monthes'))
        self.connect('delete-event', self.onDeleteEvent)
        ############
        self.altMode = 0
        self.altModeDesc = 'Gregorian'
        ############
        hbox = gtk.HBox()
        self.topLabel = gtk.Label()
        hbox.pack_start(self.topLabel, 0, 0)
        self.startDateInput = DateButton()
        self.startDateInput.set_editable(False)## FIXME
        self.startDateInput.connect('changed', lambda widget: self.updateEndDates())
        hbox.pack_start(self.startDateInput, 0, 0)
        self.vbox.pack_start(hbox, 0, 0)
        ############################
        treev = gtk.TreeView()
        trees = gtk.ListStore(int, str, str, int, str)## ym, yearShown, monthShown, monthLenCombo, endDateShown
        treev.set_model(trees)
        #treev.connect('cursor-changed', self.plugTreevCursorChanged)
        #treev.connect('row-activated', self.plugTreevRActivate)
        #treev.connect('button-press-event', self.plugTreevButtonPress)
        ###
        swin = gtk.ScrolledWindow()
        swin.add(treev)
        swin.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        ######
        cell = gtk.CellRendererText()
        col = gtk.TreeViewColumn(_('Year'), cell, text=1)
        treev.append_column(col)
        ######
        cell = gtk.CellRendererText()
        col = gtk.TreeViewColumn(_('Month'), cell, text=2)
        treev.append_column(col)
        ######
        cell = gtk.CellRendererCombo()
        mLenModel = gtk.ListStore(int)
        mLenModel.append([29])
        mLenModel.append([30])
        cell.set_property('model', mLenModel)
        #cell.set_property('has-entry', False)
        cell.set_property('editable', True)
        cell.set_property('text-column', 0)
        cell.connect('edited', self.monthLenCellEdited)
        col = gtk.TreeViewColumn(_('Month Length'), cell, text=3)
        treev.append_column(col)
        ######
        cell = gtk.CellRendererText()
        col = gtk.TreeViewColumn(_('End Date'), cell, text=4)
        treev.append_column(col)
        ######
        self.treev = treev
        self.trees = trees
        self.vbox.pack_start(swin, 1, 1)
        ######
        dialog_add_button(self, gtk.STOCK_OK, _('_OK'), gtk.RESPONSE_OK)
        dialog_add_button(self, gtk.STOCK_CANCEL, _('_Cancel'), gtk.RESPONSE_CANCEL)
        ##
        resetB = self.add_button(gtk.STOCK_UNDO, gtk.RESPONSE_NONE)
        resetB.set_label(_('_Reset to Defaults'))
        resetB.set_image(gtk.image_new_from_stock(gtk.STOCK_UNDO, gtk.ICON_SIZE_BUTTON))
        resetB.connect('clicked', self.resetToDefaults)
        ##
        self.connect('response', self.onResponse)
        #print dir(self.get_action_area())
        #self.get_action_area().set_homogeneous(False)
        ######
        self.vbox.show_all()
    def resetToDefaults(self, widget):
        if isfile(monthDb.userDbPath):
            os.remove(monthDb.userDbPath)
        monthDb.load()
        self.updateWidget()
        return True
    def updateWidget(self):
        #for index, module in calTypes.iterIndexModule():
        #    if module.name != 'hijri':
        for mode in calTypes.active:
            modeDesc = calTypes[mode].desc
            if not 'hijri' in modeDesc.lower():
                self.altMode = mode
                self.altModeDesc = modeDesc
                break
        self.topLabel.set_label(_('Start')+': '+dateLocale(*monthDb.startDate)+' '+_('Equals to')+' %s'%_(self.altModeDesc))
        self.startDateInput.set_value(jd_to(monthDb.startJd, self.altMode))
        ###########
        selectYm = getCurrentYm() - 1 ## previous month
        selectIndex = None
        self.trees.clear()
        for index, ym, mLen in monthDb.getMonthLenList():
            if ym == selectYm:
                selectIndex = index
            year, month0 = divmod(ym, 12)
            self.trees.append([
                ym,
                _(year),
                _(monthName[month0]),
                mLen,
                '',
            ])
        self.updateEndDates()
        ########
        if selectIndex is not None:
            self.treev.scroll_to_cell(str(selectIndex))
            self.treev.set_cursor(str(selectIndex))
    def updateEndDates(self):
        y, m, d = self.startDateInput.get_value()
        jd0 = to_jd(y, m, d, self.altMode) - 1
        for row in self.trees:
            mLen = row[3]
            jd0 += mLen
            row[4] = dateLocale(*jd_to(jd0, self.altMode))
    def monthLenCellEdited(self, combo, path_string, new_text):
        editIndex = int(path_string)
        mLen = int(new_text)
        if not mLen in (29, 30):
            return
        mLenPrev = self.trees[editIndex][3]
        delta = mLen - mLenPrev
        if delta == 0:
            return
        n = len(self.trees)
        self.trees[editIndex][3] = mLen
        if delta==1:
            for i in range(editIndex+1, n):
                if self.trees[i][3] == 30:
                    self.trees[i][3] = 29
                    break
        elif delta==-1:
            for i in range(editIndex+1, n):
                if self.trees[i][3] == 29:
                    self.trees[i][3] = 30
                    break
        self.updateEndDates()
    def updateVars(self):
        y, m, d = self.startDateInput.get_value()
        monthDb.endJd = monthDb.startJd = to_jd(y, m, d, self.altMode)
        monthDb.monthLenByYm = {}
        for row in self.trees:
            ym = row[0]
            mLen = row[3]
            monthDb.monthLenByYm[ym] = mLen
            monthDb.endJd += mLen
        monthDb.save()
    def run(self):
        monthDb.load()
        self.updateWidget()
        self.treev.grab_focus()
        gtk.Dialog.run(self)
    def onResponse(self, dialog, response_id):
        if response_id==gtk.RESPONSE_OK:
            self.updateVars()
            self.destroy()
        elif response_id==gtk.RESPONSE_CANCEL:
            self.destroy()
        return True
    def onDeleteEvent(self, dialog, event):
        self.destroy()
        return True

def tuneHijriMonthes(widget=None):
    dialog = EditDbDialog()
    dialog.resize(400, 400)
    dialog.run()

if __name__=='__main__':
    tuneHijriMonthes()


