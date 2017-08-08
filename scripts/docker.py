#!/usr/bin/python3
# originaly from 
import os
import json
import argparse
import sys
import time
import re
from datetime import datetime
import glob

_STAT_RE = re.compile("(\w+)\s(\w+)")
# check debug mode given in container startup
_DEBUG = os.getenv("DEBUG", False)

# discover containers
def discover():
	d = {}
	d["data"] = []
	with os.popen("docker ps -a --format \"{{.Names}} {{.ID}}\"") as pipe:
		for line in pipe:
			ps = {}
			ps["{#CONTAINERNAME}"] = line.strip().split()[0]
			ps["{#CONTAINERID}"] = line.strip().split()[1]
			d["data"].append(ps)
	print (json.dumps(d))

def count_running():
	with os.popen("docker ps -q | wc -l") as pipe:
		print (pipe.readline().strip())

# status: 0 = no container found, 1 = running, 2 = closed, 3 = abnormal
def status(args):
	with os.popen("docker inspect -f '{{.State.Status}}' " + args.container + " 2>&1") as pipe:
		status = pipe.read().strip()

	if "Error: No such object:" in status:
		print ("0")
	elif status == 'running':
		print ("10")
	elif status == 'created':
		print ("1")
	elif status == 'restarting':
		print ("2")
	elif status == 'removing':
		print ("3")
	elif status == 'paused':
		print ("4")
	elif status == 'exited':
		print ("5")
	elif status == 'dead':
		print ("6")
	else: print ("0")
	
# get the uptime in seconds, if the container is running
def uptime(args):
	with os.popen("docker inspect -f '{{json .State}}' " + args.container + " 2>&1") as pipe:
		status = pipe.read().strip()
	if "No such image or container" in status:
		print ("0")
	else:
		statusjs = json.loads(status)
		if statusjs["Running"]:
			uptime = statusjs["StartedAt"]
			start = time.strptime(uptime[:19], "%Y-%m-%dT%H:%M:%S")
			print (int(time.time() - time.mktime(start)))
		else:
			print ("0")

def disk(args):
	with os.popen("docker inspect -s -f {{.SizeRootFs}} " + args.container + " 2>&1") as pipe:
		stat = pipe.read().strip()
	pipe.close()
	# test that the docker command succeeded and pipe contained data
	if not 'stat' in locals():
		stat = ""
	print (stat.split()[0])

def cpu(args):
	#container_dir = glob.glob("/host/cgroup/cpuacct/docker/" + args.container)
	container_dir = "/sys/fs/cgroup/cpuacct"
	# cpu usage in nanoseconds
	cpuacct_usage_last = single_stat_check(args, "cpuacct.usage")
	cpuacct_usage_new = single_stat_update(args, container_dir, "cpuacct.usage")
	last_change = update_stat_time(args, "cpuacct.usage.utime")
	# time used in division should be in nanoseconds scale, but take into account
	# also that we want percentage of cpu which is x 100, so only multiply by 10 million
	time_diff = (time.time() - float(last_change)) * 10000000

	cpu = (int(cpuacct_usage_new) - int(cpuacct_usage_last)) / time_diff
	print ("{:.2f}".format(cpu))

def net_received(args):
	container_dir = "/sys/devices/virtual/net/eth0/statistics"
	eth_last = single_stat_check(args, "/rx_bytes")
	eth_new = single_stat_update(args, container_dir, "/rx_bytes")
	last_change = update_stat_time(args, "rx_bytes.utime")
	# we are dealing with seconds here, so no need to multiply
	time_diff = (time.time() - float(last_change))
	eth_bytes_per_second = (int(eth_new) - int(eth_last))/ time_diff
	print (int(eth_bytes_per_second))

def net_sent(args):
	container_dir = "/sys/devices/virtual/net/eth0/statistics"
	eth_last = single_stat_check(args, "/tx_bytes")
	eth_new = single_stat_update(args, container_dir, "/tx_bytes")
	last_change = update_stat_time(args, "tx_bytes.utime")
	# we are dealing with seconds here, so no need to multiply
	time_diff = (time.time() - float(last_change))
	eth_bytes_per_second = (int(eth_new) - int(eth_last))/ time_diff
	print (int(eth_bytes_per_second))

# helper, fetch and update the time when stat has been updated
# used in cpu calculation
def update_stat_time(args, filename):
	try:
		with open("/tmp/" + args.container + "/" + filename, "r+") as f:
			stat_time = f.readline()
			f.seek(0)
			curtime = str(time.time())
			f.write(curtime)
			f.truncate()

	except Exception:
		if not os.path.isfile("/tmp/" + args.container + "/" + filename):
			# bootstrap with one second (epoch), which makes sure we dont divide
			# by zero and causes the stat calcucation to start with close to zero value
			stat_time = 1
			f = open("/tmp/" + args.container + "/" + filename,"w")
			f.write(str(stat_time))
			f.close()
	return stat_time

