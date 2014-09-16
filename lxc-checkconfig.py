#!/usr/bin/env python
import sys
import os.path
import platform
import re
import json
import gzip
import argparse
from collections import defaultdict

config = '/proc/config.gz'

COLORS = defaultdict(lambda :'\033[0;39m')
COLORS['enabled'] = '\033[1;32m'
COLORS['requred'] = '\033[1;31m'
COLORS['missing'] = '\033[1;33m'

# simplify error handling for argparse
class ArgParser(argparse.ArgumentParser):
    def error(self, message):
        sys.stderr.write('error: %s\n' % message)
        self.print_help()
        sys.exit(2)

def is_set(config_name):
    if config.endswith('.gz'):
        config_file = [ i.decode('utf-8') for i in gzip.open(config, 'r').readlines()]
    else:
        config_file = [ i for i in open(config, 'r').readlines()]

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

def get_cgroup_mount_path(search_for, search_where):
    allmounts = open(search_where,'r')
    for mount_line in allmounts:
        if mount_line.strip().startswith(search_for):
            return mount_line.split(' ')[1]
    return ''

def print_config(config_dict):
    print_groups = {
            "Namespaces" : [ "Namespaces","Utsname namespace","Ipc namespace","Pid namespace",
                "User namespace","Network namespace","Multiple /dev/pts instances"],
            "Control groups" : ["Cgroup", "Cgroup clone_children flag", "Cgroup namespace", 
                "Cgroup device", "Cgroup sched", "Cgroup cpu account", "Cgroup memory controller",
                "Cgroup cpuset"],
            "Misc" : ["Veth pair device", "Macvlan", "Vlan", "File capabilities"]
            }
    groups_order = ["Namespaces", "Control groups", "Misc"]

    normal = COLORS['normal']
    for name in groups_order:
        print("--- %s ---" % name)
        for field in print_groups[name]:
            if field not in config_dict :
                continue
            color = COLORS[config_dict[field].lower()]
            print("%s: %s%s%s" % (field, color, config_dict[field], normal) )
        print("")
    
    print("Note : Before booting a new kernel, you can check its configuration")
    print("usage : CONFIG=/path/to/config /usr/bin/lxc-checkconfig")
    print("")

####################################
## BASH CODE NEED HELP TO CONVERT ##
####################################

# print_cgroups() {
#   # print all mountpoints for cgroup filesystems
#   awk '$1 !~ /#/ && $3 == mp { print $2; } ; END { exit(0); } '  "mp=$1" "$2" ;
# }

## DONE ## CGROUP_MNT_PATH=`print_cgroups cgroup /proc/self/mounts | head -n 1`
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

cgroup_mnt_path = get_cgroup_mount_path('cgroup','/proc/self/mounts')

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
if os.path.isfile('%s/cgroup.clone_children' % cgroup_mnt_path):
    config_dict['Cgroup clone_children flag'] = 'enabled'
else:
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



if __name__ == "__main__":

    parser = ArgParser(description='Set network for a new container')
    parser.add_argument('-j','--json', help='output in JSON format', action='store_true')
    args = vars(parser.parse_args())

    if args['json']:
        print(json.dumps(config_dict, sort_keys=True, indent=4, separators=(',', ': ')))
    else:
        print_config(config_dict)

