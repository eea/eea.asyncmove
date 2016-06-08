""" Content-rules string substitution
"""
from plone.stringinterp.adapters import BaseSubstitution

class FolderMoveFrom(BaseSubstitution):
    """ Move folder from substitution
    """
    category = u'AsyncMove'
    description = u'Move folder from'

    def safe_call(self):
        """ Safe call
        """
        return getattr(self.context, 'folder_move_from', '')

class FolderMoveTo(BaseSubstitution):
    """ Move folder to substitution
    """
    category = u'AsyncMove'
    description = u'Move folder to'

    def safe_call(self):
        """ Safe call
        """
        return getattr(self.context, 'folder_move_to', '')

class FolderMoveObjects(BaseSubstitution):
    """ Move folder objects substitution
    """
    category = u'AsyncMove'
    description = u'Move folder objects'

    def safe_call(self):
        """ Safe call
        """
        return getattr(self.context, 'folder_move_objects', '')

class FolderMoveEmail(BaseSubstitution):
    """ Move folder email substitution
    """
    category = u'AsyncMove'
    description = u'Move folder e-mail'

    def safe_call(self):
        """ Safe call
        """
        return getattr(self.context, 'asyncmove_email', '')
