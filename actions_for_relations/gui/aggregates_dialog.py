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
from qgis.PyQt.QtCore import QObject, QModelIndex, pyqtSlot
from qgis.PyQt.QtWidgets import QDialog, QStyledItemDelegate, QComboBox, QAbstractItemView, QHeaderView
from qgis.PyQt.uic import loadUiType
from qgis.core import QgsProject
from qgis.gui import QgsFieldComboBox
from actions_for_relations.core.custom_aggregate import CustomAggregate
from actions_for_relations.core.aggregate_model import AggregateModel, Role, Column
from actions_for_relations.core.settings import Settings


DialogUi, _ = loadUiType(os.path.join(os.path.dirname(__file__), '../ui/aggregates.ui'))


class RelationEditorDelegate(QStyledItemDelegate):
    def __init__(self, parent: QObject = None):
        super(RelationEditorDelegate, self).__init__(parent)

    def createEditor(self, parent, option, index):
        cb = QComboBox(parent)
        for relation in QgsProject.instance().relationManager().relations().values():
            cb.addItem(relation.name(), relation.id())
        return cb

    def setEditorData(self, editor, index):
        relation_id = index.model().data(index, Role.RelationIdRole.value)
        editor.setCurrentIndex(editor.findData(relation_id))

    def setModelData(self, editor, model, index):
        relation_id = editor.currentData()
        model.setData(index, relation_id)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)


class AggregateEditorDelegate(QStyledItemDelegate):
    def __init__(self, parent: QObject = None):
        super(AggregateEditorDelegate, self).__init__(parent)

    def createEditor(self, parent, option, index):
        cb = QComboBox(parent)
        for agg in ('min', 'max'):
            cb.addItem(agg, agg)
        return cb

    def setEditorData(self, editor, index):
        agg = index.model().data(index, Role.AggregateRole.value)
        editor.setCurrentIndex(editor.findData(agg))

    def setModelData(self, editor, model, index):
        agg = editor.currentData()
        model.setData(index, agg)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)


class FieldEditorDelegate(QStyledItemDelegate):
    def __init__(self, parent: QObject = None):
        super(FieldEditorDelegate, self).__init__(parent)

    def createEditor(self, parent, option, index: QModelIndex):
        fc = QgsFieldComboBox(parent)
        relation = index.model().data(index, Role.RelationRole.value)
        print('hey', relation, index.column())
        if relation:
            fc.setLayer(relation.referencingLayer())
        return fc

    def setEditorData(self, editor, index: QModelIndex):
        field = index.model().data(index, Role.FieldRole.value)
        editor.setField(field)

    def setModelData(self, editor, model, index: QModelIndex):
        field = editor.currentField()
        model.setData(index, field)

    def updateEditorGeometry(self, editor, option, index: QModelIndex):
        editor.setGeometry(option.rect)


class AggregatesDialog(QDialog, DialogUi):
    def __init__(self, custom_aggregates: [CustomAggregate], parent=None):
        QDialog.__init__(self, parent)
        self.setupUi(self)
        self.settings = Settings()

        self.aggregate_model = AggregateModel(custom_aggregates)
        self.aggregate_table_view.setModel(self.aggregate_model)

        self.aggregate_table_view.setItemDelegateForColumn(Column.RelationColumn.value, RelationEditorDelegate(self))
        self.aggregate_table_view.setItemDelegateForColumn(Column.AggregateColumn.value, AggregateEditorDelegate(self))
        self.aggregate_table_view.setItemDelegateForColumn(Column.FieldColumn.value, FieldEditorDelegate(self))
        self.aggregate_table_view.verticalHeader().hide()
        self.aggregate_table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.aggregate_table_view.horizontalHeader().setStretchLastSection(True)
        self.aggregate_table_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.aggregate_table_view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.aggregate_table_view.setEditTriggers(QAbstractItemView.DoubleClicked)

        self.accepted.connect(self.save_custom_aggregates)
        self.add_tool_button.clicked.connect(self.aggregate_model.add_custom_aggregate)
        self.remove_tool_button.clicked.connect(self.remove_custom_aggregate)
        self.aggregate_table_view.selectionModel().currentRowChanged.connect(self.on_selection_changed)

    def save_custom_aggregates(self):
        definitions = []
        for custom_aggregate in self.aggregate_model.custom_aggregates:
            definitions.append(custom_aggregate.as_dict())
        self.settings.set_value('custom_aggregates', definitions)

    @pyqtSlot()
    def remove_custom_aggregate(self):
        selected_rows = self.aggregate_table_view.selectionModel().selectedRows()
        if len(selected_rows):
            self.aggregate_model.remove_custom_aggregate(selected_rows[0])

    @pyqtSlot(QModelIndex)
    def on_selection_changed(self, index: QModelIndex):
        self.remove_tool_button.setEnabled(index.isValid())


