# energy_meter_setup_tool
OBS: THIS IS CURRENTLY WORK IN PROGRESS - CHECK BACK LATER

Command line tool to communicate with energy meters from Fineco and Eastron via modbus.

## Features
- Read kWh, voltage, serial number and many other parameters
- Update the relay state on Fineco meters.
- Change baudrate, unit id ('modbus address'), and serial number (useful for setting up new meters)

Both modbus rtu via a serial device (e.g. USB rs485 adaptor) as well as modbus gateways (e.g. Volison ADM5850G or Cdebyte NB114) are supported.

## Supported models
- Fineco EM115
- Fineco EM737
- Eastron SDM72
- Eastron SDM120
- Eastron SDM230
- Eastron SDM630

For the Fineco meters, the DO (Direct Output) versions with a build in relay are supported too.

## Supported modbus capabilities
You may communicate to your energy meters using this script using either of the following:

- serial device (e.g. a USB rs485 converter)
- modbus gateway (e.g. Volison ADM5850G or Cdebyte NB114)

## Notes
This software has been tested on GNU/Linux.

When configuring Fineco and Eastron meters with only one button: Hold down the "set" button for a few seconds before trying to change the baudrate etc. on the meter.

## Installation
Clone this repo into a folder and install dependencies:

```
pip3 install pymodbus pyserial
```

## Usage
```
# ./meter_setuptools.py -h
usage: fineco_setuptool.py [-h] [-p SERIAL_PORT | --host HOST] [-b BAUDRATE] [--get-baudrate]
                           [--set-baudrate {1200,2400,4800,9600,19200,38400}] [--tcp-port TCP_PORT] [-c] -m
                           {EM115,EM737,SDM72,SDM120,SDM230,SDM630} [-r] [-s {on,off,auto,0,1}] [-u UNIT_ID] [--get-unit-id]
                           [--set-unit-id SET_UNIT_ID] [--get-serial-number] [--set-serial-number SET_SERIAL_NUMBER] [-t TIMEOUT]

Read and write to various modbus registers on Fineco energy meters. E.g. Fineco EM115 DO DC. or Eastron meters (e.g. SDM120)

options:
  -h, --help            show this help message and exit
  -p SERIAL_PORT, --serial-port SERIAL_PORT
                        Serial port
  --host HOST           Hostname (if modbus gateway)
  -b BAUDRATE, --baudrate BAUDRATE
                        Serial baudrate to use when communicating with modbus rtu using a serial port
  --get-baudrate        Get configured serial baudrate of the meter
  --set-baudrate {1200,2400,4800,9600,19200,38400}
                        Set the serial baudrate
  --tcp-port TCP_PORT   Modbus gateway TCP port
  -c, --curious         Curious mode. Ask the meter about various registers
  -m {EM115,EM737,SDM72,SDM120,SDM230,SDM630}, --meter-model {EM115,EM737,SDM72,SDM120,SDM230,SDM630}
                        Meter model
  -r, --read-relay      Read relay state
  -s {on,off,auto,0,1}, --set-relay {on,off,auto,0,1}
                        Set relay state
  -u UNIT_ID, --unit-id UNIT_ID
                        Modbus unit id to use (1-255). This is the "slave id" or "address" of the modbus slave
  --get-unit-id         Get configured unit id of the meter
  --set-unit-id SET_UNIT_ID
                        Set modbus unit id (1-255)
  --get-serial-number   Get configured serial number of the meter
  --set-serial-number SET_SERIAL_NUMBER
                        Set serial number (get the current serial number by using --curious). Multiple types are supported: Integers (e.g.
                        "1234"), hexadecimal (e.g. "0x4d2") and binary (e.g. "0b10011010010")
  -t TIMEOUT, --timeout TIMEOUT
                        Request timeout
```

## Examples

