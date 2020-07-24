#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Apr  9 19:02:42 2020

@author: mep53
"""
import docker
import time
import datetime as dt
import os
from multiprocessing import Pool
from utils.Logger import Logger

class RunConfig:
    def __init__(self, client, config):
        self.base_dir = config['file_system']['base_dir']
        self.run_base_label = config['run']['run_base_label']
        self.client = client
        #userid =  1016
        #groupid = 1018
        self.userid =  config['containers']['userid']
        self.groupid = config['containers']['groupid']


class AgentConfig:
    def __init__(self, config,config_obj):
        #Create x number of agents before wait
        self.ag_wait_x = config['mas_config']['ag_wait_x']
        #Wait seconds between creation of x agents
        self.ag_wait_time = config['mas_config']['ag_wait_time']
        ########Agent Parameters ########
        self.config = config
        self.ag_img = config['run_app']['ag_img']
        self.ag_label = config['mas_config']['ag_label']
        self.ag_mem_limit = config['mas_config']['ag_mem_limit']
        self.ag_mem_res = config['mas_config']['ag_mem_res']
        self.ag_cpus = config['mas_config']['ag_cpus']
        self.ag_command = config['mas_config']['ag_command']
        self.ag_data_in = config['file_system']['base_dir'] + config['app']['ag_data_in']
        #ag_data_in = "/home/mep53/workspace/ngcdi/sckl-poc-data/100-node"
        #ag_logs_dir = "/home/mep53/workspace/scala/ngcdi/mperhez/sckl-poc-scripts/logs"
        self.ag_logs_dir = config['file_system']['base_dir'] + config['app']['ag_logs_dir']
        self.ag_data_dir = config['app']['ag_data_dir']
        self.ag_port = config['mas_config']['ag_port']
        self.ag_ports = config['mas_config']['ag_ports']

        #fix 'None' in ag_ports

        for k,v in self.ag_ports.items():
            if(v == 'None'):
                self.ag_ports[k] = None

        self.ag_seed_addr = config['app']['ag_seed_addr']
        self.ag_seed_port = config['app']['ag_seed_port']
        self.ag_sdnc_server= config['run_app']['ag_sdnc_server']
        self.ag_sdnc_port=config['run_app']['ag_sdnc_port']
        self.ag_netw_server= config['run_app']['ag_netw_server']
        self.ag_netw_port=config['run_app']['ag_netw_port']
        self.ag_netw_urls=config['run_app']['ag_netw_urls']
        self.ag_netw_api_key=config['run_app']['ag_netw_api_key']
        self.ag_ui_url=config['run_app']['ag_ui_url']
        self.ag_monitoring_url= config['run_app']['ag_monitoring_url']
        self.ag_key_services = config['app']['ag_key_services']
        self.sm_label = config['run_app']['agents']['labels'][0]
        self.fp_label = config['run_app']['agents']['labels'][1]
        self.da_label = config['run_app']['agents']['labels'][2]

        self.ag_order = {
            self.sm_label: config['app']['agents']['order'][0],
            self.fp_label:config['app']['agents']['order'][1],
            self.da_label:config['app']['agents']['order'][2]
            }



class SingleRun:
    def __init__(self,ntw,sm_q,fp_q,da_q,run_label,duration, agentCfg, config, config_obj):
        self.config = config
        self.config_obj = config_obj
        self.ntw = ntw
        self.run_label = run_label
        self.duration  = duration
        self.agents = {
                agentCfg.sm_label:{"q":sm_q,"label":"seed","mem_limit":agentCfg.ag_mem_limit, "mem_res":agentCfg.ag_mem_res, "cpus":agentCfg.ag_cpus,"vols":{},"nodes":str(da_q)},
                agentCfg.fp_label:{"q":fp_q,"label":"prov","mem_limit":agentCfg.ag_mem_limit, "mem_res":agentCfg.ag_mem_res, "cpus":agentCfg.ag_cpus,"vols":{}},
                agentCfg.da_label:{"q":da_q,"label":"c","mem_limit":agentCfg.ag_mem_limit, "mem_res":agentCfg.ag_mem_res, "cpus":agentCfg.ag_cpus, "vols":{agentCfg.ag_data_in:{"bind":"/data","mode":"ro"}}}
              }
        self.agentCfg = agentCfg

    def create_agents(self):
            ag_ids = []

            for k in sorted(self.agents, key=lambda x: self.agentCfg.ag_order[x] ):
                e = self.agents[k]
                ag_n = 0
                for ag_n in range(1,e.get("q")+1):
                    ag_name = e.get("label")+str(ag_n)


                    #####For Ring topology calculate neighbours##
                    ag_ngb_left = 0
                    ag_ngb_right = 0
                    ag_n_mod = ag_n % e.get("q")

                    if(ag_n_mod == 1):
                        ag_ngb_left = e.get("q")
                        ag_ngb_right = ag_n+1
                    else:
                        if(ag_n_mod == 0):
                            ag_ngb_left = ag_n-1
                            ag_ngb_right = 1
                        else:
                            ag_ngb_left = ag_n-1
                            ag_ngb_right = ag_n+1

                    ##############################################
                    ag_dev_id = str(ag_n)
                    if('onos' in self.config):
                        ag_dev_id = str(self.config['onos']['devices'][ag_n-1])



                    ag_env = {
                        "CLUSTER_PORT": self.agentCfg.ag_port,
                        "CLUSTER_IP": ag_name,
                        "SEED_PORT_1600_TCP_ADDR": self.agentCfg.ag_seed_addr,
                        "SEED_PORT_1600_TCP_PORT": self.agentCfg.ag_seed_port,
                        "LAUNCHER": k,
                        "DATADIR": self.agentCfg.ag_data_dir,
                        "SDNC_SERVER": self.agentCfg.ag_sdnc_server,
                        "SDNC_PORT": self.agentCfg.ag_sdnc_port,
                        "NETW_SERVER": self.agentCfg.ag_netw_server,
                        "NETW_PORT": self.agentCfg.ag_netw_port,
                        "NETW_API_KEY": self.agentCfg.ag_netw_api_key,
                        "NETW_URLS": self.agentCfg.ag_netw_urls,
                        "UI_URL": self.agentCfg.ag_ui_url,
                        "MONITORING_URL": self.agentCfg.ag_monitoring_url,
                        "DEV_ID":ag_dev_id,
                        "LEFT_NEIGHBOUR": e.get("label")+str(ag_ngb_left),
                        "RIGHT_NEIGHBOUR": e.get("label")+str(ag_ngb_right)
                        }

                    ag_vols = e.get("vols")
                    ag_vols_n = ag_vols.copy()
                    ag_log_file_name = self.config_obj.create_log_file(self.agentCfg.ag_logs_dir,self.run_label,ag_name)
                    ag_vols_n[ag_log_file_name] = {"bind":"/opt/docker/logs/app.log","mode":"rw"}

                    theports = self.agentCfg.ag_ports

                    if(k == self.agentCfg.sm_label):
                        ag_env.update({"NODES":e.get("nodes")})
                        ag_env.update({"KEY_SERVICES":"sc"+str(ag_n)})
                        theports = self.agentCfg.ag_ports.copy()
                        theports['7780']= "778"+str(ag_n)
                    else:
                        if (k == self.agentCfg.da_label and self.agentCfg.da_label == "digitalassetn" ):
                            ag_env.update({"KEY_SERVICES": self.agentCfg.ag_key_services})
                        else:
                            ag_env.update({"KEY_SERVICES": ""})


                    lmsg = self.run_label + ": For agent:" + str(ag_n)
                    Logger.get_logger(self.config['run']['run_base_label']).info(lmsg)

                    #print (ag_vols)
                    lmsg = self.run_label + ":" + str(ag_env)
                    Logger.get_logger(self.config['run']['run_base_label']).info(lmsg)

                    ag = self.config_obj.client.containers.run(self.agentCfg.ag_img,
                                  self.agentCfg.ag_command,
                                  name = ag_name,
                                  auto_remove = False,
                                  detach = True,
                                  mem_limit = e.get("mem_limit"),
                                  mem_reservation = e.get("mem_res"),
                                  network = self.ntw.name,
                                  volumes = ag_vols_n,
                                  ports = theports,
                                  environment = ag_env,
                                  hostname=ag_name
                                  )
                    ag_ids.append(ag.id)
                    if(ag_n%self.agentCfg.ag_wait_x == 0):
                      time.sleep(self.agentCfg.ag_wait_time)

            lmsg = self.run_label + ":" + "agents created..." + str(ag_ids)
            Logger.get_logger(self.config['run']['run_base_label']).info(lmsg)
            lmsg = self.run_label + ":" + "agents created at " + dt.datetime.now().strftime(self.config['dates']['date_format'])
            Logger.get_logger(self.config['run']['run_base_label']).info(lmsg)

            return ag_ids
