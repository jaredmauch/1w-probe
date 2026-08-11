#!/usr/bin/env python3

import time
import os
import sqlite3
import yaml
import influxdb

# send data to remote server
# store backlog data in the sqlite3 storage

try:
    with open('config.yaml', 'r') as f:
        config_content = yaml.safe_load(f) or {}
except (OSError, yaml.YAMLError):
    config_content = {}

# path to database file
dbpath = config_content.get('sqlite_file', 'tempsensor.db')

# server hostname
#carbon_server = config_content.get('carbon_server', 'localhost')
#carbon_port = int(config_content.get('carbon_port', 2003))
influx_host = config_content.get('influx_host', 'localhost')
try:
    influx_port = int(config_content.get('influx_port', 8086))
except (TypeError, ValueError):
    influx_port = 8086
influx_username = config_content.get('influx_username', 'user')
influx_db = config_content.get('influx_db', 'databasename')
influx_db_pw = config_content.get('influx_db_pw', 'databasepw')
try:
    sleep_duration = int(config_content.get('sleep_duration', 6))
except (TypeError, ValueError):
    sleep_duration = 6
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

def parse_w1_slave(thetext):
    """Parse DS18B20 w1_slave text. Returns (crcok, temperature_c) or None."""
    lines = thetext.strip().splitlines()
    if len(lines) < 2:
        return None

    crc_line = lines[0]
    if crc_line.endswith("YES"):
        crcok = "YES"
    elif crc_line.endswith("NO"):
        crcok = "NO"
    else:
        return None

    temp_line = lines[1]
    marker = "t="
    idx = temp_line.rfind(marker)
    if idx < 0:
        return None
    try:
        temperaturec = float(temp_line[idx + len(marker):]) / 1000.0
    except ValueError:
        return None

    return crcok, temperaturec

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
            with open(sensor_path) as tempfile:
                thetext = tempfile.read()
        except OSError as e:
            print(sensor_path, e)
            continue
## example data
# b2 01 4b 46 7f ff 0e 10 8c : crc=8c YES
# b2 01 4b 46 7f ff 0e 10 8c t=27125
## end example data

        parsed = parse_w1_slave(thetext)
        if parsed is None:
            print(sensor_path, "unparseable sensor data")
            continue
        crcok, temperaturec = parsed

        # store the time (UTC epoch seconds)
        epoch = time.time()
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
                  server_data = "%s value=%1.2f %d\n" % (oid, temperaturef, int(epoch * 1000000000))
                  influx_client.write_points(server_data, protocol='line')

#                  print("data sent ok")

                  blurb="Network"
            except Exception as e:
                  print(e)
                  c.execute("insert into temps values (?,?,?)", (sensor, int(epoch), temperaturec))
                  blurb="Sqlite"
            try:
                  conn.commit()
            except sqlite3.Error as e:
                  print("Error trying to save temp", e)

        print("%s %d %6.2f C %6.2f F Valid/CrcOK=%s %s"% (oid, int(epoch), temperaturec, temperaturef, crcok, blurb))

    # end sensor for — sleep once per full scan
    time.sleep(sleep_duration)
#/sys/bus/w1/devices/28-0000061531b5/w1_slave
