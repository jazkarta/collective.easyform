# -*- coding: utf-8 -*-

from plone.supermodel.parser import IFieldMetadataHandler
from plone.supermodel.utils import ns
from zope import schema as zs
from zope.component import adapter
from zope.component import adapts
from zope.interface import implements

from collective.formulator.interfaces import IAction
from collective.formulator.interfaces import IActionExtender
from collective.formulator.interfaces import IFieldExtender
from collective.formulator.interfaces import IFormulatorActionsContext
from collective.formulator.interfaces import IFormulatorFieldsContext


@adapter(IFormulatorFieldsContext, zs.interfaces.IField)
def get_field_extender(context, field):
    return IFieldExtender


def _get_(self, key):
    return self.field.interface.queryTaggedValue(key, {}).get(self.field.__name__)


def _set_(self, value, key):
    data = self.field.interface.queryTaggedValue(key, {})
    data[self.field.__name__] = value
    self.field.interface.setTaggedValue(key, data)


class FieldExtender(object):
    implements(IFieldExtender)
    adapts(zs.interfaces.IField)

    def __init__(self, field):
        self.field = field

    TDefault = property(lambda x: _get_(x, 'TDefault'),
                        lambda x, value: _set_(x, value, 'TDefault'))
    TEnabled = property(lambda x: _get_(x, 'TEnabled'),
                        lambda x, value: _set_(x, value, 'TEnabled'))
    TValidator = property(lambda x: _get_(x, 'TValidator'),
                          lambda x, value: _set_(x, value, 'TValidator'))
    serverSide = property(lambda x: _get_(x, 'serverSide'),
                          lambda x, value: _set_(x, value, 'serverSide'))
    validators = property(lambda x: _get_(x, 'validators'),
                          lambda x, value: _set_(x, value, 'validators'))


class FormulatorFieldMetadataHandler(object):

    """Support the formulator: namespace in model definitions.
    """
    implements(IFieldMetadataHandler)

    namespace = 'http://namespaces.plone.org/supermodel/formulator'
    prefix = 'formulator'

    def read(self, fieldNode, schema, field):
        name = field.__name__
        for i in ['TDefault', 'TEnabled', 'TValidator']:
            value = fieldNode.get(ns(i, self.namespace))
            if value:
                data = schema.queryTaggedValue(i, {})
                data[name] = value
                schema.setTaggedValue(i, data)
        # serverSide
        value = fieldNode.get(ns('serverSide', self.namespace))
        if value:
            data = schema.queryTaggedValue('serverSide', {})
            data[name] = value == 'True' or value == 'true'
            schema.setTaggedValue('serverSide', data)
        # validators
        value = fieldNode.get(ns('validators', self.namespace))
        if value:
            data = schema.queryTaggedValue('validators', {})
            data[name] = value.split("|")
            schema.setTaggedValue('validators', data)

    def write(self, fieldNode, schema, field):
        name = field.__name__
        for i in ['TDefault', 'TEnabled', 'TValidator']:
            value = schema.queryTaggedValue(i, {}).get(name, None)
            if value:
                fieldNode.set(ns(i, self.namespace), value)
        # serverSide
        value = schema.queryTaggedValue('serverSide', {}).get(name, None)
        if isinstance(value, bool):
            fieldNode.set(ns('serverSide', self.namespace), str(value))
        # validators
        value = schema.queryTaggedValue('validators', {}).get(name, None)
        if value:
            fieldNode.set(ns('validators', self.namespace), "|".join(value))


@adapter(IFormulatorActionsContext, IAction)
def get_action_extender(context, action):
    return IActionExtender


class ActionExtender(object):
    implements(IActionExtender)
    adapts(IAction)

    def __init__(self, field):
        self.field = field

    execCondition = property(lambda x: _get_(x, 'execCondition'),
                             lambda x, value: _set_(x, value, 'execCondition'))


class FormulatorActionMetadataHandler(object):

    """Support the formulator: namespace in model definitions.
    """
    implements(IFieldMetadataHandler)

    namespace = 'http://namespaces.plone.org/supermodel/formulator'
    prefix = 'formulator'

    def read(self, fieldNode, schema, field):
        name = field.__name__
        value = fieldNode.get(ns('execCondition', self.namespace))
        data = schema.queryTaggedValue('execCondition', {})
        if value:
            data[name] = value
            schema.setTaggedValue('execCondition', data)

    def write(self, fieldNode, schema, field):
        name = field.__name__
        value = schema.queryTaggedValue('execCondition', {}).get(name, None)
        if value:
            fieldNode.set(ns('execCondition', self.namespace), value)
