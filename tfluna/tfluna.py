from typing import Dict
import serial
import time


class TFLuna:
    _baudrates = [9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600]

    def __init__(self, portname, baudrate=None, sample_rate=None):
        self.portname = portname
        self.port = self.try_serial_port(baudrate)
        self.sample_rate = sample_rate or 100
        self.set_sample_rate(self.sample_rate)

    def try_serial_port(self, baudrate):
        default_baudrate = 115200
        baudrate = default_baudrate
        port = serial.Serial(self.portname, baudrate, timeout=.1)
        data = self.get_data(port)
        if not data:
            i = 0
            baudrates = self._baudrates.copy()
            baudrates.remove(default_baudrate)
            while not data:
                port.close()
                baudrate = baudrates[i]
                port = serial.Serial(self.portname, baudrate, timeout=.1)
                data = self.get_data(port)
                i += 1
        if not data:
            raise ValueError("Could not set TF Luna port")
        return port

    def set_sample_rate(self, sample_rate):
        samp_rate_packet = [0x5a, 0x06, 0x03, sample_rate, 00, 00]  # sample rate byte array
        self.port.write(samp_rate_packet)  # send sample rate instruction
        time.sleep(0.1)                   # wait for change to take effect

    def get_version(self):
        info_packet = [0x5a, 0x04, 0x14, 0x00]
        self.port.write(info_packet)
        time.sleep(0.1)
        bytes_to_read = 30
        t0 = time.time()
        while (time.time()-t0) < 5:
            counter = self.port.in_waiting
            if counter > bytes_to_read:
                bytes_data = self.port.read(bytes_to_read)
                self.port.reset_input_buffer()
                if bytes_data[0] == 0x5a:
                    version = bytes_data[3:-1].decode('utf-8')
                    return version
                else:
                    self.port.write(info_packet)
                    time.sleep(0.1)

    def _read_data(self):
        while True:
            counter = self.port.in_waiting  # count the number of bytes waiting to be read
            bytes_to_read = 9
            if counter > bytes_to_read-1:
                bytes_serial = self.port.read(bytes_to_read)  # read 9 bytes
                self.port.reset_input_buffer()               # reset buffer
                if bytes_serial[0] == 0x59 and bytes_serial[1] == 0x59:  # check first two bytes
                    distance = bytes_serial[2] + bytes_serial[3]*256  # distance in next two bytes
                    strength = bytes_serial[4] + bytes_serial[5]*256  # signal strength in next two bytes
                    temperature = bytes_serial[6] + bytes_serial[7]*256  # temp in next two bytes
                    temperature = (temperature/8) - 256  # temp scaling and offset
                    return {"distance": distance/100.0,
                            "strength": strength,
                            "temperature": temperature}

    def get_data(self, port=None) -> Dict[str, float]:
        if port is None:
            port = self.port
        port.reset_input_buffer()
        data = port.read(9)
        if data and data[0] == 0x59 and data[1] == 0x59:  # check first two bytes
            distance = data[2] + data[3]*256     # distance in next two bytes
            strength = data[4] + data[5]*256  # signal strength in next two bytes
            temperature = data[6] + data[7]*256  # temp in next two bytes
            temperature = (temperature/8) - 256  # temp scaling and offset
            return {"distance": distance/100.0,
                    "strength": strength,
                    "temperature": temperature}
        else:
            return {}


    def _try_set_baudrate(self, baudrate):
        baudrates = self._baudrates
        baud_indx = baudrates.index(baudrate)
        port = serial.Serial(self.portname, baudrates[baud_indx], timeout=0)  # mini UART serial device
        baud_hex = [[0x80, 0x25, 0x00],  # 9600
                    [0x00, 0x4b, 0x00],  # 19200
                    [0x00, 0x96, 0x00],  # 38400
                    [0x00, 0xe1, 0x00],  # 57600
                    [0x00, 0xc2, 0x01],  # 115200
                    [0x00, 0x84, 0x03],  # 230400
                    [0x00, 0x08, 0x07],  # 460800
                    [0x00, 0x10, 0x0e]]  # 921600
        info_packet = [0x5a, 0x08, 0x06, baud_hex[baud_indx][0], baud_hex[baud_indx][1],
                       baud_hex[baud_indx][2], 0x00, 0x00]  # instruction packet
        port.write(info_packet)
        time.sleep(1)
        return port.read(9)


def test_luna():
    luna = TFLuna("/dev/ttyUSB0", 115200, 100)
    while True:
        print(luna.get_data())
        time.sleep(.5)
