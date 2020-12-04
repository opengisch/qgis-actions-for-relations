# -*- coding: utf-8 -*-
# -----------------------------------------------------------
#
# QGIS Actions for relations
# Copyright (C) 2020 Denis Rouzaud
#
# licensed under the terms of GNU GPL 2+
#
# -----------------------------------------------------------

from qgis.PyQt.QtCore import QObject
from qgis.core import QgsProject, QgsRelation


class CustomAggregate(QObject):
    def __init__(self, definition: dict = {}):
        super(CustomAggregate, self).__init__()
        if not definition:
            definition['title'] = self.tr('new custom aggregate')
            relations = list(QgsProject.instance().relationManager().relations().values())
            definition['aggregate'] = 'max'
            if len(relations) > 0:
                definition['relation_id'] = relations[0].id()
                definition['field'] = relations[0].referencingLayer().fields().at(0).name()

        self.relation_id = definition.get('relation_id')
        self.title = definition.get('title')
        self.aggregate = definition.get('aggregate')
        self.field = definition.get('field')

    def relation(self):
        relation: QgsRelation = None
        for _relation in QgsProject.instance().relationManager().relations().values():
            if _relation.id() == self.relation_id:
                relation = _relation
                break
        return relation

    def relation_name(self):
        relation = self.relation()
        if relation:
            return relation.name()
        else:
            return ''

    def is_valid(self) -> bool:
        relation = self.relation()
        if relation is None:
            return False
        if relation.referencedLayer().fields().indexFromName(self.field) < 0:
            return False
        return True

    def as_dict(self):
        return {
            'relation_id': self.relation_id,
            'title': self.title,
            'aggregate': self.aggregate,
            'field': self.field,
        }
