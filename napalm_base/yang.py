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

import napalm_yang


# TODO we probably need to adapt the validate framework as well


class Yang(object):

    def __init__(self, device):
        self.device = device
        self.device.running = napalm_yang.base.Root()
        self.device.candidate = napalm_yang.base.Root()

        for model in napalm_yang.SUPPORTED_MODELS:
            # We are going to dynamically attach a getter for each
            # supported YANG model.
            module_name = model[0].replace("-", "_")
            funcname = "get_{}".format(module_name)
            setattr(Yang, funcname, yang_get_wrapper(module_name))
            funcname = "model_{}".format(module_name)
            setattr(Yang, funcname, yang_model_wrapper(module_name))

    def translate(self, merge=False, replace=False, profile=None):
        if profile is None:
            profile = self.device.profile

        if merge:
            return self.device.candidate.translate_config(profile=profile,
                                                          merge=self.device.running)
        elif replace:
            return self.device.candidate.translate_config(profile=profile,
                                                          replace=self.device.running)
        else:
            return self.device.candidate.translate_config(profile=profile)

    def diff(self):
        return napalm_yang.utils.diff(self.device.candidate, self.device.running)


def yang_get_wrapper(module):
    """
    This method basically implements the getter for YANG models.

    The method abstracts loading the model into the root objects (candidate
    and running) and calls the parsers.
    """
    module = getattr(napalm_yang.models, module)

    def method(self, data="config", candidate=False, filter=True):
        # This is the class for the model
        instance = module()

        # We attach it to the running object
        self.device.running.add_model(instance)

        # We get the correct method (parse_config or parse_state)
        parsefunc = getattr(self.device.running, "parse_{}".format(data))

        # We parse *only* the model that corresponds to this call
        running_attrs = [getattr(self.device.running, a) for a in instance.elements().keys()]
        parsefunc(device=self.device, attrs=running_attrs)

        # If we are in configuration mode and the user requests it
        # we create a candidate as well
        if candidate:
            instance = module()
            self.device.candidate.add_model(instance)
            import pdb
            pdb.set_trace()
            parsefunc = getattr(self.device.candidate, "parse_{}".format(data))
            attrs = [getattr(self.device.candidate, a) for a in instance.elements().keys()]
            parsefunc(device=self.device, attrs=attrs)

        # In addition to populate the running object, we return a dict with the contents
        # of the parsed model
        return {a._yang_name: a.get(filter=filter) for a in running_attrs}

    return method


def yang_model_wrapper(module):
    """
    This method basically implements the getter for YANG models.

    The method abstracts loading the model into the root objects (candidate
    and running) and calls the parsers.
    """
    module = getattr(napalm_yang.models, module)

    def method(self, data="config"):
        root = napalm_yang.base.Root()
        root.add_model(module)
        return napalm_yang.utils.model_to_dict(root, data)

    return method
