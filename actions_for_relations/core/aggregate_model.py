# -*- coding: utf-8 -*-
# -----------------------------------------------------------
#
# QGIS Actions for relations
# Copyright (C) 2020 Denis Rouzaud
#
# licensed under the terms of GNU GPL 2+
#
# -----------------------------------------------------------

from enum import Enum
from qgis.PyQt.QtCore import Qt, QObject, QAbstractTableModel, QModelIndex
from actions_for_relations.core.custom_aggregate import CustomAggregate


class Column(Enum):
    TitleColumn = 0
    RelationColumn = 1
    AggregateColumn = 2
    FieldColumn = 3


class Role(Enum):
    RelationRole = Qt.UserRole + 1
    RelationIdRole = Qt.UserRole + 2
    AggregateRole = Qt.UserRole + 3
    FieldRole = Qt.UserRole + 4


class AggregateModel(QAbstractTableModel):
    def __init__(self, custom_aggregates: [CustomAggregate], parent: QObject = None):
        super(AggregateModel, self).__init__(parent)
        self.custom_aggregates = custom_aggregates

    def rowCount(self, parent: QModelIndex = ...) -> int:
        return len(self.custom_aggregates)

    def columnCount(self, parent: QModelIndex = ...) -> int:
        return 4

    def add_custom_aggregate(self):
        c = self.rowCount(QModelIndex())
        self.beginInsertRows(QModelIndex(), c, c)
        self.custom_aggregates.append(CustomAggregate())
        self.endResetModel()

    def remove_custom_aggregate(self, index: QModelIndex):
        if not index.isValid():
            return
        self.beginRemoveRows(QModelIndex(), index.row(), index.row())
        del self.custom_aggregates[index.row()]
        self.endRemoveRows()

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = ...):
        if role == Qt.DisplayRole:
            if section == Column.TitleColumn.value:
                return self.tr('Title')
            if section == Column.RelationColumn.value:
                return self.tr('Relation')
            if section == Column.AggregateColumn.value:
                return self.tr('Aggregate')
            if section == Column.FieldColumn.value:
                return self.tr('Field')

        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable
        return flags

    def data(self, index: QModelIndex, role: int = ...):
        if index.row() < 0 or index.row() >= self.rowCount(QModelIndex()):
            return None

        if role == Qt.DisplayRole:
            if index.column() == Column.TitleColumn.value:
                return self.custom_aggregates[index.row()].title
            if index.column() == Column.RelationColumn.value:
                return self.custom_aggregates[index.row()].relation_name()
            if index.column() == Column.AggregateColumn.value:
                return self.custom_aggregates[index.row()].aggregate
            if index.column() == Column.FieldColumn.value:
                return self.custom_aggregates[index.row()].field

        if role == Qt.EditRole and index.column() == Column.TitleColumn.value:
            return self.custom_aggregates[index.row()].title

        if role == Role.RelationRole.value:
            return self.custom_aggregates[index.row()].relation()

        if role == Role.RelationIdRole.value:
            return self.custom_aggregates[index.row()].relation_id

        if role == Role.AggregateRole.value:
                return self.custom_aggregates[index.row()].aggregate

        if role == Role.FieldRole.value:
            return self.custom_aggregates[index.row()].field

        return None

    def setData(self, index: QModelIndex, value, role: int = Qt.EditRole) -> bool:
        if index.row() < 0 or index.row() >= self.rowCount(QModelIndex()):
            return False

        if index.column() == Column.TitleColumn.value:
            self.custom_aggregates[index.row()].title = value
            return True

        if index.column() == Column.RelationColumn.value:
            self.custom_aggregates[index.row()].relation_id = value
            return True

        if index.column() == Column.AggregateColumn.value:
            self.custom_aggregates[index.row()].aggregate = value
            return True

        if index.column() == Column.FieldColumn.value:
            self.custom_aggregates[index.row()].field = value
            return True

        return False
