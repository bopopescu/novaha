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
KVMHA Service Manager
"""

import contextlib
import datetime
import operator
import os
import sys
import setproctitle
import testtools
import time
import traceback
import uuid
import atexit

import mox
from oslo.config import cfg
from oslo import messaging
import six
from testtools import matchers as testtools_matchers
from signal import SIGTERM

import nova
from nova import availability_zones
from nova import block_device
from nova import compute
from nova import manager
#from nova.compute import api as compute_api
from nova.compute import flavors
from nova.compute import manager as compute_manager
from nova.compute import power_state
from nova.compute import rpcapi as compute_rpcapi
from nova.compute import task_states
from nova.compute import utils as compute_utils
from nova.compute import vm_states
from nova.conductor import manager as conductor_manager
from nova.kvmha import rpcapi as kvmha_rpcai
from nova import context
from nova import db
from nova import exception
from nova.image import glance
from nova.network import api as network_api
from nova.network import model as network_model
from nova.network.security_group import openstack_driver
from nova.objects import base as obj_base
from nova.objects import block_device as block_device_obj
from nova.objects import instance as instance_obj
from nova.objects import instance_group as instance_group_obj
from nova.objects import migration as migration_obj
from nova.objects import quotas as quotas_obj
from nova.openstack.common.gettextutils import _
from nova.openstack.common import importutils
from nova.openstack.common import jsonutils
from nova.openstack.common import log as logging
from nova.openstack.common import timeutils
from nova.openstack.common import uuidutils
from nova.openstack.common import periodic_task
from nova import policy
from nova import quota
from nova import utils
from nova.virt import block_device as driver_block_device
from nova.virt import event
from nova.virt import fake
from nova.volume import cinder


LOG = logging.getLogger(__name__)
CONF = cfg.CONF


QUOTAS = quota.QUOTAS


class KvmhaManager(manager.Manager):

    target = messaging.Target(version='3.23')

    def __init__(self, *args, **kwargs):
        #if not kvmha_driver:
        #    kvmha_driver = CONF.kvmha_driver
        #self.driver = importutils.import_object(kvmha_driver)
        #self.compute_api = compute.API()
        #print("!!!!!!!!!!!!!!!!!!!!!!!1\n")
        super(KvmhaManager, self).__init__(service_name='kvmha',
                                           *args, **kwargs)
        #print("!!!!!!!!!!!!!!!!!!!!!!!1\n")

    #def init_host(self):
    #    pass

    #@periodic_task.periodic_task(spacing=CONF.detect_host_failure_interval)
    #def kvmha_test(self, context):
    #    """KVM HA test"""
    #    print("KVM HA\n")

    @periodic_task.periodic_task
    def kvmha_test_print(self, context, start_time=None):
        """track for periodic task code path."""
        print("############### :-)")


