""" Uninstall Profile
"""
from Products.CMFCore.utils import getToolByName
from plone.app.contentrules import api
from plone.contentrules.engine.interfaces import IRuleStorage
from zope.component import queryUtility


def uninstall(portal, reinstall=False):
    """ Uninstall profile setup
    """
    if not reinstall:
        setup_tool = getToolByName(portal, 'portal_setup')
        setup_tool.runAllImportStepsFromProfile(
            'profile-eea.asyncmove:uninstall')
        remove_content_rules(portal)
        return "Ran all uninstall steps."


def remove_content_rules(portal):
    """ Remove content rules on uninstall
    """
    storage = queryUtility(IRuleStorage)
    if not storage:
        return
    ids = ["eea-asyncmove-rule-fail", "eea-asyncmove-rule-success",
           "eea-asyncmove-rename-rule-fail",
           "eea-asyncmove-rename-rule-success"]
    for i in ids:
        found = storage.get(i)
        if found:
            api.unassign_rule(portal, i)
            del storage[i]


def remove_request_from_content_rules_conditions(portal):
    """ Change conditions to use absolute_url instead of request
    """
    logger.info("Starting check of content rules tales expression")
    storage = queryUtility(IRuleStorage)
    if not storage:
        return
    rules = storage.values()
    for rule in rules:
        conditions = rule.conditions
        for condition in conditions:
            if len(condition) > 1:
                condition = condition[0]
            tales = getattr(condition, 'tales_expression', None)
            if tales:
                if 'REQUEST.URL' in tales:
                    logging.warn('changing tales expression %s', tales)
                    condition.tales_expression = tales.replace(
                                'REQUEST.URL', 'absolute_url')
                    logging.warn('tales expression changed to %s',
                                 condition.tales_expression)