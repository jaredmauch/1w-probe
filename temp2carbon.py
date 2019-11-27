#!/usr/bin/python3
 
import socket
import sqlite3
from sqlite3 import Error

conn = sqlite3.connect('file:tempsensor.db?mode=ro', uri=True)
cur = conn.cursor()
cur.execute("SELECT probe, temp, time_t from temps");
row = cur.fetchone()
 

#sock = socket.socket()
#sock.connect( ("204.42.254.22", 2003) )

while row is not None:
  sensor = row[0];
  oid = sensor.replace('/', '.');
  oid = oid[1:];

  temp_c = float(row[1])

  # convert to F
  temp_f = (temp_c * 9)/5 +32

  line = "%s %2.2f %s" % (str(oid), temp_f, str(row[2]))
#  sock.send(line.encode())
  print(line)
  row = cur.fetchone()
#sock.close()


