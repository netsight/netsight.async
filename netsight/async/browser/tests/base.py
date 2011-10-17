from Products.Five import zcml
from Products.Five import fiveconfigure
from Products.PloneTestCase import PloneTestCase as ptc
from Products.PloneTestCase.layer import onsetup


@onsetup
def setup_product():
    fiveconfigure.debug_mode = True
    import netsight.async
    zcml.load_config('configure.zcml', netsight.async) #@UndefinedVariable
    fiveconfigure.debug_mode = False


setup_product()
ptc.installPackage('netsight.async')
ptc.setupPloneSite(
    products=(
        'netsight.async', 
        ),
    extension_profiles=(
        'netsight.async:default',
        ),
    )

import netsight.async
netsight.async.initialize(None)


class BaseTestCase(ptc.PloneTestCase):
    pass