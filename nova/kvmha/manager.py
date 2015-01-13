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
KVMHA Service Manager
"""

import contextlib
import datetime
import operator
import os
import sys
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
from nova import servicegroup
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
from novaclient.client import Client
from keystoneclient.auth.identity import v2
from keystoneclient import session


kvmha_opts = [
    cfg.StrOpt('kvmha_admin_auth_url',
               default='http://localhost:5000/v2.0',
               help='Authorization URL for server evacuate in admin '
               'context'),
    cfg.StrOpt('client_version',
               default=3,
               help='Client version for authorization'),
    cfg.StrOpt('password',
               default='root',
               help='Password for authorization of keystoneclient session '
               'Will get from config file, hardcode here for now'),
    ]

CONF = cfg.CONF
CONF.register_opts(kvmha_opts)

LOG = logging.getLogger(__name__)
QUOTAS = quota.QUOTAS


class KvmhaManager(manager.Manager):

    target = messaging.Target(version='3.23')

    def __init__(self, *args, **kwargs):
        #if not kvmha_driver:
        #    kvmha_driver = CONF.kvmha_driver
        #self.driver = importutils.import_object(kvmha_driver)
        #self.compute_api = compute.API()
        super(KvmhaManager, self).__init__(service_name='kvmha',
                                           *args, **kwargs)

    #def init_host(self):
    #    pass

    #@periodic_task.periodic_task(spacing=CONF.detect_host_failure_interval)
    #def kvmha_test(self, context):
    #    """KVM HA test"""
    #    print("KVM HA\n")

    def _detect_failure_host(self):
        """
        Periodicly check in _run() for status of compute hosts.
        Via service status

        Return: Name of the failure compute node if detected.
                None if everything going fine.
        """
        servicegroup_api = servicegroup.API()
        ctxt = context.get_admin_context()
        services = db.service_get_all(ctxt)
        services = availability_zones.set_availability_zones(ctxt, services)
        compute_services = []
        for service in services:
            if (service['binary'] == 'nova-compute'):
                if not [cs for cs in compute_services if cs['host'] == service['host']]:
                    compute_services.append(service)
        LOG.debug(_("Current compute services: %s" % compute_services))

        for s in compute_services:
            alive = servicegroup_api.service_is_up(s)
            if not alive:
                return s['host']

        return None

    def _get_target_instances(self, host):
        """
        Get VM list running on the target host.
        """
        admin_context = context.get_admin_context()
        instances_list = db.instance_get_all_by_host(admin_context, host,
                                                     columns_to_join=None, use_slave=False)

        return instances_list

    def _sum_instances_memory(self, failure_node):
        """
        Sumlize the total memory for all of the instances that need
        to be evacuated.
        """
        instances_list = self._get_target_instances(failure_node)
        total_memory = 0
        for instance in instances_list:
            instance_memory = instance['memory_mb']
            total_memory += instance_memory

        return total_memory

    def _get_hosts(self):
        """
        Return the list of hosts.
        """
        ctxt = context.get_admin_context()
        services = db.service_get_all(ctxt)
        services = availability_zones.set_availability_zones(ctxt, services)

        hosts = []
        for service in services:
            if not [h for h in hosts if h['host'] == service['host']]:
                hosts.append(service)
        hosts_list = []
        for host in hosts:
            hosts_list.append(host['host'].encode("utf-8"))

        return hosts_list

    def _get_available_memory(self, host):
        """
        Get available memory of gaven host.
        """
        ctxt = context.get_admin_context()
        service_resource = db.service_get_by_compute_host(ctxt, host)
        node_resource = service_resource['compute_node'][0]
        current_memory = node_resource['memory_mb'] - node_resource['memory_mb_used']
        if current_memory < 0:
            LOG.exception(_("Failed to get available node resource"))
        else:
            return current_memory

    def _lookup_available_node(self, failure_node):
        """
        Look up an available compute node. Mainly based on memory.
        """
        host_list = self._get_hosts()
        #target_hosts = host_list.remove(failure_node)
        #target_memory = self._sum_instances_memory(failure_node)

        #for host in target_hosts:
        #    current_memory = _get_available_memory(host)
        #    if target_memory < current_memory:
        #        return host
        #    else:
        #        pop_error

        target_memory = self._sum_instances_memory(failure_node)
        for host in host_list:
            if host is not failure_node:
                current_memory = self._get_available_memory(host)
                if target_memory < current_memory:
                    return host
                else:
                    LOG.exception(_("No available resource"))
            else:
                continue

    def _evacuate(self, failure_host):
        """
        Evacuate VM(s) on the failure node to target host.
        """
        available_node = self._lookup_available_node(failure_host)
        if available_node:

        # The auth_url hardcode here for now, will be replaced when
        # porting to Helion OpenStack environment.
        #auth = v2.Password(auth_url='http://localhost:5000/v2.0/',
        #                   username='admin',
        #                   password='root',
        #                   tenant_name='admin')

            auth = v2.Password(auth_url=CONF.kvmha_admin_auth_url,
                               username='admin',
                               password=CONF.password,
                               tenant_name='admin')
            sess = session.Session(auth=auth)
            nova_evacuate = Client(CONF.client_version, session=sess)

            instances_list = self._get_target_instances(failure_host)
            if instances_list:
                for instance in instances_list:
                # Will point target host when enable shared storage later.

                    ctxt = nova.context.get_admin_context()
                    compute_api = compute.API()
                    #name = instance['display_name']
                    instance_final = compute_api.get(ctxt, instance['id'])
                    check_host = instance_final['host']

                    LOG.audit(_("Checking host: %s") % check_host)

                    #print("check_host = %s" % check_host)
                    #on_shared_storage = False
                    #password = None
                    #res = compute_api.evacuate(self.context.elevated(),
                    #                           instance_final,
                    #                           host='ubuntu',
                    #                           on_shared_storage=False,
                    #                           admin_password=None)

                    res = nova_evacuate.servers.evacuate(instance['uuid'],
                                                         host=available_node,
                                                         on_shared_storage=False,
                                                         password=None)
                    if type(res) is dict:
                        utils.print_dict(res)

                    LOG.audit(_("Instance: %s restarted on host: %s") %
                              (instance['display_name'], available_node))
                    time.sleep(15)
        else:
            LOG.exception(_("Failed to lookup available node"))

        LOG.audit(_("No instance needs to be evacuated"))

    @periodic_task.periodic_task
    def kvmha_proxy_run(self, context, start_time=None):
        """Track for periodic task code path."""
        LOG.audit(_("KVM HA proxy run"))
        failure_host = self._detect_failure_host()
        if failure_host:
            LOG.audit(_("Failure host has been detected: %s" % failure_host))
            self._evacuate(failure_host)

