#!/usr/bin/env python3
#
# fineco_setuptool A tool to read and write to various rs485 modbus registers for Fineco electricity meters
#
#    Copyright (C) 2024 Georg Sluyterman van Langeweyde
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
#

import argparse
import sys
import struct
import pymodbus.client as modbusClient
from pymodbus import ModbusException


def ieee754(value):
    '''Function to convert IEEE 754 floats from the electricity meters'''
    bin_float = format(value[0] & 0xffff,'016b') + format(value[1] & 0xffff,'016b')
    packed_v = struct.pack('>L', int(bin_float, 2))
    return struct.unpack('>f', packed_v)[0]

def address_limit(arg):
    ''' Type function for argparse - an int within some predefined bounds '''
    try:
        arg = int(arg)
    except ValueError:
        raise argparse.ArgumentTypeError('Must be an integer')
    min_val = 1
    max_val = 255
    if arg < min_val or arg > max_val:
        raise argparse.ArgumentTypeError('Argument must be < ' + str(min_val) + 'and > ' + str(max_val))
    return arg

def generate_key(serial_number_str):
    ''' Compute "key" based on the meteres serial number. This key is necessary in order to being able to change the relay state. '''
    # Based on a piece of example C-code from the manufacturer
    meter_serial_number = int(serial_number_str)
    tmp = meter_serial_number >> 24
    tmp += meter_serial_number >> 8
    tmp &= 0x1234
    return tmp

def main():
    ''' The main function '''
    parser = argparse.ArgumentParser(prog='fineco_setuptool.py', description='Read and write to various modbus registers on Fineco energy meters. E.g. Fineco EM115 DO DC. or Eastron meters')
    ch_group = parser.add_mutually_exclusive_group()
    dev_group = parser.add_mutually_exclusive_group()
    dev_group.add_argument("-d", "--device", help="Device name (if serial device)", required=False)
    dev_group.add_argument("--host", help="Hostname (if modbus gateway)", required=False)
    parser.add_argument('-b', '--baudrate', help='Serial baudrate', default=9600, type=int)
    parser.add_argument('-p', '--port', help='Modbus gateway TCP port', default=502, type=int)
    parser.add_argument('-v', '--verbose', help='Verbose. Read verious registers', action='store_true')
    parser.add_argument('-m', '--meter-model', help='Fineco meter model', default='EM115', choices = ['EM115', 'EM737', 'Eastron'])
    ch_group.add_argument('--new-baud-rate', help='Baud rate')
    parser.add_argument('-r', '--read-relay', help='Read relay state', action='store_true')
    parser.add_argument('-s', '--set-relay', help='Set relay state', choices=['on', 'off'])
    parser.add_argument('-u', '--unit-id', help='Modbus unit id (1-255). This is the "slave id" or "address" of the modbus slave', default='1', type=address_limit,  )
    ch_group.add_argument('--new-unit-id', help='New modbus unit id (1-255)', type=address_limit, )
    parser.add_argument('-t', '--timeout', help='Request timeout', default=2, type=int)
    args = parser.parse_args()
    if not args.device and not args.host:
        print("ERROR: at least one of the following arguments must be set: -d/--device or --host")
        sys.exit(1)

    print('Starting Fineco setuptool')

    # Registers (hex address, length of registers to read, unit to print)
    meter_regs = { 
                'Eastron': {
                    "kWh": [ 0x156, 2, "kWh" ],
                    "imp_kWh": [ 0x48, 2, "kWh" ],
                    "exp_kWh": [ 0x4A, 2, "kWh" ],
                    "power": [ 0x34, 2, "W"],
                    "L1A": [ 0x6, 2, "A" ],
                    "L2A": [ 0x8, 2, "A" ],
                    "L3A": [ 0xA, 2, "A" ],
                    "L1V": [ 0x0, 2, "V" ],
                    "L2V": [ 0x2, 2, "V" ],
                    "L3V": [ 0x4, 2, "V" ],
                    "Totpf": [ 0x3E, 2, "" ],
                    "TotHz": [ 0x46, 2, "Hz" ],
                    },
                'EM115':
                    { 'kWh': [ 0x16A, 2, 'kWh' ],
                        'imp_kWh': [ 0x160, 2, 'kWh' ],
                        'exp_kWh': [ 0x166, 2, 'kWh' ],
                        'power': [ 0x8, 2, 'W'],
                        'L1A': [ 0x6, 2, 'A' ],
                        'L2A': [ 0x0, 2, 'A' ],
                        'L3A': [ 0x0, 2, 'A' ],
                        'L1V': [ 0x2, 2, 'V' ],
                        'L2V': [ 0x0, 2, 'V' ],
                        'L3V': [ 0x0, 2, 'V' ],
                        'Totpf': [ 0xE, 2, '' ],
                        'TotHz': [ 0x4, 2, 'Hz' ],
                     }, 
                'EM737': 
                    {
                        'kWh': [ 0x700, 2, 'kWh' ],
                        'imp_kWh': [ 0x800, 2, 'kWh' ],
                        'exp_kWh': [ 0x900, 2, 'kWh' ],
                        'power': [ 0x26, 2, 'W'],
                        'L1A': [ 0x16, 2, 'A' ],
                        'L2A': [ 0x18, 2, 'A' ],
                        'L3A': [ 0x1A, 2, 'A' ],
                        'L1V': [ 0x10, 2, 'V' ],
                        'L2V': [ 0x12, 2, 'V' ],
                        'L3V': [ 0x14, 2, 'V' ],
                        'Totpf': [ 0x3E, 2, '' ],
                        'TotHz': [ 0x40, 2, 'Hz' ],
                    }
                }

    # Connect
    if args.host:
        # Modbus gateway
        client = modbusClient.ModbusTcpClient(args.host, 
                                              port = args.port,
                                              timeout = args.timeout,
                                              retries = 3)

    elif args.device:
        # Serial rs485 port
        client = modbusClient.ModbusSerialClient(port=args.device,
                                                 timeout=args.timeout,
                                                 baudrate=args.baudrate,
                                                 bytesize=8,
                                                 parity='N',
                                                 stopbits=1)
    else:
        print('Neither a serial port or a host has been defined. I can not work like this!!', file=sys.stderr)
        sys.exit(1)
    
    # First read the voltage and complain if it is outside boundries
    print(f'\nTrying to get voltage from unit id {args.unit_id} with configured meter model is {args.meter_model} \n')
    mregs = meter_regs[args.meter_model]
    address_reg, count_reg = mregs['L1V'][0], mregs['L1V'][1]
    res = client.read_input_registers(address_reg,count_reg,args.unit_id)
    regs = res.registers
    voltage = ieee754(regs)
    print('Voltage: %.1f V' % voltage, end =' ')
    # a tolerance of 0.1 means +/- 10%
    tolerance = 0.1 
    if voltage < 115*(1-tolerance) or voltage > 115*(1+tolerance) and voltage < 230*(1-tolerance) or voltage > 230*(1+tolerance):
        voltage_ok = False
    else:
        voltage_ok = True
    if voltage_ok:
        print('which seems ok!\n')
    else:
        print('which seems out of range for 115/230 V +/- 10%')
        print('Exiting!')
        sys.exit(1)


if __name__ == '__main__':
    main()
