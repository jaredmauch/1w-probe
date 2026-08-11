#!/usr/bin/python3

import socket
import sqlite3
from sqlite3 import Error
import influxdb
import yaml

conn = sqlite3.connect('file:tempsensor.db?mode=ro', uri=True)
cur = conn.cursor()
cur.execute("SELECT probe, temp, time_t from temps");
row = cur.fetchone()

try:
    with open('config.yaml', 'r') as f:
        config_content = yaml.safe_load(f) or {}
except (OSError, yaml.YAMLError):
    config_content = {}

# path to database file
dbpath = config_content.get('sqlite_file', 'tempsensor.db')

# server hostname
influx_host = config_content.get('influx_host', 'localhost')
influx_port = int(config_content.get('influx_port', 8086))
influx_username = config_content.get('influx_username', 'user')
influx_db = config_content.get('influx_db', 'databasename')
influx_db_pw = config_content.get('influx_db_pw', 'databasepw')

influx_client = influxdb.InfluxDBClient(host=influx_host, port=influx_port, username=influx_username, database=influx_db, password=influx_db_pw, ssl=False, verify_ssl=False)

while row is not None:
    sensor = row[0];
    oid = sensor.replace('/', '.');
    oid = oid[1:];

    temp_c = float(row[1])

    # convert to F
    temp_f = (temp_c * 9)/5 +32

    line = "%s %2.2f %s" % (str(oid), temp_f, str(row[2]))
    server_data = "%s value=%1.2f %d\n" % (oid, temp_f, int(row[2] * 1000000000))

    try:
        influx_client.write_points(server_data, protocol='line')
    except influxdb.exceptions.InfluxDBClientError as e:
         print(e, server_data)

    print(server_data)
    row = cur.fetchone()
