# -*- coding: utf-8 -*-
'''
Decorators for napalm methods.
'''
from __future__ import absolute_import
from __future__ import unicode_literals

from functools import wraps


def always_alive(fun):
    def _connection_alive(obj):
        _alive = True
        _default_alive_method = lambda: True
        try:
            _is_alive_method = getattr(obj, 'is_alive')
            _auto_reconnect = getattr(obj, 'auto_reconnect')
            if not _auto_reconnect:
                # if not requested to check if the connection is alive
                _is_alive_method = _default_alive_method
        except AttributeError:
                _is_alive_method = _default_alive_method
                # if not implemented in the driver, will just assume it is connected...
        _alive = _is_alive_method()
        return _alive
    @wraps(fun)
    def _always_alive_wrapper(*args, **kwargs):
        _obj = args[0]  # instance of driver class
        _alive = _connection_alive(_obj)
        if not _alive:
            _obj.open()
        return fun(*args, **kwargs)
    return _always_alive_wrapper
