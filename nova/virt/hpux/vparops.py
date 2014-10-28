__author__ = 'psteam'

"""
Management class for basic vPar operations.
"""

import pxssh
import re

from nova.compute import power_state
from nova import context
from nova import db
from nova import exception
from nova.openstack.common.gettextutils import _
from nova.openstack.common import log as logging
from nova.virt.hpux import utils
from oslo.config import cfg

CONF = cfg.CONF

LOG = logging.getLogger(__name__)

HPUX_VPAR_NOSTATE = 0
HPUX_VPAR_RUNNING = 1
HPUX_VPAR_BLOCKED = 2
HPUX_VPAR_SHUTDOWN = 4
HPUX_VPAR_SHUTOFF = 5

HPUX_POWER_STATE = {
    HPUX_VPAR_NOSTATE: power_state.NOSTATE,
    HPUX_VPAR_RUNNING: power_state.RUNNING,
    HPUX_VPAR_BLOCKED: power_state.RUNNING,
    HPUX_VPAR_SHUTDOWN: power_state.SHUTDOWN,
    HPUX_VPAR_SHUTOFF: power_state.SHUTDOWN,
}


class VParOps(object):

    def __init__(self):
        pass

    def _get_vpar_resource_info(self, vpar_name, npar_ip_addr):
        """Get vPar resource info.

        :returns: A dict including CPU, memory and run state info.
        """
        vpar_info = {}
        cmd_for_vpar = {
            'username': CONF.hpux.username,
            'password': CONF.hpux.password,
            'ip_address': npar_ip_addr,
            'command': '/opt/hpvm/bin/vparstatus -p ' + vpar_name + ' -v'
        }
        exec_result = utils.ExecRemoteCmd().exec_remote_cmd(**cmd_for_vpar)
        results = exec_result.strip().split('\n')
        for item in results:
            if 'RunState' in item:
                # item as 'RunState: UP'
                vpar_info['run_state'] = item.split(':')[1].strip()
            elif 'System assigned [Count]' in item:
                # item as 'System assigned [Count]:  5\r'
                vpar_info['CPU'] = int(item.split(':')[1].strip())
            elif 'Total Memory(MB)' in item:
                # item as 'Total Memory(MB):  2048\r'
                vpar_info['Total_memory'] = int(item.split(':')[1].strip())
            else:
                continue
        return vpar_info

    def list_instances(self):
        """Get the up(running) vPar name list of all nPars.

        :returns: A list of up(running) vPar name
        """
        vpar_names = []
        admin_context = context.get_admin_context()
        npar_list = db.npar_get_all(admin_context)
        for npar in npar_list:
            cmd_for_npar = {
                'username': CONF.hpux.username,
                'password': CONF.hpux.password,
                'ip_address': npar['ip_addr'],
                'command': '/opt/hpvm/bin/vparstatus'
            }
            exec_result = utils.ExecRemoteCmd().exec_remote_cmd(**cmd_for_npar)
            results = exec_result.strip().split('\n')
            for ret in results:
                # ret likes '  2 vpar-test  UP  Active \r'
                if 'UP' in ret:
                    vpar_names.append(ret.split()[1])
        return vpar_names

    def get_info(self, instance):
        """Get status of given vPar instance.

        :returns: A dict including CPU, memory, disk info and
        run state of required vPar.
        """
        # Here, instance doesn't include metadata info, so must get it from db
        admin_context = context.get_admin_context()
        metadata = db.instance_metadata_get(admin_context, instance['_uuid'])
        vpar_info = self._get_vpar_resource_info(instance['_display_name'],
                                                 metadata['npar_host'])
        if not vpar_info:
            raise exception.VparNotFound(instance['_display_name'])
        current_vpar_state = HPUX_POWER_STATE[0]
        if vpar_info['run_state'] == 'UP':
            current_vpar_state = HPUX_POWER_STATE[1]
        elif vpar_info['run_state'] == 'DOWN':
            current_vpar_state = HPUX_POWER_STATE[4]
        return {'state': current_vpar_state}

    def destroy(self, context, instance, network_info):
        """Destroy vPar on specified nPar.

        :param context:
        :param instance:
        :param network_info:
        :returns:
        """
        LOG.debug(_("Begin to destroy vPar %s.") % instance['display_name'])
        npar_host = instance['metadata']['npar_host']
        # Power off vPar before "vparremove"
        vpar_info = {
            'npar_host': npar_host,
            'vpar_name': instance['display_name']
        }
        self.power_off_vpar(vpar_info)
        # Get specified vPar info
        vpar_info = self._get_vpar_resource_info(instance['display_name'],
                                                 npar_host)
        # Delete the specified vPar if status is "DOWN"
        if vpar_info['run_state'] == 'DOWN':
            cmd = {
                'username': CONF.hpux.username,
                'password': CONF.hpux.password,
                'ip_address': npar_host,
                'command': '/opt/hpvm/bin/vparremove -p '
                           + instance['display_name'] + ' -f'
            }
            utils.ExecRemoteCmd().exec_remote_cmd(**cmd)
            # Delete the specified logical volume
            lv_path = CONF.hpux.vg_name + '/lv-' + instance['uuid']
            self.delete_lv(npar_host, lv_path)
            LOG.debug(_("Destroy vPar %s successfully.")
                      % instance['display_name'])

    def delete_lv(self, npar_host, lv_path):
        """Delete logical volume on specified nPar.

        :param: npar_host: The IP address of specified nPar
        :param: lv_path: The path of logical volume
        :returns:
        """
        LOG.debug(_("Begin to delete logical volume %s.") % lv_path)
        cmd = {
            'username': CONF.hpux.username,
            'password': CONF.hpux.password,
            'ip_address': npar_host,
            'command': 'lvremove -f ' + lv_path
        }
        result = utils.ExecRemoteCmd().exec_remote_cmd(**cmd)

    def create_lv(self, lv_dic):
        """Create logical volume for vPar on specified nPar.

        :param: A dict containing:
             :lv_size: The size of logical volume
             :lv_name: The name of logical volume
             :vg_path: The path of volume group
             :npar_host: The IP address of specified nPar
        :returns: created_lv_path: The path of created logical volume
        """
        cmd = {
            'username': CONF.hpux.username,
            'password': CONF.hpux.password,
            'ip_address': lv_dic['npar_host'],
            'command': 'lvcreate -L ' + str(lv_dic['lv_size']) +
                       ' -n ' + lv_dic['lv_name'] +
                       ' ' + lv_dic['vg_path']
        }
        created_lv_path = lv_dic['vg_path'] + '/r' + lv_dic['lv_name']
        LOG.debug(_("Begin to create logical volume %s.")
                  % lv_dic['lv_name'])
        result = utils.ExecRemoteCmd().exec_remote_cmd(**cmd)
        if created_lv_path in result:
            LOG.debug(_("Create logical volume %s successfully.")
                      % created_lv_path)
            return created_lv_path
        return None

    def define_vpar(self, vpar_dic):
        """Define vPar resources on specified nPar.

        :param: A dict containing:
             :vpar_name: The name of vPar
             :npar_host: The IP address of specified nPar
             :mem: The memory of vPar
             :cpu: The cpu of vPar
             :lv_path: The path of logical volume
        :returns:
        """
        LOG.debug(_("Begin to create vPar %s.") % vpar_dic['vpar_name'])
        cmd = {
            'username': CONF.hpux.username,
            'password': CONF.hpux.password,
            'ip_address': vpar_dic['npar_host'],
            'command': '/opt/hpvm/bin/vparcreate -p ' +
                       vpar_dic['vpar_name'] +
                       ' -a mem::' + str(vpar_dic['mem']) +
                       ' -a cpu::' + str(vpar_dic['cpu']) +
                       ' -a disk:avio_stor::lv:' + vpar_dic['lv_path'] +
                       ' -a network:avio_lan::vswitch:' +
                       CONF.hpux.management_network +
                       ' -a network:avio_lan::vswitch:' +
                       CONF.hpux.production_network
        }
        utils.ExecRemoteCmd().exec_remote_cmd(**cmd)

    def init_vpar(self, vpar_info):
        """Initialize the specified vPar so that could enter live console mode.

        :param: A dict containing:
             :vpar_name: The name of vPar
             :npar_host: The IP address of specified nPar
        :return: True if vPar boot successfully
        """
        cmd = {
            'username': CONF.hpux.username,
            'password': CONF.hpux.password,
            'ip_address': vpar_info['npar_host'],
            'command': '/opt/hpvm/bin/vparboot -p ' +
                       vpar_info['vpar_name']
        }
        LOG.debug(_("Begin to initialize vPar %s.") % vpar_info['vpar_name'])
        result = utils.ExecRemoteCmd().exec_remote_cmd(**cmd)
        if 'Successful start initiation' in result:
            LOG.debug(_("Initialize vPar %s successfully.")
                      % vpar_info['vpar_name'])
            return True
        return False

    def get_mac_addr(self, vpar_info):
        """Get "sitelan" MAC address of vPar from specified nPar.

        :param: A dict containing:
             :vpar_name: The name of vPar
             :npar_host: The IP address of specified nPar
        :return: mgmt_mac: The MAC address of vPar for Management Network
        """
        LOG.debug(_("Begin to get MAC of vPar %s.") % vpar_info['vpar_name'])
        mgmt_mac = None
        cmd = {
            'username': CONF.hpux.username,
            'password': CONF.hpux.password,
            'ip_address': vpar_info['npar_host'],
            'command': '/opt/hpvm/bin/vparstatus -p ' +
                       vpar_info['vpar_name'] + ' -v'
        }
        exec_result = utils.ExecRemoteCmd().exec_remote_cmd(**cmd)
        results = exec_result.strip().split('\n')
        for item in results:
            if CONF.hpux.management_network in item:
                io_details = item.split()
                for io in io_details:
                    if CONF.hpux.management_network in io:
                        mac_addr = io.split(':')[2].split(',')[2]
                        mgmt_mac = '0x' + mac_addr[2:].upper()
        return mgmt_mac

    def register_vpar_into_ignite(self, vpar_info):
        """Register vPar into ignite server.

        :param: A dict containing:
             :vpar_name: The name of vPar
             :mgmt_mac: The mac address of vPar for Management Network
             :mgmt_ip: The IP address of vPar for Management Network
             :mgmt_gw: The gateway of vPar for Management Network
             :mgmt_mask: The mask of vPar for Management Network
        :return: True if no error in the process of registration
        """
        # Add vPar network info into the end of /etc/bootptab on ignite server
        LOG.debug(_("Begin to register network info on ignite server %s"
                    " for vPar.") % CONF.hpux.ignite_ip)
        cmd_for_network = {
            'username': CONF.hpux.username,
            'password': CONF.hpux.password,
            'ip_address': CONF.hpux.ignite_ip,
            'command': ' echo \'' + vpar_info['vpar_name'] + ':\\\''
                + ' >> /etc/bootptab'
                + ' && echo \'\ttc=ignite-defaults:\\\'' + ' >> /etc/bootptab'
                + ' && echo \'\tha=' + vpar_info['mgmt_mac'] + ':\\\''
                + ' >> /etc/bootptab'
                + ' && echo \'\tbf=/opt/ignite/boot/Rel_B.11.31/nbp.efi:\\\''
                + ' >> /etc/bootptab'
                + ' && echo \'\tgw=' + vpar_info['mgmt_gw'] + ':\\\''
                + ' >> /etc/bootptab'
                + ' && echo \'\tip=' + vpar_info['mgmt_ip'] + ':\\\''
                + ' >> /etc/bootptab'
                + ' && echo \'\tsm=' + vpar_info['mgmt_mask'] + '\''
                + ' >> /etc/bootptab'
        }
        utils.ExecRemoteCmd().exec_remote_cmd(**cmd_for_network)

        # Create config file for client(vPar)
        LOG.debug(_("Begin to create client directory on ignite server %s"
                    " for vPar by MAC.") % CONF.hpux.ignite_ip)
        config_path = '/var/opt/ignite/clients/'\
                      + vpar_info['mgmt_mac'] + '/config'
        cmd_for_create_config = {
            'username': CONF.hpux.username,
            'password': CONF.hpux.password,
            'ip_address': CONF.hpux.ignite_ip,
            'command': 'mkdir /var/opt/ignite/clients/' + vpar_info['mgmt_mac']
                       + '&& touch ' + config_path
        }
        utils.ExecRemoteCmd().exec_remote_cmd(**cmd_for_create_config)

        # Add config info into the end of /var/opt/ignite/clients/<MAC>/config
        LOG.debug(_("Begin to create config file on ignite server %s"
                    " for vPar.") % CONF.hpux.ignite_ip)
        cmd_for_config = {
            'username': CONF.hpux.username,
            'password': CONF.hpux.password,
            'ip_address': CONF.hpux.ignite_ip,
            'command': ' echo \'cfg "' + vpar_info['image_name'] + '"=TRUE\''
                + '>> ' + config_path
                + ' && echo \'_hp_cfg_detail_level="v"\''
                + '>> ' + config_path
                + ' && echo \'final system_name="' + vpar_info['vpar_name']
                + '"\'' + '>> ' + config_path
                + ' && echo \'_hp_keyboard="USB_PS2_DIN_US_English"\''
                + '>> ' + config_path
                + ' && echo \'root_password="1uGsgzGKG95gU"\''
                + '>> ' + config_path
                + ' && echo \'_hp_root_disk="0/0/0/0.0x0.0x0"\''
                + '>> ' + config_path
                + ' && echo \'_my_second_disk_path=""\''
                + '>> ' + config_path
        }
        utils.ExecRemoteCmd().exec_remote_cmd(**cmd_for_config)
        return True

    def lanboot_vpar_by_efi(self, vpar_info):
        """Lanboot vPar by enter EFI Shell on specified nPar.

        :param: A dict containing:
             :vpar_name: The name of vPar
             :npar_host: The IP address of specified nPar
             :mgmt_ip: The IP address of vPar for Management Network
             :mgmt_gw: The gateway of vPar for Management Network
             :mgmt_mask: The mask of vPar for Management Network
        :return: True if no error in the process of lanboot
        """
        cmd_vparconsole = '/opt/hpvm/bin/vparconsole -P '\
                          + vpar_info['vpar_name']
        cmd_dbprofile_network = 'dbprofile -dn profile-test' +\
                                ' -sip ' + CONF.hpux.ignite_ip +\
                                ' -cip ' + vpar_info['mgmt_ip'] +\
                                ' -gip ' + vpar_info['mgmt_gw'] +\
                                ' -m ' + vpar_info['mgmt_mask']
        cmd_dbprofile_kernel = 'dbprofile -dn profile-test' +\
                               ' -b "/opt/ignite/boot/Rel_B.11.31/nbp.efi"'
        cmd_lanboot = 'lanboot select -index 01 -dn profile-test'
        try:
            LOG.debug(_("Begin to lanboot vPar %s by enter EFI Shell.")
                      % vpar_info['vpar_name'])
            # Get ssh connection
            ssh = pxssh.pxssh()
            ssh.login(vpar_info['npar_host'], CONF.hpux.username,
                      CONF.hpux.password, original_prompt='[$#>]',
                      login_timeout=CONF.hpux.ssh_timeout_seconds)

            # Send command "vparconsole -P <vpar_name>"
            ssh.sendline(cmd_vparconsole)
            ssh.prompt(timeout=CONF.hpux.ssh_timeout_seconds)
            ssh.sendline('CO')
            ssh.sendline('\r\n')
            ssh.prompt(timeout=CONF.hpux.ssh_timeout_seconds)
            # Replace the color code of output
            efi_prompt = re.sub('\x1b\[[0-9;]*[m|H|J]', '', ssh.before)
            efi_prompt = re.sub('\[0m', '', efi_prompt)

            # Send "Ctrl-Ecf" to EFI Shell if have no write access
            if 'Read only' in efi_prompt[-70:]:
                # [Read only - use Ctrl-Ecf for console write access.]
                ssh.send('\x05\x63\x66')
                ssh.sendline('\r\n')
                ssh.prompt(timeout=CONF.hpux.ssh_timeout_seconds)

            # Send command related to "dbprofile"
            ssh.sendline(cmd_dbprofile_network)
            ssh.sendline('\r\n')
            ssh.prompt(timeout=CONF.hpux.ssh_timeout_seconds)
            ssh.sendline(cmd_dbprofile_kernel)
            ssh.sendline('\r\n')
            ssh.prompt(timeout=CONF.hpux.ssh_timeout_seconds)
            # Output the log before executing "lanboot"
            console_log = re.sub('\x1b\[[0-9;]*[m|H|J]', '', ssh.before)
            LOG.info(_("\n%s") % console_log)

            # Send command related to "lanboot"
            ssh.send(cmd_lanboot)
            ssh.send('\r\n')
            ssh.prompt(timeout=CONF.hpux.lanboot_timeout_seconds)
            console_log = re.sub('\x1b\[[0-9;]*[m|H|J]', '', ssh.before)
            LOG.info(_("\n%s") % console_log)
        except pxssh.ExceptionPxssh:
            raise exception.Invalid(_("pxssh failed on login."))
        finally:
            ssh.logout()

        return True

    def power_off_vpar(self, vpar_info):
        """Power off vPar on specified nPar.

        :param: A dict containing:
             :vpar_name: The name of vPar
             :npar_host: The IP address of specified nPar
        :return:
        """
        # Force to power off vPar
        LOG.debug(_("Begin to power off vPar %s.") % vpar_info['vpar_name'])
        cmd = {
            'username': CONF.hpux.username,
            'password': CONF.hpux.password,
            'ip_address': vpar_info['npar_host'],
            'command': '/opt/hpvm/bin/vparreset -f -p '
                       + vpar_info['vpar_name'] + ' -d'
        }
        utils.ExecRemoteCmd().exec_remote_cmd(**cmd)
        # TODO(Sunny): Work around
        # Here, "vparreset" need some time to power off vPar.
        # The better way is to check vPar status in real time.
        import time
        time.sleep(10)

    def init_vhba(self, vpar_info):
        """Attach vHBA to vPar on specified nPar.

        :param: A dict containing:
             :vpar_name: The name of vPar
             :npar_host: The IP address of specified nPar
             :wwpn: The wwpn for FC HBA "/dev/fcd0"
             :wwnn: The wwnn for FC HBA "/dev/fcd0"
        :return:
        """
        # Force to power off vPar, don't care succeed or fail
        self.power_off_vpar(vpar_info)
        # Attach vHBA
        LOG.debug(_("Begin to attach vHBA for vPar %s.")
                  % vpar_info['vpar_name'])
        cmd = {
            'username': CONF.hpux.username,
            'password': CONF.hpux.password,
            'ip_address': vpar_info['npar_host'],
            'command': '/opt/hpvm/bin/vparmodify -p ' + vpar_info['vpar_name']
                       + ' -a ' + 'hba:avio_stor:,,' + vpar_info['wwpn']
                       + ',' + vpar_info['wwnn'] + ':npiv:/dev/fcd0'
        }
        utils.ExecRemoteCmd().exec_remote_cmd(**cmd)

    def boot_vpar(self, vpar_info):
        """Boot vPar on specified nPar.

        :param: A dict containing:
             :vpar_name: The name of vPar
             :npar_host: The IP address of specified nPar
        :return:
        """
        LOG.debug(_("Begin to boot vPar %s.") % vpar_info['vpar_name'])
        cmd = {
            'username': CONF.hpux.username,
            'password': CONF.hpux.password,
            'ip_address': vpar_info['npar_host'],
            'command': '/opt/hpvm/bin/vparboot -p ' + vpar_info['vpar_name']
        }
        utils.ExecRemoteCmd().exec_remote_cmd(**cmd)
