""" Uninstall Profile
"""
from Products.CMFCore.utils import getToolByName
from plone.app.contentrules import api
from plone.contentrules.engine.interfaces import IRuleStorage
from zope.component import queryUtility
import logging

log = logging.getLogger(__name__)


def uninstall(portal, reinstall=False):
    """ Uninstall profile setup
    """
    if not reinstall:
        setup_tool = getToolByName(portal, 'portal_setup')
        setup_tool.runAllImportStepsFromProfile(
            'profile-eea.asyncmove:uninstall')
        remove_content_rules(portal)
        return "Ran all uninstall steps."


def install(portal):
    """ Install profile setup
    """
    setup_tool = getToolByName(portal, 'portal_setup')
    setup_tool.runAllImportStepsFromProfile('profile-eea.asyncmove:default')
    return "Ran all uninstall steps."


def remove_content_rules(portal):
    """ Remove content rules on uninstall
    """
    storage = queryUtility(IRuleStorage)
    if not storage:
        return
    ids = ["eea-asyncmove-rule-fail", "eea-asyncmove-rule-success",
           "eea-asyncmove-rename-rule-fail", "eea-asyncmove-rule-added",
           "eea-asyncmove-rename-rule-success"]
    for i in ids:
        found = storage.get(i)
        if found:
            api.unassign_rule(portal, i)
            del storage[i]
