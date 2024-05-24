from plone import api
from .. import api as easyform_api
from ..interfaces import IFieldExtender
from ..browser.widgets import EasyFormMultiSelectFieldWidget

import logging


logger = logging.getLogger(__name__)


def update_last_compilation(contex, timetuple):
    # Let's do the imports inline, so they are not needlessly done at startup.
    # Should not really matter, but oh well.
    from datetime import datetime
    from plone.registry.interfaces import IRegistry
    from Products.CMFPlone.interfaces import IBundleRegistry
    from zope.component import getUtility

    registry = getUtility(IRegistry)
    records = registry.forInterface(IBundleRegistry, prefix="plone.bundles/easyform")
    # Technically we only need year, month and day.
    # But keep this in sync with registry.xml.
    records.last_compilation = datetime(*timetuple)
    logger.info("Updated the last_compilation date of the easyform bundle.")

    # Run the combine-bundles import step or its handler.
    # Can be done with an upgrade step:
    #   <gs:upgradeDepends
    #     title="combine bundles"
    #     import_steps="combine-bundles"
    #     run_deps="false"
    #     />
    # But directly calling the basic function works fine.
    # See also comment here:
    # https://github.com/collective/collective.easyform/pull/248#issuecomment-689365240
    # Also, here we can do a try/except so it does not fail on Plone 5.0,
    # which I think does not have the import step, not the function.
    try:
        from Products.CMFPlone.resources.browser.combine import combine_bundles
    except ImportError:
        logger.warning("Could not call combine_bundles. You should do that yourself.")
        return
    portal = api.portal.get()
    combine_bundles(portal)


def update_last_compilation_1007(context):
    update_last_compilation(context, (2020, 9, 8, 17, 52, 0))


def update_last_compilation_1008(context):
    update_last_compilation(context, (2020, 12, 9, 14, 2, 0))


def update_last_compilation_1009(context):
    update_last_compilation(context, (2021, 8, 31, 0, 0, 0))


def fix_savedata_persistence_issues(context):

    from persistent.mapping import PersistentMapping

    catalog = api.portal.get_tool("portal_catalog")
    forms = catalog.unrestrictedSearchResults(portal_type='EasyForm')
    for item in forms:
        form = item.getObject()
        if hasattr(form, '_inputStorage'):
            # Convert to persistent mapping
            form._inputStorage = PersistentMapping(form._inputStorage)
            logger.info(
                'Fixed storage of {}'.format('/'.join(form.getPhysicalPath()))
            )


def update_form_select_widgets(context):
    catalog = api.portal.get_tool('portal_catalog')
    form_brains = catalog.unrestrictedSearchResults(portal_type="EasyForm")
    forms_updated = fields_updated = 0
    for brain in form_brains:
        form = brain._unrestrictedGetObject()
        schema = easyform_api.get_schema(form)
        changed = False
        for fname in schema:
            field = schema[fname]
            efield = IFieldExtender(field)
            field_widget = getattr(efield, "field_widget", None)
            if field_widget and field_widget.widget_factory.__name__ == 'CollectionSelectFieldWidget':
                efield.field_widget = EasyFormMultiSelectFieldWidget
                changed = True
                fields_updated += 1
        if changed:
            easyform_api.set_fields(form, schema)
            forms_updated += 1
    logger.info("Update {} fields on {} forms".format(fields_updated, forms_updated))
