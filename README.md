# 1w-probe
1wire probe code

This code collects data from the DS18B20 temperature sensors connected to
a raspberry pi and sends it to a carbon/graphite server for storage and
rendering.

It stores the data in a local sqlite3 backlog if it can't reach the server.
You can manually re-submit the data using the included temp2carbon.py

/boot/config.txt needs this:

dtoverlay=w1-gpio-pullup,gpiopin=4,extpullup=5,pullup=on

the mcp3204.py code reads from MCP3204 on the SPI.  The resistor values and VREF are all coded to make it easy to sense and send data to your server as well.

I uploaded the eagle schematic and gerber zip for the latest board that works so you can have them made at a pace like pcb.ng or jlcpcb.
