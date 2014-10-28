__author__ = 'psteam'

"""
A HP-UX Nova Compute driver.
"""

from nova import db
from nova import exception
from nova.openstack.common.gettextutils import _
from nova.openstack.common import log as logging
from nova.virt import driver
from nova.virt.hpux import hostops
from nova.virt.hpux import vparops
from oslo.config import cfg

hpux_opts = [
    cfg.StrOpt('username',
               default='root',
               help='Username for ssh command'),
    cfg.StrOpt('password',
               default='root',
               help='Password for ssh command'),
    cfg.StrOpt('ignite_ip',
               default='192.168.172.51',
               help='IP for ignite server'),
    cfg.IntOpt('ssh_timeout_seconds',
               default=20,
               help='Number of seconds to wait for ssh command'),
    cfg.IntOpt('lanboot_timeout_seconds',
               default=1200,
               help='Number of seconds to wait for lanboot command'),
    cfg.StrOpt('vg_name',
               default='/dev/vg00',
               help='Volume group of nPar for creating logical volume'),
    cfg.StrOpt('management_network',
               default='sitelan',
               help='Management network for vPar'),
    cfg.StrOpt('production_network',
               default='localnet',
               help='Production network for vPar'),
    cfg.StrOpt('network_label',
               default='hpux',
               help='Network label for hpux vPar'),
    ]

CONF = cfg.CONF
CONF.register_opts(hpux_opts, 'hpux')

LOG = logging.getLogger(__name__)


class HPUXDriver(driver.ComputeDriver):
    def __init__(self, virtapi,
                 vparops=vparops.VParOps(),
                 hostops=hostops.HostOps()):
        super(HPUXDriver, self).__init__(virtapi)
        self._vparops = vparops
        self._hostops = hostops

    def init_host(self, host):
        pass

    def list_instances(self):
        return self._vparops.list_instances()

    def get_host_stats(self, refresh=False):
        """Return the current state of the host.

        If 'refresh' is True, run update the stats first.
        """
        return self._hostops.get_host_stats(refresh=refresh)

    def get_available_resource(self, nodename):
        """Retrieve resource information.

        This method is called when nova-compute launches    , and
        as part of a periodic task that records the results in the DB.

        :param nodename: will be put in PCI device
        :returns: dictionary containing resource info
        """
        return self._hostops.get_available_resource()

    def get_info(self, instance):
        """Get the current status of an instance, by name (not ID!)

        :param instance: nova.objects.instance.Instance object

        Returns a dict containing:

        :state:           the running state, one of the power_state codes
        :max_mem:         (int) the maximum memory in KBytes allowed
        :num_cpu:         (int) the number of virtual CPUs for the domain
        """
        return self._vparops.get_info(instance)

    def get_num_instances(self):
        """Get the current number of vpar

        Return integer with the number of running instances
        """
        instances_list = self._vparops.list_instances()
        return len(instances_list)

    def instance_exists(self, instance_name):
        """Check if target instance exists.

        :param instance_name:
        :return:
        :True:
        :False:
        """
        instance_list = self.list_instances()
        for inst_name in instance_list:
            if instance_name == inst_name:
                return True
            continue
        return False

    def destroy(self, context, instance, network_info, block_device_info=None,
                destroy_disks=True):
        """Destroy specific vpar

        :param context:
        :param instance:
        :param network_info:
        :param block_device_info:
        :param destroy_disks:
        :return:
        """
        if self.instance_exists(instance['display_name']):
            self._vparops.destroy(context, instance, network_info)

    def scheduler_dispatch(self, context, vPar_info):
        """Lookup target nPar.

        :param context:
        :param vPar_info: (dict) the required vPar info
        :returns: dictionary containing nPar info
        """
        nPar_list = db.npar_get_all(context)
        npar = self._hostops.nPar_lookup(vPar_info, nPar_list)
        if npar:
            LOG.debug(_("Scheduler successfully, find available nPar %s.")
                      % npar['ip_addr'])
            # Try to update nPar IP into "nova.instance_metadata" table
            # NOTE(Sunny): Here, we can't update "host" field for
            # "nova.instances" table, otherwise, compute manager will not
            # be able to receive asynchronous request (eg. when you delete
            # specified vPar).
            meta = vPar_info['meta']
            meta['npar_host'] = npar['ip_addr']
            db.instance_update(context, vPar_info['uuid'], {'metadata': meta})
        else:
            LOG.exception(_("Scheduler failed in driver,"
                            "couldn't find available nPar."))
            raise
        return npar

    def spawn(self, context, instance, image_meta, injected_files,
              admin_password, network_info=None, block_device_info=None):
        """Spawn new vPar.

        :param context:
        :param instance:
        :param image_meta:
        :param injected_files:
        :param admin_password:
        :param network_info:
        :param block_device_info:
        :return:
        """
        # Get fixed ip address from network_info
        mgmt_ip = None
        for vif in network_info:
            if vif['network']['label'] == CONF.hpux.network_label:
                for ip in vif.fixed_ips():
                    if ip['version'] == 4:
                        mgmt_ip = ip['address']
        if not mgmt_ip:
            LOG.exception(_("Couldn't get fixed ip from network info."))
            raise exception.FixedIpNotFoundForInstance(
                instance_uuid=instance['_uuid'])

        # Scheduler in driver
        memory = int(instance['_system_metadata']['instance_type_memory_mb'])
        cpu = int(instance['_system_metadata']['instance_type_vcpus'])
        disk = int(instance['_system_metadata']['instance_type_root_gb'])
        vpar_info_for_scheduler = {
            'mem': memory,
            'cpu': cpu,
            'disk': disk,
            'uuid': instance['_uuid'],
            'meta': instance['_metadata']
        }
        npar = self.scheduler_dispatch(context, vpar_info_for_scheduler)

        # Here, we can't use instance['_host'] or
        # instance['_metadata']['npar_host'] as npar_host value,
        # should use selected npar['ip_addr'].
        lv_dict = {
            'lv_size': disk,
            'lv_name': 'lv-' + instance['_uuid'],
            'vg_path': CONF.hpux.vg_name,
            'npar_host': npar['ip_addr']
        }
        lv_path = self._vparops.create_lv(lv_dict)
        vpar_info = {
            'vpar_name': instance['_display_name'],
            'npar_host': npar['ip_addr'],
            'mem': memory,
            'cpu': cpu,
            'lv_path': lv_path,
            'image_name': image_meta['name']
        }
        self._vparops.define_vpar(vpar_info)
        self._vparops.init_vpar(vpar_info)
        mac = self._vparops.get_mac_addr(vpar_info)
        vpar_info['mgmt_mac'] = mac
        vpar_info['mgmt_ip'] = mgmt_ip
        vpar_info['mgmt_gw'] = instance['_metadata']['mgmt_gw']
        vpar_info['mgmt_mask'] = instance['_metadata']['mgmt_mask']
        self._vparops.register_vpar_into_ignite(vpar_info)
        self._vparops.lanboot_vpar_by_efi(vpar_info)
