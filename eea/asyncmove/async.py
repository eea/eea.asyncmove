""" Async move
"""
import sys
import logging
from cgi import escape
from plone.uuid.interfaces import IUUID
from Acquisition._Acquisition import aq_inner, aq_base
from Acquisition._Acquisition import aq_parent
from OFS.CopySupport import CopyError, eNoData, _cb_decode
from OFS.CopySupport import eInvalid, eNotFound, sanity_check
from OFS.CopySupport import eNoItemsSpecified, eNotSupported
from OFS.Moniker import loadMoniker
from OFS.subscribers import compatibilityCall
from Products.CMFCore.utils import getToolByName
from ZODB.POSException import ConflictError
from ZPublisher.HTTPRequest import HTTPRequest
from ZPublisher.HTTPResponse import HTTPResponse
from zope import event
from zope.annotation import IAnnotations
from eea.asyncmove.interfaces import IContextWrapper
from Products.Archetypes.interfaces.base import IBaseObject
from App.Dialogs import MessageDialog
from eea.asyncmove.events.async import AsyncMoveSaveProgress
logger = logging.getLogger('eea.asyncmove')


JOB_PROGRESS_DETAILS = {
    25: 'Uncatalog and delete objects under old position',
    50: 'Copy objects under the new position',
    75: 'Reindexing objects under new position',
    100: 'Completed',
}

def uncatalog_object(obj, catalog):
    """ Remove object from catalog
    """
    ctool = getToolByName(obj, catalog, None)
    if not ctool:
        return

    brains = ctool(UID=IUUID(obj))
    for brain in brains:
        ctool.uncatalog_object(brain.getPath())


def unindex_object(obj, recursive=0):
    """ Unindex the given object

    If 'recursive' is true then also take unindex of all sub-objects.
    """
    if not IBaseObject.providedBy(obj):
        return

    try:
        obj.unindexObject()
        uncatalog_object(obj, 'uid_catalog')
        uncatalog_object(obj, 'reference_catalog')

        # Also unindex AT References
        if hasattr(obj, 'at_references'):
            refs = getattr(obj.at_references, 'objectValues', lambda: ())()
            for ref in refs:
                ref.unindexObject()
                uncatalog_object(ref, 'uid_catalog')
                uncatalog_object(ref, 'reference_catalog')
    except Exception, err:
        logger.warn("Couldn't unindex obj --> %s",
                    getattr(obj, 'absolute_url', lambda: 'None')())
        logger.exception(err)

    # No need to unindex Topic criteria
    if getattr(obj, 'portal_type', None) in ('Topic', 'Collection'):
        return

    if recursive:
        children = getattr(obj, 'objectValues', lambda: ())()
        for child in children:
            reindex_object(child, recursive)


def reindex_object(obj, recursive=0):
    """reindex the given object.

    If 'recursive' is true then also take reindex of all sub-objects.
    """
    if not IBaseObject.providedBy(obj):
        return

    try:
        obj.reindexObject()

        # Also reindex AT References
        if hasattr(obj, 'at_references'):
            refs = getattr(obj.at_references, 'objectValues', lambda: ())()
            for ref in refs:
                ref.reindexObject()
    except Exception, err:
        logger.warn("Couldn't reindex obj --> %s",
                    getattr(obj, 'absolute_url', lambda: 'None')())
        logger.exception(err)

    # No need to reindex Topic criteria
    if getattr(obj, 'portal_type', None) in ('Topic', 'Collection'):
        return

    if recursive:
        children = getattr(obj, 'objectValues', lambda: ())()
        for child in children:
            reindex_object(child, recursive)


