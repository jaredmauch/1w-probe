#!/usr/bin/python3
#
#       MCP3204 streaming program for Raspberry Pi
#
#       how to setup /dev/spidev?.?
#               $ sudo raspi-config -> interfacing -> spi
#
#       how to setup spidev
#               $ sudo apt-get install python3-spidev
#
import socket
import spidev
import time
import uuid
import yaml

class MCP3208:
    def __init__(self, spi_channel=0):
        self.spi_channel = spi_channel
        self.conn = spidev.SpiDev(0, spi_channel)
#        self.conn.max_speed_hz = 1000000 # 1MHz
        self.conn.max_speed_hz = 50000 # 0.05MHz


    def __del__(self):
        self.close

    def close(self):
        if self.conn is not None:
            self.conn.close
            self.conn = None

    def bitstring(self, n):
        s = bin(n)[2:]
        return '0'*(8-len(s)) + s

    def read(self, adc_channel=0):
        # build command
        cmd = 128 # start bit
        cmd += 64 # single end / diff
        if adc_channel % 2 == 1:
            cmd += 8
        if (adc_channel/2) % 2 == 1:
            cmd += 16
        if (adc_channel/4) % 2 == 1:
            cmd += 32

        # send & receive data
        reply_bytes = self.conn.xfer2([cmd, 0, 0, 0])

        #
        reply_bitstring = ''.join(self.bitstring(n) for n in reply_bytes)
        # print reply_bitstring

        # see also... http://akizukidenshi.com/download/MCP3204.pdf (page.20)
        reply = reply_bitstring[5:19]
        return int(reply, 2)

if __name__ == '__main__':
    resistor_1 = 1620 # R1
    resistor_2 = 28000 # R2
    vref = 3.3 # vref voltage
    bits = (2**12) # 4096 - mcp3204 is 12-bit ADC

    divider = resistor_1 / (resistor_1 + resistor_2)

    hostname = uuid.getnode()

    with open('config.yaml', 'r') as f:
        config_content = yaml.load(f)

    # server hostname
    carbon_server = config_content['carbon_server']
    carbon_port = config_content['carbon_port']

    vmult = vref/bits

    spi = MCP3208(0)

    count = 0
    a0 = 0
    a1 = 0
    a2 = 0
    a3 = 0

    while True:
        count += 1
        a0 += spi.read(0)
        a1 += spi.read(1)
        a2 += spi.read(2)
        a3 += spi.read(3)

        if count == 10:
#        print("ch0=%04d, ch1=%04d, ch2=%04d, ch3=%04d" % (a0/10, a1/10, a2/10, a3/10))
            vbits0 = ((a0/10) / bits)
            vbits1 = ((a1/10) / bits)
            vbits2 = ((a2/10) / bits)
            vbits3 = ((a3/10) / bits)

            vout0 = (vbits0 * vref) / divider
            vout1 = (vbits1 * vref) / divider
            vout2 = (vbits2 * vref) / divider
            vout3 = (vbits3 * vref) / divider

            print("%x VIN0=%04.2f, VIN1=%04.2f, VIN2=%04.2f, VIN3=%04.2f" % (hostname, vout0, vout1, vout2, vout3))

            try:
                sock = socket.socket()
                sock.connect((carbon_server, carbon_port))
                base_oid = "sys.bus.spi.%x." % hostname

                oid0 = base_oid + 'vin0'
                oid1 = base_oid + 'vin1'
                oid2 = base_oid + 'vin2'
                oid3 = base_oid + 'vin3'

                server_data0 = "%s %6.2f %d \n" % (oid0, vout0, time.time())
                server_data1 = "%s %6.2f %d \n" % (oid1, vout1, time.time())
                server_data2 = "%s %6.2f %d \n" % (oid2, vout2, time.time())
                server_data3 = "%s %6.2f %d \n" % (oid3, vout3, time.time())

    #            print(server_data0)
    #            print(server_data1)
    #            print(server_data2)
    #            print(server_data3)

                sock.send(server_data0.encode())
                sock.send(server_data1.encode())
                sock.send(server_data2.encode())
                sock.send(server_data3.encode())

                sock.close()
            except Exception as e:
                print(e)

            count = 0
            a0 = 0
            a1 = 0
            a2 = 0
            a3 = 0
            time.sleep(10)

