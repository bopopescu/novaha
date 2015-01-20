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
Unit Tests for nova.kvmha.manager
"""

import mox
import mock
from oslo.config import cfg

import nova
from nova import context
from nova import exception
#from nova.kvmha import manager as kvmha_manager
from nova.openstack.common import importutils
from nova.openstack.common import log as logging
from nova import test
from nova.tests import fake_instance
from nova import utils

CONF = cfg.CONF
CONF.import_opt('kvmha_manager', 'nova.service')

LOG = logging.getLogger(__name__)


class KvmhaTestCase(test.TestCase):
    def setUp(self):
        super(KvmhaTestCase, self).setUp()
        self.context = context.RequestContext('fake', 'fake')
        self.kvmha = importutils.import_object(CONF.kvmha_manager)

    @mock.patch('nova.kvmha.manager.KvmhaManager._get_target_instances')
    def test_get_target_instances(self, get_target_instances):
        fake_host = 'fake-host'
        fake_instances = ['fake1', 'fake2']
        get_target_instances.return_value = fake_instances
        res = self.kvmha._get_target_instances(fake_host)
        self.assertEqual(fake_instances, res)
