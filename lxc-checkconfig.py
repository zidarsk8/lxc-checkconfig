#!/usr/bin/env python
import os.path
import platform
import re
import json
import gzip

config = '/proc/config.gz'


def is_set(config_name):
    if config.endswith('.gz'):
        config_file = gzip.open(config, 'r')
    else:
        config_file = open(config, 'r')

    for line in config_file:
        if re.match('%s=[y|m]' % config_name, line):
            return True

def is_enabled(config_name, mandatory=None):
    if is_set(config_name):
        return 'enabled'
    else:
        if mandatory == True:
            return 'required'
        else:
            return 'missing'

def get_cgroup_mount_path(search_for,search_where):
    allmounts = open(search_where,'r')
    for mount_line in allmounts:
        if mount_line.startswith('#'):
            pass
        else:
            mls = mount_line.split(' ')
            if mls[2] == search_for:
                return mls[1]


####################################
## BASH CODE NEED HELP TO CONVERT ##
####################################

# print_cgroups() {
#   # print all mountpoints for cgroup filesystems
#   awk '$1 !~ /#/ && $3 == mp { print $2; } ; END { exit(0); } '  "mp=$1" "$2" ;
# }

# CGROUP_MNT_PATH=`print_cgroups cgroup /proc/self/mounts | head -n 1`
# KVER_MAJOR=$($GREP '^# Linux.*Kernel Configuration' $CONFIG | \
#     sed -r 's/.* ([0-9])\.[0-9]{1,2}\.[0-9]{1,3}.*/\1/')
# if [ "$KVER_MAJOR" = "2" ]; then
# KVER_MINOR=$($GREP '^# Linux.*Kernel Configuration' $CONFIG | \
#     sed -r 's/.* 2.6.([0-9]{2}).*/\1/')
# else
# KVER_MINOR=$($GREP '^# Linux.*Kernel Configuration' $CONFIG | \
#     sed -r 's/.* [0-9]\.([0-9]{1,3})\.[0-9]{1,3}.*/\1/')
# fi

####################################
####################################

CGROUP_MNT_PATH = get_cgroup_mount_path('cgroup','/proc/self/mounts')

kver = platform.uname()[2]
kver_split = kver.split('.')
kver_major = int(kver_split[0])
kver_minor = int(kver_split[1])

if not os.path.isfile(config):
    headers_config = '/lib/modules/%s/build/.config' % kver
    boot_config = '/boot/config-%s' % kver

    if os.path.isfile(headers_config):
        config = headers_config

    if os.path.isfile(boot_config):
        config = boot_config



# Define dict type
config_dict = {}


# Namespaces
config_dict['Namespaces'] = is_enabled('CONFIG_NAMESPACES', True)
config_dict['Utsname namespace'] = is_enabled('CONFIG_UTS_NS')
config_dict['Ipc namespace'] = is_enabled('CONFIG_IPC_NS', True)
config_dict['Pid namespace'] = is_enabled('CONFIG_PID_NS', True)
config_dict['User namespace'] = is_enabled('CONFIG_USER_NS')
config_dict['Network namespace'] = is_enabled('CONFIG_NET_NS')
config_dict['Multiple /dev/pts instances'] = is_enabled('CONFIG_DEVPTS_MULTIPLE_INSTANCES')



# Control groups
config_dict['Cgroup'] = is_enabled('CONFIG_CGROUPS', True)
config_dict['Cgroup namespace'] = is_enabled('CONFIG_CGROUP_NS', True)
config_dict['Cgroup device'] = is_enabled('CONFIG_CGROUP_DEVICE')
config_dict['Cgroup sched'] = is_enabled('CONFIG_CGROUP_SCHED')
config_dict['Cgroup cpu account'] = is_enabled('CONFIG_CGROUP_CPUACCT')

if kver_major >= 3 and kver_minor >= 6:
    config_dict['Cgroup memory controller'] = is_enabled('CONFIG_MEMCG')
else:
    config_dict['Cgroup memory controller'] = is_enabled('CONFIG_CGROUP_MEM_RES_CTLR')

if is_set('CONFIG_SMP'):
    config_dict['Cgroup cpuset'] = is_enabled('CONFIG_CPUSETS')



# Misc
config_dict['Veth pair device'] = is_enabled('CONFIG_VETH')
config_dict['Macvlan'] = is_enabled('CONFIG_MACVLAN')
config_dict['Vlan'] = is_enabled('CONFIG_VLAN_8021Q')

if kver_major == 2 and kver_minor < 33:
    config_dict['File capabilities'] = is_enabled('CONFIG_SECURITY_FILE_CAPABILITIES')
if (kver_major == 2 and kver_minor > 32) or kver_major > 2:
    config_dict['File capabilities'] = 'enabled'



print(json.dumps(config_dict, sort_keys=True,
                 indent=4, separators=(',', ': ')))
