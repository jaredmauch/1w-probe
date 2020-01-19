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
import time
import uuid
import yaml
import spidev

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

    def read(self, ch):
        if 7 <= ch <= 0:
            raise Exception('MCP3208 channel must be 0-7: ' + str(ch))

        cmd = 128  # 1000 0000
        cmd += 64  # 1100 0000
        cmd += ((ch & 0x07) << 3)
        ret = self.conn.xfer2([cmd, 0x0, 0x0])

        # get the 12b out of the return
        val = (ret[0] & 0x01) << 11  # only B11 is here
        val |= ret[1] << 3           # B10:B3
        val |= ret[2] >> 5           # MSB has B2:B0 ... need to move down to LSB

        return val & 0x0FFF # ensure we are only sending 12b

if __name__ == '__main__':
    resistor_1 = 1620 # R1
    resistor_2 = 28000 # R2
    vref = 3.3 # vref voltage
    adc_bits = 12
    bits = (2**adc_bits) # 4096 - mcp3204 is 12-bit ADC

    divider = resistor_1 / (resistor_1 + resistor_2)

    hostname = uuid.getnode()

    with open('config.yaml', 'r') as f:
        config_content = yaml.load(f)

    # server hostname
    carbon_server = config_content['carbon_server']
    carbon_port = config_content['carbon_port']
    try:
        sleep_duration = config_content['sleep_duration']
    except KeyError:
        sleep_duration = 1

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


        if count == adc_bits:
            print("ch0=%04d, ch1=%04d, ch2=%04d, ch3=%04d" % (a0/adc_bits, a1/adc_bits, a2/adc_bits, a3/adc_bits))
            vbits0 = ((a0/adc_bits) / bits)
            vbits1 = ((a1/adc_bits) / bits)
            vbits2 = ((a2/adc_bits) / bits)
            vbits3 = ((a3/adc_bits) / bits)

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

            time.sleep(sleep_duration)
