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
    if not (pyudev or fcntl):
        raise Exception('Unable to load pyudev or fcntl - is this a Linux system?')

    context = pyudev.Context()
    device = pyudev.Devices.from_device_file(context, path)

    while device is not None:
        try:
            return device.attributes.asstring('serial')
        except KeyError:
            device = device.parent

    raise Exception('Unable to find serial number of device')
