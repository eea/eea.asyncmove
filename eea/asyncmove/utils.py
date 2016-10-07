""" Async Utils
"""
import transaction
from Acquisition._Acquisition import aq_parent, aq_inner
from Products.Archetypes.utils import transaction_note
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.utils import getDefaultPage
from ZODB.POSException import ConflictError
from zope.event import notify
from zope.lifecycleevent import ObjectModifiedEvent
from AccessControl import getSecurityManager
from AccessControl import Unauthorized


def renameObjectsByPaths(self, paths, new_ids, new_titles,
                         handle_errors=True, REQUEST=None):
    """ CMFPlone override
    """
    smanager = getSecurityManager()
    obj = self
    if not smanager.checkPermission('Delete objects', obj) and not \
                        smanager.checkPermission('Copy or Move', obj):
        return Unauthorized("You may not modify this object")
    failure = {}
    success = {}
    # use the portal for traversal in case we have relative paths
    portal = getToolByName(self, 'portal_url').getPortalObject()
    traverse = portal.restrictedTraverse
    for i, path in enumerate(paths):
        new_id = new_ids[i]
        new_title = new_titles[i]
        if handle_errors:
            sp = transaction.savepoint(optimistic=True)
        try:
            obj = traverse(path, None)
            obid = obj.getId()
            title = obj.Title()
            change_title = new_title and title != new_title
            changed = False
            if change_title:
                getSecurityManager().validate(obj, obj, 'setTitle',
                                              obj.setTitle)
                obj.setTitle(new_title)
                notify(ObjectModifiedEvent(obj))
                changed = True
            if new_id and obid != new_id:
                parent = aq_parent(aq_inner(obj))

                # Don't forget default page.
                if hasattr(parent, 'getDefaultPage'):
                    default_page = getDefaultPage(parent, request=REQUEST)
                    if default_page == obid:
                        parent.setDefaultPage(new_id)

                parent.manage_renameObjects((obid,), (new_id,))
                changed = True

            elif change_title:
                # the rename will have already triggered a reindex
                obj.reindexObject()
            if changed:
                success[path] = (new_id, new_title)
        except ConflictError:
            raise
        except Exception, e:
            if handle_errors:
                # skip this object but continue with sub-objects.
                sp.rollback()
                failure[path] = e
            else:
                raise
    transaction_note('Renamed %s' % str(success.keys()))
    return success, failure