def manage_pasteObjects_no_events(self, cb_copy_data=None, REQUEST=None):
    """Paste previously copied objects into the current object.
    If calling manage_pasteObjects from python code, pass the result of a
    previous call to manage_cutObjects or manage_copyObjects as the first
    argument.
    Also sends IObjectCopiedEvent and IObjectClonedEvent
    or IObjectWillBeMovedEvent and IObjectMovedEvent.
    """

    anno = IAnnotations(self)
    job_id = anno.get('async_move_job')

    if not REQUEST:
        # Create a request to work with
        response = HTTPResponse(stdout=sys.stdout)
        env = {'SERVER_NAME':'fake_server',
               'SERVER_PORT':'80',
               'REQUEST_METHOD':'GET'}
        REQUEST = HTTPRequest(sys.stdin, env, response)

    if cb_copy_data is not None:
        cp = cb_copy_data
    elif REQUEST is not None and REQUEST.has_key('__cp'):
        cp = REQUEST['__cp']
    else:
        cp = None
    if cp is None:
        raise CopyError(eNoData)

    try:
        op, mdatas = _cb_decode(cp)
    except:
        raise CopyError(eInvalid)

    oblist = []
    app = self.getPhysicalRoot()
    cat = getToolByName(self, 'portal_catalog')

    for mdata in mdatas:
        m = loadMoniker(mdata)
        try:
            ob = m.bind(app)
        except ConflictError:
            raise
        except:
            raise CopyError(eNotFound)
        # self._verifyObjectPaste(ob, validate_src=op+1)
        oblist.append(ob)

    result = []

    steps = oblist and int(100/len(oblist)) or 0

    event.notify(AsyncMoveSaveProgress(
        self, operation='initialize', job_id=job_id, oblist_id=[
            (o.getId(), o.Title()) for o in oblist
    ]))

    if op == 0:
        # Copy operation
        for i, ob in enumerate(oblist):
            orig_id = ob.getId()
            if not ob.cb_isCopyable():
                raise CopyError(eNotSupported % escape(orig_id))

            oid = self._get_id(orig_id)
            result.append({'id': orig_id, 'new_id': oid})

            event.notify(AsyncMoveSaveProgress(
                self,
                operation='sub_progress',
                job_id=job_id,
                obj_id=ob.getId(), progress=.25
            ))

            ob = ob._getCopy(self)
            ob._setId(oid)

            event.notify(AsyncMoveSaveProgress(
                self,
                operation='sub_progress',
                job_id=job_id,
                obj_id=ob.getId(),
                progress=.50
            ))

            self._setObject(oid, ob)
            ob = self._getOb(oid)
            ob.wl_clearLocks()

            event.notify(AsyncMoveSaveProgress(
                self,
                operation='sub_progress',
                job_id=job_id,
                obj_id=ob.getId(),
                progress=.75
            ))

            ob._postCopy(self, op=0)

            compatibilityCall('manage_afterClone', ob, ob)

            event.notify(AsyncMoveSaveProgress(
                self,
                operation='sub_progress',
                job_id=job_id,
                obj_id=ob.getId(),
                progress=1
            ))

            event.notify(AsyncMoveSaveProgress(
                self,
                operation='progress',
                job_id=job_id,
                progress=steps*(i+1)/100
            ))

    if op == 1:
        # Move operation
        for i, ob in enumerate(oblist):
            orig_id = ob.getId()

            if not sanity_check(self, ob):
                raise CopyError(
                    "This object cannot be pasted into itself")

            orig_container = aq_parent(aq_inner(ob))
            if aq_base(orig_container) is aq_base(self):
                oid = orig_id
            else:
                oid = self._get_id(orig_id)
            result.append({'id': orig_id, 'new_id': oid})

            unindex_object(ob, recursive=1)
            # try to make ownership explicit so that it gets carried
            # along to the new location if needed.
            ob.manage_changeOwnershipType(explicit=1)

            event.notify(AsyncMoveSaveProgress(
                self,
                operation='sub_progress',
                job_id=job_id,
                obj_id=ob.getId(),
                progress=.25
            ))

            try:
                obj_path = '/'.join(
                    orig_container.getPhysicalPath()) + '/' + orig_id
                orig_container._delObject(orig_id, suppress_events=True)
                try:
                    uncatalog_objs = cat(path=obj_path)
                    uncatalog_path = obj_path
                    for obj_brain in uncatalog_objs:
                        uncatalog_path = obj_brain.getPath()
                        cat.uncatalog_object(uncatalog_path)
                except AttributeError:
                    logger.warn("%s could not be found", uncatalog_path)
            except TypeError:
                orig_container._delObject(orig_id)
                logger.warn(
                    "%s._delObject without suppress_events is discouraged.",
                    orig_container.__class__.__name__)

            event.notify(AsyncMoveSaveProgress(
                self,
                operation='sub_progress',
                job_id=job_id,
                obj_id=ob.getId(),
                progress=.50
            ))

            ob = aq_base(ob)
            ob._setId(oid)

            try:
                self._setObject(oid, ob, set_owner=0, suppress_events=True)
            except TypeError:
                self._setObject(oid, ob, set_owner=0)
                logger.warn(
                    "%s._setObject without suppress_events is discouraged.",
                    self.__class__.__name__)
            ob = self._getOb(oid)

            ob._postCopy(self, op=1)
            # try to make ownership implicit if possible
            ob.manage_changeOwnershipType(explicit=0)

            event.notify(AsyncMoveSaveProgress(
                self,
                operation='sub_progress',
                job_id=job_id,
                obj_id=ob.getId(),
                progress=.75
            ))

            reindex_object(ob, recursive=1)

            event.notify(AsyncMoveSaveProgress(
                self,
                operation='sub_progress',
                job_id=job_id,
                obj_id=ob.getId(),
                progress=1
            ))

            event.notify(AsyncMoveSaveProgress(
                self,
                operation='progress',
                job_id=job_id,
                progress=steps*(i+1)/100
            ))

    event.notify(AsyncMoveSaveProgress(
        self, operation='progress', job_id=job_id,
        progress=1
    ))
    del anno['async_move_job']

    return result


def async_move(context, success_event, fail_event, **kwargs):
    """ Async job
    """
    newid = kwargs.get('newid', '')
    email = kwargs.get('email', '')

    anno = IAnnotations(context)
    job_id = anno.get('async_move_job')

    if not newid:
        wrapper = IContextWrapper(context)(
            error=u'Invalid newid'
        )
        event.notify(fail_event(wrapper))
        raise CopyError(eNoItemsSpecified)

    try:
        _op, mdatas = _cb_decode(newid)
    except:
        raise CopyError(eInvalid)
    oblist = []
    app = context.getPhysicalRoot()

    for mdata in mdatas:
        m = loadMoniker(mdata)
        try:
            ob = m.bind(app)
        except ConflictError:
            raise
        except:
            raise CopyError(eNotFound)

        oblist.append(ob)

    wrapper = IContextWrapper(context)(
        folder_move_from=oblist and aq_parent(
            aq_inner(oblist[0])).absolute_url(),
        folder_move_to=context.absolute_url(),
        folder_move_objects=', '.join([obj.getId() for obj in oblist]),
        asyncmove_email=email,
    )

    try:
        manage_pasteObjects_no_events(context, cb_copy_data=newid)
    except Exception, err:
        wrapper.error = err.message
        wrapper.job_id = job_id

        event.notify(fail_event(wrapper))
        raise CopyError(MessageDialog(
            title='Error',
            message=err.message,
            action='manage_main',
        ))

    event.notify(success_event(wrapper))
