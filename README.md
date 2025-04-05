# pylon2mqtt

pylon2mqtt can periodically poll data from a Pylon Battery debug
interface and publish to MQTT. It should run on Linux and Windows but
since most people will likely run this on something like a Raspberry Pi,
only instructions for Linux are shown here.

## Required Hardware

You will need some sort of serial connection to the Pylontech battery. You can either
build your own or buy a premade cable that embeds a USB->RS232 chip on one
side and the custom RJ45 pinout on the other.

## Installing

Get it from PyPI (you might want to do this in a virtualenv):

```console
$ pip install pylon2mqtt
```

You should then have the `pylon2mqtt` CLI on your path.

## Setting Up

First, it's probably a good idea to test if it works at all. Assuming your serial adapter is `/dev/ttyUSB0`, run:

```console
$ pylon2mqtt test -s /dev/ttyUSB0
```

which should spit out values for all connected batteries. After confirming the basics work, you can give exporting to
MQTT a try:

```console
$ pylon2mqtt run -s /dev/ttyUSB0 -h mymqtthost.example.org
```

once you have it working with the desired flags, you can generate a systemd unit. Just replace `run` with
`generate-systemd` and you'll get a systemd unit file that should use the right virtualenv/interpreter and
set the flags you specified:

```console
$ pylon2mqtt generate-systemd -s /dev/ttyUSB0 -h mymqtthost.example.org
```

## Dealing with multiple serial adapters

If you have multiple USB->serial adapters plugged in, it might be a good idea to get a stable device symlink for
it to avoid confusion. Use the following command to generate a udev rule to create a symlink:

```console
$ pylon2mqtt generate-udev-rule -s /dev/ttyUSB0 
```

put the output into a rules file in `/etc/udev/rules.d/` and then use the symlink instead of ttyUSB0.