# -*- coding: utf-8 -*-
# -----------------------------------------------------------
#
# QGIS Actions for relations
# Copyright (C) 2020 Denis Rouzaud
#
# licensed under the terms of GNU GPL 2+
#
# -----------------------------------------------------------

import os
from qgis.PyQt.QtCore import pyqtSlot, QCoreApplication, QTranslator, QObject, QLocale, QSettings
from qgis.PyQt.QtWidgets import QAction
from qgis.core import QgsProject, QgsRelation, QgsFeature, QgsEditorWidgetSetup, QgsGeometry, QgsMapLayer, Qgis, QgsVectorLayer
from qgis.gui import QgsGui, QgisInterface, QgsMapLayerAction
from actions_for_relations.core.settings import Settings
from actions_for_relations.core.custom_aggregate import CustomAggregate
from actions_for_relations.gui.aggregates_dialog import AggregatesDialog

DEBUG = True


class ActionsForRelationsPlugin(QObject):

    plugin_name = "&Actions for Relations"

    def __init__(self, iface: QgisInterface):
        QObject.__init__(self)
        self.iface = iface
        self.settings = Settings()
        self.map_layer_actions = []
        # context menu entries
        self.layer_tree_actions = []
        self.menu_action = None
        self.custom_aggregates = []

        for definition in self.settings.value('custom_aggregates'):
            self.custom_aggregates.append(CustomAggregate(definition))

        QgsProject.instance().relationManager().changed.connect(self.reload_relations)

        self.load_relations()

        # initialize translation
        qgis_locale = QLocale(QSettings().value('locale/userLocale'))
        locale_path = os.path.join(os.path.dirname(__file__), 'i18n')
        self.translator = QTranslator()
        self.translator.load(qgis_locale, 'actions_for_relations', '_', locale_path)
        QCoreApplication.installTranslator(self.translator)

    def initGui(self):
        self.menu_action = QAction(self.tr('Set custom aggregate actions'), self.iface.mainWindow())
        self.menu_action.triggered.connect(self.set_aggregates)
        self.iface.addPluginToMenu(self.plugin_name, self.menu_action)

    def unload(self):
        self.unload_relations()
        if self.menu_action:
            self.iface.removePluginMenu(self.plugin_name, self.menu_action)

    def set_aggregates(self):
        dlg = AggregatesDialog(self.custom_aggregates)
        if dlg.exec_():
            self.custom_aggregates = dlg.aggregate_model.custom_aggregates
            self.reload_relations()

    def reload_relations(self):
        self.unload_relations()
        self.load_relations()

    def unload_relations(self):
        for action in self.map_layer_actions:
            # remove general actions
            QgsGui.instance().mapLayerActionRegistry().removeMapLayerAction(action)
        self.map_layer_actions = []
        # remove legend context menu entries
        for action in self.layer_tree_actions:
            self.iface.removeCustomActionForLayerType(action)
        self.layer_tree_actions = []

    def load_relations(self):
        self.unload_relations()
        for relation in QgsProject.instance().relationManager().relations().values():
            # show children
            self.add_map_layer_action(
                self.tr('Show referencing features in "{layer}" for relation "{rel}"')
                    .format(layer=relation.referencingLayer().name(), rel=relation.name()),
                relation, self.show_children
            )
            self.add_layer_tree_action(
                self.tr('Show referencing features in "{referencing}" for the selected features in "{referenced}"')
                    .format(referencing=relation.referencingLayer().name(), referenced=relation.referencedLayer().name()),
                relation, self.show_children
            )
            # batch insert
            self.add_map_layer_action(
                self.tr('Add features in referencing layer "{layer}" for "relation "{rel}"')
                    .format(layer=relation.referencingLayer().name(), rel=relation.name()),
                relation, self.batch_insert
            )
            self.add_layer_tree_action(
                self.tr('Add features in "{referencing}" for the selected features in "{referenced}"')
                    .format(referencing=relation.referencingLayer().name(), referenced=relation.referencedLayer().name()),
                relation, self.batch_insert
            )
            # add custom aggregates
            for custom_aggregate in self.custom_aggregates:
                if custom_aggregate.relation_id == relation.id():
                    data = [custom_aggregate.aggregate, custom_aggregate.field]
                    self.add_map_layer_action(custom_aggregate.title, relation, self.run_aggregate, data)
                    self.add_layer_tree_action(custom_aggregate.title, relation, self.run_aggregate, data)
                    break

    def add_map_layer_action(self, title: str, relation: QgsRelation, slot, data=None) -> QgsMapLayerAction:

        def layer_action_triggered(layer: QgsVectorLayer, features: [QgsFeature]):
            assert layer == relation.referencedLayer()
            slot(relation, features, data)

        action = QgsMapLayerAction(
            title,
            self.iface.mainWindow(),
            relation.referencedLayer(),
            QgsMapLayerAction.MultipleFeatures
        )
        if DEBUG:
            print('Adding insert action for relation "{}" in layer "{}"'.format(relation.name(),
                                                                         relation.referencedLayer().name()))
        QgsGui.instance().mapLayerActionRegistry().addMapLayerAction(action)
        action.triggeredForFeatures.connect(layer_action_triggered)
        self.map_layer_actions.append(action)

    def add_layer_tree_action(self, title: str, relation: QgsRelation, slot, data=None) -> QAction:
        # add legend context menu entry
        layer_tree_action = QAction(title, self.iface.mainWindow())
        self.iface.addCustomActionForLayerType(layer_tree_action, None, QgsMapLayer.VectorLayer, False)
        self.iface.addCustomActionForLayer(layer_tree_action, relation.referencedLayer())
        layer_tree_action.setData(relation.id())
        layer_tree_action.triggered.connect(lambda: slot(relation, relation.referencedLayer().selectedFeatures(), data))
        self.layer_tree_actions.append(layer_tree_action)

    def show_children(self, relation: QgsRelation, features: [QgsFeature], data=None):
        """
        :param relation: the relation
        :param features: the list of feature on the referenced layer
        :return:
        """
        # works only for single key relation
        for referencing, referenced in relation.fieldPairs().items():
            break
        expression = '{fk} IN ({parent_ids})'.format(
            fk=referencing,
            parent_ids=', '.join([str(f.attribute(referenced)) for f in features])
        )
        print(expression)
        self.iface.showAttributeTable(relation.referencingLayer(), expression)

    def batch_insert(self, relation: QgsRelation, features: [QgsFeature], data=None):
        """
        :param relation: the relation
        :param features: the list of feature on the referenced layer
        :return:
        """
        layer = relation.referencingLayer()
        if not layer.isEditable():
            self.iface.messageBar().pushMessage(
                'Relation Batch Insert',
                self.tr('layer "{layer}" is not editable').format(layer=layer.name()), Qgis.Warning
            )
            return

        if len(features) < 1:
            self.iface.messageBar().pushMessage(
                'Relation Batch Insert',
                self.tr('There is no features to batch insert for. Select some in layer "{layer}" first.')
                    .format(layer=relation.referencedLayer().name()),
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
                self.tr('{count} features were written to "{layer}"').format(count=features_written, layer=layer.name())
            )
        else:
            self.iface.messageBar().pushMessage(
                'Relation Batch Insert',
                self.tr('There was an error while inserting features, '
                        '{count} features were written to "{layer}", '
                        '{expected_count} were expected.').format(
                    count=features_written,
                    layer=layer.name(),
                    expected_count=len(features)
                ),
                Qgis.Critical
            )

    def run_aggregate(self, relation: QgsRelation, features: [QgsFeature], data=None):
        conditions = []
        for referencing, referenced in relation.fieldPairs().items():
            break

        field = relation.referencedLayer().fields().field(referenced)
        quote = "" if field.isNumeric() else "'"

        for feature in features:
            base_condition = '{fk} = {quote}{parent_id}{quote}'.format(
                fk=referencing,
                parent_id=feature.attribute(referenced),
                quote=quote,
            )
            condition = "( {filter} AND {field} = aggregate(layer:='{lyr}', aggregate:='{agg}', expression:={field}, filter:={filter}) )".format(
                filter=base_condition,
                field=data[1],
                lyr=relation.referencingLayer().id(),
                agg=data[0]
            )
            conditions.append(condition)
        expression = ' OR '.join(conditions)
        print(expression)
        self.iface.showAttributeTable(relation.referencingLayer(), expression)



