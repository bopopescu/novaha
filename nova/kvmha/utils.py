#
#    KVM HA in OpenStack
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
KVMHA Service Utils
"""

from oslo.config import cfg
from oslo import messaging
from nova import availability_zones
from nova import block_device
from nova import compute
from nova import manager
from nova import servicegroup
from nova.compute import api as compute_api
from nova import context
from nova import db
from nova import exception
from nova.openstack.common.gettextutils import _
from nova.openstack.common import importutils
from nova.openstack.common import jsonutils
from nova.openstack.common import log as logging
from nova.openstack.common import timeutils
from nova.openstack.common import uuidutils
from nova import quota
from nova import utils
from nova.virt import block_device as driver_block_device
from nova.virt import event
from nova.virt import fake
from nova.volume import cinder
from novaclient.client import Client
from keystoneclient.auth.identity import v2
from keystoneclient import session

util_opts = [
    cfg.StrOpt('client_version',
               default=3,
               help='Client version for authorization'),
    ]

CONF = cfg.CONF
CONF.register_opts(util_opts)
LOG = logging.getLogger(__name__)



def auth_client(auth_url, password):
    """
    Authorization for server evacuate.
    """
    auth = v2.Password(auth_url=auth_url,
                       username='admin', password=password,
                       tenant_name='admin')
    sess = session.Session(auth=auth)
    nova_evacuate = Client(CONF.client_version, session=sess)

    return nova_evacuate
