__author__ = 'psteam'

from nova import test
from nova.virt.hpux import utils


class ExecRemoteCmdTestCase(test.TestCase):

    @test.testtools.skip("exec_remote_cmd")
    def test_exec_remote_cmd(self):
        remote_cmd_info = {
            "username": "psteam",
            "password": "hpinvent",
            "ip_address": "127.0.0.1",
            "command": "echo 'Hello World'"
        }
        remote_cmd = utils.ExecRemoteCmd()
        ret_str = remote_cmd.exec_remote_cmd(**remote_cmd_info)
        self.assertEqual("Hello World", ret_str.strip())

    @test.testtools.skip("exec_efi_cmd")
    def test_exec_efi_cmd(self):
        efi_cmd_info = {
            "username": "vpar_creater",
            "vpar_name": "vpar_one",
            "ip_address": "192.168.0.1",
            "remote_command": "connect console",
            "efi_command": "echo 'efi shell session'"
        }
        efi_cmd = utils.ExecRemoteCmd()
        exec_result = efi_cmd.exec_efi_cmd(**efi_cmd_info)
        self.assertEqual("efi shell session", exec_result.strip())
