import pytest
from napalm_base.test import conftest as parent_conftest
from napalm_base.test.double import BaseTestDouble
from napalm_base.base import NetworkDriver


@pytest.fixture(scope='class')
def set_device_parameters(request):
    """Set up the class."""
    def fin():
        request.cls.device.close()
    request.addfinalizer(fin)

    request.cls.driver = NetworkDriver
    request.cls.patched_driver = PatchedNetworkDriver
    request.cls.vendor = 'base'
    parent_conftest.set_device_parameters(request)


def pytest_generate_tests(metafunc):
    """Generate test cases dynamically."""
    parent_conftest.pytest_generate_tests(metafunc, __file__)


class PatchedNetworkDriver(NetworkDriver):
    """Patched Network Driver."""

    def __init__(self, hostname, username, password, timeout=60, optional_args=None):
        self.patched_attrs = ['device']
        self.device = FakeNetworkDevice()

    def open(self):
        pass

    def close(self):
        pass


class FakeNetworkDevice(BaseTestDouble):
    pass
