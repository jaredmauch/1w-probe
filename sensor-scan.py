#!/usr/bin/env python

import os

sensors = []
for dirname, dirnames, filenames in os.walk('/sys/bus/w1/devices/'):
    # print path to all subdirectories first.
    for subdirname in dirnames:
	temppath = os.path.join(dirname, subdirname)
	if "28-" in temppath:
		sensors.append(temppath) # push
#		print temppath

    # Advanced usage:
    # editing the 'dirnames' list will stop os.walk() from recursing into there.
#    if '28-' in dirnames:
#        # don't go into any .git directories.
#        print "found a sensor"

print "should probe these sensors"

for sensor in sensors:
	print sensor
