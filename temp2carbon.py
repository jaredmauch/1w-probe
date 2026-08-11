#!/usr/bin/python3

import sqlite3
import influxdb
import yaml

try:
    with open('config.yaml', 'r') as f:
        config_content = yaml.safe_load(f) or {}
except (OSError, yaml.YAMLError):
    config_content = {}

# path to database file
dbpath = config_content.get('sqlite_file', 'tempsensor.db')

# server hostname
influx_host = config_content.get('influx_host', 'localhost')
try:
    influx_port = int(config_content.get('influx_port', 8086))
except (TypeError, ValueError):
    influx_port = 8086
influx_username = config_content.get('influx_username', 'user')
influx_db = config_content.get('influx_db', 'databasename')
influx_db_pw = config_content.get('influx_db_pw', 'databasepw')

influx_client = influxdb.InfluxDBClient(host=influx_host, port=influx_port, username=influx_username, database=influx_db, password=influx_db_pw, ssl=False, verify_ssl=False)

conn = sqlite3.connect(dbpath)
conn.execute("PRAGMA busy_timeout = 30000")
cur = conn.cursor()
cur.execute("SELECT rowid, probe, temp, time_t from temps")
row = cur.fetchone()

while row is not None:
    rowid, sensor, temp_c, time_t = row
    oid = sensor.replace('/', '.')
    oid = oid[1:]

    temp_c = float(temp_c)

    # convert to F
    temp_f = (temp_c * 9)/5 +32

    server_data = "%s value=%1.2f %d\n" % (oid, temp_f, int(time_t * 1000000000))

    try:
        influx_client.write_points(server_data, protocol='line')
        cur.execute("DELETE FROM temps WHERE rowid=?", (rowid,))
        conn.commit()
    except Exception as e:
         print(e, server_data)

    print(server_data)
    row = cur.fetchone()

conn.close()
