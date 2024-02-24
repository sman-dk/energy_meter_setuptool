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


def ieee754(value_list):
    '''Convert the value list as IEEE 754 32 bit single precision floats from the electricity meters'''
    bin_float = format(value_list[0] & 0xffff,'016b') + format(value_list[1] & 0xffff,'016b')
    packed_v = struct.pack('>L', int(bin_float, 2))
    return struct.unpack('>f', packed_v)[0]

def u32(value_list):
    '''Convert the value list as unsigned 32 bit integer'''
    return int(''.join(['{0:016b}'.format(i) for i in value_list]), 2)

def binary(value_list):
    '''Return the value list as a binary string'''
    return ''.join(['{0:016b}'.format(i) for i in value_list])

def hex_str(value_list):
    '''Return the value list as hex'''
    return f'{value_list[0]:x}{value_list[1]:x}'

def address_limit(address):
    ''' Type function for argparse - an int within some predefined bounds '''
    try:
        address = int(address)
    except ValueError:
        raise argparse.ArgumentTypeError('Must be an integer')
    min_val = 1
    max_val = 255
    if address < min_val or address > max_val:
        raise argparse.ArgumentTypeError('Argument must be < ' + str(min_val) + 'and > ' + str(max_val))
    return address

def connect(args):
    '''Connect to serial port or modbus gateway'''
    if args.host:
        # Modbus gateway
        client = modbusClient.ModbusTcpClient(args.host, 
                                              port = args.tcp_port,
                                              timeout = args.timeout,
                                              retries = 3)

    elif args.serial_port:
        # Serial rs485 port
        client = modbusClient.ModbusSerialClient(port=args.serial_port,
                                                 timeout=args.timeout,
                                                 baudrate=args.baudrate,
                                                 bytesize=8,
                                                 parity='N',
                                                 stopbits=1)
    else:
        print('Neither a serial port or a host has been defined. I can not work like this!!', file=sys.stderr)
        sys.exit(1)
 
    return client

def fineco_generate_key(meter_serial_number):
    ''' Compute the "key" based on the meteres serial number. This key is necessary in order to being able to change the relay state. '''
    # Fineco is writing me in an email 2022-03-10: 
    # '''The reason to set default SN as 11111111 is you do not need to calculate the "key", the key always as "1l020", it would be easier.'''
    # note2self: the numbers above are in hex
    #
    # Based on a piece of example C-code from the manufacturer
    tmp = meter_serial_number >> 24
    tmp += meter_serial_number >> 8
    tmp &= 0x1234
    return tmp

