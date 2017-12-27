#!/usr/bin/python
 
import socket
import sqlite3
from sqlite3 import Error


# path to database file
dbpath = 'tempsensor.db'

conn = sqlite3.connect(dbpath)
cur = conn.cursor()
cur.execute("SELECT probe, temp, time_t from temps");
row = cur.fetchone()
 

while row is not None:
  sensor = row[0];
  oid = sensor.replace('/', '.');
  oid = oid[1:];

  line = str(oid) + " " + str(row[1]) + " " + str(row[2]) + " ";
#  sock = socket.socket()
#  sock.connect( ("204.42.254.22", 2003) )
#  sock.send(line)
#  sock.close()
  print line
  row = cur.fetchone()

