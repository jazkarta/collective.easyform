# -*- coding: utf-8 -*-
from collections import namedtuple
from collective.easyform.interfaces.mailer import default_mail_body
from collective.easyform.migration.fields import append_field
from collective.easyform.migration.fields import append_list_node
from collective.easyform.migration.fields import append_node
from collective.easyform.migration.fields import set_attribute
from collective.easyform.migration.fields import to_text
from lxml import etree
from plone import api
from Products.PloneFormGen.content.actionAdapter import FormActionAdapter

import logging
import re


logger = logging.getLogger("collective.easyform.migration")


NAMESPACES = {
    "easyform": "http://namespaces.plone.org/supermodel/easyform",
    "form": "http://namespaces.plone.org/supermodel/form",
}


Type = namedtuple("Type", ["name", "handler"])
Property = namedtuple("Property", ["name", "handler"])


TYPES_MAPPING = {
    "FormMailerAdapter": Type("collective.easyform.actions.Mailer", append_field),
    "FormSaveDataAdapter": Type("collective.easyform.actions.SaveData", append_field),
    "FormCustomScriptAdapter": Type(
        "collective.easyform.actions.CustomScript", append_field
    ),
}

PROPERTIES_MAPPING = {
    "additional_headers": Property("additional_headers", append_node),
    "bcc_recipients": Property("bcc_recipients", append_node),
    "bccOverride": Property("bccOverride", append_node),
    "body_footer": Property("body_footer", append_node),
    "body_post": Property("body_post", append_node),
    "body_pre": Property("body_pre", append_node),
    "body_pt": Property("body_pt", append_node),
    "body_type": Property("body_type", append_node),
    "cc_recipients": Property("cc_recipients", append_node),
    "ccOverride": Property("ccOverride", append_node),
    "description": Property("description", append_node),
    "execCondition": Property("easyform:execCondition", set_attribute),
    "includeEmpties": Property("includeEmpties", append_node),
    "msg_subject": Property("msg_subject", append_node),
    "recipient_email": Property("recipient_email", append_node),
    "recipient_name": Property("recipient_name", append_node),
    "recipientOverride": Property("recipientOverride", append_node),
    "replyto_field": Property("replyto_field", append_node),
    "required": Property("required", append_node),
    "senderOverride": Property("senderOverride", append_node),
    "showAll": Property("showAll", append_node),
    "showFields": Property("showFields", append_list_node),
    "subject_field": Property("subject_field", append_node),
    "subjectOverride": Property("subjectOverride", append_node),
    "title": Property("title", append_node),
    "to_field": Property("to_field", append_node),
    "xinfo_headers": Property("xinfo_headers", append_node),
    "ExtraData": Property("ExtraData", append_list_node),
    "DownloadFormat": Property("DownloadFormat", append_node),
    "UseColumnNames": Property("UseColumnNames", append_node),
    "ProxyRole": Property("ProxyRole", append_node),
    "ScriptBody": Property("ScriptBody", append_node),
}

LEGACY_MAILER_TEMPLATES = (
    '<html xmlns="http://www.w3.org/1999/xhtml"> <head><title></title></head> <body> <p tal:content="here/getBody_pre | nothing" /> <dl> <tal:block repeat="field options/wrappedFields"> <dt tal:content="field/fgField/widget/label" /> <dd tal:content="structure python:field.htmlValue(request)" /> </tal:block> </dl> <p tal:content="here/getBody_post | nothing" /> <pre tal:content="here/getBody_footer | nothing" /> </body> </html> ',
    '<html xmlns="http://www.w3.org/1999/xhtml"> <head><title></title></head> <body> <p tal:content="here/body_pre | nothing" /> <dl> <tal:block repeat="field options/wrappedFields"> <dt tal:content="field/fgField/widget/label" /> <dd tal:content="structure python:field.htmlValue(request)" /> </tal:block> </dl> <p tal:content="here/body_post | nothing" /> <pre tal:content="here/body_footer | nothing" /> </body> </html> ',
)


def pfg_actions(context):
    actions = []
    enabled_adapters = context.getRawActionAdapter()
    for obj in context.objectValues():
        if not isinstance(obj, FormActionAdapter):
            continue
        id_ = obj.getId()
        props = {}
        props["_portal_type"] = obj.portal_type
        props["required"] = id_ in enabled_adapters
        for field in obj.Schema().fields():
            name = field.getName()
            accessor = field.getEditAccessor(obj)
            props[name] = accessor()
        actions.append((id_, props))
    return actions


def actions_model(ploneformgen):
    """Create an actions xml model from a PloneFormGen instance."""
    parser = etree.XMLParser(remove_blank_text=True)
    model = etree.fromstring(ACTIONS_MODEL, parser)
    schema = model.find("{http://namespaces.plone.org/supermodel/schema}schema")
    portal_workflow = api.portal.get_tool("portal_workflow")

    for actionname, properties in pfg_actions(ploneformgen):
        type_ = TYPES_MAPPING.get(properties["_portal_type"])
        if type_ is None:
            # ploneformgen has been renamed with _MIGRATION_ suffix
            # hence, we remove 11 chars
            pfgpath = "/".join(ploneformgen.getPhysicalPath())[:-11]
            logger.warning(
                "Ignoring field '%s' of type '%s' of form '%s'.",
                actionname,
                properties["_portal_type"],
                pfgpath,
            )
            continue

        field = type_.handler(schema, type_.name, actionname, properties)

        for name, value in properties.items():
            prop = PROPERTIES_MAPPING.get(name)
            if prop is None:
                continue

            value = to_text(value)

            if name == "body_pt":
                review_state = portal_workflow.getInfoFor(ploneformgen, "review_state")
                body_pt = re.sub(r'<title>.*?</title>', '<title></title>', value)
                is_legacy_default = re.sub(r"\s+", " ", body_pt) in LEGACY_MAILER_TEMPLATES
                if is_legacy_default or ("wrappedFields" in value and review_state == "published"):
                    value = default_mail_body()

            prop.handler(field, prop.name, value)

    return etree.tostring(model, pretty_print=True)


ACTIONS_MODEL = b"""
<model xmlns="http://namespaces.plone.org/supermodel/schema">
  <schema></schema>
</model>
"""
