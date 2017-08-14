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
import json
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
                    logger.debug("{} - Successful".format(name))
                    return r
                except NotImplementedError:
                    if name not in ["pre_connection_tests", "connection_tests",
                                    "post_connection_tests"]:
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
def call_get_network_driver(vendor):
    return get_network_driver(vendor)


@debugging("__init__")
def call_instantiating_object(driver, *args, **kwargs):
    return driver(*args, **kwargs)


@debugging("pre_connection_tests")
def call_pre_connection(driver):
    driver.pre_connection_tests()


@debugging("connection_tests")
def call_connection(driver):
    driver.connection_tests()


@debugging("post_connection_tests")
def call_post_connection(driver):
    driver.post_connection_tests()


@debugging("get_facts")
def call_facts(driver):
    facts = driver.get_facts()
    logger.debug("Gathered facts:\n{}".format(json.dumps(facts, indent=4)))


@debugging("close")
def call_close(driver):
    return driver.close()


@debugging("open")
def call_open_device(device):
    return device.open()


@debugging("load_replace_candidate")
def call_load_replace_candidate(device, *args, **kwargs):
    return device.load_replace_candidate(*args, **kwargs)


@debugging("load_merge_candidate")
def call_load_merge_candidate(device, *args, **kwargs):
    return device.load_merge_candidate(*args, **kwargs)


@debugging("compare_config")
def call_compare_config(device, *args, **kwargs):
    diff = device.compare_config(*args, **kwargs)
    logger.info("Gathered diff:\n{}".format(diff))
    return diff


@debugging("commit_config")
def call_commit_config(device, *args, **kwargs):
    return device.commit_config(*args, **kwargs)


def configuration_change(device, config_file, strategy, dry_run):
    if strategy == 'replace':
        strategy_method = call_load_replace_candidate
    elif strategy == 'merge':
        strategy_method = call_load_merge_candidate

    strategy_method(device, filename=config_file)

    diff = call_compare_config(device)

    if not dry_run:
        call_commit_config(device)
    return diff


@debugging("getter")
def call_getter(device, getter, **kwargs):
    logger.debug("{} - Attempting to resolve getter".format(getter))
    func = getattr(device, getter)
    logger.debug("{} - Attempting to call getter with kwargs: {}".format(getter, kwargs))
    r = func(**kwargs)
    logger.debug("{} - Response".format(getter))
    logger.info("Result of {}:\n{}".format(getter, json.dumps(r, indent=4)))


def run_tests(args):
    driver = call_get_network_driver(args.vendor)
    optional_args = helpers.parse_optional_args(args.optional_args)

    device = call_instantiating_object(driver, args.hostname, args.user, password=args.password,
                                       timeout=60, optional_args=optional_args)

    if args.debug:
        call_pre_connection(device)

    call_open_device(device)

    if args.debug:
        call_connection(device)
        call_facts(device)

    if args.getter:
        getter_kwargs = helpers.parse_optional_args(args.getter_kwargs)
        call_getter(device, args.getter, **getter_kwargs)

    if args.config_file:
        configuration_change(device, args.config_file, args.strategy, args.dry_run)

    call_close(device)

    if args.debug:
        call_post_connection(device)


def main():
    args = helpers.build_help(show_tech=True)
    helpers.configure_logging(logger, debug=args.debug)
    logger.debug("Starting napalm's debugging tool")
    check_installed_packages()
    run_tests(args)


if __name__ == '__main__':
    main()
