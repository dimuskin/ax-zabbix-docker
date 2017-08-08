# AX Zabbix Docker Monitoring

* Support Windows or Linux (tested on Ubuntu and Debian) docker hosts
* Discover running containers
* Collect containers memory and CPU usage
* Same template for both platforms (PASSIVE or ACTIVE mode)
* Easy install

# Instalation

## Linux 
* Install latest Zabbix agent (https://www.zabbix.com/documentation/3.2/manual/installation/install_from_packages/repository_installation)
* mv zabbix-agent/linux_zabbix_agent.conf  /etc/zabbix/zabbix_agentd.d/
* mv scripts/docker.py /etc/zabbix
* chmod 755 /etc/zabbix/docker.py
* Add zabbix to docker group: # sudo usermod -a -G docker zabbix
* Restart agent
* Go to Zabbix and add "Template AX App Docker ACTIVE" (or PASSIVE) to this server.

## Windows
* Install latest Zabbix agent (http://www.suiviperf.com/zabbix/)
* Add zabbix-agent/windows_zabbix_agent.conf to C:\Program Files\Zabbix Agent\zabbix_agentd.conf (DO NOT REPLACE !!!)
* Copy scripts\docker.ps1 to c:\zabbix
* Restart agent
* Go to Zabbix and add "Template AX App Docker ACTIVE" (or PASSIVE) to this server.
