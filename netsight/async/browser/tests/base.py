from Products.Five import zcml
from Products.Five import fiveconfigure
from Testing.ZopeTestCase import PortalTestCase as ptc

def setup_product():
    fiveconfigure.debug_mode = True
    import netsight.async
    zcml.load_config('configure.zcml', netsight.async) #@UndefinedVariable
    fiveconfigure.debug_mode = False


setup_product()

import netsight.async
netsight.async.initialize(None)


class BaseTestCase(ptc.PortalTestCase):
    pass