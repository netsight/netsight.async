from Products.CMFCore.utils import ToolInit

from netsight.async.registry import ProcessRegistry
from netsight.async import config


def initialize(context):
    ToolInit(config.PROCESS_REGISTRY_TYPE, [ProcessRegistry]).initialize(context)