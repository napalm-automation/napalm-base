from napalm_base import get_network_driver

import json


def pretty_print(dictionary):
    print(json.dumps(dictionary, sort_keys=True, indent=4))


eos_configuration = {
    'hostname': '127.0.0.1',
    'username': 'vagrant',
    'password': 'vagrant',
    'optional_args': {'port': 12443}
}

eos = get_network_driver("eos")
eos_device = eos(**eos_configuration)

eos_device.open()
pretty_print(eos_device.yang.get_openconfig_interfaces(candidate=True))
print(eos_device.yang.get_openconfig_network_instance())

print("# Raw translation")
print(eos_device.yang.translate())
print("-------------")

print("# Merge without changes, should be empty")
print(eos_device.yang.translate(merge=True))
print("-------------")

print("# Replace without changes")
print(eos_device.yang.translate(replace=True))
print("-------------")


print("# Change a description")
eos_device.candidate.interfaces.interface["Ethernet1"].config.description = "This is a new description"  # noqa
pretty_print(eos_device.yang.diff())
print("-------------")

print("# Merge change")
merge_config = eos_device.yang.translate(merge=True)
print(merge_config)
print("-------------")

print("# Replace change")
replace_config = eos_device.yang.translate(replace=True)
print(replace_config)
print("-------------")

print("# Let's replace the current interfaces configuration from the device")
eos_device.load_merge_candidate(config=replace_config)
print(eos_device.compare_config())
eos_device.discard_config()
print("-------------")

print("# Let's merge the current interfaces configuration from the device")
eos_device.load_merge_candidate(config=merge_config)
print(eos_device.compare_config())
eos_device.discard_config()
print("-------------")

eos_device.close()

print("# For reference, you can also print the model for both the config and the state parts of the model")  # noqa
pretty_print(eos_device.yang.model_openconfig_vlan())
pretty_print(eos_device.yang.model_openconfig_vlan(data="state"))
