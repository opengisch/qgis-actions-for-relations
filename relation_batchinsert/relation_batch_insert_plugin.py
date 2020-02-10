# -*- coding: utf-8 -*-
# -----------------------------------------------------------
#
# QGIS Relation Batch Insert Plugin
# Copyright (C) 2020 Denis Rouzaud
#
# licensed under the terms of GNU GPL 2
#
# -----------------------------------------------------------

import os
from qgis.PyQt.QtCore import pyqtSlot, QCoreApplication, QTranslator, QObject, QLocale, QSettings
from qgis.PyQt.QtWidgets import QAction
from qgis.core import QgsProject, QgsRelation, QgsFeature, QgsEditorWidgetSetup, QgsGeometry, QgsMapLayer, Qgis
from qgis.gui import QgsGui, QgisInterface, QgsMapLayerAction

DEBUG = True


class RelationBatchInsertPlugin(QObject):

    plugin_name = "&Relation Batch Insert"

    def __init__(self, iface: QgisInterface):
        QObject.__init__(self)
        self.iface = iface
        self.map_layer_actions = {}
        # context menu entries
        self.menu_actions = []

        QgsProject.instance().relationManager().changed.connect(self.reload_relations)

        self.load_relations()

        # initialize translation
        qgis_locale = QLocale(QSettings().value('locale/userLocale'))
        locale_path = os.path.join(os.path.dirname(__file__), 'i18n')
        self.translator = QTranslator()
        self.translator.load(qgis_locale, 'relation_batchinsert', '_', locale_path)
        QCoreApplication.installTranslator(self.translator)

    def initGui(self):
        pass

    def unload(self):
        self.unload_relations()

    def reload_relations(self):
        self.unload_relations()
        self.load_relations()

    def unload_relations(self):
        for relation_id in self.map_layer_actions.keys():
            # remove general actions
            QgsGui.instance().mapLayerActionRegistry().removeMapLayerAction(self.map_layer_actions[relation_id])
        self.map_layer_actions = {}
        # remove legend context menu entries
        for action in self.menu_actions:
            self.iface.removeCustomActionForLayerType(action)
        self.menu_actions = []

    def load_relations(self):
        self.unload_relations()
        for relation in QgsProject.instance().relationManager().relations().values():
            action = QgsMapLayerAction(
                self.tr('Add features in referencing layer "{layer}" for "relation "{rel}"')
                    .format(layer=relation.referencingLayer().name(), rel=relation.name()),
                self.iface.mainWindow(),
                relation.referencedLayer(),
                QgsMapLayerAction.MultipleFeatures
            )
            action.setData(relation.id())
            if DEBUG:
                print('Adding action for relation "{}" in layer "{}"'.format(relation.name(), relation.referencedLayer().name()))
            QgsGui.instance().mapLayerActionRegistry().addMapLayerAction(action)
            action.triggeredForFeatures.connect(self.map_layer_action_triggered)
            self.map_layer_actions[relation.id()] = action
            # add legend context menu entry
            menu_action = QAction(
                self.tr('Add features in "{referencing}" for the selected features in "{referenced}"')
                    .format(referencing=relation.referencingLayer().name(), referenced=relation.referencedLayer().name()),
                self.iface.mainWindow()
            )
            self.iface.addCustomActionForLayerType(menu_action, None, QgsMapLayer.VectorLayer, False)
            self.iface.addCustomActionForLayer(menu_action, relation.referencedLayer())
            menu_action.setData(relation.id())
            menu_action.triggered.connect(self.context_menu_triggered)
            self.menu_actions.append(menu_action)

    @pyqtSlot()
    def context_menu_triggered(self):
        relation_id = self.sender().data()
        relation = QgsProject.instance().relationManager().relation(relation_id)
        self.batch_insert(relation, relation.referencedLayer().selectedFeatures())

    def map_layer_action_triggered(self, layer, features):
        relation_id = self.sender().data()
        relation = QgsProject.instance().relationManager().relation(relation_id)
        assert layer == relation.referencedLayer()
        self.batch_insert(relation, features)

    def batch_insert(self, relation: QgsRelation, features: list):
        """
        :param relation: the relation
        :param features: the list of feature on the referenced layer
        :return:
        """
        layer = relation.referencingLayer()
        if not layer.isEditable():
            self.iface.messageBar().pushMessage(
                'Relation Batch Insert',
                self.tr('layer "{layer}" is not editable'.format(layer=layer.name())), Qgis.Warning
            )
            return

        if len(features) < 1:
            self.iface.messageBar().pushMessage(
                'Relation Batch Insert',
                self.tr('There is no features to batch insert for. Select some in layer "{layer}" first.'
                        .format(layer=relation.referencedLayer().name())
                        ),
                Qgis.Warning
            )
            return

        default_values = {}
        orignal_cfg = {}
        first_feature_created = False
        referencing_feature = QgsFeature()
        features_written = 0
        ok = True

        for referenced_feature in features:
            # define values for the referencing field over the possible several field pairs
            for referencing_field, referenced_field in relation.fieldPairs().items():
                referencing_field_index = relation.referencingLayer().fields().indexFromName(referencing_field)

                # disabled the widgets for the referenced feature in the form (since it will be replaced)
                if not first_feature_created:
                    default_values[referencing_field_index] = referenced_feature[referenced_field]
                    orignal_cfg[referencing_field_index] = layer.editorWidgetSetup(referencing_field_index)
                    layer.setEditorWidgetSetup(referencing_field_index, QgsEditorWidgetSetup('Hidden', {}))

                else:
                    # it has been created at previous iteration
                    referencing_feature[referencing_field_index] = referenced_feature[referenced_field]

            if not first_feature_created:
                # show form for the feature with disabled widgets for the referencing fields
                ok, referencing_feature = self.iface.vectorLayerTools().addFeature(layer, default_values, QgsGeometry())
                if not ok:
                    break
                # restore widget config of the layer
                for index, cfg in orignal_cfg.items():
                    layer.setEditorWidgetSetup(index, cfg)
                first_feature_created = True
            else:
                ok = layer.addFeature(referencing_feature)
                if not ok:
                    break
            features_written += 1

        if ok:
            self.iface.messageBar().pushMessage(
                'Relation Batch Insert',
                self.tr('{count} features were written to "{layer}"'.format(count=features_written, layer=layer.name()))
            )
        else:
            self.iface.messageBar().pushMessage(
                'Relation Batch Insert',
                self.tr('There was an error while inserting features, '
                        '{count} features were written to "{layer}", '
                        '{expected_count} were expected.'.format(
                    count=features_written, layer=layer.name(), expected_count=len(features))
                ),
                Qgis.Critical
            )

