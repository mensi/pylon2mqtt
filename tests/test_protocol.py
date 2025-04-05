from unittest.mock import Mock
from datetime import datetime

from pylon2mqtt.protocol import Protocol

PWR_RESPONSE = (
    b'pwr\n\r@\r\r\n'
    b'Power Volt   Curr   Tempr  Tlow   Tlow.Id  Thigh  Thigh.Id Vlow   Vlow.Id  Vhigh  Vhigh.Id Base.St  Volt.St  '
    b'Curr.St  Temp.St  Coulomb  Time                 B.V.St   B.T.St  MosTempr M.T.St   SysAlarm.St\r\r\n'
    
    b'1     49874  -642   19100  17000  8        17600  0        3324   2        3325   0        Dischg   Normal   '
    b'Normal   Normal   81%      2025-03-18 05:58:51  Normal   Normal  18200    Normal   Normal  \r\r\n'
    b'2     -      -      -      -      -      -      -      Absent   -        -        -        -        '
    b'-                    -        -       \r\r\n'
    b'3     -      -      -      -      -      -      -      Absent   -        -        -        -        '
    b'-                    -        -       \r\r\n'
    b'4     -      -      -      -      -      -      -      Absent   -        -        -        -        '
    b'-                    -        -       \r\r\n'
    b'5     -      -      -      -      -      -      -      Absent   -        -        -        -        '
    b'-                    -        -       \r\r\n'
    b'6     -      -      -      -      -      -      -      Absent   -        -        -        -        '
    b'-                    -        -       \r\r\n'
    b'7     -      -      -      -      -      -      -      Absent   -        -        -        -        '
    b'-                    -        -       \r\r\n'
    b'8     -      -      -      -      -      -      -      Absent   -        -        -        -        '
    b'-                    -        -       \r\r\n'
    b'9     -      -      -      -      -      -      -      Absent   -        -        -        -        '
    b'-                    -        -       \r\r\n'
    b'10    -      -      -      -      -      -      -      Absent   -        -        -        -        '
    b'-                    -        -       \r\r\n'
    b'11    -      -      -      -      -      -      -      Absent   -        -        -        -        '
    b'-                    -        -       \r\r\n'
    b'12    -      -      -      -      -      -      -      Absent   -        -        -        -        '
    b'-                    -        -       \r\r\n'
    b'13    -      -      -      -      -      -      -      Absent   -        -        -        -        '
    b'-                    -        -       \r\r\n'
    b'14    -      -      -      -      -      -      -      Absent   -        -        -        -        '
    b'-                    -        -       \r\r\n'
    b'15    -      -      -      -      -      -      -      Absent   -        -        -        -        '
    b'-                    -        -       \r\r\n'
    b'16    -      -      -      -      -      -      -      Absent   -        -        -        -        '
    b'-                    -        -       \r\n'
    b'\rCommand completed successfully\r\n'
    b'\r$$\r\n'
    b'\rpylon>')


def test_parsing():
    serial = Mock()
    serial.write = Mock(side_effect=lambda x: len(x))
    serial.read_until = Mock(side_effect=[b'pylon>', PWR_RESPONSE])
    protocol = Protocol(serial)
    result = protocol.read_update()
    assert result[0].voltage == 49.874
    assert result[0].current == -0.642
    assert result[1].voltage is None


def test_dict_conversion():
    serial = Mock()
    serial.write = Mock(side_effect=lambda x: len(x))
    serial.read_until = Mock(side_effect=[b'pylon>', PWR_RESPONSE])
    protocol = Protocol(serial)
    result = protocol.read_update()
    assert result[0].to_dict() == {
        'battery_index': 1,
        'voltage': 49.874,
        'current': -0.642,
        'temperature': 19.1,
        'coldest_cell_temperature': 17.0,
        'coldest_cell_id': 8,
        'hottest_cell_temperature': 17.6,
        'hottest_cell_id': 0,
        'lowest_cell_voltage': 3.324,
        'lowest_cell_id': 2,
        'highest_cell_voltage': 3.325,
        'highest_cell_id': 0,
        'base_status': 'Dischg',
        'voltage_status': 'Normal',
        'current_status': 'Normal',
        'temperature_status': 'Normal',
        'state_of_charge': 81,
        'time': datetime(2025, 3, 18, 5, 58, 51),
        'b_v_status': 'Normal',
        'b_t_status': 'Normal',
        'mosfet_temperature': 18.2,
        'm_t_status': 'Normal',
        'sysalarm_status': 'Normal',
    }


def test_dict_conversion_absent_battery():
    serial = Mock()
    serial.write = Mock(side_effect=lambda x: len(x))
    serial.read_until = Mock(side_effect=[b'pylon>', PWR_RESPONSE])
    protocol = Protocol(serial)
    result = protocol.read_update()
    assert result[1].to_dict() == {
        'battery_index': 2,
        'voltage': None,
        'current': None,
        'temperature': None,
        'coldest_cell_temperature': None,
        'coldest_cell_id': None,
        'hottest_cell_temperature': None,
        'hottest_cell_id': None,
        'lowest_cell_voltage': None,
        'lowest_cell_id': None,
        'highest_cell_voltage': None,
        'highest_cell_id': None,
        'base_status': None,
        'voltage_status': None,
        'current_status': None,
        'temperature_status': None,
        'state_of_charge': None,
        'time': None,
        'b_v_status': None,
        'b_t_status': None,
        'mosfet_temperature': None,
        'm_t_status': None,
        'sysalarm_status': None,
    }
