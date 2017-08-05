"""
Test base helpers.
"""

# Python3 support
from __future__ import print_function
from __future__ import unicode_literals


# NAPALM base
from napalm_base import get_network_driver
import napalm_base.exceptions

import pytest

import copy
import os


BASE_PATH = os.path.dirname(__file__)


driver = get_network_driver("mock")
optional_args = {
    "path": os.path.join(BASE_PATH, "test_mock_driver"),
    "profile": ["eos"],
}


class TestMockDriver(object):
    """Test Mock Driver."""

    def test_basic(self):
        d = driver("blah", "bleh", "blih", optional_args=optional_args)
        assert d.is_alive() == {u'is_alive': False}
        d.open()
        assert d.is_alive() == {u'is_alive': True}
        d.close()
        assert d.is_alive() == {u'is_alive': False}

        with pytest.raises(napalm_base.exceptions.ConnectionClosedException) as excinfo:
            d.get_facts()
        assert "connection closed" in excinfo.value

    def test_context_manager(self):
        with driver("blah", "bleh", "blih", optional_args=optional_args) as d:
            assert d.is_alive() == {u'is_alive': True}
        assert d.is_alive() == {u'is_alive': False}

    def test_mocking_getters(self):
        d = driver("blah", "bleh", "blih", optional_args=optional_args)
        d.open()
        assert d.get_facts()["hostname"] == "localhost"
        assert d.get_facts()["hostname"] == "changed_hostname"
        d.close()

    def test_not_mocking_getters(self):
        d = driver("blah", "bleh", "blih", optional_args=optional_args)
        d.open()

        with pytest.raises(NotImplementedError) as excinfo:
            d.get_route_to()
        expected = "You can provide mocked data in {}/get_route_to.1".format(optional_args["path"])
        assert expected in excinfo.value

        with pytest.raises(NotImplementedError) as excinfo:
            d.get_route_to()
        expected = "You can provide mocked data in {}/get_route_to.2".format(optional_args["path"])
        assert expected in excinfo.value

        d.close()

    def test_arguments(self):
        d = driver("blah", "bleh", "blih", optional_args=optional_args)
        d.open()

        with pytest.raises(TypeError) as excinfo:
            d.get_route_to(1, 2, 3)
        assert "get_route_to: expected at most 3 arguments, got 4" in excinfo.value

        with pytest.raises(TypeError) as excinfo:
            d.get_route_to(1, 1, protocol=2)
        assert "get_route_to: expected at most 3 arguments, got 3" in excinfo.value

        with pytest.raises(TypeError) as excinfo:
            d.get_route_to(proto=2)
        assert "get_route_to got an unexpected keyword argument 'proto'" in excinfo.value

        d.close()

    def test_mock_error(self):
        d = driver("blah", "bleh", "blih", optional_args=optional_args)
        d.open()

        with pytest.raises(KeyError) as excinfo:
            d.get_bgp_neighbors()
        assert "Something" in excinfo.value

        with pytest.raises(napalm_base.exceptions.ConnectionClosedException) as excinfo:
            d.get_bgp_neighbors()
        assert "Something" in excinfo.value

        with pytest.raises(TypeError) as excinfo:
            d.get_bgp_neighbors()
        assert "Couldn't resolve exception NoIdeaException" in str(excinfo.value)

        d.close()

    def test_cli(self):
        d = driver("blah", "bleh", "blih", optional_args=optional_args)
        d.open()
        result = d.cli(["a_command", "b_command"])
        assert result == {'a_command': 'result command a\n', 'b_command': 'result command b\n'}
        d.close()

    def test_configuration_merge(self):
        d = driver("blah", "bleh", "blih", optional_args=optional_args)
        d.open()
        d.load_merge_candidate(config="asdasdasd")
        assert d.merge is True
        d.compare_config() == "a_diff"
        d.commit_config()
        d.close()

    def test_configuration_replace(self):
        d = driver("blah", "bleh", "blih", optional_args=optional_args)
        d.open()
        d.load_replace_candidate(config="asdasdasd")
        assert d.merge is False
        d.compare_config() == "a_diff"
        d.commit_config()
        d.close()

    def test_count_on_error(self):
        optargs = copy.deepcopy(optional_args)
        optargs["increase_count_on_error"] = True
        d = driver("blah", "bleh", "blih", optional_args=optargs)
        d.open()
        try:
            d.get_ntp_peers()
        except Exception:
            pass

        with pytest.raises(NotImplementedError) as excinfo:
            d.get_ntp_peers()
        assert "get_ntp_peers.2" in str(excinfo.value)
        d.close()

    def test_dont_count_on_error(self):
        optargs = copy.deepcopy(optional_args)
        optargs["increase_count_on_error"] = False
        d = driver("blah", "bleh", "blih", optional_args=optargs)
        d.open()
        try:
            d.get_ntp_peers()
        except Exception:
            pass

        with pytest.raises(NotImplementedError) as excinfo:
            d.get_ntp_peers()
        assert "get_ntp_peers.1" in str(excinfo.value)
        d.close()
