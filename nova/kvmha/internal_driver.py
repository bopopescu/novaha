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
Detect failure of compute nodes. Provides the scheduler with
useful information about availability through kinds of approach.
"""

from nova import servicegroup
from nova import db
from nova import context
from nova import availability_zones
from nova.openstack.common import log as logging
from nova.openstack.common import timeutils
from nova.openstack.common import uuidutils
from nova.openstack.common.gettextutils import _

LOG = logging.getLogger(__name__)


class MonitorManager(object):
    """
    Monitor module by checking OpenStack service to detect
    host failure.
    """
    pass


def detect_failure_host():
    """
    Periodicly check in kvm_proxy_run() for status of compute hosts.
    Approach via service status.

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

monitor_manager = MonitorManager()