def modbus_req(args, register_name, client=None):
    '''Fetch a register from a meter and return the value as a result'''
    assert type(register_name) is str
    if not client:
        client = connect(args)

    # Function code, hex address, count/length of registers to read (multiple of 2 bytes, i.e. 2=4bytes), info text (e.g. unit), response type (how to interpret the response)
    meter_regs = { 
                'Eastron': 
                  { 'kWh': [ 4, 0x156, 2, 'kWh', 'F32' ],
                    'imp_kWh': [ 4, 0x48, 2, 'kWh', 'F32' ],
                    'exp_kWh': [ 4, 0x4A, 2, 'kWh', 'F32' ],
                    'power': [ 4, 0x34, 2, 'W', 'F32'],
                    'L1A': [ 4, 0x6, 2, 'A', 'F32' ],
                    'L2A': [ 4, 0x8, 2, 'A', 'F32' ],
                    'L3A': [ 4, 0xA, 2, 'A', 'F32' ],
                    'L1V': [ 4, 0x0, 2, 'V', 'F32' ],
                    'L2V': [ 4, 0x2, 2, 'V', 'F32' ],
                    'L3V': [ 4, 0x4, 2, 'V', 'F32' ],
                    'Totpf': [ 4, 0x3E, 2, '', 'F32' ],
                    'TotHz': [ 4, 0x46, 2, 'Hz', 'F32' ],
                    'Serial_no': [ 3, 0xFC00, 2, '(integer)', 'U32' ],
                    'Serial_no_bin': [ 3, 0xFC00, 2, '(binary)', 'bin' ],
                    'Serial_no_hex': [ 3, 0xFC00, 2, '(hex)', 'hex' ],
                    },
                'EM115': 
                  { 'kWh': [ 4, 0x16A, 2, 'kWh', 'F32' ],
                    'imp_kWh': [ 4, 0x160, 2, 'kWh', 'F32' ],
                    'exp_kWh': [ 4, 0x166, 2, 'kWh', 'F32' ],
                    'power': [ 4, 0x8, 2, 'W', 'F32'],
                    'L1A': [ 4, 0x6, 2, 'A', 'F32' ],
                    'L2A': [ 4, 0x0, 2, 'A', 'F32' ],
                    'L3A': [ 4, 0x0, 2, 'A', 'F32' ],
                    'L1V': [ 4, 0x2, 2, 'V', 'F32' ],
                    'L2V': [ 4, 0x0, 2, 'V', 'F32' ],
                    'L3V': [ 4, 0x0, 2, 'V', 'F32' ],
                    'Totpf': [ 4, 0xE, 2, '', 'F32' ],
                    'TotHz': [ 4, 0x4, 2, 'Hz', 'F32' ],
                    'Serial_no': [ 4, 0xFF00, 2, '(integer)', 'U32' ],
                    'Serial_no_bin': [ 4, 0xFF00, 2, '(binary)', 'bin' ],
                    'Serial_no_hex': [ 4, 0xFF00, 2, '(hex)', 'hex' ],
                    'relay_state': [ 4, 0x566, 1, '(binary)', 'bin' ],
                    'set_relay_state': [ 16, 0x566, 1, '(binary)', 'bin' ],
                     }, 
                'EM737': 
                  { 'kWh': [ 4, 0x700, 2, 'kWh', 'F32' ],
                    'imp_kWh': [ 4, 0x800, 2, 'kWh', 'F32' ],
                    'exp_kWh': [ 4, 0x900, 2, 'kWh', 'F32' ],
                    'power': [ 4, 0x26, 2, 'W', 'F32'],
                    'L1A': [ 4, 0x16, 2, 'A', 'F32' ],
                    'L2A': [ 4, 0x18, 2, 'A', 'F32' ],
                    'L3A': [ 4, 0x1A, 2, 'A', 'F32' ],
                    'L1V': [ 4, 0x10, 2, 'V', 'F32' ],
                    'L2V': [ 4, 0x12, 2, 'V', 'F32' ],
                    'L3V': [ 4, 0x14, 2, 'V', 'F32' ],
                    'Totpf': [ 4, 0x3E, 2, '', 'F32' ],
                    'TotHz': [ 4, 0x40, 2, 'Hz', 'F32' ],
                    'Serial_no': [ 4, 0xFF00, 2, '(integer)', 'U32' ],
                    'Serial_no_bin': [ 4, 0xFF00, 2, '(binary)', 'bin' ],
                    'Serial_no_hex': [ 4, 0xFF00, 2, '(hex)', 'hex' ],
                    'relay_state': [ 4, 0x566, 1, '(binary)', 'bin' ],
                    }
                }

    mregs = meter_regs[args.meter_model]
    if not register_name in mregs:
        info_text = 'Not supported for this model'
        value = None
    else:
        function_code, address, count, info_text, response_type = mregs[register_name]
        if function_code == 3:
            res = client.read_holding_registers(address, count, args.unit_id)
        elif function_code == 4:
            res = client.read_input_registers(address, count, args.unit_id)
        elif function_code == 16:
            # FIXME tmp
            print("off")
            res = client.write_registers(address, 25973, args.unit_id)
            #import time
            #time.sleep(1)
            print("on")
            res = client.write_registers(address, 47818, args.unit_id)
            #time.sleep(1)
            #print("on")
            #res = client.write_registers(address, [25973], args.unit_id)
            #time.sleep(1)
            #print("off")
            #res = client.write_registers(address, [47818], args.unit_id)
        else:
            print('ERROR: Unsupported function code. This should not be happening (check that all function codes are supported in the script).\nExiting!', file=sys.stderr)
            sys.exit(1)
        if res.isError():
            print(f'ERROR: We got an error back when requesting {register_name}:')
            print(dir(res))
            print(res.encode())
            print(res.string)
            print('Exiting!')
            sys.exit(1)
        regs = res.registers
        if regs:
            if response_type == 'F32':
                value = ieee754(regs)
            elif response_type == 'U32':
                value = u32(regs)
            elif response_type == 'bin':
                value = binary(regs)
            elif response_type == 'hex':
                value = hex_str(regs)
            else:
                print('ERROR: Response type not supported. This should not be happening (check that all response types are supported in the script).\nExiting!', file=sys.stderr)
                sys.exit(1)
        else:
            value = None
    return {'value': value, 'info_text': info_text}

