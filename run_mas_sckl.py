#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Apr  9 21:05:03 2020

@author: mep53
"""
from mas.VCAInfrastructure import VCAInfrastructure
import hiyapyco
import pprint
import argparse
import os

base_dir = os.getcwd() + "/"

def main():

    parser = argparse.ArgumentParser(description='Runs a container-based multi agent system. By default uses: run_config.yaml')
    parser.add_argument('-c','--config', action='store', help='run with a specific configuration file')
    args= parser.parse_args()


    if args.config != None:
         config = hiyapyco.load( # Order is important the latest files override the first ones
             base_dir+'resources/base_config.yaml',
             base_dir+'resources/reporting_config.yaml',
             base_dir+'resources/net_emu_config.yaml',
             base_dir+'resources/agents_config.yaml',
             base_dir+args.config,
             method=hiyapyco.METHOD_SIMPLE,   # Just replace the overriden values
             interpolate=True,
             usedefaultyamlloader=True,
             #method=hiyapyco.METHOD_MERGE  # Replace the entire section
             )
    else:
        config = hiyapyco.load( # Order is important the latest files override the first ones
             base_dir+'resources/base_config.yaml',
             base_dir+'resources/reporting_config.yaml',
             base_dir+'resources/net_emu_config.yaml',
             base_dir+'resources/agents_config.yaml',
             base_dir+'run_config.yaml',
             method=hiyapyco.METHOD_SIMPLE,   # Just replace the overriden values
             interpolate=True,
             usedefaultyamlloader=True,
             #method=hiyapyco.METHOD_MERGE  # Replace the entire section
             )

    #pprint.PrettyPrinter(indent=4).pprint(config)
    #print(conf['run']['infrastructure_q'][0]['net_emu'])


    sckl = VCAInfrastructure(config)
    sckl.run()

main()
