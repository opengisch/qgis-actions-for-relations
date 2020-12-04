# -*- coding: utf-8 -*-
# -----------------------------------------------------------
#
# QGIS Actions for relations
# Copyright (C) 2020 Denis Rouzaud
#
# licensed under the terms of GNU GPL 2+
#
# -----------------------------------------------------------


from actions_for_relations.setting_manager import SettingManager, Scope, List

pluginName = "actions_for_relations"


class Settings(SettingManager):
    def __init__(self):
        SettingManager.__init__(self, pluginName)
        self.add_setting(List('custom_aggregates', Scope.Global, []))