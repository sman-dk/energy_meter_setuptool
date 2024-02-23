# meter_setuptool
OBS: THIS IS CURRENTLY WORK IN PROGRESS - CHECK BACK LATER

Read kWh and set modbus address, baud rate etc. via RS485 modbus for Fineco energy meters (e.g. Fineco EM115 MOD DO DC) and various Eastron meters (e.g. SDM120, SDM72D, SDM630 etc.). Both serial devices and modbus gateways (e.g. Volison ADM5850G or Cdebyte NB114) are supported
The script may also read kWh, voltage, relay state (if applicable) and other parameters.

This software has been tested on GNU/Linux.

When configuring Fineco and Eastron meters with only the set button: Hold down the "set" button for a few seconds before changing registers on the meter.

# Installation
Clone this repo into a folder and install pymodbus:

```
pip3 install pymodbus
```

# Examples

