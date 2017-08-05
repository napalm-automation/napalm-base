# Copyright 2017 Dravetech AB. All rights reserved.
#
# The contents of this file are licensed under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with the
# License. You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.

# Python3 support
from __future__ import print_function
from __future__ import unicode_literals

from napalm_base.base import NetworkDriver
import napalm_base.exceptions

import ast
import inspect
import json
import os
import re


from functools import wraps
from pydoc import locate


def count_calls(name=None, pass_self=True):
    def real_decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                funcname = name or func.__name__
                self = args[0]
                args = args if pass_self else args[1:]
                try:
                    self.current_count = self.calls[funcname]
                except KeyError:
                    self.calls[funcname] = 1
                    self.current_count = 1
                r = func(*args, **kwargs)
                self.calls[funcname] += 1
            except Exception:
                if self.increase_count_on_error:
                    self.calls[funcname] += 1
                raise
            return r
        return wrapper
    return real_decorator


def raise_exception(result):
    exc = locate(result["exception"])
    if exc:
        raise exc(*result.get("args", []), **result.get("kwargs", {}))
    else:
        raise TypeError("Couldn't resolve exception {}".format(result["exception"]))


def is_mocked_method(method):
    mocked_methods = []
    if method.startswith("get_") or method in mocked_methods:
        return True
    return False


def mocked_method(self, name):
    parent_method = getattr(NetworkDriver, name)
    parent_method_args = inspect.getargspec(parent_method)
    modifier = 0 if 'self' not in parent_method_args.args else 1

    def _mocked_method(*args, **kwargs):
        # Check len(args)
        if len(args) + len(kwargs) + modifier > len(parent_method_args.args):
            raise TypeError(
                "{}: expected at most {} arguments, got {}".format(
                    name, len(parent_method_args.args), len(args) + modifier))

        # Check kwargs
        unexpected = [x for x in kwargs if x not in parent_method_args.args]
        if unexpected:
            raise TypeError("{} got an unexpected keyword argument '{}'".format(name,
                                                                                unexpected[0]))
        return count_calls(name, pass_self=False)(
            mocked_data)(self, self.path, name, self.calls.get(name, 1))

    return _mocked_method


def mocked_data(path, name, count):
    filename = "{}.{}".format(os.path.join(path, name), count)
    try:
        with open(filename) as f:
            result = json.loads(f.read())
    except IOError:
        raise NotImplementedError("You can provide mocked data in {}".format(filename))

    if "exception" in result:
        raise_exception(result)
    elif "plain_text" in result:
        return result["plain_text"]
    elif "direct_value" in result:
        return ast.literal_eval(result["direct_value"])
    else:
        return result


class MockDevice(object):

    def __init__(self, parent, profile):
        self.parent = parent
        self.profile = profile

    def run_commands(self, commands):
        """Only useful for EOS"""
        if "eos" in self.profile:
            return self.parent.cli(commands).values()[0]
        else:
            raise AttributeError("MockedDriver instance has not attribute '_rpc'")


class MockDriver(NetworkDriver):

    def __init__(self, hostname, username, password, timeout=60, optional_args=None):
        """
        Supported optional_args:
            * path(str) - path to where the mocked files are located
            * profile(list) - List of profiles to assign
        """
        self.hostname = hostname
        self.username = username
        self.password = password
        self.path = optional_args["path"]
        self.profile = optional_args.get("profile", [])

        self.opened = False
        self.calls = {}
        self.device = MockDevice(self, self.profile)

        # None no action, True load_merge, False load_replace
        self.merge = None
        self.filename = None
        self.config = None

        self.increase_count_on_error = optional_args.get("increase_count_on_error", True)

    def _raise_if_closed(self):
        if not self.opened:
            raise napalm_base.exceptions.ConnectionClosedException("connection closed")

    def open(self):
        self.opened = True

    def close(self):
        self.opened = False

    def is_alive(self):
        return {"is_alive": self.opened}

    @count_calls()
    def cli(self, commands):
        result = {}
        regexp = re.compile('[^a-zA-Z0-9]+')
        for i, c in enumerate(commands):
            sanitized = re.sub(regexp, '_', c)
            name = "cli.{}.{}".format(self.current_count, sanitized)
            filename = "{}.{}".format(os.path.join(self.path, name), i)
            with open(filename, 'r') as f:
                result[c] = f.read()
        return result

    @count_calls()
    def load_merge_candidate(self, filename=None, config=None):
        self._raise_if_closed()
        self.merge = True
        self.filename = filename
        self.config = config
        mocked_data(self.path, "load_merge_candidate", self.current_count)

    @count_calls()
    def load_replace_candidate(self, filename=None, config=None):
        self._raise_if_closed()
        self.merge = False
        self.filename = filename
        self.config = config
        mocked_data(self.path, "load_replace_candidate", self.current_count)

    @count_calls()
    def compare_config(self, filename=None, config=None):
        self._raise_if_closed()
        return mocked_data(self.path, "compare_config", self.current_count)["diff"]

    @count_calls()
    def commit_config(self):
        self._raise_if_closed()
        self.merge = None
        self.filename = None
        self.config = None
        mocked_data(self.path, "commit_config", self.current_count)

    @count_calls()
    def discard_config(self):
        self._raise_if_closed()
        self.merge = None
        self.filename = None
        self.config = None
        mocked_data(self.path, "discard_config", self.current_count)

    def _rpc(self, get):
        """This one is only useful for junos."""
        if "junos" in self.profile:
            return self.cli([get]).values()[0]
        else:
            raise AttributeError("MockedDriver instance has not attribute '_rpc'")

    def __getattribute__(self, name):
        if is_mocked_method(name):
            self._raise_if_closed()
            return mocked_method(self, name)
        else:
            return object.__getattribute__(self, name)
