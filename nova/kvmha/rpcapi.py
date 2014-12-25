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
Client side of the cert manager RPC API.
"""

from oslo.config import cfg
from oslo import messaging

from nova import rpc

rpcapi_opts = [
    cfg.StrOpt('kvmha_topic',
               default='kvmha',
               help='The topic kvmha nodes listen on'),
]

CONF = cfg.CONF
CONF.register_opts(rpcapi_opts)

rpcapi_cap_opt = cfg.StrOpt('kvmha',
        help='Set a version cap for messages sent to kvmha services')
CONF.register_opt(rpcapi_cap_opt, 'upgrade_levels')

class KvmhaAPI(object):
    '''Client side of the kvmha rpc API.'''

    VERSION_ALIASES = {
        'grizzly': '2.27',
        'havana': '2.47',
        'icehouse-compat': '3.0',
    }

    def __init__(self):
        super(KvmhaAPI, self).__init__()
        target = messaging.Target(topic=CONF.kvmha_topic, version='3.0')
        version_cap = self.VERSION_ALIASES.get(CONF.upgrade_levels.kvmha,
                                               CONF.upgrade_levels.kvmha)
        self.client = rpc.get_client(target, version_cap=version_cap)

    #def kvmha_test(self, ctxt):
        #version = self._get_compat_version('2.0', '1.0')
    #    cctxt = self.client.prepare(version=version)
    #    return cctxt.call(ctxt, 'kvmha_test')

