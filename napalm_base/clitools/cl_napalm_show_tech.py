# -*- coding: utf-8 -*-
'''
NAPALM CLI Tools: show tech
===========================

Gathering useful information for debugging purposes
'''

# Python3 support
from __future__ import print_function
from __future__ import unicode_literals

# import helpers
from napalm_base import get_network_driver
from napalm_base.clitools import helpers

# stdlib
import pip
import pprint
import logging
from functools import wraps


def debugging(name):
    def real_decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
                censor_parameters = ["password"]
                censored_kwargs = {k: v if k not in censor_parameters else "*******"
                                   for k, v in kwargs.items()}
                logger.debug("{} - Calling with args: {}, {}".format(name, args, censored_kwargs))
                try:
                    r = func(*args, **kwargs)
                    logger.error("{} - Successful".format(name))
                    return r
                except NotImplementedError:
                    logger.info("{} - Not implemented".format(name))
                except Exception as e:
                    logger.error("{} - Failed: {}".format(name, e))
                    print("\n================= Traceback =================\n")
                    raise
        return wrapper
    return real_decorator


logger = logging.getLogger('napalm')


def check_installed_packages():
    logger.debug("Gathering napalm packages")
    installed_packages = pip.get_installed_distributions()
    napalm_packages = sorted(["{}=={}".format(i.key, i.version)
                              for i in installed_packages if i.key.startswith("napalm")])
    for n in napalm_packages:
        logger.debug(n)


@debugging("get_network_driver")
def test_get_network_driver(vendor):
    return get_network_driver(vendor)


@debugging("__init__")
def test_instantiating_object(driver, *args, **kwargs):
    return driver(*args, **kwargs)


@debugging("pre_connection_tests")
def test_pre_connection(driver):
    driver.pre_connection_tests()


@debugging("connection_tests")
def test_connection(driver):
    driver.connection_tests()


@debugging("post_connection_tests")
def test_post_connection(driver):
    driver.post_connection_tests()


@debugging("get_facts")
def test_facts(driver):
    facts = driver.get_facts()
    logger.debug("Gathered facts:")
    pprint.pprint(facts)


@debugging("close")
def test_close(driver):
    driver.close()


@debugging("open")
def test_open_device(device):
    device.open()


@debugging("getter")
def test_getter(device, getter, **kwargs):
    logger.debug("{} - Attempting to resolve getter".format(getter))
    func = getattr(device, getter)
    logger.debug("{} - Attempting to call getter with kwargs: {}".format(getter, kwargs))
    r = func(**kwargs)
    logger.debug("{} - Response".format(getter))
    pprint.pprint(r)


def run_tests(args):
    driver = test_get_network_driver(args.vendor)
    optional_args = helpers.parse_optional_args(args.optional_args)

    device = test_instantiating_object(driver, args.hostname, args.user, password=args.password,
                                       timeout=60, optional_args=optional_args)

    test_pre_connection(device)
    test_open_device(device)
    test_connection(device)
    test_facts(device)

    if args.getter:
        getter_kwargs = helpers.parse_optional_args(args.getter_kwargs)
        test_getter(device, args.getter, **getter_kwargs)

    test_close(device)
    test_post_connection(device)


def main():
    args = helpers.build_help(show_tech=True)
    helpers.configure_logging(logger, logging.DEBUG)
    logger.debug("Starting napalm's debugging tool")
    check_installed_packages()
    run_tests(args)


if __name__ == '__main__':
    main()
