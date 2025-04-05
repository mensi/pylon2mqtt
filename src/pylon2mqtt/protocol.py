import time
from typing import Any

import serial
from collections.abc import Iterator
from datetime import datetime
from .usbutils import reset_device

import logging
logger = logging.getLogger(__name__)


PWR_FIELDS = {
    b'Power': {
        'property': 'battery_index',
        'converter': int
    },
    b'Volt': {
        'property': 'voltage',
        'converter': lambda x: float(x) / 1000.0
    },
    b'Curr': {
        'property': 'current',
        'converter': lambda x: float(x) / 1000.0
    },
    b'Tempr': {
        'property': 'temperature',
        'converter': lambda x: float(x) / 1000.0
    },
    b'Tlow': {
        'property': 'coldest_cell_temperature',
        'converter': lambda x: float(x) / 1000.0
    },
    b'Tlow.Id': {
        'property': 'coldest_cell_id',
        'converter': lambda x: int(x)
    },
    b'Thigh': {
        'property': 'hottest_cell_temperature',
        'converter': lambda x: float(x) / 1000.0
    },
    b'Thigh.Id': {
        'property': 'hottest_cell_id',
        'converter': lambda x: int(x)
    },
    b'Vlow': {
        'property': 'lowest_cell_voltage',
        'converter': lambda x: float(x) / 1000.0
    },
    b'Vlow.Id': {
        'property': 'lowest_cell_id',
        'converter': lambda x: int(x)
    },
    b'Vhigh': {
        'property': 'highest_cell_voltage',
        'converter': lambda x: float(x) / 1000.0
    },
    b'Vhigh.Id': {
        'property': 'highest_cell_id',
        'converter': lambda x: int(x)
    },
    b'Base.St': {
        'property': 'base_status',
        'converter': lambda x: x.decode('ascii')
    },
    b'Volt.St': {
        'property': 'voltage_status',
        'converter': lambda x: x.decode('ascii')
    },
    b'Curr.St': {
        'property': 'current_status',
        'converter': lambda x: x.decode('ascii')
    },
    b'Temp.St': {
        'property': 'temperature_status',
        'converter': lambda x: x.decode('ascii')
    },
    b'Coulomb': {
        'property': 'state_of_charge',
        'converter': lambda x: int(x[:-1])
    },
    b'Time': {
        'property': 'time',
        'converter': lambda x: datetime.strptime(x.decode('ascii'), '%Y-%m-%d %H:%M:%S')
    },
    b'B.V.St': {
        'property': 'b_v_status',
        'converter': lambda x: x.decode('ascii')
    },
    b'B.T.St': {
        'property': 'b_t_status',
        'converter': lambda x: x.decode('ascii')
    },
    b'MosTempr': {
        'property': 'mosfet_temperature',
        'converter': lambda x: float(x) / 1000.0
    },
    b'M.T.St': {
        'property': 'm_t_status',
        'converter': lambda x: x.decode('ascii')
    },
    b'SysAlarm.St': {
        'property': 'sysalarm_status',
        'converter': lambda x: x.decode('ascii')
    },
}


class BatteryState:
    battery_index: int
    voltage: float
    current: float
    temperature: float
    coldest_cell_temperature: float
    coldest_cell_id: int
    hottest_cell_temperature: float
    hottest_cell_id: int
    lowest_cell_voltage: float
    lowest_cell_id: int
    highest_cell_voltage: float
    highest_cell_id: int
    base_status: str
    voltage_status: str
    current_status: str
    temperature_status: str
    state_of_charge: int
    time: datetime
    b_v_status: str
    b_t_status: str
    mosfet_temperature: float
    m_t_status: str
    sysalarm_status: str

    @classmethod
    def from_pwr_output(cls, header: list[bytes], fields: list[bytes]) -> 'BatteryState':
        res = BatteryState()

        # The output of absent batteries makes no sense - it does have some empty field
        # markers but they neither align consistently nor are the right count. So let's just
        # look for "Absent" to detect this and fill everything with None.
        if b'Absent' in fields:
            for name in header:
                setattr(res, PWR_FIELDS[name]['property'], None)
            res.battery_index = int(fields[0])
            return res

        # Since there doesn't seem to be any proper escaping, the Time ends up in two fields
        if len(header) + 1 == len(fields) and header[17] == b'Time':
            fields[17] += b' ' + fields[18]
            del fields[18]

        # After that fix, the number of fields and headers should match
        if len(header) != len(fields):
            raise ValueError('Expected %d fields, got %d', len(header), len(fields))

        # Parse the expected fields, with some tolerance for None values
        for name, value in zip(header, fields):
            if name not in PWR_FIELDS:
                logger.warning('Unrecognized field %r', name)
                continue
            if value == b'-':
                setattr(res, PWR_FIELDS[name]['property'], None)
            elif value == b'Absent':
                setattr(res, PWR_FIELDS[name]['property'], None)
            else:
                setattr(res, PWR_FIELDS[name]['property'], PWR_FIELDS[name]['converter'](value))
        return res

    def to_dict(self) -> dict[str, Any]:
        return {k: getattr(self, k) for k in [f['property'] for f in PWR_FIELDS.values()]}

    @property
    def is_absent(self) -> bool:
        return self.voltage is None


class Protocol:
    def __init__(self, serial_port: str | serial.Serial):
        if isinstance(serial_port, str):
            self.serial = serial.Serial(port=serial_port, baudrate=115200, timeout=2)
        else:
            self.serial = serial_port

    def read_updates(self, interval_secs: float = 5) -> Iterator[list[BatteryState]]:
        while True:
            yield self.read_update()
            time.sleep(interval_secs)

    def read_update(self) -> list[BatteryState]:
        self.get_prompt()
        self.serial.write(b'pwr\n')
        pwr = self.serial.read_until(b'pylon>')
        lines = pwr.split(b'\r\n')
        if len(lines) != 21:
            logger.error('Expected 21 lines of pwr output, got %d: %r', len(lines), pwr)
            raise Exception('Received malformed data')

        if lines[-1] != b'\rpylon>':
            logger.error('Expected pylon> prompt after response, got %r', lines[-1])
            raise Exception('Received malformed data')

        if lines[-2] != b'\r$$':
            logger.error('Expected response to end with $$ line, got %r', lines[-2])
            raise Exception('Received malformed data')

        if lines[-3] != b'\rCommand completed successfully':
            logger.error('Command did not complete successfully, got %r', lines[-3])
            raise Exception('Received malformed data')

        header = lines[1].split()
        return [BatteryState.from_pwr_output(header, line.split()) for line in lines[2:18]]

    def have_prompt(self) -> bool:
        """Check that we have a pylon> prompt"""
        self.serial.write(b'\n')
        prompt = self.serial.read_until(b'>')
        return prompt.endswith(b'pylon>')

    def get_prompt(self):
        """Make sure we have a pylon> prompt. Try to get one if we don't."""
        if self.have_prompt():
            return True

        # Is the adapter wedged? Try resetting it
        logger.warning('No pylon> prompt, trying to reset the serial port')
        self.reset_port()
        if self.have_prompt():
            return True

        # Does the console need to be unlocked?
        logger.warning('Still no pylon> prompt, trying to unlock it with the magic string')
        self.serial.baudrate = 1200
        self.serial.write(b'~20014682C0048520FCC3\r')
        time.sleep(1)
        self.serial.baudrate = 115200
        return self.have_prompt()

    def reset_port(self):
        """Try to reset the serial port."""
        self.serial.close()
        reset_device(self.serial.port)
        time.sleep(0.1)
        self.serial.open()
