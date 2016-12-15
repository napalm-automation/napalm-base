
import os
import json
import yaml
import collections


from napalm import get_network_driver


class Inventory(object):

    def __init__(self, filename=None):
        self.LIB_PATH_DEFAULT = '~/napalm.yml'
        self.LIB_PATH_ENV_VAR = 'NAPALM_CONF'
        self.filename = self._get_filename(filename)
        self._raw_inventory = self._generate_inventory()
        self.inventory = self.get_inventory()

    def get_groups(self):
        return self.inventory.keys()

    def _get_group(self, group_name):
        devices_in_group = self.inventory.get(group_name)
        if devices_in_group:
            return devices_in_group.keys()
        return []

    def get_devices(self, group_name='all'):
        device_list = []
        if group_name == 'all':
            for group_name, devices in self.inventory.items():
                for device_name, attrs in devices.items():
                    device_list.append(device_name)
        else:
            device_list = self._get_group(group_name)

        return device_list

    def get_device(self, device):
        device_kwargs = {}

        for group_name, devices in self.inventory.items():
            for device_name, attrs in devices.items():
                if device == device_name:
                    device_kwargs = attrs
        dev_os = device_kwargs.get('dev_os')
        driver = get_network_driver(dev_os)
        device = self._get_device(driver, device_kwargs)
        return device

    def get_group(self, group_name):
        devices = self.get_devices(group_name=group_name)
        napalm_devices = []
        for device in devices:
            napalm_devices.append(self.get_device(device))
        return napalm_devices

    def _get_device(self, driver, device_kwargs):

        hostname = device_kwargs['hostname']
        un = device_kwargs['username']
        pwd = device_kwargs['password']
        optional_args = device_kwargs.get('optional_args')

        if device_kwargs.get('timeout'):
            timeout = device_kwargs.get('timeout')
            if optional_args:
                device = driver(hostname, un, pwd, timeout=timeout,
                                optional_args=optional_args)
            else:
                device = driver(hostname, un, pwd, timeout=timeout)
        else:
            if optional_args:
                device = driver(hostname, un, pwd,
                                optional_args=optional_args)
            else:
                device = driver(hostname, un, pwd)
        return device

    def _ensure_hostname(self, inventory, device):
        """Ensure hostname key is in device kwargs
        If hostname key not suppplied, device name is supplied
        back in hostname key.
        """

        hostname = inventory.get('hostname')
        if not hostname:
            inventory['hostname'] = device
        return inventory

    def _sort_dict(self, unsorted_dict):
        return collections.OrderedDict(sorted(unsorted_dict.items()))

    def _sort_inventory(self, unsorted_inventory):
        sorted_inventory = {}
        for group_name, devices in self._raw_inventory.items():
            sorted_inventory[group_name] = {}
            for device_name, attrs in devices.items():
                sorted_inventory[group_name][device_name] = self._sort_dict(attrs)
            sorted_inventory[group_name] = self._sort_dict(sorted_inventory[group_name])
        sorted_inventory = self._sort_dict(sorted_inventory)
        return sorted_inventory

    def _get_filename(self, filename):
        """Get filename for NAPALM conf file

        Priority:
            1. Use filename param in constructor
            2. NAPALM ENV Variable, i.e. LIB_PATH_ENV_VAR
            3. Home directory
        """

        if filename is None:
            if self.LIB_PATH_ENV_VAR in os.environ:
                filename = os.path.expanduser(os.environ[self.LIB_PATH_ENV_VAR])
            else:
                filename = os.path.expanduser(self.LIB_PATH_DEFAULT)
        elif '~' in filename:
            filename = os.path.expanduser(filename)
        return filename

    def get_inventory(self):
        sorted_inventory = self._sort_inventory(self._raw_inventory)
        return sorted_inventory

    def _generate_inventory(self):
        inventory_data = yaml.load(open(self.filename))

        groups = inventory_data.get('groups')
        default_vars = {}
        if groups:
            if groups.get('default'):
                default_vars = groups.get('default')
            inventory_data.pop('groups')
        expanded_inventory = {}
        for device, attributes in inventory_data.items():
            groups_for_device = attributes.get('groups') or 'default'
            if isinstance(groups_for_device, str):
                groups_for_device = [groups_for_device]
            for group, group_params in groups.items():
                if group in groups_for_device and group != 'default':
                    if not expanded_inventory.get(group):
                        expanded_inventory[group] = {}
                    expanded_inventory[group][device] = {}
                    group_vars = groups.get(group)

                    # apply default variables first (default group)
                    if default_vars:
                        expanded_inventory[group][device].update(default_vars)
                    # if group vars supplied, applies them
                    if group_vars:
                        expanded_inventory[group][device].update(group_vars)
                    # finally applies highest priority variables, i.e. device specific vars
                    expanded_inventory[group][device].update(attributes)
                    # removing groups key to more easily pass to napalm kwargs
                    if 'groups' in expanded_inventory[group][device]:
                        expanded_inventory[group][device].pop('groups')
                    expanded_inventory[group][device] = self._ensure_hostname(expanded_inventory[group][device], device)
        return expanded_inventory


if __name__ == "__main__":

    inventory = Inventory('~/napalm2.yml')  # Inventory() would use default settings
    inv = inventory.get_inventory()
    # print json.dumps(inv, indent=4)

    # list of group names
    print inventory.get_groups()

    # list of all devices
    print inventory.get_devices()

    # optionally, pass group name- return list of devices in group
    print inventory.get_devices('dc_edge')

    # return instantiated driver device object for provided device
    print inventory.get_device('csr1')
    print inventory.get_device('eos-spine1')

    # return list of instantiated driver device objects for provided group
    cisco_devices = inventory.get_group('cisco_ios')
    print cisco_devices
    dc_edge_devices = inventory.get_group('dc_edge')
    print dc_edge_devices
