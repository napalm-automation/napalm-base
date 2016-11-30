#!/usr/bin/env python

devicearg = {
    'hostname':   '127.0.0.1',
    'username': 'vagrant',
    'password': 'vagrant',
    'optional_args': {'port': 12206, 'use_keys': False},
}

import napalm_vyos
import os

mydevice = napalm_vyos.VyOSDriver(**devicearg)
mydevice.open()

mydevice.load_replace_candidate(filename='../vyos/initial.conf')
mydevice.commit_config()

mydevice.close()
