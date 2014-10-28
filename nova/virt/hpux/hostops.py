__author__ = 'psteam'

"""
Management class for host operations.
"""

from nova import context
from nova import db
from nova.openstack.common.gettextutils import _
from nova.openstack.common import jsonutils
from nova.openstack.common import log as logging
from nova.virt.hpux import utils
from oslo.config import cfg
from xml.dom import minidom

CONF = cfg.CONF

LOG = logging.getLogger(__name__)


class HostOps(object):
    def __init__(self):
        self._stats = None

    def _get_cpu_and_memory_mb_free(self, ip_addr):
        """Get the free cpu core and memory size(MB) of nPar.

        :param ip_addr: IP address of specified nPar
        :returns: A dict containing:
             :cpus_free: How much cpu is free
             :memory_free: How much space is free (in MB)
        """
        info = {'cpus_free': 0, 'mem_free': 0}
        cmd_for_npar = {
            'username': CONF.hpux.username,
            'password': CONF.hpux.password,
            'ip_address': ip_addr,
            'command': '/opt/hpvm/bin/vparstatus -A'
        }
        exec_result = utils.ExecRemoteCmd().exec_remote_cmd(**cmd_for_npar)
        results = exec_result.strip().split('\n')
        for item in results:
            if 'Available CPUs' in item:
                # item likes '[Available CPUs]:  5\r'
                info['cpus_free'] = int(item.split(':')[1].strip())
            elif 'Available Memory' in item:
                # item likes '[Available Memory]:  55936 Mbytes\r'
                info['mem_free'] = int(item.split(':')[1].split()[0].strip())
            else:
                continue
        return info

    def _get_local_gb_info(self, ip_addr):
        """Get local storage info of the compute node in GB.

        :param ip_addr: IP address of specified nPar
        :returns: A dict containing:
             :total: How big the overall usable filesystem is (in gigabytes)
             :free: How much space is free (in gigabytes)
             :used: How much space is used (in gigabytes)
        """
        info = {}
        cmd_for_npar = {
            'username': CONF.hpux.username,
            'password': CONF.hpux.password,
            'ip_address': ip_addr,
            'command': 'vgdisplay ' + CONF.hpux.vg_name
        }
        exec_result = utils.ExecRemoteCmd().exec_remote_cmd(**cmd_for_npar)
        results = exec_result.strip().split('\n')
        for item in results:
            if 'PE Size (Mbytes)' in item:
                # item likes 'PE Size (Mbytes)  64  \r'
                pe_size = int(item.split()[3].strip())
            elif 'Total PE' in item:
                # item likes 'Total PE  8922  \r'
                total_pe = int(item.split()[2].strip())
            elif 'Alloc PE' in item:
                # item likes 'Alloc PE  7469  \r'
                used_pe = int(item.split()[2].strip())
            else:
                continue
        info['total'] = pe_size * total_pe / 1024
        info['used'] = pe_size * used_pe / 1024
        info['free'] = info['total'] - info['used']
        return info

    def _get_hypervisor_type(self):
        """Get hypervisor type.

        :returns: hypervisor type (ex. qemu)

        """
        return 'hpux'

    def _get_hypervisor_version(self):
        """Get hypervisor version.

        :returns: hypervisor version (ex. 12003)

        """
        return '20140918'

    def _get_hypervisor_hostname(self):
        """Returns the hostname of the hypervisor."""
        return 'hpux'

    def _get_cpu_info(self):
        """Get cpuinfo information.

        Obtains cpu feature from virConnect.getCapabilities,
        and returns as a json string.

        :return: see above description

        """
        cpu_info = dict()

        return jsonutils.dumps(cpu_info)

    def _get_client_list(self):
        """Get client (npar/vpar) list."""
        npar_list = []
        vpar_list = []
        cmd_for_ignite = {
            'username': CONF.hpux.username,
            'password': CONF.hpux.password,
            'ip_address': CONF.hpux.ignite_ip,
            'command': '/opt/ignite/bin/ignite client list -m xml -l details'
        }
        exec_result = utils.ExecRemoteCmd().exec_remote_cmd(**cmd_for_ignite)
        dom1 = minidom.parseString(exec_result)
        clients_xml = dom1.getElementsByTagName("iux:client")
        for item in clients_xml:
            client_dict = {'name': '', 'model': '', 'ip_addr': ''}
            client_dict['name'] = item.getAttribute('name')
            attr_list = item.getElementsByTagName('iux:attr')
            for attr in attr_list:
                if attr.getAttribute('name') == 'model':
                    client_dict['model'] = attr.childNodes[0].nodeValue
                elif attr.getAttribute('name') == 'ipaddress':
                    client_dict['ip_addr'] = attr.firstChild.nodeValue
                elif attr.getAttribute('name') == 'hostname':
                    client_dict['hostname'] = attr.firstChild.nodeValue
                elif attr.getAttribute('name') == 'memory':
                    mem = attr.firstChild.nodeValue
                    client_dict['memory'] = int(mem) / 1024
                elif attr.getAttribute('name') == 'cpus':
                    client_dict['cpus'] = int(attr.firstChild.nodeValue)
                else:
                    continue
            if 'nPar' in client_dict['model']:
                npar_list.append(client_dict)
            if 'Virtual Partition' in client_dict['model']:
                vpar_list.append(client_dict)
        return npar_list, vpar_list

    def get_host_stats(self, refresh=False):
        """Return the current state of the host.

        If 'refresh' is True, run update the stats first.
        """
        if refresh or not self._stats:
            self._update_status()
        return self._stats

    def get_available_resource(self):
        """Retrieve resource info.

        This method is called when nova-compute launches, and
        as part of a periodic task.

        :returns: dictionary describing resources

        """
        LOG.debug(_('get_available_resource called'))
        stats = self.get_host_stats(refresh=True)
        stats['supported_instances'] = jsonutils.dumps(
                stats['supported_instances'])
        return stats

    def _update_status(self):
        LOG.debug(_("Updating host stats"))

        data = {
            'vcpus': 0,
            'memory_mb': 0,
            'vcpus_used': 0,
            'memory_mb_used': 0,
            'local_gb': 0,
            'local_gb_used': 0,
            'supported_instances': []
        }
        admin_context = context.get_admin_context()
        npar_list, vpar_list = self._get_client_list()
        # TODO(Sunny): Delete the hard code "npar_list"
        # Do the deletion after all functions are ready,
        # here 'npar_list' is just for testing.
        npar_list = [{'ip_addr': u'192.168.169.100',
                      'name': u'bl890npar1', 'hostname': u'bl890npar1',
                      'cpus': 8, 'memory': 66994944 / 1024,
                      'model': u'ia64 hp Integrity BL890c i4 nPar'}]
        for npar in npar_list:
            update_info = {}
            cpu_mem_dict = self._get_cpu_and_memory_mb_free(npar['ip_addr'])
            disk_info_dict = self._get_local_gb_info(npar['ip_addr'])
            update_info['vcpus_used'] = (npar['cpus'] -
                                         cpu_mem_dict['cpus_free'])
            update_info['memory_used'] = (npar['memory'] -
                                          cpu_mem_dict['mem_free'])
            update_info['vcpus'] = npar['cpus']
            update_info['memory'] = npar['memory']
            update_info['disk'] = disk_info_dict['total']
            update_info['disk_used'] = disk_info_dict['used']
            # Try to create/update npar info into table "nPar_resource"
            npar_res = db.npar_get_by_ip(admin_context, npar['ip_addr'])
            if npar_res:
                if not (npar_res['vcpus'] == update_info['vcpus'] and
                    npar_res['vcpus_used'] == update_info['vcpus_used'] and
                    npar_res['memory'] == update_info['memory'] and
                    npar_res['memory_used'] == update_info['memory_used'] and
                    npar_res['disk'] == update_info['disk'] and
                    npar_res['disk_used'] == update_info['disk_used']):
                    db.npar_resource_update(admin_context,
                                            npar_res['id'], update_info)
            else:
                update_info['ip_addr'] = npar['ip_addr']
                db.npar_resource_create(admin_context, update_info)
            # Sum up all the nPar resources
            data['vcpus'] += npar['cpus']
            data['memory_mb'] += npar['memory']
            data['vcpus_used'] += update_info['vcpus_used']
            data['memory_mb_used'] += update_info['memory_used']
            data['local_gb'] += disk_info_dict['total']
            data['local_gb_used'] += disk_info_dict['used']

        data['hypervisor_type'] = self._get_hypervisor_type()
        data['hypervisor_version'] = self._get_hypervisor_version()
        data['hypervisor_hostname'] = self._get_hypervisor_hostname()
        data['cpu_info'] = self._get_cpu_info()
        self._stats = data

        return data

    def nPar_lookup(self, vPar_info, nPar_list):
        # Initial dispatch policy
        for nPar in nPar_list:
            current_mem = nPar['memory'] - nPar['memory_used']
            current_vcpus = nPar['vcpus'] - nPar['vcpus_used']
            current_disk = nPar['disk'] - nPar['disk_used']
            if (vPar_info['mem'] < current_mem and
                vPar_info['cpu'] < current_vcpus and
                vPar_info['disk'] < current_disk):
                return nPar
        return None
