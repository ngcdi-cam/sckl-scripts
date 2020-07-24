#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Apr 16 10:42:25 2020

@author: mep53
"""


import base64
import json
import requests

def getONOSDevices():
    r = requests.get(' https://onos.demo.ng-cdi.com/onos/v1/devices', auth=('onos', 'rocks'))
    
   #js = r.json()
   
    data = json.loads(r.text)
    devices = []
    for d in data['devices']:
       print(d['id'])
       devices.append(d['id'])
    devices.sort()
    return devices

#def main():       
#   getONOSDevices()
#main()
    