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

from nova.compute import utils as compute_utils
from nova.compute import vm_states
from nova.conductor import api as conductor_api
from nova import db
from nova import exception
from nova import notifications
from nova.openstack.common.gettextutils import _
from nova.openstack.common import importutils
from nova.openstack.common import log as logging
from nova.openstack.common import timeutils
from nova import rpc
from nova import servicegroup

LOG = logging.getLogger(__name__)

CONF = cfg.CONF

class KVMHA(object):
    """The base class that all KVMHA classes should inherit from."""

    def __init__(self):
        self.servicegroup_api = servicegroup.API()

    def run_periodic_tasks(self, context):
        """Manager calls this so drivers can perform periodic tasks."""
        print("run_periodic_tasks???????\n")
        pass

