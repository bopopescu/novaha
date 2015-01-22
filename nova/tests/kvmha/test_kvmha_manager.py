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

    @mock.patch('nova.kvmha.manager.KvmhaManager._sum_instances_memory')
    def test_sum_instances_memory(self, sum_instances_memory):
        fake_host = 'fake-host'
        fake_memory = 1024
        sum_instances_memory.return_value = fake_memory
        total_memory = self.kvmha._sum_instances_memory(fake_host)
        self.assertEqual(fake_memory, total_memory)

    @mock.patch('nova.kvmha.manager.KvmhaManager._get_hosts')
    def test_get_hosts(self, get_hosts):
        fake_hosts = ['fake1', 'fake2']
        get_hosts.return_value = fake_hosts
        host_list = self.kvmha._get_hosts()
        self.assertEqual(host_list, fake_hosts)

    @mock.patch('nova.kvmha.manager.KvmhaManager._get_available_memory')
    def test_get_available_memory(self, get_available_memory):
        fake_host = 'fake-host'
        fake_memory = 1024
        get_available_memory.return_value = fake_memory
        current_memory = self.kvmha._get_available_memory(fake_host)
        self.assertEqual(current_memory, fake_memory)

    @mock.patch('nova.kvmha.manager.KvmhaManager._lookup_available_node')
    def test_lookup_available_node(self, lookup_available_node):
        fake_host = 'fake-host'
        expected_host = 'expected_host'
        lookup_available_node.return_value = expected_host
        target_host = self.kvmha._lookup_available_node(fake_host)
        self.assertEqual(expected_host, target_host)

