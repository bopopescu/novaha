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

import sys

from oslo.config import cfg

from nova.openstack.common.gettextutils import _
from nova.openstack.common import importutils
from nova.openstack.common import log as logging


driver_opts = [
    cfg.StrOpt('kvmha_driver',
               default='nova.kvmha.internal_driver',
               help='Driver to use for monitor host'),
]
CONF = cfg.CONF
CONF.register_opts(driver_opts)

LOG = logging.getLogger(__name__)


def load_kvmha_driver(kvmha_driver=None):
    if not kvmha_driver:
        kvmha_driver = CONF.kvmha_driver

    if not kvmha_driver:
        LOG.error(_("KVM HA driver option required, but not specified"))
        sys.exit(1)

    LOG.info(_("Loading KVM HA driver '%s'") % kvmha_driver)

    return importutils.import_module(kvmha_driver)

