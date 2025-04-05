import traceback
import click
import json
import logging
import sys

from click.core import ParameterSource
import paho.mqtt.publish as mqtt
from textwrap import dedent

from .protocol import Protocol
from .usbutils import get_device_serial, reset_device


@click.group()
def cli():
    pass


@cli.command()
@click.option('--serial', '-s', required=True, help='Serial port')
def test(serial):
    """Try to read one status update"""
    protocol = Protocol(serial)
    for battery_status in protocol.read_update():
        click.echo(repr(battery_status.to_dict()))


@cli.command()
@click.option('--serial', '-s', required=True, help='Serial port')
@click.option('--hostname', '-h', required=True, help="MQTT hostname")
@click.option('--topic_prefix', '-t', help="MQTT topic prefix", default="pylon2mqtt")
@click.option('--publish_absent', is_flag=True, help="Publish absent battery slots", default=False)
@click.option('--first_only', is_flag=True, default=False,
              help="Only publish the first battery (directly to --topic_prefix)")
@click.option('--update_interval', '-i', help="Update interval in seconds", type=float, default=60.0)
def run(serial: str, hostname: str, topic_prefix: str, publish_absent: bool, first_only: bool, update_interval: float):
    """Read values from a Pylon battery and publish to MQTT periodically"""
    protocol = Protocol(serial)
    for battery_states in protocol.read_updates(interval_secs=update_interval):
        messages = []
        for battery_state in battery_states:
            if battery_state.is_absent and not publish_absent:
                continue
            if first_only and not battery_state.is_absent:
                messages.append({
                    'topic': topic_prefix,
                    'payload': json.dumps(battery_state.to_dict(), default=str),
                })
                break
            messages.append({
                'topic': f'{topic_prefix}/{battery_state.battery_index}',
                'payload': json.dumps(battery_state.to_dict(), default=str),
            })
        mqtt.multiple(messages, hostname)


@cli.command()
def generate_systemd(**kwargs):
    """Generates a systemd unit file

    This command takes the same flags as the "run" command and will embed them in the systemd unit."""
    ctx = click.get_current_context()
    provided_options = {k: v for k, v in kwargs.items() if ctx.get_parameter_source(k) == ParameterSource.COMMANDLINE}

    click.echo(dedent(f"""\
    [Unit]
    Description=Pylon Battery to MQTT publisher
    After=network.target
    
    [Service]
    ExecStart={sys.argv[0]} run {' '.join(f'--{k}' if v == True else f'--{k}={v}' for k, v in provided_options.items())}
    Restart=on-failure
    
    [Install]
    WantedBy=multi-user.target"""))
generate_systemd.params = run.params


@cli.command()
@click.option('--serial', '-s', required=True, help='Serial port')
def reset(serial: str):
    """Reset the serial device

    This is useful for cases where you have a cheap clone USB->Serial adapter that sometimes drops data. Resetting
    it usually fixes the issue for a while. Currently only works on Linux."""
    reset_device(serial)


@cli.command()
@click.option('--serial', '-s', required=True, help='Serial port')
@click.option('--symlink_name', '-l', help='Serial port', default='pylonBattery')
def generate_udev_rule(serial: str, symlink_name: str):
    """Generates a udev rule to use a stable symlink for your serial adapter

    You can for example pipe the output of this command to /etc/udev/rules.d/99-pylonBattery.custom.rules
    to get a udev rule that will make the device appear at a predictable /dev path. This way, you
    don't have to worry about having multiple USB->Serial adapters plugged in as the one connected
    to your battery will get the same name based on its serial number.
    """
    sn = get_device_serial(serial)
    click.echo(f'ACTION=="add", SUBSYSTEM=="tty", ATTRS{{serial}}=="{sn}", SYMLINK+="{symlink_name}"')


def main():
    logging.basicConfig(level=logging.INFO)
    try:
        cli()
    except Exception as e:
        click.echo(click.style('An unexpected error occurred during execution:', fg='red'), err=True)
        for line in traceback.format_exception(e):
            click.echo('  ' + line, err=True)
        return 1
