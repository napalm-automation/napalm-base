#!/usr/bin/env python

import os
import yaml
import collections


from napalm import get_network_driver


class Inventory(object):

    def __init__(self, filename=None):
        self.LIB_PATH_DEFAULT = '~/napalm.yml'
        self.LIB_PATH_ENV_VAR = 'NAPALM_CONF'
        self.group_vars = {}
        self.groups = []
        self.default_vars = {}
        self.devices = []
        self.device_vars = {}
        self.group_inventory = {}
        self.device_inventory = {}
        self.filename = self._get_filename(filename)
        self._generate_inventory()

    def get_device_inventory(self):
        """Return complete inventory - doesn't include groups
        """
        return self.device_inventory

    def get_group_inventory(self):
        """Return mapping of groups to device list
        """
        return self.group_inventory

    def get_inventory(self):
        """Get complete inventory rooted by group names
        """
        inventory = {}
        for group, device_list in self.group_inventory.items():
            inventory[group] = {}
            for device in device_list:
                inventory[group][device] = self.device_inventory.get(device)
        return inventory

    def get_groups(self):
        """Return list of all groups
        """

        return self.groups

    def get_devices(self, group_name='all'):
        """Return a list of devices in a given group.  Default is all devices.
        """

        if group_name == 'all':
            return self.device_inventory.keys()
        else:
            return self.group_inventory.get(group_name, [])

    def get_device(self, device):
        """Return NAPALM device object for a single device by inventory name
        """

        device_kwargs = self.device_inventory.get(device, {})
        dev_os = device_kwargs.get('dev_os')
        driver = get_network_driver(dev_os)
        device = self._get_device(driver, device_kwargs)
        return device

    def get_group(self, group_name):
        """Return a list of NAPALM device objects in a specified group
        """

        devices = self.group_inventory.get(group_name)
        napalm_devices = []
        for device in devices:
            napalm_devices.append(self.get_device(device))
        return napalm_devices

    def _get_device(self, driver, device_kwargs):

        hostname = device_kwargs['hostname']
        un = device_kwargs['username']
        pwd = device_kwargs['password']
        optional_args = device_kwargs.get('optional_args')

        # TODO: PROBABLY CLEAN UP PARSING TO ALLOW FOR USE OF **KWARGS HERE
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
        for device, d_vars in unsorted_inventory.items():
            sorted_inventory[device] = self._sort_dict(d_vars)
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

    def get_inventory_data_from_file(self):
        return yaml.load(open(self.filename))

    def _get_device_groups(self, data):
        device_groups = data.get('groups')
        if isinstance(device_groups, str):
            device_groups = [device_groups]
        return device_groups

    def _remove_groups(self):
        inventory = self.get_inventory_data_from_file()
        try:
            inventory.pop('groups')
        except KeyError:
            # no group vars defined, all host vars
            pass
        return inventory

    def _get_host_inventory(self):
        return self._remove_groups()

    def _parse_device_data(self):
        host_inventory = self._get_host_inventory()
        groups = []
        for device, device_attributes in host_inventory.items():
            groups.extend(self._get_device_groups(device_attributes))
        return groups

    def _parse_group_data(self):
        groups = self.group_vars.keys()
        # obtain groups that do not have any group variables
        groups.extend(self._parse_device_data())
        return list(set(groups))

    def _build_group_inventory(self, groups):
        for group in groups:
            if group != 'default':
                self.group_inventory[group] = []

    def _get_group_data(self):
        self.group_vars = self.get_inventory_data_from_file().get('groups') or {}
        self.groups = self._parse_group_data()
        self._build_group_inventory(self.groups)
        if self.group_vars.get('default'):
            self.default_vars = self.group_vars.get('default')

    def _get_host_data(self):
        self.device_vars = self._get_host_inventory()
        self.devices = self.device_vars.keys()

    def _generate_inventory(self):
        self._get_group_data()
        self._get_host_data()
        self.device_inventory = self._get_inventory()

    def _get_inventory(self):
        expanded_inventory = {}
        for device, d_vars in self.device_vars.items():
            expanded_inventory[device] = {}
            if self.default_vars:
                expanded_inventory[device].update(self.default_vars)
            groups_for_device = self._get_device_groups(d_vars)
            groups_for_device.reverse()

            if groups_for_device:
                for group in groups_for_device:
                    group_vars = self.group_vars.get(group)
                    # apply group variables in reverse order from inventory file
                    if group_vars:
                        expanded_inventory[device].update(group_vars)

                    # maintain dictionary to map groups to device names
                    self.group_inventory[group].append(device)

                # finally applies highest priority variables, i.e. device specific vars
                expanded_inventory[device].update(d_vars)
                # removing groups key to more easily pass to napalm kwargs
                if 'groups' in expanded_inventory[device]:
                    expanded_inventory[device].pop('groups')
                expanded_inventory[device] = self._ensure_hostname(expanded_inventory[device],
                                                                   device)

        return self._sort_inventory(expanded_inventory)


if __name__ == "__main__":
    import json
    inventory = Inventory('~/napalm2.yml')  # Inventory() would use default settings

    # device inventory
    print 'INVENTORY BASED ON DEVICE ONLY'
    print json.dumps(inventory.get_device_inventory(), indent=4)

    # complete inventory based on group
    print 'INVENTORY BASED ON GROUP AND DEVICE ONLY'
    print json.dumps(inventory.get_inventory(), indent=4)

    # list of group names
    print "ALL GROUPS:"
    print inventory.get_groups()

    # list of all devices
    print "ALL DEVICES:"
    print inventory.get_devices()

    # list of devices per group
    print "DEVICE PER GROUP:"
    print inventory.get_group_inventory()


    # optionally, pass group name- return list of devices in group
    print "GET DEVICES FOR A SINGLE GROUP (dc_edge)"
    print inventory.get_devices('dc_edge')

    # return instantiated driver device object for provided device
    print "GET A SINGLE NAPALM DEVICE OBJECT:"
    print inventory.get_device('csr1')
    print inventory.get_device('eos-spine1')

    # return list of instantiated driver device objects for provided group
    print "GET A LIST OF NAPALM DEVICE OBJECT:"
    cisco_devices = inventory.get_group('cisco_ios')
    print cisco_devices
    dc_edge_devices = inventory.get_group('dc_edge')
    print dc_edge_devices

