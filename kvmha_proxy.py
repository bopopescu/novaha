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
from nova.compute import api as compute_api
from nova.compute import flavors
from nova.compute import manager as compute_manager
from nova.compute import power_state
from nova.compute import rpcapi as compute_rpcapi
from nova.compute import task_states
from nova.compute import utils as compute_utils
from nova.compute import vm_states
from nova.conductor import manager as conductor_manager
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
from nova import policy
from nova import quota
from nova import utils
from nova.virt import block_device as driver_block_device
from nova.virt import event
from nova.virt import fake
from nova.volume import cinder

QUOTAS = quota.QUOTAS
LOG = logging.getLogger(__name__)
CONF = cfg.CONF
CONF.import_opt('compute_manager', 'nova.service')
CONF.import_opt('host', 'nova.netconf')
CONF.import_opt('live_migration_retry_count', 'nova.compute.manager')
CONF.import_opt('default_ephemeral_format', 'nova.virt.driver')


class Daemon:
    """
    A generic daemon class.
    
    Usage: subclass the Daemon class and override the _run() method
    """
    def __init__(self, pidfile, stdin='/dev/null', stdout='/dev/null', stderr='/dev/null'):
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.pidfile = pidfile

    def _daemonize(self):
        """
        Start a deamon to execute periodic task to check status of
        compute nodes from DB.
        """
        # 1st fork
        try:
            pid = os.fork()
            if pid > 0:
                # first parent returns
                sys.exit(0)
        except OSError, e:
            sys.stderr.error("fork #1 failed: %d (%s)" % (
                e.errno, e.strerror))
            sys.exit(1)

        # decouple from parent environment
        os.setsid()
        os.chdir("/")
        os.umask(0)

        # 2nd fork
        try:
            pid = os.fork()
            if pid > 0:
                # second parent exits
                sys.exit(0)
        except OSError, e:
            sys.stderr.error("fork #2 failed: %d (%s)" % (
                e.errno, e.strerror))
            sys.exit(1)

        # redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        si = file(self.stdin, 'r')
        so = file(self.stdout, 'a+')
        se = file(self.stderr, 'a+', 0)
        #os.dup2(si.fileno(), sys.stdin.fileno())
        #os.dup2(so.fileno(), sys.stdout.fileno())
        #os.dup2(se.fileno(), sys.stderr.fileno())

        atexit.register(self.delpid)
        pid = str(os.getpid())
        file(self.pidfile,'w+').write("%s\n" % pid)

    def delpid(self):
        os.remove(self.pidfile)

    def start(self):
        """
        Start the daemon
        """
        # Check for a pidfile to see if the daemon already runs
        try:
            pf = file(self.pidfile,'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None

        if pid:
            message = "pidfile %s already exist. Daemon already running\n"
            sys.stderr.write(message % self.pidfile)
            sys.exit(1)

        # Start the daemon
        self._daemonize()
        self._run()

    def stop(self):
        """
        Stop the daemon
        """
        # Get the pid from the pidfile
        try:
            pf = file(self.pidfile,'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None

        if not pid:
            message = "pidfile %s does not exist. Daemon not running\n"
            sys.stderr.write(message % self.pidfile)
            return # not an error in a restart
        # Try killing the daemon process    
        try:
            while 1:
                os.kill(pid, SIGTERM)
                time.sleep(0.1)
        except OSError, err:
            err = str(err)
            if err.find("No such process") > 0:
                if os.path.exists(self.pidfile):
                    os.remove(self.pidfile)
            else:
                print str(err)
                sys.exit(1)
    def restart(self):
        """
        Restart the daemon
        """
        self.stop()
        self.start()
    def _run(self):
        """
        You should override this method when you subclass Daemon. It will be called after the process has been
        daemonized by start() or restart().
        """

class MyDaemon(Daemon):
    def _detect_failure_host(self):
        """
        Periodicly check in _run() for status of compute hosts.

        Return: Name of the failure compute node if detected.
                None if everything going fine.
        """

    def _get_target_instances(self, host):
        """
        Get VM list running on the target host.
        """
        admin_context = context.get_admin_context()
        instances_list = db.instance_get_all_by_host(admin_context, host,
                                                     columns_to_join=None, use_slave=False)
        #vm_list = ['123']


        return instances_list

    def _lookup_available_node(self, memory):
        """
        Look up an available compute node. Mainly based on memory.
        """
        host_list = get_compute_node_list()
        if memory < host_memory:
            return target_host
        else:
            pop_error

    def _evacuate(self):
        """
        Evacuate VM(s) on the failure node to target host.
        """
        available_node = _detect_failure_host()
        instances_list = _get_target_instances(available_node)
        for instance in instances_list:
            evacuate()

    def _run(self):
        setproctitle.setproctitle('kvmha-proxy')
        while True:
            test_list = self._get_target_instances('ubuntu')
            print("### test_list = %s" % test_list)
            time.sleep(10)


def main():
    """
    child = _daemonize()
    print("child = %d" % child)
    if not child:
        return
    """
    daemon = MyDaemon('/tmp/daemon-example.pid')
    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            daemon.start()
        elif 'stop' == sys.argv[1]:
            daemon.stop()
        elif 'restart' == sys.argv[1]:
            daemon.restart()
        else:
            print "Unknown command"
            sys.exit(2)
        sys.exit(0)
    else:
        print "usage: %s start|stop|restart" % sys.argv[0]
        sys.exit(2)
    
if __name__ == "__main__":
    main()
