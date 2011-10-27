from Products.Five import zcml
from Products.Five import fiveconfigure
from Zope2.App.schema import configure_vocabulary_registry
from Testing.ZopeTestCase.ZopeTestCase import ZopeTestCase
from Testing.ZopeTestCase.layer import ZopeLiteLayer, onsetup
from Testing.ZopeTestCase import ZopeLite

@onsetup
def setup_product():
    fiveconfigure.debug_mode = True
    ZopeLite.installProduct('Five', quiet=1)
    zcml.load_site()
    configure_vocabulary_registry()
    
    import Products.CMFCore
    import Products.Five
    import Products.GenericSetup
    import zope.i18n
    import netsight.async
        
    zcml.load_config('meta.zcml', Products.GenericSetup)
    zcml.load_config('meta.zcml', Products.Five) #@UndefinedVariable
    zcml.load_config('meta.zcml', zope.i18n) #@UndefinedVariable
    zcml.load_config('configure.zcml', Products.Five) #@UndefinedVariable
    zcml.load_config('configure.zcml', Products.CMFCore)
    zcml.load_config('configure.zcml', netsight.async) #@UndefinedVariable
    fiveconfigure.debug_mode = False


class BaseTestCase(ZopeTestCase):
    
    layer = ZopeLiteLayer