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

import inspect
import json
import os
import re


from pydoc import locate


def raise_exception(result):
    exc = locate(result["exception"])
    if exc:
        raise exc(*result.get("args", []), **result.get("kwargs", {}))
    else:
        raise TypeError("Couldn't resolve exception {}", result["exception"])


def is_mocked_method(method):
    mocked_methods = []
    if method.startswith("get_") or method in mocked_methods:
        return True
    return False


def mocked_method(path, name, count):
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

        filename = "{}.{}".format(os.path.join(path, name), count)
        try:
            with open(filename) as f:
                result = json.loads(f.read())
        except IOError:
            raise NotImplementedError("You can provide mocked data in {}".format(filename))

        if "exception" in result:
            raise_exception(result)
        else:
            return result

    return _mocked_method


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

    def _count_calls(self, name):
        current_count = self.calls.get(name, 0)
        self.calls[name] = current_count + 1
        return self.calls[name]

    def open(self):
        self.opened = True

    def close(self):
        self.opened = False

    def is_alive(self):
        return {"is_alive": self.opened}

    def cli(self, commands):
        count = self._count_calls("cli")
        result = {}
        regexp = re.compile('[^a-zA-Z0-9]+')
        for i, c in enumerate(commands):
            sanitized = re.sub(regexp, '_', c)
            name = "cli.{}.{}".format(count, sanitized)
            filename = "{}.{}".format(os.path.join(self.path, name), i)
            with open(filename, 'r') as f:
                result[c] = f.read()
        return result

    def _rpc(self, get):
        """This one is only useful for junos."""
        if "junos" in self.profile:
            return self.cli([get]).values()[0]
        else:
            raise AttributeError("MockedDriver instance has not attribute '_rpc'")

    def __getattribute__(self, name):
        if is_mocked_method(name):
            if not self.opened:
                raise napalm_base.exceptions.ConnectionClosedException("connection closed")
            count = self._count_calls(name)
            return mocked_method(self.path, name, count)
        else:
            return object.__getattribute__(self, name)
