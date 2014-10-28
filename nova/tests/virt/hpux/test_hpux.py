__author__ = 'psteam'

import mock

from nova import context
from nova import db
from nova import test
from nova.tests import utils as test_utils
from nova.virt.hpux import driver as hpux_driver
from nova.virt.hpux import hostops
from nova.virt.hpux import vparops
from oslo.config import cfg

CONF = cfg.CONF


class HPUXDriverTestCase(test.NoDBTestCase):
    """Unit tests for HP-UX driver calls."""

    @mock.patch.object(vparops.VParOps, 'list_instances')
    def test_list_instances(self, mock_list_instances):
        fake_instances = ['fake1', 'fake2']
        mock_list_instances.return_value = fake_instances
        conn = hpux_driver.HPUXDriver(None, vparops=vparops.VParOps())
        instances = conn.list_instances()
        self.assertEqual(fake_instances, instances)
        mock_list_instances.assert_called_once_with()

    @mock.patch.object(hostops.HostOps, 'get_host_stats')
    def test_get_host_stats(self, mock_get_host_stats):
        fake_stats = {
            'supported_instances': [],
            'vcpus': 2,
            'memory_mb': 2048,
            'local_gb': 100,
            'vcpus_used': 0,
            'memory_mb_used': 1024,
            'local_gb_used': 10,
            'hypervisor_type': 'hpux',
            'hypervisor_version': '201409',
            'hypervisor_hostname': 'hpux'
        }
        mock_get_host_stats.return_value = fake_stats
        conn = hpux_driver.HPUXDriver(None, hostops=hostops.HostOps())
        host_stats = conn.get_host_stats(refresh=True)
        self.assertEqual(fake_stats, host_stats)
        mock_get_host_stats.assert_called_once_with(refresh=True)

    @mock.patch.object(hostops.HostOps, 'get_available_resource')
    def test_get_available_resource(self, mock_get_available_resource):
        fake_resource = {
            'supported_instances': [],
            'vcpus': 2,
            'memory_mb': 2048,
            'local_gb': 100,
            'vcpus_used': 0,
            'memory_mb_used': 1024,
            'local_gb_used': 10,
            'hypervisor_type': 'hpux',
            'hypervisor_version': '201409',
            'hypervisor_hostname': 'hpux'
        }
        mock_get_available_resource.return_value = fake_resource
        conn = hpux_driver.HPUXDriver(None, hostops=hostops.HostOps())
        available_resource = conn.get_available_resource(None)
        self.assertEqual(fake_resource, available_resource)
        mock_get_available_resource.assert_called_once_with()

    @mock.patch.object(vparops.VParOps, 'get_info')
    def test_get_info(self, mock_get_info):
        fake_info = {
            'state': 'UP',
            'max_mem': 4096,
            'num_cpu': 2,
        }
        mock_get_info.return_value = fake_info
        conn = hpux_driver.HPUXDriver(None, vparops=vparops.VParOps())
        fake_instance = {
            'vpar_name': 'fake1',
            'npar_ip_addr': '192.168.0.1'
        }
        instance_info = conn.get_info(fake_instance)
        self.assertEqual(fake_info, instance_info)
        mock_get_info.assert_called_once_with(fake_instance)

    @mock.patch.object(hpux_driver.HPUXDriver, 'list_instances')
    def test_instance_exists_or_not(self, mock_list_instances):
        fake_instances = ['fake1', 'fake2']
        mock_list_instances.return_value = fake_instances
        conn = hpux_driver.HPUXDriver(None)
        self.assertTrue(conn.instance_exists('fake1'))
        self.assertFalse(conn.instance_exists('fake3'))
        mock_list_instances.assert_any_call()
        assert 2 == mock_list_instances.call_count

    @mock.patch.object(hpux_driver.HPUXDriver, 'get_num_instances')
    @mock.patch.object(hpux_driver.HPUXDriver, 'list_instances')
    def test_get_num_instances(self, mock_list_instances,
                               mock_get_num_instances):
        fake_instances = ['fake1', 'fake2']
        mock_list_instances.return_value = fake_instances
        mock_get_num_instances.return_value = 2
        conn = hpux_driver.HPUXDriver(None)
        instances = conn.get_num_instances()
        self.assertEqual(len(fake_instances), instances)
        mock_get_num_instances.assert_called_once_with()

    @mock.patch.object(vparops.VParOps, 'destroy')
    @mock.patch.object(hpux_driver.HPUXDriver, 'instance_exists')
    def test_destroy(self, mock_instance_exists, mock_destroy):
        fake_context = context.get_admin_context()
        fake_instance = {'display_name': 'vpar-test'}
        fake_network_info = {
            'fixed_ip': '1.1.1.1',
            'floating_ip': '11.11.11.11'
        }
        mock_instance_exists.return_value = True
        conn = hpux_driver.HPUXDriver(None)
        conn.destroy(fake_context, fake_instance, fake_network_info)
        mock_instance_exists.assert_called_once_with(
                                             fake_instance['display_name'])
        mock_destroy.assert_called_once_with(fake_context,
                                             fake_instance, fake_network_info)

    @mock.patch.object(db, 'instance_update')
    @mock.patch.object(hostops.HostOps, "nPar_lookup")
    @mock.patch.object(db, 'npar_get_all')
    def test_scheduler_dispatch(self, mock_npar_get_all,
                                mock_nPar_lookup, mock_instance_update):
        fake_context = context.get_admin_context()
        fake_nPar = {'ip_addr': '192.168.169.100'}
        fake_vPar_info = {
            'mem': 1024,
            'num_cpu': 2,
            'disk': 5,
            'uuid': '15e173c9-500a-4a8b-8189-80ff5693fc58',
            'meta': {
                'npar_host': fake_nPar['ip_addr']
            }
        }
        fake_update_info = {'metadata': fake_vPar_info['meta']}
        fake_nPar_list = []
        fake_nPar_list.append(fake_nPar)
        mock_npar_get_all.return_value = fake_nPar_list
        mock_nPar_lookup.return_value = fake_nPar
        conn = hpux_driver.HPUXDriver(None, hostops=hostops.HostOps())
        nPar = conn.scheduler_dispatch(fake_context, fake_vPar_info)
        self.assertEqual(fake_nPar, nPar)
        mock_npar_get_all.assert_called_once_with(fake_context)
        mock_nPar_lookup.assert_called_once_with(fake_vPar_info,
                                                 fake_nPar_list)
        mock_instance_update.assert_called_once_with(fake_context,
                                                     fake_vPar_info['uuid'],
                                                     fake_update_info)

    @mock.patch.object(vparops.VParOps, 'lanboot_vpar_by_efi')
    @mock.patch.object(vparops.VParOps, 'register_vpar_into_ignite')
    @mock.patch.object(vparops.VParOps, 'get_mac_addr')
    @mock.patch.object(vparops.VParOps, 'init_vpar')
    @mock.patch.object(vparops.VParOps, 'define_vpar')
    @mock.patch.object(vparops.VParOps, 'create_lv')
    @mock.patch.object(hpux_driver.HPUXDriver, 'scheduler_dispatch')
    def test_spawn(self, mock_scheduler_dispatch, mock_create_lv,
                   mock_define_vpar, mock_init_vpar,
                   mock_get_mac_addr, mock_register_vpar_into_ignite,
                   mock_lanboot_vpar_by_efi):
        fake_context = context.get_admin_context()
        fake_image_meta = {'name': 'HP-UX B.11.31.1403 golden_image'}
        fake_network_info = test_utils.get_test_network_info()
        fake_network_info[0]['network']['label'] = 'hpux'
        mgmt_ip = '192.168.169.105'
        for ip in fake_network_info[0].fixed_ips():
            if ip['version'] == 4:
                mgmt_ip = ip['address']
        fake_npar = {'ip_addr': '192.168.169.100',
                     'name': 'bl890npar1', 'hostname': 'bl890npar1',
                     'cpus': 8, 'memory': 66994944 / 1024,
                     'model': 'ia64 hp Integrity BL890c i4 nPar'}
        fake_instance = {
            '_id': 2,
            '_uuid': '15e173c9-500a-4a8b-8189-80ff5693fc58',
            '_display_name': 'vpar-test',
            '_system_metadata': {
                'instance_type_root_gb': 20,
                'instance_type_memory_mb': 1024,
                'instance_type_vcpus': 1
            },
            '_metadata': {
                'mgmt_gw': '192.168.168.1',
                'mgmt_mask': '255.255.248.0'
            }
        }
        disk = fake_instance['_system_metadata']['instance_type_root_gb']
        memory = fake_instance['_system_metadata']['instance_type_memory_mb']
        cpu = fake_instance['_system_metadata']['instance_type_vcpus']
        fake_lv_dict = {
            'lv_size': disk,
            'lv_name': 'lv-' + fake_instance['_uuid'],
            'vg_path': CONF.hpux.vg_name,
            'npar_host': fake_npar['ip_addr']
        }
        fake_lv_path = CONF.hpux.vg_name + '/rlv-' + fake_instance['_uuid']
        fake_vpar_info = {
            'vpar_name': fake_instance['_display_name'],
            'npar_host': fake_npar['ip_addr'],
            'mem': memory,
            'cpu': cpu,
            'lv_path': fake_lv_path,
            'image_name': fake_image_meta['name']
        }
        fake_mac = '0x888888'
        fake_vpar_info['mgmt_mac'] = fake_mac
        fake_vpar_info['mgmt_ip'] = mgmt_ip
        fake_vpar_info['mgmt_gw'] = fake_instance['_metadata']['mgmt_gw']
        fake_vpar_info['mgmt_mask'] = fake_instance['_metadata']['mgmt_mask']
        fake_vpar_info_for_scheduler = {
            'mem': memory,
            'cpu': cpu,
            'disk': disk,
            'uuid': fake_instance['_uuid'],
            'meta': fake_instance['_metadata']
        }
        mock_scheduler_dispatch.return_value = fake_npar
        mock_create_lv.return_value = fake_lv_path
        mock_get_mac_addr.return_value = fake_mac
        conn = hpux_driver.HPUXDriver(None)
        conn.spawn(fake_context, fake_instance, fake_image_meta, None, None,
                   network_info=fake_network_info, block_device_info=None)
        mock_scheduler_dispatch.assert_called_once_with(fake_context,
                                                fake_vpar_info_for_scheduler)
        mock_create_lv.assert_called_once_with(fake_lv_dict)
        mock_define_vpar.assert_called_once_with(fake_vpar_info)
        mock_init_vpar.assert_called_once_with(fake_vpar_info)
        mock_get_mac_addr.assert_called_once_with(fake_vpar_info)
        mock_register_vpar_into_ignite.assert_called_once_with(fake_vpar_info)
        mock_lanboot_vpar_by_efi.assert_called_once_with(fake_vpar_info)
