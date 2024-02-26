# energy_meter_setuptool
OBS: THIS IS CURRENTLY WORK IN PROGRESS - CHECK BACK LATER

Command line tool to communicate with energy meters from Fineco and Eastron via modbus.

## Features
- Read kWh, voltage, serial number and many other parameters
- Update the relay state on Fineco meters.
- Change baudrate, unit id ('modbus address'), and serial number (useful for setting up new meters)

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
Clone this repo into a folder and install the following dependencies:

```
pip3 install pymodbus pyserial
```

## Usage
```
# ./energy_meter_setuptool.py -h
usage: energy_meter_setuptool.py [-h] [-p SERIAL_PORT | --host HOST] [-b BAUDRATE] [--get-baudrate]
                                  [--set-baudrate {1200,2400,4800,9600,19200,38400}] [--tcp-port TCP_PORT] [-c] -m
                                  {EM115,EM737,SDM72,SDM120,SDM230,SDM630} [--get-relay] [--set-relay {on,off,auto,0,1}] [-u UNIT_ID]
                                  [--get-unit-id] [--set-unit-id SET_UNIT_ID] [--get-serial] [--set-serial SET_SERIAL]
                                  [-t TIMEOUT]

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
  --get-relay           Get relay state
  --set-relay {on,off,auto,0,1}
                        Set relay state
  -u UNIT_ID, --unit-id UNIT_ID
                        Modbus unit id to use (1-255). This is the "slave id" or "address" of the modbus slave
  --get-unit-id         Get configured unit id of the meter
  --set-unit-id SET_UNIT_ID
                        Set modbus unit id (1-255)
  --get-serial          Get configured serial number of the meter
  --set-serial        SET_SERIAL
                        Set serial number. Multiple types are supported: Integers (e.g. "1234"), hexadecimal (e.g. "0x4d2") and binary (e.g.
                        "0b10011010010")
  -t TIMEOUT, --timeout TIMEOUT
                        Timeout in seconds
```

## Examples
Get various info from a Fineco EM115 meter:
```
# ./energy_meter_setuptool.py --serial-port /dev/ttyUSB0 --baudrate 9600 --unit-id 1 --meter-model EM115 --curious
Starting energy meter setup tool

Trying to get voltage from meter model EM115 with unit id 1 

Voltage is 231.4 V which seems ok!

kWh: 5.5 kWh
imp_kWh: 5.5 kWh
power: 4.0 W
L1A: 0.014000000432133675 A
L2A: 0.0 A
L3A: 0.0 A
L1V: 231.3800048828125 V
L2V: 0.0 V
L3V: 0.0 V
Totpf: 1.0 
TotHz: 50.0099983215332 Hz
serial_no: 286331153 (integer)
serial_no_bin: 00010001000100010001000100010001 (binary)
serial_no_hex: 11111111 (hex)
relay_state: 1010101010101010 (01..=on, 10..=off)
```

Set the relay state to on for a Fineco EM115 meter:
```
# ./energy_meter_setuptool.py --serial-port /dev/ttyUSB0 --baudrate 9600 --unit-id 1 --meter-model EM115 --set-relay on
Starting energy meter setup tool

Trying to get voltage from meter model EM115 with unit id 1 

Voltage is 230.5 V which seems ok!

Current relay state is: off
The meter has serial number: 286331153
Calculated "key" based on s/n: 4128
Setting relay state to: on
Current relay state is: on
```

Change the baudrate from 9600 to 19200 on a Fineco EM115 meter:

```
# ./energy_meter_setuptool.py --serial-port /dev/ttyUSB0 --baudrate 9600 -u 1 --meter-model EM115  --set-baudrate 19200
Starting energy meter setup tool

Trying to get voltage from meter model EM115 with unit id 1 

Voltage is 232.0 V which seems ok!

The meter reports a baudrate of: 9600
OBS remember to put the meter into "set" mode!
Setting the baudrate to 19200
Checking that we can now communicate with the meter using the new baudrate
The meter reports a baudrate of: 19200
```

Change the unit id ("modbus address") from 6 to 3 for an Eastron SDM120 meter using a modbus gateway called modbus-gw.example.com:
```
# ./energy_meter_setuptool.py --host modbus-gw.example.com --unit-id 6 --meter-model SDM120 --set-unit-id 3
Starting energy meter setup tool

Trying to get voltage from meter model SDM120 with unit id 6 

Voltage is 231.4 V which seems ok!

The meter reports unit id: 6
Setting the unit id to: 3
The meter reports unit id: 3
```

