import sys
import warnings
from Acquisition._Acquisition import aq_inner, aq_base
from Acquisition._Acquisition import aq_parent
from OFS.CopySupport import cookie_path, CopyError, eNoData, _cb_decode, eInvalid, eNotFound
from OFS.Moniker import loadMoniker
from Products.CMFCore.utils import getToolByName
from ZODB.POSException import ConflictError
from ZPublisher.HTTPRequest import HTTPRequest
from ZPublisher.HTTPResponse import HTTPResponse


def manage_pasteObjects_no_events(self, cb_copy_data=None, REQUEST=None):
    """Paste previously copied objects into the current object.
    If calling manage_pasteObjects from python code, pass the result of a
    previous call to manage_cutObjects or manage_copyObjects as the first
    argument.
    Also sends IObjectCopiedEvent and IObjectClonedEvent
    or IObjectWillBeMovedEvent and IObjectMovedEvent.
    """
    import pdb; pdb.set_trace()
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
    response = HTTPResponse(stdout=sys.stdout)
    env = {'SERVER_NAME':'fake_server',
           'SERVER_PORT':'80',
           'REQUEST_METHOD':'GET'}
    # create fake request needed for reindexObject
    request = HTTPRequest(sys.stdin, env, response)

    if op == 1:
        # Move operation
        for ob in oblist:
            orig_id = ob.getId()
            # if not ob.cb_isMoveable():
            #     raise CopyError(eNotSupported % escape(orig_id))

            # try:
            #     ob._notifyOfCopyTo(self, op=1)
            # except ConflictError:
            #     raise
            # except:
            #     raise CopyError(MessageDialog(
            #         title="Move Error",
            #         message=sys.exc_info()[1],
            #         action='manage_main'))
            #
            # if not sanity_check(self, ob):
            #     raise CopyError(
            #         "This object cannot be pasted into itself")

            orig_container = aq_parent(aq_inner(ob))
            if aq_base(orig_container) is aq_base(self):
                id = orig_id
            else:
                id = self._get_id(orig_id)
            result.append({'id': orig_id, 'new_id': id})

            # notify(ObjectWillBeMovedEvent(ob, orig_container, orig_id,
            #                               self, id))

            # try to make ownership explicit so that it gets carried
            # along to the new location if needed.
            ob.manage_changeOwnershipType(explicit=1)

            try:
                orig_container_url = '/' + orig_container.absolute_url(1) + '/'
                cat = getToolByName(orig_container, 'portal_catalog')
                obj_path = orig_container_url + orig_id
                try:
                    cat.uncatalog_object(obj_path)
                except AttributeError:
                    warnings.warn("%s could not be found" % obj_path)

                for obj_id in ob.objectIds():
                    cat.uncatalog_object(obj_path + '/' + obj_id)
                orig_container._delObject(orig_id, suppress_events=True)

            except TypeError:
                orig_container._delObject(orig_id)
                warnings.warn(
                    "%s._delObject without suppress_events is discouraged."
                    % orig_container.__class__.__name__,
                    DeprecationWarning)
            ob = aq_base(ob)
            ob._setId(id)

            try:
                self._setObject(id, ob, set_owner=0, suppress_events=True)
            except TypeError:
                self._setObject(id, ob, set_owner=0)
                warnings.warn(
                    "%s._setObject without suppress_events is discouraged."
                    % self.__class__.__name__, DeprecationWarning)
            ob = self._getOb(id)

            # if not ob.get('REQUEST'):
            #     ob.REQUEST = REQUEST
            # notify(ObjectMovedEvent(ob, orig_container, orig_id, self, id))
            # notifyContainerModified(orig_container)
            # if aq_base(orig_container) is not aq_base(self):
            #     notifyContainerModified(self)

            ob._postCopy(self, op=1)
            # try to make ownership implicit if possible
            ob.manage_changeOwnershipType(explicit=0)
            ob.reindexObject()
            for objs in ob.objectValues():
                try:
                    objs.REQUEST = request
                    objs.reindexObject()
                    del objs.REQUEST
                except Exception:
                    warnings.warn('coulnt reindex obj --> %s', objs.absolute_url(1))

        if REQUEST is not None:
            REQUEST['RESPONSE'].setCookie('__cp', 'deleted',
                                          path='%s' % cookie_path(REQUEST),
                                          expires='Wed, 31-Dec-97 23:59:59 GMT')
            REQUEST['__cp'] = None
            return self.manage_main(self, REQUEST, update_menu=1,
                                    cb_dataValid=0)

    return result


def async_move(context, newid):
    manage_pasteObjects_no_events(context, newid)
