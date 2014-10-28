__author__ = 'psteam'

"""
A HP-UX Nova Compute driver.
"""

import pexpect

from nova import exception
from nova.openstack.common.gettextutils import _
from oslo.config import cfg

CONF = cfg.CONF


class ExecRemoteCmd(object):
    def exec_remote_cmd(self, **remote_cmd_info):
        execute_result = None
        try:
            ssh = pexpect.spawn('ssh %s@%s "%s"' %
                                (remote_cmd_info["username"],
                                 remote_cmd_info["ip_address"],
                                 remote_cmd_info["command"]))
            expect_ret = ssh.expect(['Password:',
                                     'continue connecting (yes/no)?'],
                                    timeout=CONF.hpux.ssh_timeout_seconds)
            if expect_ret == 0:
                ssh.sendline(remote_cmd_info["password"])
            elif expect_ret == 1:
                ssh.sendline("yes\n")
                ssh.expect("password:")
                ssh.sendline(remote_cmd_info["password"])
            else:
                raise exception.Invalid(_("ssh connection error UNKNOWN"))
            execute_result = ssh.read()
        except pexpect.EOF:
            raise exception.Invalid(_("pexpect error EOF"))
        except pexpect.TIMEOUT:
            raise exception.Invalid(_("pexpect error TIMEOUT"))
        except pexpect.ExceptionPexpect as e:
            raise exception.Invalid(_("pexpect error UNKNOWN"))
        finally:
            ssh.close()

        return execute_result
