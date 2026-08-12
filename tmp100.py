#!/usr/bin/python3
#
#       TI TMP100 reader for Raspberry Pi
#
#       Board wiring (sensor_board_v1.3): IC1 on I2C0 (SDA0/SCL0),
#       ADD0/ADD1 pulled high → 7-bit address 0x4e.
#
#       how to setup i2c:
#               $ sudo raspi-config -> interfacing -> i2c
#               $ sudo apt-get install python3-smbus
#               # or: sudo apt-get install python3-smbus2
#
import time
import yaml

try:
    from smbus2 import SMBus
except ImportError:
    from smbus import SMBus

# TMP100 defaults for this board
I2C_BUS = 0
I2C_ADDR = 0x4e

REG_TEMP = 0x00
REG_CONFIG = 0x01

# Configuration: R1=R0=1 → 12-bit / 0.0625°C (needs ~320ms conversion)
CONFIG_12BIT = 0x60


class TMP100:
    def __init__(self, bus=I2C_BUS, address=I2C_ADDR):
        self.bus_num = bus
        self.address = address
        self.bus = None

    def open(self):
        self.bus = SMBus(self.bus_num)

    def close(self):
        if self.bus is not None:
            self.bus.close()
            self.bus = None

    def __del__(self):
        self.close()

    def present(self):
        """Return True if a device ACKs at this address."""
        try:
            self.bus.write_quick(self.address)
            return True
        except OSError:
            # write_quick is not on every smbus binding; fall back to a read
            try:
                self.bus.read_byte_data(self.address, REG_TEMP)
                return True
            except OSError:
                return False

    def set_resolution_12bit(self):
        self.bus.write_byte_data(self.address, REG_CONFIG, CONFIG_12BIT)
        # 12-bit conversion time is typically 320ms
        time.sleep(0.35)

    def read_config(self):
        return self.bus.read_byte_data(self.address, REG_CONFIG)

    def read_raw(self):
        """Return (msb, lsb) from the temperature register."""
        data = self.bus.read_i2c_block_data(self.address, REG_TEMP, 2)
        return data[0], data[1]

    @staticmethod
    def decipher(msb, lsb):
        """
        Decode TMP100 temperature register bytes.

        Datasheet stores a left-justified signed value in two bytes.
        At 12-bit resolution the top 12 bits are the reading (0.0625°C/LSB);
        dividing the signed 16-bit word by 256 yields °C.
        """
        raw_u16 = (msb << 8) | lsb
        if raw_u16 & 0x8000:
            raw_s16 = raw_u16 - 0x10000
        else:
            raw_s16 = raw_u16

        temp_c = raw_s16 / 256.0
        temp_f = (temp_c * 9.0) / 5.0 + 32.0
        # 12-bit code as shown in the datasheet temperature table
        code_12 = raw_s16 >> 4

        return {
            'msb': msb,
            'lsb': lsb,
            'raw_u16': raw_u16,
            'raw_s16': raw_s16,
            'code_12': code_12,
            'temp_c': temp_c,
            'temp_f': temp_f,
        }

    @staticmethod
    def decipher_config(cfg):
        resolutions = {
            0b00: '9-bit (0.5°C)',
            0b01: '10-bit (0.25°C)',
            0b10: '11-bit (0.125°C)',
            0b11: '12-bit (0.0625°C)',
        }
        r1r0 = (cfg >> 5) & 0x03
        return {
            'raw': cfg,
            'shutdown': bool(cfg & 0x01),
            'thermostat_mode': 'interrupt' if (cfg & 0x02) else 'comparator',
            'polarity': 'active-high' if (cfg & 0x04) else 'active-low',
            'fault_queue': 1 << ((cfg >> 3) & 0x03),
            'resolution': resolutions[r1r0],
            'one_shot': bool(cfg & 0x80),
        }


def load_sleep_duration(default=6.0):
    try:
        with open('config.yaml', 'r') as f:
            config_content = yaml.safe_load(f) or {}
    except (OSError, yaml.YAMLError):
        config_content = {}
    try:
        return float(config_content.get('sleep_duration', default))
    except (TypeError, ValueError):
        return default


if __name__ == '__main__':
    sleep_duration = load_sleep_duration()
    sensor = TMP100(I2C_BUS, I2C_ADDR)

    try:
        sensor.open()
    except OSError as e:
        print("Unable to open I2C bus %d: %s" % (I2C_BUS, e))
        raise SystemExit(1)

    if not sensor.present():
        print("No device at i2c-%d address 0x%02x (TMP100)" % (I2C_BUS, I2C_ADDR))
        sensor.close()
        raise SystemExit(1)

    print("Found device at i2c-%d address 0x%02x" % (I2C_BUS, I2C_ADDR))

    try:
        sensor.set_resolution_12bit()
        cfg = sensor.decipher_config(sensor.read_config())
        print("Config 0x%02x  resolution=%s  shutdown=%s  mode=%s" % (
            cfg['raw'], cfg['resolution'], cfg['shutdown'], cfg['thermostat_mode']))
    except OSError as e:
        print("Failed to configure TMP100: %s" % e)
        sensor.close()
        raise SystemExit(1)

    try:
        while True:
            try:
                msb, lsb = sensor.read_raw()
                reading = sensor.decipher(msb, lsb)
                print(
                    "TMP100 raw=0x%04x code12=0x%03x  %6.4f C  %6.2f F" % (
                        reading['raw_u16'],
                        reading['code_12'] & 0xFFF,
                        reading['temp_c'],
                        reading['temp_f'],
                    )
                )
            except OSError as e:
                print("Read failed: %s" % e)

            time.sleep(sleep_duration)
    except KeyboardInterrupt:
        pass
    finally:
        sensor.close()