# helper function to gather single stats
def single_stat_check(args, filename):

	try:
		with open("/tmp/" + args.container + "/" + filename, "r") as f:
			stat = f.read().strip()
	except Exception:
		if not os.path.isdir("/tmp/" + args.container):
			os.mkdir("/tmp/" + args.container)

		# first time running for this container, bootstrap with empty zero
		stat = "0"
		f = open("/tmp/" + args.container + "/" + filename,"w")
		f.write(str(stat) + '\n')
		f.close()

	return stat

# helper function to update single stats
def single_stat_update(args, container_dir, filename):

	pipe = os.popen("docker exec " + args.container + " cat " + container_dir + "/" + filename  + " 2>&1")
	for line in pipe:
		stat = line
	pipe.close()
	# test that the docker command succeeded and pipe contained data
	if not 'stat' in locals():
		stat = ""
	try:
		f = open("/tmp/" + args.container + "/" + filename,"w")
		f.write(stat)
		f.close()
	except Exception:
		if not os.path.isdir("/tmp/" + args.container):
			os.mkdir("/tmp/" + args.container)
		with open("/tmp/" + args.container + "/" + filename, "w") as f:
			f.write(stat)

	return stat

# helper function to gather stat type data (multiple rows of key value pairs)
def multi_stat_check(args, filename):
	dict = {}
	try:
		with open("/tmp/" + args.container + "/" + filename, "r") as f:
			for line in f:
				m = _STAT_RE.match(line)
				if m:
					dict[m.group(1)] = m.group(2)
	except Exception:
		if not os.path.isdir("/tmp/" + args.container):
			os.mkdir("/tmp/" + args.container)
		debug(args.container + ": could not get last stats from " + filename)
		debug(str(e))

		# first time running for this container create empty file
		open("/tmp/" + args.container + "/" + filename,"w").close()
	return dict

def multi_stat_update(args, container_dir, filename):
	dict = {}
	try:
		pipe = os.popen("docker exec " + args.container + " cat " + container_dir + "/" + filename  + " 2>&1")
		for line in pipe:
			m = _STAT_RE.match(line)
			if m:
				dict[m.group(1)] = m.group(2)
		pipe.close()
		f = open("/tmp/" + args.container + "/" + filename,"w")

		for key in dict.keys():
			f.write(key + " " + dict[key] + "\n")
		f.close()
	except Exception:
		debug(args.container + ": could not update " + filename)
		debug(str(sys.exc_info()))
	return dict


def memory(args):
	container_dir = "/sys/fs/cgroup/memory"
	memory_stat_last = {}
	memory_stat_new = {}
	memory_usage_last = single_stat_update(args, container_dir, "memory.usage_in_bytes")
	print (memory_usage_last.strip())

def debug(output):
	if _DEBUG:
		if not "debuglog" in globals():
			global debuglog
			debuglog = open("debuglog","a")
		timestamp = time.strftime("%Y-%m-%d %H:%M:%S : ", time.gmtime())
		debuglog.write(timestamp + str(output)+"\n")

if __name__ == "__main__":


	if len(sys.argv) > 2:

		parser = argparse.ArgumentParser(prog="discover.py", description="discover and get stats from docker containers")
		parser.add_argument("container", help="container id")
		parser.add_argument("stat", help="container stat", choices=["status", "uptime", "cpu","mem", "disk", "netin", "netout"])
		args = parser.parse_args()
		# validate the parameter for container
		m = re.match("(^[a-zA-Z0-9-_]+$)", args.container)
		if not m:
			print ("Invalid parameter for container id detected")
			debug("Invalid parameter for container id detected" + str(args.container))
			sys.exit(2)

		# call the correct function to get the stats
		if args.stat == "status":
			debug("calling status for " + args.container)
			status(args)
		elif args.stat == "uptime":
			debug("calling uptime for " + args.container)
			uptime(args)
		elif args.stat == "cpu":
			debug("calling cpu for " + args.container)
			cpu(args)
		elif args.stat == "mem":
			debug("calling memory for " + args.container)
			memory(args)
		elif args.stat == "disk":
			debug("calling disk for " + args.container)
			disk(args)
		elif args.stat == "netin":
			debug("calling net_received for " + args.container)
			net_received(args)
		elif args.stat == "netout":
			debug("calling net_sent for " + args.container)
			net_sent(args)
	elif len(sys.argv) == 2:
		if sys.argv[1] == "count":
			debug("calling count")
			count_running()
	else:
		debug("discovery called.")
		discover()

	if "debuglog" in globals():
		debuglog.close()
