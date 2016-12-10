"""Tests for the validate operation."""
from napalm_base.base import NetworkDriver
from napalm_base.validate import compliance_errors

import json

import os


BASEPATH = os.path.dirname(__file__)


class TestValidate:
    """Wrapsts tests."""

    def test_simple(self):
        """A simple test."""
        mocked_data = os.path.join(BASEPATH, "mocked_data", "simple")
        device = FakeDriver(mocked_data)
        errors = compliance_errors(device, os.path.join(mocked_data, "validate.yml"))
        assert not errors

    def test_simple_fail(self):
        """A simple test fail."""
        mocked_data = os.path.join(BASEPATH, "mocked_data", "simple_fail")
        device = FakeDriver(mocked_data)
        errors = compliance_errors(device, os.path.join(mocked_data, "validate.yml"))
        assert errors == {'get_arp_table': {'not_matched': [
                    "Expected but not found: {'interface': 'Ethernet3/1', 'ip': '192.0.2.3'}"]},
                          'get_bgp_neighbors': {'default': ['Expected key but not found.']}}

    def test_simple_config_fail(self):
        """A simple test."""
        mocked_data = os.path.join(BASEPATH, "mocked_data", "simple_config_fail")
        device = FakeDriver(mocked_data)
        errors = compliance_errors(device, os.path.join(mocked_data, "validate.yml"))
        assert errors == {'Expected but not found in running config': ['blah']}


class FakeDriver(NetworkDriver):
    """This is a fake NetworkDriver."""

    def __init__(self, path):
        self.path = path

    def __getattribute__(self, name):
        def load_json(filename):
            def func(**kwargs):
                with open(filename, 'r') as f:
                    return json.loads(f.read())
            return func
        if name.startswith("get_"):
            filename = os.path.join(self.path, "{}.json".format(name))
            return load_json(filename)
        else:
            return object.__getattribute__(self, name)
