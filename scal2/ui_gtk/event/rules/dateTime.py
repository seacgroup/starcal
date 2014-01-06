#!/usr/bin/env python
# -*- coding: utf-8 -*-
from scal2 import core
from scal2.locale_man import tr as _
from scal2 import event_lib

from scal2.ui_gtk import *
from scal2.ui_gtk.mywidgets.multi_spin_button import DateButton, TimeButton


class RuleWidget(gtk.HBox):
    def __init__(self, rule):
        self.rule = rule
        ###
        gtk.ComboBox.__init__(self)
        ###
        self.dateInput = DateButton()
        pack(self, self.dateInput)
        ###
        pack(self, gtk.Label('   '+_('Time')))
        self.timeInput = TimeButton()
        pack(self, self.timeInput)
    def updateWidget(self):
        self.dateInput.set_value(self.rule.date)
        self.timeInput.set_value(self.rule.time)
    def updateVars(self):
        self.rule.date = self.dateInput.get_value()
        self.rule.time = self.timeInput.get_value()
    def changeMode(self, mode):
        curMode = self.rule.getMode()
        if mode!=curMode:
            y, m, d = self.dateInput.get_value()
            self.dateInput.set_value(core.convert(y, m, d, curMode, mode))
