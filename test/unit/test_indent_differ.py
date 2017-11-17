from napalm_base import get_network_driver
from napalm_base import indent_differ

from glob import glob
import pytest

import os


BASE_PATH = os.path.dirname(__file__)


driver = get_network_driver("mock")


test_cases_differ = [x.split('/')[-1] for x in glob('{}/test_indent_differ/*'.format(BASE_PATH))]


class Test_Indent_differ(object):
    """Test Mock Driver."""

    def test_parser(self):
        candidate = '''
enable password whatever

interface Loopback0
  description "blah"
interface GigabitEthernet1
  description "bleh"

  fake nested
    nested nested configuration

  switchport mode trunk

interface GigabitEthernet2
  no ip address

interface GigabitEthernet3
 no ip address
 shutdown

 negotiation auto'''

        parsed = indent_differ.IndentedConfig(candidate)

        expected = {'enable password whatever': {},
                    'interface GigabitEthernet1': {
                        'description "bleh"': {},
                        'fake nested': {
                            'nested nested configuration': {}},
                        'switchport mode trunk': {}},
                    'interface GigabitEthernet2': {
                        'no ip address': {}},
                    'interface GigabitEthernet3': {
                        'negotiation auto': {},
                        'no ip address': {},
                        'shutdown': {}},
                    'interface Loopback0': {
                        'description "blah"': {}}}

        assert parsed.to_dict() == expected

    @pytest.mark.parametrize("case", test_cases_differ)
    def test_basic(self, case):
        path = os.path.join(BASE_PATH, "test_indent_differ", case)
        optional_args = {
            "path": path,
            "profile": ["mock"],
        }

        with driver("blah", "bleh", "blih", optional_args=optional_args) as d:
            running = d.cli(["show running config"])["show running config"]

        with open(os.path.join(path, "candidate.txt"), "r") as f:
            candidate = f.read()

        with open(os.path.join(path, "diff.txt"), "r") as f:
            expected = f.read()

        diff = indent_differ.IndentedConfig(running).diff(candidate)
        assert diff.strip() == expected.strip(), diff
