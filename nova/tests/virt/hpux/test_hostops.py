__author__ = 'psteam'

import mock

from nova import test
from nova.virt.hpux import hostops


class HostOpsTestCase(test.TestCase):

    def setUp(self):
        super(HostOpsTestCase, self).setUp()

    @mock.patch.object(hostops.HostOps, '_update_status')
    def test_get_host_stats(self, mock_update_status):
        pass
