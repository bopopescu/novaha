#
#    KVM HA in OpenStack (Demo Version)
#
#    Copyright HP, Corp. 2014
#
#    Authors:
#     Lei Li   <li.lei2@hp.com>
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.i
#

"""
Unit Tests for nova.kvmha.internal_driver
"""

import mox
import mock
from oslo.config import cfg

from nova import context
from nova import exception
from nova.kvmha import driver
from nova.openstack.common import importutils
from nova.openstack.common import log as logging
from nova import test
from nova.tests import fake_instance
from nova import utils

CONF = cfg.CONF

LOG = logging.getLogger(__name__)


class InternalDriverTestCase(test.TestCase):

    def setUp(self):
        super(InternalDriverTestCase, self).setUp()
        self.driver = driver.load_kvmha_driver()
        self.context = context.RequestContext('testuser', 'testproject',
                                              is_admin=True)

    def test_detect_failure_host(self):
        expected = None
        actual_hosts = self.driver.detect_failure_host()
        self.assertEqual(actual_hosts, expected)

    @mock.patch('nova.kvmha.internal_driver.detect_failure_host')
    def test_detect_failure_host2(self, detect_failure_host):
        fake_host = ['fake_host']
        detect_failure_host.return_value = fake_host
        failure_host = self.driver.detect_failure_host()
        self.assertEqual(fake_host, failure_host)
