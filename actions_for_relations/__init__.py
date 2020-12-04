# -*- coding: utf-8 -*-
# -----------------------------------------------------------
#
# QGIS Relation Batch Insert Plugin
# Copyright (C) 2020 Denis Rouzaud
#
# licensed under the terms of GNU GPL 2
#
# -----------------------------------------------------------


def classFactory(iface):
    """Load plugin.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from actions_for_relations.actions_for_relations_plugin import ActionsForRelationsPlugin
    return ActionsForRelationsPlugin(iface)
