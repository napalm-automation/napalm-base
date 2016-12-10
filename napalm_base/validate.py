"""Validation methods for the NAPALM base."""

import yaml

from napalm_base.exceptions import ValidationException


def _check_getters(cls, getters):
    if isinstance(getters, str):
        getters = [getters]

    for getter in getters:
        if (getter.startswith('get_') and getter in dir(cls)) is False:
            raise ValidationException("{0} method not found.".format(getter))

    return getters


def _check_config(config):
    if config not in ['running', 'candidate']:
        raise ValidationException("{0} config not supported. Only running or "
                                  "candidate are allowed".format(config))


def _get_validation_file(validation_file):
    try:
        with open(validation_file, 'r') as stream:
            try:
                validation_source = yaml.load(stream)
            except yaml.YAMLError, exc:
                raise ValidationException(exc)
    except IOError:
        raise ValidationException("File {0} not found.".format(validation_file))
    return validation_source


def _find_differences(cls, key, actual_value, expected_values):
    not_matched_result = ''
    if actual_value is None:
        not_matched_result = "Expected key but not found."

    if isinstance(actual_value, dict):
        not_matched_result = _handle_dict(cls, actual_value, expected_values[key])

    elif (isinstance(actual_value, unicode) or
          isinstance(actual_value, int)):
        not_matched_result = _handle_unicode_int(actual_value, expected_values[key])

    elif isinstance(actual_value, list):
        not_matched_result = _handle_list(actual_value, expected_values[key])
    return not_matched_result


def _handle_dict(cls, actual_values, expected_values):
    not_matched = []
    not_matched_dict = {}
    try:
        delta = dict(set(expected_values.iteritems()).difference(actual_values.iteritems()))
    except TypeError:
        for key in expected_values.keys():
            actual_value = actual_values.get(key)

            not_matched_result = _find_differences(cls, key, actual_value, expected_values)
            if not_matched_result:
                not_matched_dict[key] = not_matched_result

        return not_matched_dict

    if delta:
        for delta_key in delta.keys():
            not_matched_string = ''
            not_matched_string = ("Expected '{0}: {1}', found '{2}: {3}' "
                                  "instead".format(delta_key, delta[delta_key],
                                                   delta_key, actual_values[delta_key]))
            if not_matched_string:
                not_matched.append(not_matched_string)
    return not_matched


def _handle_unicode_int(actual_values, expected_values):
    not_matched_string = ''
    if str(actual_values) != str(expected_values):
        not_matched_string = ("Expected '{0}', "
                              "found '{1}' instead".format(expected_values, actual_values))
    return not_matched_string


def _handle_list(actual_values, expected_values):
    not_matched = []
    not_matched_string = ''
    for value in expected_values:
        if isinstance(value, dict):
            found = False
            for act_values in actual_values:
                delta = dict(set(value.iteritems()).difference(act_values.iteritems()))
                if not delta:
                    found = True
            if found is False:
                not_matched_string = ("Expected but not found: {0}".format(value, actual_values))
        else:
            if value not in actual_values:
                not_matched_string = ("Expected but not found: {0}".format(value, actual_values))

        if not_matched_string:
            not_matched.append(not_matched_string)

    return not_matched


def _find_config_differences(actual_config, expected_config):
    not_matched = []

    for config_line in expected_config:
        if config_line not in actual_config:
            not_matched.append(config_line)

    return not_matched


def validate(cls, getters=None, config=None, validation_file=None):
    """
    Validate getter methods outputs and configurations comparing them with a validation
    YAML file containing expected results.

    In order to validate getter methods, YAML file's keys have to match the getter
    method's name willing to validate and its values structure must reflect the getter
    output format.

    Example:
    ---

    get_bgp_neighbors:
      default:
        router_id: 192.0.2.2
        peers:
          192.0.2.3:
            is_enabled: false

    get_interfaces:
      Ethernet2/5:
        is_enabled: true
        is_up: true

      Vlan100:
        is_enabled: false
        is_up: false

    In order to validate configuration, the YAML file must contain keys like 'running'
    or 'candidate' and their content must be a list of configuration lines that must be
    present in the configuration. To do that, get_config() method must be supported by
    the network driver.

    Example:
    ---

    running:
      - username napalm password napalm

    :param cls: Instance of the driver class
    :param getters: Specifies the name of the getter function to be tested.
    :param config: Either 'running' or 'candidate', specifying which config should be tested.
    :param validation_file: Name of the YAML file used for the validation.
    :return: True if a full match is found, Otherwise, it will return a dictionary.
    """
    errors = {}
    if getters:
        getters = _check_getters(cls, getters)

    if config:
        _check_config(config)

    validation_source = _get_validation_file(validation_file)

    if getters:
        for getter in getters:
            not_matched_getter = {}

            try:
                expected_results = validation_source[getter]
            except KeyError:
                raise ValidationException('{0} key not found in validation file.'
                                          ' Check your syntax.'.format(getter))

            actual_results = getattr(cls, getter)()
            if isinstance(actual_results, list):
                actual_results = dict(not_matched=actual_results)
                expected_results = dict(not_matched=expected_results)

            for key in expected_results.keys():
                not_matched_result = ''
                not_matched = []
                actual_values = actual_results.get(key)
                not_matched_result = _find_differences(cls, key, actual_values, expected_results)

                if not_matched_result:
                    if (isinstance(not_matched_result, dict) or
                            isinstance(not_matched_result, str)):
                        not_matched.append(not_matched_result)
                    else:
                        not_matched.extend(not_matched_result)

                if not_matched:
                    not_matched_getter[key] = not_matched

            if not_matched_getter:
                errors[getter] = not_matched_getter

    elif config:
        try:
            expected_config = validation_source[config]
        except KeyError:
            raise ValidationException('{0} key not found in validation file.'
                                      ' Check your syntax.'.format(config))

        actual_config = cls.get_config(retrieve=config)[config]
        not_matched_result = _find_config_differences(actual_config, expected_config)

        if not_matched_result:
            error_string = "Expected but not found in {0} config".format(config)
            errors[error_string] = not_matched_result

    if not errors:
        return True
    else:
        return errors