def modbus_req_alot(client, args, printout = False):
    '''Fetch a lot bunch of registers. Used for "curious mode" where we fetch a bunch of registers if available'''
    reg_names = ['kWh', 'imp_kWh', 'power', 'L1A', 'L2A', 'L3A', 'L1V', 'L2V', 'L3V', 'Totpf', 'TotHz', 'Serial_no', 'Serial_no_bin', 'Serial_no_hex', 'relay_state']
    result = []
    for register_name in reg_names:
        reading = modbus_req(args, register_name, client=client)
        result.append(reading)
        if printout:
            if type(reading['value']) != None:
                print(f'{register_name}: {reading["value"]} {reading["info_text"]}')
    if args.meter_model in ['EM115', 'EM737']:
        reading = modbus_req(args, "Serial_no", client=client)
        fineco_key = fineco_generate_key(reading['value'])
        hex_key_str = str(hex(fineco_key))
        print(f'Fineco hex "key": {hex_key_str}')
    return result

def voltage_test(client, args):
    '''Read the voltage and complain if it is outside boundries'''
    print(f'\nTrying to get voltage from unit id {args.unit_id} with configured meter model is {args.meter_model} \n')
    reading = modbus_req(args, 'L1V', client=client)
    voltage = reading['value']
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



def main():
    ''' The main function '''
    # Argument parsing
    parser = argparse.ArgumentParser(prog='fineco_setuptool.py', description='Read and write to various modbus registers on Fineco energy meters. E.g. Fineco EM115 DO DC. or Eastron meters')
    ch_group = parser.add_mutually_exclusive_group()
    dev_group = parser.add_mutually_exclusive_group()
    dev_group.add_argument('-p', '--serial-port', help='Serial port', required=False)
    dev_group.add_argument('--host', help='Hostname (if modbus gateway)', required=False)
    parser.add_argument('-b', '--baudrate', help='Serial baudrate', default=9600, type=int)
    parser.add_argument('--tcp-port', help='Modbus gateway TCP port', default=502, type=int)
    parser.add_argument('-c', '--curious', help='Curious mode. Ask the meter about various registers', action='store_true')
    parser.add_argument('-m', '--meter-model', help='Fineco meter model', default='EM115', choices = ['EM115', 'EM737', 'Eastron'])
    ch_group.add_argument('--new-baud-rate', help='Baud rate')
    parser.add_argument('-r', '--read-relay', help='Read relay state', action='store_true')
    parser.add_argument('-s', '--set-relay', help='Set relay state', choices=['on', 'off'])
    parser.add_argument('-u', '--unit-id', help='Modbus unit id (1-255). This is the "slave id" or "address" of the modbus slave', default='1', type=address_limit,  )
    ch_group.add_argument('--new-unit-id', help='New modbus unit id (1-255)', type=address_limit, )
    parser.add_argument('-t', '--timeout', help='Request timeout', default=2, type=int)
    args = parser.parse_args()
    if not args.serial_port and not args.host:
        print("ERROR: at least one of the following arguments must be set: --serial-port or --host")
        sys.exit(1)

    print('Starting Fineco setuptool')

    # Connect
    client = connect(args)

    # Voltage test
    voltage_test(client, args)

    if args.curious:
        # Fetch some more registers
        readings = modbus_req_alot(client, args, printout=True)

    reading = modbus_req(args, 'set_relay_state', client=client)

    # Finishing up
    client.close()


if __name__ == '__main__':
    main()
