# -*- coding: utf-8 -*-
# -----------------------------------------------------------
#
# QGIS Actions for relations
# Copyright (C) 2020 Denis Rouzaud
#
# licensed under the terms of GNU GPL 2+
#
# -----------------------------------------------------------


from qgis.core import QgsSettingsEntryVariant

from actions_for_relations import SETTINGS_NODE as _node


custom_aggregates = QgsSettingsEntryVariant("custom_aggregates", _node, [])
