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
from qgis.PyQt.QtCore import QCoreApplication, QTranslator, QObject, QLocale, QSettings
from qgis.core import QgsProject, QgsRelation, QgsFeature, QgsEditorWidgetSetup, QgsGeometry
from qgis.gui import QgsGui, QgisInterface, QgsMapLayerAction

DEBUG = True


class RelationBatchInsertPlugin(QObject):

    plugin_name = "&Relation Batch Insert"

    def __init__(self, iface: QgisInterface):
        QObject.__init__(self)
        self.iface = iface
        self.mapLayerActions = {}

        QgsProject.instance().relationManager().changed.connect(self.load_relations)
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

    def unload_relations(self):
        for relation_id in self.mapLayerActions.keys():
            QgsGui.instance().mapLayerActionRegistry().removeMapLayerAction(self.mapLayerActions[relation_id])
        self.mapLayerActions = {}

    def load_relations(self):
        self.unload_relations()
        for relation in QgsProject.instance().relationManager().relations().values():
            action = QgsMapLayerAction('Add features in referencing layer "{layer}" for "relation "{rel}"'
                                       .format(layer=relation.referencingLayer().name(), rel=relation.name()),
                                       self.iface.mainWindow(),
                                       relation.referencedLayer(),
                                       QgsMapLayerAction.MultipleFeatures)
            if DEBUG:
                print('Adding action for relation "{}" in layer "{}"'.format(relation.name(), relation.referencedLayer().name()))
            QgsGui.instance().mapLayerActionRegistry().addMapLayerAction(action)
            action.triggeredForFeatures.connect(self.action_triggered)
            self.mapLayerActions[relation.id()] = action

    def action_triggered(self, layer, features):
        sender_action = self.sender()
        for relation_id, action in self.mapLayerActions.items():
            if action == sender_action:
                relation = QgsProject.instance().relationManager().relation(relation_id)
                assert layer == relation.referencedLayer()
                self.batch_insert(relation, features)
                return
        assert False

    def batch_insert(self, relation: QgsRelation, features: list):
        """
        :param relation: the relation
        :param features: the list of feature on the referenced layer
        :return:
        """
        layer = relation.referencingLayer()
        if not layer.isEditable():
            self.iface.messageBar().pushMessage('Relation Batch Insert',
                                                self.tr('layer "{}" is not editable'.format(layer.name())))

        if len(features) < 1:
            self.iface.messageBar().pushMessage('Relation Batch Insert',
                                                self.tr('There is no features to batch insert for. Select some'))

        default_values = {}
        orignal_cfg = {}
        first_feature_created = False
        referencing_feature = QgsFeature()

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
                    self.iface.messageBar().pushMessage('Relation Batch Insert',
                                                        self.tr('There was an error while inserting features'))
                # restore widget config of the layer
                for index, cfg in orignal_cfg.items():
                    layer.setEditorWidgetSetup(index, cfg)
                first_feature_created = True
            else:
                layer.addFeature(referencing_feature)

