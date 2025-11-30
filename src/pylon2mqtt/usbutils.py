from serial.tools import list_ports

# For resetting USB devices, we need udev on Linux
try:
    import pyudev
    import fcntl
except ImportError:
    pyudev = None
    fcntl = None

import logging
logger = logging.getLogger(__name__)


def reset_device(path: str) -> bool:
    """Reset the USB device.

    Returns: True if successful, False otherwise."""
    if pyudev and fcntl:
        return reset_linux_device(path)
    else:
        logger.info('Unable to reset USB device since no known methods are supported')
        return False


def reset_linux_device(path: str) -> bool:
    try:
        context = pyudev.Context()
        device = pyudev.Devices.from_device_file(context, path)
    except pyudev.DeviceNotFoundByFileError:
        return False

    # This should be a tty device, but we need to find the USB device parent
    while (device.subsystem != 'usb' or 'DEVNAME' not in device) and device.parent:
        device = device.parent
    if device.subsystem != 'usb' and 'DEVNAME' not in device:
        logger.error('Didn\'t find USB parent device, went all the way to: ' + str(device))
        return False

    logger.info('Resetting ' + str(device['DEVNAME']))
    with open(device['DEVNAME'], 'w') as f:
        try:
            r = fcntl.ioctl(f, 21780)
            if r != 0:
                logger.error('Unable to reset USB device, ioctl returned ' + str(r))
                return False
        except OSError as e:
            logger.error('Unable to reset USB device, ioctl failed: ' + str(e))

    return True


def get_device_serial(path: str) -> str:
    """Get the serial number of the USB device."""
    for port in list_ports.comports():
        if port.device == path and port.serial_number:
            return port.serial_number
    raise Exception('Unable to find serial number of device')


def find_device_by_serial(serial_number: str) -> str:
    """Find a serial device path by USB serial number."""
    for port in list_ports.comports():
        if port.serial_number == serial_number:
            return port.device
    raise Exception(f'Unable to find device with serial number: {serial_number}')
