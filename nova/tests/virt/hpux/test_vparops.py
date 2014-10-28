__author__ = 'psteam'

import mock

from nova import test
from nova.virt.hpux import driver as hpux_driver
from nova.virt.hpux import hostops
from nova.virt.hpux import utils
from oslo.config import cfg

CONF = cfg.CONF


class VParOpsTestCase(test.TestCase):

    @mock.patch.object(utils.ExecRemoteCmd, 'exec_remote_cmd')
    @mock.patch.object(hostops.HostOps, '_get_client_list')
    def test_list_instances(self, mock_get_client_list, mock_exec_remote_cmd):
        up_state_vpar = 'vpar-test'
        npar_ip_addr = '192.168.169.100'
        vpar_names = [up_state_vpar]
        fake_npar_list = [{'ip_addr': npar_ip_addr,
                           'name': u'bl890npar1', 'hostname': u'bl890npar1',
                           'cpus': 8, 'memory': 66994944 / 1024,
                           'model': u'ia64 hp Integrity BL890c i4 nPar'}]
        fake_vpar_list = [{'name': 'vpar1', 'model': 'Virtual Partition',
                           'ip_addr': '192.168.0.11'}]
        mock_get_client_list.return_value = fake_npar_list, fake_vpar_list
        mock_exec_remote_cmd.return_value = ' \r\n[Virtual Partition]\r\n' +\
                        'Num Name  RunState State\r\n==' +\
                        '\r\n  2 ' + up_state_vpar + ' UP Active\r\n'
        cmd_for_npar = {
            'username': CONF.hpux.username,
            'password': CONF.hpux.password,
            'ip_address': npar_ip_addr,
            'command': '/opt/hpvm/bin/vparstatus'
        }
        conn = hpux_driver.HPUXDriver(None)
        result = conn.list_instances()
        self.assertEqual(vpar_names, result)
        mock_get_client_list.assert_called_once_with()
        mock_exec_remote_cmd.assert_called_once_with(**cmd_for_npar)
