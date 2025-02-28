#!/usr/bin/env python3

import multiprocessing as mp
import time
import datetime
import os
import sqlite3
import yaml
import influxdb

# send data to remote server
# store backlog data in the sqlite3 storage

with open('config.yaml', 'r') as f:
    config_content = yaml.load(f, Loader=yaml.BaseLoader)

# path to database file
dbpath = config_content['sqlite_file']

# server hostname
#carbon_server = config_content['carbon_server']
#carbon_port = int(config_content['carbon_port'])
influx_host = config_content['influx_host']
influx_port = int(config_content['influx_port'])
influx_username = config_content['influx_username']
influx_db = config_content['influx_db']
influx_db_pw = config_content['influx_db_pw']
influx_client = influxdb.InfluxDBClient(host=influx_host, port=influx_port, username=influx_username, database=influx_db, password=influx_db_pw, ssl=False, verify_ssl=False)

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
    print("Unable to create table")

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
#                        print(temppath)

#print("should probe these sensors")

    for sensor in sensors:
#        print(sensor)
        # build the full sensor path
        sensor_path = sensor + "/w1_slave"
    
        # open the sensor
        try:
            tempfile = open(sensor_path)
        except Exception as e:
            print(sensor_path, e)
            continue
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
        oid = sensor.replace('/', '.')
        oid = oid[1:]

        blurb='Unknown'
        if crcok == "YES":
            try:
#                  print("attempting to connect to %s:%d" % (carbon_server, carbon_port))
#                  sock = socket.socket()
#                  sock.connect( (carbon_server, carbon_port) )
#                  sock.send("%s %6.2f %d \n" % (oid, temperaturec, time.time()))
#                  print("forming server_data")
#                  server_data = "%s %6.2f %d \n" % (oid, temperaturef, time.time())
                  server_data = "%s value=%1.2f %d\n" % (oid, temperaturef, time.time() * 1000000000)
                  influx_client.write_points(server_data, protocol='line')

#                  print("data sent ok")

                  blurb="Network"
            except Exception as e:
                  print(e)
                  c.execute("insert into temps values (?,?,?)", (sensor, time.mktime(tstamp.timetuple()), temperaturec))
                  blurb="Sqlite"
            try:
                  conn.commit()
            except sqlite3.Error as e:
                  print("Error trying to save temp", e)

        print("%s %d %6.2f C %6.2f F Valid/CrcOK=%s %s"% (oid, time.mktime(tstamp.timetuple()), temperaturec, temperaturef, crcok, blurb))

        # end sensor for
        time.sleep(int(config_content['sleep_duration']))
#/sys/bus/w1/devices/28-0000061531b5/w1_slave
