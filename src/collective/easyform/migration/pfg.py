# -*- coding: utf-8 -*-
from collections import namedtuple
from collective.easyform.migration.actions import actions_model
from collective.easyform.migration.data import migrate_saved_data
from collective.easyform.migration.fields import fields_model
from plone import api
from plone.app.contenttypes.migration.field_migrators import (  # noqa
    migrate_richtextfield,
)
from plone.app.contenttypes.migration.migration import ATCTContentMigrator
from plone.app.contenttypes.migration.migration import migrate
from plone.autoform.form import AutoExtensibleForm
from plone.protect.interfaces import IDisableCSRFProtection
from plone.supermodel import model
from Products.CMFPlone.utils import safe_unicode
from six import StringIO
from z3c.form.button import buttonAndHandler
from z3c.form.form import Form
from zope import schema
from zope.interface import alsoProvides

import logging
import transaction


logger = logging.getLogger("collective.easyform.migration")

Field = namedtuple("Type", ["name", "handler"])

def migrate_simplefield(src_obj, dst_obj, src_fieldname, dst_fieldname):
    """Migrate a generic simple field.

    Copies the value of a Archetypes-object to a attribute of the same name
    to the target-object. The only transform is a safe_unicode of the value.
    """
    field = src_obj.getField(src_fieldname)
    if field:
        at_value = field.get(src_obj)
    else:
        at_value = getattr(src_obj, src_fieldname, None)
        if at_value and hasattr(at_value, '__call__'):
            at_value = at_value()
    if isinstance(at_value, tuple):
        at_value = tuple(safe_unicode(i) for i in at_value)
    if isinstance(at_value, list):
        at_value = [safe_unicode(i) for i in at_value]
    if at_value is not None:
        setattr(dst_obj, dst_fieldname, safe_unicode(at_value))


FIELD_MAPPING = {
    "submitLabel": Field("submitLabel", migrate_simplefield),
    "resetLabel": Field("resetLabel", migrate_simplefield),
    "useCancelButton": Field("useCancelButton", migrate_simplefield),
    "forceSSL": Field("forceSSL", migrate_simplefield),
    "formPrologue": Field("formPrologue", migrate_richtextfield),
    "formEpilogue": Field("formEpilogue", migrate_richtextfield),
    "thanksPageOverride": Field("thanksPageOverride", migrate_simplefield),
    "formActionOverride": Field("formActionOverride", migrate_simplefield),
    "onDisplayOverride": Field("onDisplayOverride", migrate_simplefield),
    "afterValidationOverride": Field(
        "afterValidationOverride", migrate_simplefield
    ),  # noqa
    "headerInjection": Field("headerInjection", migrate_simplefield),
    "checkAuthenticator": Field("CSRFProtection", migrate_simplefield),
}

THANKS_FIELD_MAPPING = {
    "description": Field("thanksdescription", migrate_simplefield),
    "includeEmpties": Field("includeEmpties", migrate_simplefield),
    "showAll": Field("showAll", migrate_simplefield),
    "showFields": Field("showFields", migrate_simplefield),
    "title": Field("thankstitle", migrate_simplefield),
    "thanksPrologue": Field("thanksPrologue", migrate_richtextfield),
    "thanksEpilogue": Field("thanksEpilogue", migrate_richtextfield),
}


class PloneFormGenMigrator(ATCTContentMigrator):
    """Migrator for PFG to easyform"""

    src_portal_type = "FormFolder"
    src_meta_type = "FormFolder"
    dst_portal_type = "EasyForm"
    dst_meta_type = None  # not used

    def migrate_owner(self):
        # ignore case where owner no longer exists
        try:
            super(PloneFormGenMigrator, self).migrate_owner()
        except AttributeError:
            pass

    def beforeChange_ploneformgen(self):
        self.old.old_actionAdapter = self.old.actionAdapter

    def migrate_ploneformgen(self):
        self.old.actionAdapter = self.old.old_actionAdapter
        for pfg_field, ef_field in FIELD_MAPPING.items():
            ef_field.handler(self.old, self.new, pfg_field, ef_field.name)
        self.new.fields_model = fields_model(self.old)
        self.new.actions_model = actions_model(self.old)
        self.new.form_tabbing = False

        pfg_thankspage = self.old.get(self.old.getThanksPage(), None)
        if pfg_thankspage:
            for pfg_field, ef_field in THANKS_FIELD_MAPPING.items():
                ef_field.handler(pfg_thankspage, self.new, pfg_field, ef_field.name)
            if not pfg_thankspage.Description():
                self.new.thanksdescription = ""

        migrate_saved_data(self.old, self.new)

    def migrate(self, unittest=0):
        super(PloneFormGenMigrator, self).migrate()
        logger.info("Migrated FormFolder %s", "/".join(self.new.getPhysicalPath()))


class IMigratePloneFormGenFormSchema(model.Schema):
    dry_run = schema.Bool(
        title=u"Dry run",
        required=True,
        default=False,
    )


class MigratePloneFormGenForm(AutoExtensibleForm, Form):
    label = u"Migrate PloneFormGen Forms"
    ignoreContext = True
    schema = IMigratePloneFormGenFormSchema

    @buttonAndHandler(u"Migrate")
    def handle_migrate(self, action):
        data, errors = self.extractData()
        if len(errors) > 0:
            return

        self.log = StringIO()
        handler = logging.StreamHandler(self.log)
        logger.addHandler(handler)
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
        handler.setFormatter(formatter)

        self.migrate()

        self.migration_done = True
        if data.get("dry_run", False):
            transaction.abort()
            logger.info(u"PloneFormGen migration finished (dry run)")
        else:
            logger.info(u"PloneFormGen migration finished")

    def migrate(self):
        alsoProvides(self.request, IDisableCSRFProtection)
        portal = api.portal.get()
        migrate(portal, PloneFormGenMigrator)

    def render(self):
        if getattr(self, "migration_done", False):
            return self.log.getvalue()
        return super(MigratePloneFormGenForm, self).render()
