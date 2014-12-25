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

from nova import config
from nova.openstack.common import log as logging
from nova.openstack.common.report import guru_meditation_report as gmr
from nova import service
from nova import utils
from nova import version
#from nova.kvmha import kvmha_proxy

CONF = cfg.CONF
CONF.import_opt('kvmha_topic', 'nova.kvmha.rpcapi')
#CONF.import_opt('topic', 'nova.kvmha.opts', group='kvmha')
#CONF.import_opt('manager', 'nova.kvmha.opts', group='kvmha')


def main():
    config.parse_args(sys.argv)
    logging.setup('nova')
    utils.monkey_patch()

    gmr.TextGuruMeditation.setup_autorun(version)

    #daemon = kvmha_proxy.MyDaemon('/tmp/daemon-example.pid')
    server = service.Service.create(binary='nova-kvmha', topic=CONF.kvmha_topic)
    service.serve(server)
    service.wait()


#if __name__ == "__main__":
#    main()

