#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Oct 12 09:55:37 2019

@author: mep53
"""

import docker
import time
import datetime as dt
import os
import sys
from multiprocessing import Pool
from utils.Logger import Logger
from mas.AgentInfrastructure import AgentConfig
from mas.AgentInfrastructure import SingleRun
import onos.ONOSInterface
from pathlib import Path
path = Path(os.getcwd())
ne_path = str(path.parent) + '/ryu-sdn-mininet/'
sys.path.insert(0, ne_path)
from NetworkEmulator import NetworkEmulator

########This part here because thread pool-map does not allow methods only functions....#######
run_base_label = ''
client = docker.from_env() #Needs to be here because of threading, TODO: check later
client_low = docker.APIClient(base_url='unix://var/run/docker.sock') # low level api
###################################
class VCAInfrastructure:
    def __init__(self,config):

        self.config = config
        self.base_dir = config['file_system']['base_dir']
        self.dateFormat = config['dates']['date_format']

        self.ntw_name = config['containers']['ntw_name']
        self.userid = config['containers']['userid']
        self.groupid = config['containers']['groupid']

        ########Prometheus Parameters ########
        self.prom_img = config['prometheus']['prom_img']
        self.prom_label = config['prometheus']['prom_label']
        self.prom_mem_limit = config['prometheus']['prom_mem_limit']
        self.prom_mem_res = config['prometheus']['prom_mem_res']
        self.prom_command = config['prometheus']['prom_command']
        self.prom_config = self.base_dir + config['prometheus']['prom_config']
        self.prom_ports = config['prometheus']['prom_ports']
        #######################################

        ########Influxdb Parameters ########
        self.ifxdb_img = config['influxdb']['ifxdb_img']
        self.ifxdb_label = config['influxdb']['ifxdb_label']
        self.ifxdb_command = config['influxdb']['ifxdb_command']
        self.ifxdb_mem_limit = config['influxdb']['ifxdb_mem_limit']
        self.ifxdb_mem_res = config['influxdb']['ifxdb_mem_res']
        self.ifxdb_db = config['influxdb']['ifxdb_db']
        self.ifxdb_env = config['influxdb']['ifxdb_env']
        self.ifxdb_port = config['influxdb']['ifxdb_port']
        #######################################

        ########CAdvisor Parameters ########
        self.cadvisor_img = config['cadvisor']['cadvisor_img']
        self.cadvisor_label = config['cadvisor']['cadvisor_label']
        self.cadvisor_mem_limit = config['cadvisor']['cadvisor_mem_limit']
        self.cadvisor_mem_res = config['cadvisor']['cadvisor_mem_res']
        #cadvisor_mem_limit = "1g"
        #cadvisor_mem_res = "900m"
        self.cadvisor_command = config['cadvisor']['cadvisor_command']
        self.cadvisor_env = config['cadvisor']['cadvisor_env']
        self.cadvisor_vols = config['cadvisor']['cadvisor_vols']

        #cadvisor_ports = {"8080/tcp":"8080"}
        self.cadvisor_ports = config['cadvisor']['cadvisor_ports'] # 9080 to avoid clash with sdn controller
        #######################################

        ###############Grafana#################

        self.grafana_img= config['grafana']['grafana_img']
        self.grafana_label= config['grafana']['grafana_label']
        self.grafana_mem_limit= config['grafana']['grafana_mem_limit']
        self.grafana_mem_res = config['grafana']['grafana_mem_res']
        self.grafana_command = config['grafana']['grafana_command']
        self.grafana_env = config['grafana']['grafana_env']
        self.grafana_vols = config['grafana']['grafana_vols']
       #self.grafana_vols = {self.base_dir+"sckl-poc-scripts/dashboards/":{"bind":"/var/lib/grafana/dashboards","mode":"ro"}}
        self.grafana_ports = config['grafana']['grafana_ports']

        #######################################

        ########Agent Parameters ########
        # ag_label = "c"
        # ag_mem_limit = "350m"
        # ag_mem_res = "300m"
        # ag_cpus = 2
        # ag_command = ""
        # ag_data_in = base_dir+"sckl-poc-data/4-node"
        # #ag_data_in = "/home/mep53/workspace/ngcdi/sckl-poc-data/100-node"
        # #ag_logs_dir = "/home/mep53/workspace/scala/ngcdi/mperhez/sckl-poc-scripts/logs"
        # ag_logs_dir = "/home/mep53/workspace/ngcdi/sckl-poc-scripts/runs"
        # ag_data_dir = "/data/"
        # ag_port = "1600"
        # ag_ports = {ag_port+"/tcp":None,"9095":None,"5266":None}
        # ag_seed_addr = "seed1"
        # ag_seed_port = ag_port
        # ag_sdnc_server="ryu-sdn-1"
        # ag_sdnc_port="8080"
        # ag_monitoring_url="/stats/port/"
        # ag_key_services = "sc1, sc2, sc3"
        #######################################



        #logger_label = "sckl_run"
        self.run_base_label = config['run']['run_base_label']
        run_base_label = config['run']['run_base_label']
        self.q_runs=config['run']['q_runs']
        self.duration = config['run']['duration']

        self.q_sm = config['run']['agents_q'][0]
        self.q_fp = config['run']['agents_q'][1]

        # FOR ONOS Integration:
        if(config['run']['agents_q'][2] < 0):
            config['onos'] = {}
            config['onos']['devices'] = ONOSInterface.getONOSDevices()
            print('ONOS DEVICES===>',config['onos']['devices'])
            config['run']['agents_q'][2] = len(config['onos']['devices'])

        self.q_da = config['run']['agents_q'][2]
        self.q_ifxdb = config['run']['infr_q'][3]
        ########################################
        self.client = client
        self.client_low = client_low

    def run(self):



        inf_config = {
                    #0: mininet, 1:prometheus, 2:grafana, 3:influxdb, 4:cadvisor, 5:sdncontroller
                    #run_base_label:[1,1,0,q_ifxdb,1,1]
                    self.run_base_label:self.config['run']['infr_q']
                    }
        run_config = {}

        agentConfig = AgentConfig(self.config, self)

        for x in range(1, (self.q_runs+1), 1): # from, to, step
            run_config[self.run_base_label + "-" +str(x)] = self.config['run']['agents_q'] # sm, fp, da


        for x in range(1, (self.q_runs+1), 1): # from, to, step
            #0: mininet, 1:prometheus, 2:grafana, 3:influxdb, 4:cadvisor, 5:sdncontroller
            #inf_config[run_base_label + "-" + str(x)] = [1,1,0,q_ifxdb,1,1]
            inf_config[self.run_base_label + "-" + str(x)] = self.config['run']['infr_q']


        lmsg = "inf_config: "+str(inf_config)
        Logger.get_logger(self.run_base_label).info(lmsg)
        lmsg = "run_config: "+str(run_config)
        Logger.get_logger(self.run_base_label).info(lmsg)

        # Create Network
        #ntw_name = "ntwk_"+run_label
        #ntw = client.networks.create("ntwk_"+run_label, driver="bridge")
        ntw = self.client.networks.get(self.ntw_name)

        #ninf_ids = emu_network_inf(ntw,run_base_label,inf_config)
        #ninf_ids = [] #moved to be created for every run

        cinf_ids = self.create_common_inf(ntw,self.run_base_label,inf_config)

        self.multiple_runs(ntw,inf_config,run_config,self.duration,agentConfig)

        #shutdown(run_base_label,cinf_ids, ninf_ids,ntw)


    def multiple_runs(self,ntw,inf_config,run_config,duration, agentConfig):
        for k,v in run_config.items():
            lmsg = k +": Starting..."
            Logger.get_logger(self.run_base_label).info(lmsg)
            self.single_run(inf_config,SingleRun(ntw, int(v[0]), int(v[1]), int(v[2]), k, duration, agentConfig,self.config,self))
            time.sleep(10)

        lmsg = k +": End..."
        Logger.get_logger(self.run_base_label).info(lmsg)




    def single_run(self,inf_config,singleRun):

        #print(agents)
        #Prometheus config file
        #print("all:",inf_config)
        #print("prom:",inf_config.get(run_label)[1])

        if(inf_config.get(singleRun.run_label)[1]>0):
            self.create_prometheus_config(singleRun.run_label,singleRun.agents)

        ninf_ids =[]
        if (inf_config.get(singleRun.run_label)[0] > 0 and inf_config.get(singleRun.run_label)[5] > 0):
            ne = NetworkEmulator(self.client,self.client_low,singleRun.ntw,self.config)
            mnet_n = inf_config.get(singleRun.run_label)[0]
            sdnc_n = inf_config.get(singleRun.run_label)[5]
            ninf_ids = ne.emu_network_inf(singleRun.ntw,singleRun.run_label,mnet_n, sdnc_n)
        elif (inf_config.get(singleRun.run_label)[5] < 0):
            ne = NetworkEmulator(self.client,self.client_low,singleRun.ntw,self.config)
            ninf_ids = ne.test_controller_server(singleRun.run_label)

        # Create monitoring infrastructure
        inf_ids =  self.create_monitoring_inf(singleRun.ntw,singleRun.run_label,inf_config)
        #inf_ids = []
        #time.sleep(60)
        # Create agents
        ag_ids = singleRun.create_agents()
        #ag_ids = []
        lmsg = singleRun.run_label +": Waiting to run..."
        Logger.get_logger(self.run_base_label).info(lmsg)

        time.sleep(self.duration)



        #Destroy agents, infrastructure & network
        self.shutdown_run(singleRun.run_label,ag_ids,inf_ids,ninf_ids)



    def shutdown_run(self,run_label,ag_ids,inf_ids,ninf_ids):
        # Remove Agent containers
        lmsg = run_label+": ready to remove..."+str(ag_ids)
        Logger.get_logger(self.run_base_label).info(lmsg)

        p = pool_handler(ag_ids)
        p.close()


        lmsg = run_label+": "+str(len(ag_ids))," agents removed"
        Logger.get_logger(self.run_base_label).info(lmsg)

        # Remove Infrastructure containers
        # Except influxdb

        for i in range(0,len(inf_ids)):
            c = self.client.containers.get(inf_ids[i])
            c.stop(timeout=5)
            c.remove(v=False)

        self.client.volumes.prune()

        for i in range(0,len(ninf_ids)):
            c = self.client.containers.get(ninf_ids[i])
            c.stop(timeout=5)
            c.remove(v=False)

        lmsg = run_label+": inf removed..."
        Logger.get_logger(self.run_base_label).info(lmsg)

        #time.sleep(10)

        # Remove Network
        #ntw.remove()
        lmsg = run_label+":run shutdown finished..."
        Logger.get_logger(self.run_base_label).info(lmsg)

    def shutdown(self,run_base_label,cinf_ids,ninf_ids,ntw):
        # Remove  containers
        lmsg = run_base_label+": whole ready to remove..."+str(cinf_ids)
        Logger.get_logger(run_base_label).info(lmsg)

        for i in range(self.q_ifxdb,len(cinf_ids)):
            c = self.client.containers.get(cinf_ids[i])
            c.stop(timeout=5)
            c.remove(v=False)

        #client.volumes.prune()

        for i in range(0,len(ninf_ids)):
            c = self.client.containers.get(ninf_ids[i])
            c.stop(timeout=5)
            c.remove(v=False)

        lmsg = run_base_label+": whole inf removed..."
        Logger.get_logger(run_base_label).info(lmsg)

        #time.sleep(10)

        # Remove Network
        #ntw.remove()
        lmsg = run_base_label+":shutdown finished..."
        Logger.get_logger(run_base_label).info(lmsg)






    def create_common_inf(self,ntw,run_base_label,inf_config):
        cinf_ids = []
        cadvisor_n = inf_config.get(run_base_label)[4]
        ifxdb_n = inf_config.get(run_base_label)[3]

    # Influxdb

        for i in range(1,ifxdb_n+1):
            ifxdb_vols = {
                    self.ifxdb_label+str(i)+"_"+self.run_base_label: {"bind": "/var/lib/influxdb", 'mode': "rw"}
                    }
            ifxdb_ports = {self.ifxdb_port:str(i)+self.ifxdb_port}
            #print(ifxdb_vols)
            #print(ifxdb_env)

            ifxdb = self.client.containers.run(self.ifxdb_img,
                              self.ifxdb_command,
                              name = self.ifxdb_label+str(i),
                              auto_remove = False,
                              detach = True,
                              mem_limit = self.ifxdb_mem_limit,
                              mem_reservation = self.ifxdb_mem_res,
                              network = ntw.name,
                              volumes = ifxdb_vols,
                              ports = ifxdb_ports,
                              environment = self.ifxdb_env
                              )
            cinf_ids.append(ifxdb.id) #ifxdb is the head

        if(ifxdb_n > 0):time.sleep(5)

        # CAdvisor
            #print(cadvisor_vols)
            #print(cadvisor_env)

        for j in range(1,cadvisor_n+1):
            cadvisor = self.client.containers.run(self.cadvisor_img,
                                  self.cadvisor_command,
                                  name = self.cadvisor_label+str(i),
                                  auto_remove = False,
                                  privileged = True,
                                  detach = True,
                                  mem_limit = self.cadvisor_mem_limit,
                                  mem_reservation = self.cadvisor_mem_res,
                                  network = ntw.name,
                                  ports = self.cadvisor_ports,
                                  volumes = self.cadvisor_vols,
                                  environment = self.cadvisor_env
                                  )
            cinf_ids.append(cadvisor.id)
        time.sleep(10)


        return cinf_ids

    def create_monitoring_inf(self,ntw,run_label,inf_config):
        inf_ids = []
        prom_n = inf_config.get(run_label)[1]
        graf_n = inf_config.get(run_label)[2]

        #inf_ids.append(create_db_inf(ntw,run_label,inf_config))
    # Prometheus

        for i in range(1,prom_n+1):
            prom_vols = {
                    self.prom_config: {"bind": "/etc/prometheus/prometheus.yml", "mode": "ro"},
                    self.prom_label+str(i)+"_vol": {"bind": "/prometheus", 'mode': "rw"}
                    }
            #print(prom_vols)
            prom = self.client.containers.run(self.prom_img,
                              self.prom_command,
                              name = self.prom_label+str(i),
                              auto_remove = False,
                              detach = True,
                              mem_limit = self.prom_mem_limit,
                              mem_reservation = self.prom_mem_res,
                              network = ntw.name,
                              ports = self.prom_ports,
                              volumes = prom_vols
                              )
            inf_ids.append(prom.id)

            time.sleep(5)

            # Grafana
        for i in range(1,graf_n+1):
            #print(prom_vols)
            grafana = self.client.containers.run(self.grafana_img,
                              self.grafana_command,
                              name = self.grafana_label+str(i),
                              auto_remove = False,
                              detach = True,
                              mem_limit = self.grafana_mem_limit,
                              mem_reservation = self.grafana_mem_res,
                              network = ntw.name,
                              ports = self.grafana_ports,
                              volumes = self.grafana_vols,
                              environment = self.grafana_env
                              )
            inf_ids.append(grafana.id)

            time.sleep(5)

            #for line in cadvisor.logs(stream=True):
            #    print (line.strip())
        lmsg = run_label + ":" + "inf created..." + str(inf_ids)
        Logger.get_logger(self.run_base_label).info(lmsg)

        return inf_ids


    def create_prometheus_config(self,run_label,agents):
        file = open(self.prom_config,"w")

        config_str = ( "global:\n"
                     + "  scrape_interval: 5s\n" # change to higher if too slow
                     + "  evaluation_interval: 5s\n"
                     + "alerting:\n"
                     + "  alertmanagers:\n"
                     + "  - static_configs:\n"
                     + "    - targets:\n"
                     + "rule_files:\n"
                     + "remote_write:\n"
                     + "  - url:  \"http://" + self.ifxdb_label + "1:"+ self.ifxdb_port + "/api/v1/prom/write?db="+ self.ifxdb_db + "\"\n"
                     + "scrape_configs:\n"
                     + "  - job_name: '"+ run_label +"-ca1'\n"
                     + "    scrape_interval: 5s\n" #change to 20s if too slow
                     + "    static_configs:\n"
                     + "    - targets: ['cadvisor1:8080']\n"
                     + "  - job_name: '" + run_label + "'\n"
                     + "    scrape_interval: 5s\n"
                     + "    static_configs:\n"
                     )

        config_str += "    - targets: ["

        ag_type = 0
        ag_total_k = 0
        ag_t_done = 0

        for k,e in agents.items():
            ag_total_k += e.get("q")

        for k, e in agents.items():
            ag_type += 1
            ag_n = 0
            for i in range(1,e.get("q")+1):
                ag_t_done += 1
                ag_n = ag_n + 1

                config_str += "'"+e.get("label")+str(ag_n) + ":9095'"

                if(ag_t_done == ag_total_k):
                    config_str += "]\n"
                else:
                    config_str += ","

        Logger.get_logger(self.run_base_label).info(config_str)
        file.write(config_str)
        file.close()
    def create_log_file(self,ag_logs_dir,run_label,ag_name):
            log_run_dir = ag_logs_dir + "/" + run_label
            log_file_name = log_run_dir + "/" + ag_name + ".log"

            if not os.path.exists(log_run_dir ):
                         os.makedirs(log_run_dir)
                         os.chown(log_run_dir,self.userid,self.groupid)
            log_file = open(log_file_name,"w")
            log_file.close()
            return log_file_name

def pool_handler(c_ids):
            p = Pool(20)
            p.map(rm_container, c_ids)
            return p

def rm_container(ag_ids):
    lmsg = "Removing ->"+ag_ids
    Logger.get_logger(run_base_label).info(lmsg)

    c = client.containers.get(ag_ids)
    c.stop(timeout=5)
    time.sleep(5)
    c.remove(v=False)
    lmsg = "Removing ->"+ag_ids
    Logger.get_logger(run_base_label).info(lmsg)
