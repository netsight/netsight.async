from AccessControl import ClassSecurityInfo

from OFS.SimpleItem import SimpleItem
from persistent.dict import PersistentDict
from Products.CMFCore.utils import UniqueObject
    
from netsight.async import config


class ProcessRegistry(SimpleItem, UniqueObject):
    
    security = ClassSecurityInfo()
    
    portal_type = config.PROCESS_REGISTRY_TYPE
    
    def __init__(self, *args, **kwargs):
        self._process_registry = PersistentDict()


def _add_process_registry(app):
    app[config.PROCESS_REGISTRY_ID] = ProcessRegistry(config.PROCESS_REGISTRY_ID)
    return app.get(config.PROCESS_REGISTRY_ID)


def getProcessRegistry(context):
    app = context.getPhysicalRoot()
    if config.PROCESS_REGISTRY_ID not in app.objectIds():
        _add_process_registry(app)
        
    return app.get(config.PROCESS_REGISTRY_ID)._process_registry