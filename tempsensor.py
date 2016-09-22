#!/usr/bin/env python

import time
import datetime
import os
import sqlite3

#third party libs
# apt-get install python-daemon
from daemon import runner
# http://www.gavinj.net/2012/06/building-python-daemon-process.html

# path to database file
dbpath = 'tempsensor.db'

conn = sqlite3.connect(dbpath)

# wait up to 30 seconds for database connection
conn.execute("PRAGMA busy_timeout = 30000")   # 30 s

# create the dataset for storing the temps
sql = 'create table if not exists temps (probe text not null, time_t integer, temp real)'
c = conn.cursor()
c.execute(sql)
try:
	conn.commit()
except sqlite3.Error:
	print "Unable to create table";

# create a list of the sensors
sql = 'create table if not exists sensors (probe text not null, description text not null)'

c = conn.cursor()
c.execute(sql)
conn.commit()

# while forever, talk to the sensors
while 1:

# zero out the list of sensors
	sensors = []

# iterate through the 1w bus directories
# collecting the sensors

	for dirname, dirnames, filenames in os.walk('/sys/bus/w1/devices/'):
	    # print path to all subdirectories first.
	    for subdirname in dirnames:
		temppath = os.path.join(dirname, subdirname)
		if "28-" in temppath:
			sensors.append(temppath) # push
#			print temppath

#print "should probe these sensors"

	for sensor in sensors:
#		print sensor
		# build the full sensor path
		sensor_path = sensor + "/w1_slave"
	
		# open the sensor
#		tempfile = open("/sys/bus/w1/devices/28-0000061531b5/w1_slave")
		tempfile = open(sensor_path)
		# read data into thetext
		thetext = tempfile.read()
## example data
# b2 01 4b 46 7f ff 0e 10 8c : crc=8c YES
# b2 01 4b 46 7f ff 0e 10 8c t=27125
## end example data

		# close the sensor
		tempfile.close()
		# store the time
		tstamp = datetime.datetime.utcnow()
		# split the first line (0) by newline, split it by = and space
		crcok = thetext.split("\n")[0].split("=")[1].split(" ")[1]
		# on the second line, split by spaces
		tempdata = thetext.split("\n")[1].split(" ")[9]
		# extract the temperature
		temperaturec = float(tempdata[2:])
		# convert to actual float
		temperaturec = temperaturec / 1000
		# convert to F
		temperaturef = (temperaturec * 9)/5 +32
                oid = sensor.replace('/', '.');
                oid = oid[1:];

		print "%s %d %6.2f C %6.2f F Valid/CrcOK=%s"% (oid, time.mktime(tstamp.timetuple()), temperaturec, temperaturef, crcok)
		c.execute("insert into temps values (?,?,?)", (sensor, time.mktime(tstamp.timetuple()), temperaturec))
		try:
			conn.commit()
		except sqlite3.Error:
			print "Error trying to save temp";

	# end sensor for
	time.sleep(5)
#/sys/bus/w1/devices/28-0000061531b5/w1_slave
