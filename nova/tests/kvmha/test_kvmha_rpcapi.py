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
Unit Tests for nova.kvmha.rpcapi
"""

from oslo.config import cfg
import mock

from nova.kvmha import rpcapi as kvmha_rpcapi
from nova import context
from nova import exception
from nova import test
from nova.tests import fake_instance

CONF = cfg.CONF


class KvmhaAPITestCase(test.NoDBTestCase):
    """Test case for kvmha.api interfaces."""

    def setUp(self):
        super(KvmhaAPITestCase, self).setUp()
        self.fake_topic = 'fake_topic'
        self.fake_context = 'fake_context'
        self.flags(topic=self.fake_topic, enable=True, group='kvmha')
        self.kvmha_rpcapi = kvmha_rpcapi.KvmhaAPI()
