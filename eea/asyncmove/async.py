""" Async jobs
"""
from zope.interface import implementer
from Acquisition import Implicit
from eea.asyncmove.interfaces import IContextWrapper


#
# Custom context
#
@implementer(IContextWrapper)
class ContextWrapper(Implicit):
    """ Context wrapper
    """
    def __init__(self, context):
        self.context = context

    def __call__(self, *args, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        return self.__of__(self.context)
