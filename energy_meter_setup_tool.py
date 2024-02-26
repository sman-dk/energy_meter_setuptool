#!/usr/bin/env python3
#
# energy_meter_setup_tool A tool to communicate via rs485 modbus with Fineco and Eastron electricity meters
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
import pymodbus.client as modbus_client
from pymodbus import ModbusException
import time


def ieee754(value_list):
    """Convert the value list as IEEE 754 32 bit single precision floats from the electricity meters"""
    bin_float = format(value_list[0] & 0xffff, '016b') + format(value_list[1] & 0xffff, '016b')
    packed_v = struct.pack('>L', int(bin_float, 2))
    return struct.unpack('>f', packed_v)[0]


def reverse_ieee754(float_value):
    """Convert a float to an IEEE 754 32 bit single precision value list"""
    # Pack the float as a 32-bit unsigned long (big-endian)
    packed_v = struct.pack('>f', float_value)
    # Unpack as a 32-bit unsigned long (big-endian) and convert to binary
    bin_value = format(struct.unpack('>L', packed_v)[0], '032b')
    # Split the binary string into two 16-bit parts and convert them to integers
    value1 = int(bin_value[:16], 2)
    value2 = int(bin_value[16:], 2)
    return [value1, value2]


def u32(value_list):
    """Convert the value list as unsigned 32-bit integer"""
    return int(''.join(['{0:016b}'.format(i) for i in value_list]), 2)


def reverse_u32(integer_value):
    """Convert an int into a value list as if it were a 32-bit integer"""
    # Convert the integer to a 32-bit binary string
    bin_value = format(integer_value, '032b')
    # Split the binary string into two 16-bit parts and convert them to integers
    value1 = int(bin_value[:16], 2)
    value2 = int(bin_value[16:], 2)
    return [value1, value2]


def u16(value_list):
    """Convert the value list as an unsigned 16 bit integer"""
    # Well this is almost too easy...
    return value_list[0]


def binary(value_list):
    """Return the value list as a binary string"""
    return ''.join(['{0:016b}'.format(i) for i in value_list])


def hex_str(value_list):
    """Return the value list as hex"""
    return f'{value_list[0]:x}{value_list[1]:x}'


def address_limit(address):
    """ Type function for argparse - an int within some predefined bounds """
    try:
        address = int(address)
    except ValueError:
        raise argparse.ArgumentTypeError('Must be an integer')
    min_val = 1
    max_val = 255
    if address < min_val or address > max_val:
        raise argparse.ArgumentTypeError('Argument must be < ' + str(min_val) + 'and > ' + str(max_val))
    return address


def connect(args, new_baudrate=None):
    """Connect to serial port or modbus gateway"""
    if args.host:
        # Modbus gateway
        client = modbus_client.ModbusTcpClient(args.host,
                                               port=args.tcp_port,
                                               timeout=args.timeout,
                                               retries=3)

    elif args.serial_port:
        # Serial rs485 port
        if new_baudrate:
            baudrate = new_baudrate
        else:
            baudrate = args.baudrate
        client = modbus_client.ModbusSerialClient(port=args.serial_port,
                                                  timeout=args.timeout,
                                                  baudrate=baudrate,
                                                  bytesize=8,
                                                  parity='N',
                                                  stopbits=1)
    else:
        print('Neither a serial port or a host has been defined. I can not work like this!!', file=sys.stderr)
        sys.exit(1)
 
    return client


def fineco_generate_key(meter_serial_number):
    """Compute the 'key' based on the meters serial number. This is used when changing the relay state. """
    # Based on a piece of example C-code from the manufacturer
    tmp = meter_serial_number >> 24
    tmp += meter_serial_number >> 8
    tmp &= 0x1234
    return tmp


def modbus_req(args, register_name, client=None, payload=None, unit_id=None):
    """Fetch a register from a meter and return the value as a result"""
    assert type(register_name) is str
    if not client:
        client = connect(args)
    if not unit_id:
        unit_id = args.unit_id

    # Function code, hex address, count/length of registers to read (multiple of 2 bytes, i.e. 2=4bytes),
    # info text (e.g. unit), response type (how to interpret the response)
    meter_regs = { 
                'SDM72': {
                    'kWh': [4, 0x156, 2, 'kWh', 'F32'],
                    'imp_kWh': [4, 0x48, 2, 'kWh', 'F32'],
                    'exp_kWh': [4, 0x4A, 2, 'kWh', 'F32'],
                    'power': [4, 0x34, 2, 'W', 'F32'],
                    'L1A': [4, 0x6, 2, 'A', 'F32'],
                    'L2A': [4, 0x8, 2, 'A', 'F32'],
                    'L3A': [4, 0xA, 2, 'A', 'F32'],
                    'L1V': [4, 0x0, 2, 'V', 'F32'],
                    'L2V': [4, 0x2, 2, 'V', 'F32'],
                    'L3V': [4, 0x4, 2, 'V', 'F32'],
                    'Totpf': [4, 0x3E, 2, '', 'F32'],
                    'TotHz': [4, 0x46, 2, 'Hz', 'F32'],
                    'serial_no': [3, 0xFC00, 2, '(integer)', 'U32'],
                    'serial_no_bin': [3, 0xFC00, 2, '(binary)', 'bin'],
                    'serial_no_hex': [3, 0xFC00, 2, '(hex)', 'hex'],
                    'baudrate': [3, 0x1C, 2, '(integer)', 'F32'],
                    'set_baudrate': [16, 0x1C, 2, '', 'F32'],
                    'unit_id': [3, 0x14, 2, '(modbus id/address)', 'F32'],
                    'set_unit_id': [16, 0x14, 2, '', 'F32'],
                    },
                'SDM120': {
                    'kWh': [4, 0x156, 2, 'kWh', 'F32'],
                    'imp_kWh': [4, 0x48, 2, 'kWh', 'F32'],
                    'exp_kWh': [4, 0x4A, 2, 'kWh', 'F32'],
                    'power': [4, 0x34, 2, 'W', 'F32'],
                    'L1A': [4, 0x6, 2, 'A', 'F32'],
                    'L1V': [4, 0x0, 2, 'V', 'F32'],
                    'Totpf': [4, 0x3E, 2, '', 'F32'],
                    'TotHz': [4, 0x46, 2, 'Hz', 'F32'],
                    'serial_no': [3, 0xFC00, 2, '(integer)', 'U32'],
                    'serial_no_bin': [3, 0xFC00, 2, '(binary)', 'bin'],
                    'serial_no_hex': [3, 0xFC00, 2, '(hex)', 'hex'],
                    'baudrate': [3, 0x1C, 2, '(integer)', 'F32'],
                    'set_baudrate': [16, 0x1C, 2, '', 'F32'],
                    'unit_id': [3, 0x14, 2, '(modbus id/address)', 'F32'],
                    'set_unit_id': [16, 0x14, 2, '', 'F32'],
                    },
                'SDM230': {
                    'kWh': [4, 0x156, 2, 'kWh', 'F32'],
                    'imp_kWh': [4, 0x48, 2, 'kWh', 'F32'],
                    'exp_kWh': [4, 0x4A, 2, 'kWh', 'F32'],
                    'power': [4, 0x34, 2, 'W', 'F32'],
                    'L1A': [4, 0x6, 2, 'A', 'F32'],
                    'L1V': [4, 0x0, 2, 'V', 'F32'],
                    'Totpf': [4, 0x3E, 2, '', 'F32'],
                    'TotHz': [4, 0x46, 2, 'Hz', 'F32'],
                    'serial_no': [3, 0xFC00, 2, '(integer)', 'U32'],
                    'serial_no_bin': [3, 0xFC00, 2, '(binary)', 'bin'],
                    'serial_no_hex': [3, 0xFC00, 2, '(hex)', 'hex'],
                    'baudrate': [3, 0x1C, 2, '(integer)', 'F32'],
                    'set_baudrate': [16, 0x1C, 2, '', 'F32'],
                    'unit_id': [3, 0x14, 2, '(modbus id/address)', 'F32'],
                    'set_unit_id': [16, 0x14, 2, '', 'F32'],
                    },
                'SDM630': {
                    'kWh': [4, 0x156, 2, 'kWh', 'F32'],
                    'imp_kWh': [4, 0x48, 2, 'kWh', 'F32'],
                    'exp_kWh': [4, 0x4A, 2, 'kWh', 'F32'],
                    'power': [4, 0x34, 2, 'W', 'F32'],
                    'L1A': [4, 0x6, 2, 'A', 'F32'],
                    'L2A': [4, 0x8, 2, 'A', 'F32'],
                    'L3A': [4, 0xA, 2, 'A', 'F32'],
                    'L1V': [4, 0x0, 2, 'V', 'F32'],
                    'L2V': [4, 0x2, 2, 'V', 'F32'],
                    'L3V': [4, 0x4, 2, 'V', 'F32'],
                    'Totpf': [4, 0x3E, 2, '', 'F32'],
                    'TotHz': [4, 0x46, 2, 'Hz', 'F32'],
                    'serial_no': [3, 0xFC00, 2, '(integer)', 'U32'],
                    'serial_no_bin': [3, 0xFC00, 2, '(binary)', 'bin'],
                    'serial_no_hex': [3, 0xFC00, 2, '(hex)', 'hex'],
                    'baudrate': [3, 0x1C, 2, '(integer)', 'F32'],
                    'set_baudrate': [16, 0x1C, 2, '', 'F32'],
                    'unit_id': [3, 0x14, 2, '(modbus id/address)', 'F32'],
                    'set_unit_id': [16, 0x14, 2, '', 'F32'],
                    },
                'EM115': {
                    'kWh': [4, 0x16A, 2, 'kWh', 'F32'],
                    'imp_kWh': [4, 0x160, 2, 'kWh', 'F32'],
                    'exp_kWh': [4, 0x166, 2, 'kWh', 'F32'],
                    'power': [4, 0x8, 2, 'W', 'F32'],
                    'L1A': [4, 0x6, 2, 'A', 'F32'],
                    'L2A': [4, 0x0, 2, 'A', 'F32'],
                    'L3A': [4, 0x0, 2, 'A', 'F32'],
                    'L1V': [4, 0x2, 2, 'V', 'F32'],
                    'L2V': [4, 0x0, 2, 'V', 'F32'],
                    'L3V': [4, 0x0, 2, 'V', 'F32'],
                    'Totpf': [4, 0xE, 2, '', 'F32'],
                    'TotHz': [4, 0x4, 2, 'Hz', 'F32'],
                    'serial_no': [4, 0xFF00, 2, '(integer)', 'U32'],
                    'serial_no_bin': [4, 0xFF00, 2, '(binary)', 'bin'],
                    'serial_no_hex': [4, 0xFF00, 2, '(hex)', 'hex'],
                    'set_serial_no': [16, 0xFF00, 2, '', 'U32'],
                    'relay_state': [4, 0x566, 1, '(01..=on, 10..=off)', 'bin'],
                    'set_relay_state': [16, 0x566, 2, '', ''],
                    'baudrate': [4, 0x525, 1, '(integer)', 'U16'],
                    'set_baudrate': [16, 0x525, 1, '', ''],
                    'unit_id': [4, 0x524, 1, '(modbus id/address)', 'U16'],
                    'set_unit_id': [16, 0x524, 1, '', ''],
                     }, 
                'EM737': {
                    'kWh': [4, 0x700, 2, 'kWh', 'F32'],
                    'imp_kWh': [4, 0x800, 2, 'kWh', 'F32'],
                    'exp_kWh': [4, 0x900, 2, 'kWh', 'F32'],
                    'power': [4, 0x26, 2, 'W', 'F32'],
                    'L1A': [4, 0x16, 2, 'A', 'F32'],
                    'L2A': [4, 0x18, 2, 'A', 'F32'],
                    'L3A': [4, 0x1A, 2, 'A', 'F32'],
                    'L1V': [4, 0x10, 2, 'V', 'F32'],
                    'L2V': [4, 0x12, 2, 'V', 'F32'],
                    'L3V': [4, 0x14, 2, 'V', 'F32'],
                    'Totpf': [4, 0x3E, 2, '', 'F32'],
                    'TotHz': [4, 0x40, 2, 'Hz', 'F32'],
                    'serial_no': [4, 0xFF00, 2, '(integer)', 'U32'],
                    'serial_no_bin': [4, 0xFF00, 2, '(binary)', 'bin'],
                    'serial_no_hex': [4, 0xFF00, 2, '(hex)', 'hex'],
                    'set_serial_no': [16, 0xFF00, 2, '', 'U32'],
                    'relay_state': [4, 0x566, 1, '(01..=on, 10..=off)', 'bin'],
                    'set_relay_state': [16, 0x566, 2, '', ''],
                    'baudrate': [4, 0x525, 1, '(integer)', 'U16'],
                    'set_baudrate': [16, 0x525, 1, '', ''],
                    'unit_id': [3, 0x524, 1, '(modbus id/address)', 'U16'],
                    'set_unit_id': [16, 0x524, 1, '', ''],
                    }
                }

    mregs = meter_regs[args.meter_model]
    if register_name not in mregs:
        info_text = 'Not supported for this model'
        value = None
    else:
        function_code, address, count, info_text, data_type = mregs[register_name]
        if function_code == 3:
            res = client.read_holding_registers(address, count, unit_id)
        elif function_code == 4:
            res = client.read_input_registers(address, count, unit_id)
        elif function_code == 16:
            if not payload:
                print(f'ERROR missing payload for {register_name}\nExiting!', sys.stderr)
                sys.exit(1)
            if data_type:
                if data_type == 'F32':
                    payload = reverse_ieee754(payload)
                elif data_type == 'U32':
                    payload = reverse_u32(payload)
                else:
                    print(f'ERROR data type for {register_name} using {function_code} is not supported. '
                          f'Please check the script.\nExiting!', sys.stderr)
                    sys.exit(1)
            res = client.write_registers(address, payload, unit_id)
        else:
            print('ERROR: Unsupported function code. This should not be happening '
                  '(check that all function codes are supported in the script).\nExiting!', file=sys.stderr)
            sys.exit(1)
        if res.isError():
            print(f'ERROR: We got an error back when requesting {register_name}:')
            if hasattr(res, 'encode'):
                print('res.encode(): %s' % res.encode())
            if hasattr(res, 'function_code'):
                print("Function code: %s" % res.function_code)
            if hasattr(res, 'string'):
                print("Error string: %s" % res.string)
            print('Exiting!')
            sys.exit(1)
        regs = res.registers
        if regs:
            if data_type == 'F32':
                value = ieee754(regs)
            elif data_type == 'U32':
                value = u32(regs)
            elif data_type == 'U16':
                value = u16(regs)
            elif data_type == 'bin':
                value = binary(regs)
            elif data_type == 'hex':
                value = hex_str(regs)
            elif data_type == '':
                value = None
            else:
                print('ERROR: Response type not supported. This should not be happening '
                      '(check that all response types are supported in the script).\nExiting!', file=sys.stderr)
                sys.exit(1)
        else:
            value = None
    return {'value': value, 'info_text': info_text}


def modbus_req_alot(args, client=None, printout=False):
    """Fetch a lot bunch of registers. Used for "curious mode" where we fetch a bunch of registers if available"""
    reg_names = ['kWh', 'imp_kWh', 'power', 'L1A', 'L2A', 'L3A', 'L1V', 'L2V', 'L3V', 'Totpf', 'TotHz',
                 'serial_no', 'serial_no_bin', 'serial_no_hex', 'relay_state']
    result = []
    for register_name in reg_names:
        reading = modbus_req(args, register_name, client=client)
        result.append(reading)
        if printout:
            if reading['value'] is not None:
                print(f'{register_name}: {reading["value"]} {reading["info_text"]}')
    return result


def get_relay_state(args, client=None):
    # Get relay state
    reading = modbus_req(args, 'relay_state', client=client)
    value = reading['value']
    if value not in ['1010101010101010', '0101010101010101']:
        print(f'ERROR the current relay state is "{value}". '
              f'I do not know how to interpret that\nExiting!', file=sys.stderr)
        sys.exit(1)
    cur_state = ['on' if value == '0101010101010101' else 'off'][0]
    return cur_state


def modbus_relay(args, client=None):
    """Check and change the relay state of a meter. If set_state is not set, then the relay state is not altered."""
    set_state = args.set_relay
    # Support for state as an integer
    if set_state in [0, '0']:
        set_state = 'off'
    if set_state in [1, '1']:
        set_state = 'on'

    # Basic check of meter model
    if args.meter_model[:2] != 'EM':
        print(f'ERROR reading and setting relay state is not supported for '
              f'meter model: {args.meter_model}\nExiting!', file=sys.stderr)
        sys.exit(1)

    # Check if we can work with the relay state variable
    if set_state not in [None, 'on', 'off', 'auto']:
        print(f'ERROR relay_state() called with relay state "{set_state}" '
              f'which is not supported!\nExiting!', file=sys.stderr)
        sys.exit(1)

    # Get relay state
    cur_state = get_relay_state(args, client=client)
    if set_state == cur_state:
        # There is really not much for us to do here...
        print(f'Relay state is already: {cur_state}')
        return cur_state
    print(f'Current relay state is: {cur_state}')

    # Get serial
    reading = modbus_req(args, 'serial_no', client=client)
    serial_no = reading['value']
    print(f'The meter has serial number: {serial_no}')

    # Calculate key
    key = fineco_generate_key(serial_no)
    print(f'Calculated "key" based on s/n: {key}')

    # If this is a "read only" run
    if not set_state:
        return set_state

    # Set relay state
    print(f'Setting relay state to: {set_state}')
    state_value_dict = {'on': 21845, 'off': 43690, 'auto': 34952}
    state_value = state_value_dict[set_state]
    reading = modbus_req(args, 'set_relay_state', client=client, payload=[key, state_value])

    # Get and confirm relay state
    cur_state = get_relay_state(args, client=client)
    print(f'Current relay state is: {cur_state}')
    if not cur_state == set_state:
        print('WARNING it seems the relay state was not changed as we expected. We failed. Sorry...')

    return cur_state


def voltage_test(args, client=None):
    """Read the voltage and complain if it is outside boundries"""
    print(f'\nTrying to get voltage from meter model {args.meter_model} with unit id {args.unit_id} \n')
    reading = modbus_req(args, 'L1V', client=client)
    voltage = reading['value']
    print('Voltage is %.1f V' % voltage, end=' ')
    # a tolerance of 0.1 means +/- 10%
    tolerance = 0.1 
    if 115*(1-tolerance) < voltage < 115*(1+tolerance) and 230*(1-tolerance) < voltage < 230*(1+tolerance):
        voltage_ok = False
    else:
        voltage_ok = True
    if voltage_ok:
        print('which seems ok!\n')
    else:
        print('which seems out of range for 115/230 V +/- 10%')
        print('Did you configure the right meter model?')
        print('Exiting!')
        sys.exit(1)


def modbus_baudrate(args, client=None, read_only=None):
    """Read or write the configured baudrate of the meter"""
    assert args.set_baudrate in [None, '1200', '2400', '4800', '9600', '19200', '38400']
    if args.meter_model[:2] == 'EM':
        # Seems like a Fineco meter
        meter_brand = 'Fineco'
    elif args.meter_model[:3] == 'SDM':
        # Seems like a Fineco meter
        meter_brand = 'Eastron'
    else:
        print(f'ERROR Baudrate settings for meter model {args.meter_model} '
              f'is not supported in this script.\nExiting!', file=sys.stderr)
        sys.exit(1)
    
    # Fetch the raw value
    reading = modbus_req(args, 'baudrate', client=client)
    value = reading['value']

    # For Eastron meters the value must be mapped
    if meter_brand == 'Eastron':
        baudrate_dict = {0: 2400, 1: 4800, 2: 9600, 3: 19200, 4: 38400, 5: 1200}
        # For eastron the result is a float, so lets convert it to an int
        value = int(value)
        # Check if we like the result
        if value not in baudrate_dict.keys():
            print(f'ERROR we got the value {value} which is not something we can map to a baudrate. '
                  f'It must be one of the following values: {baudrate_dict.keys()}\nExiting!', file=sys.stderr)
            sys.exit(1)
        # Map the value to a baudrate
        baudrate = baudrate_dict[value]

    # Fineco
    elif meter_brand == 'Fineco':
        baudrate = value

    print(f'The meter reports a baudrate of: {baudrate}')

    if read_only or not args.set_baudrate:
        return baudrate, client
    else:
        # Set the new baudrate
        new_baudrate = int(args.set_baudrate)
        if meter_brand == 'Eastron':
            new_value = list(baudrate_dict.keys())[list(baudrate_dict.values()).index(new_baudrate)]
        elif meter_brand == 'Fineco':
            new_value = new_baudrate
        print('OBS remember to put the meter into "set" mode!')
        print(f'Setting the baudrate to {new_baudrate}')
        reading = modbus_req(args, 'set_baudrate', payload=new_value, client=client)
        # Close the current connection and open a new
        # (only if it is a serial connection, for modbus gateways the setting on the gateway must be changed
        if not args.serial_port:
            print('OBS: Since you are not communicating with the meter directly via a serial connection, '
                  'then we can not validate that the setting is in effect. '
                  'Please update the configuration of your modbus gateway to the new baudrate.')
        else:
            print('Checking that we can now communicate with the meter using the new baudrate')
            # Get the new baudrate and confirm
            client.close()
            # Let us sleep for a sec as a precaution for the meter to adapt to the new reality
            time.sleep(1)
            client = connect(args, new_baudrate)
            new_baudrate, client = modbus_baudrate(args, client=client, read_only=True)
        return new_baudrate, client


def modbus_unit_id(args, unit_id=None, client=None):
    """Read and write the configured unit id of the meter"""
    if not unit_id:
        unit_id = args.unit_id
    # Get the current unit id
    reading = modbus_req(args, 'unit_id', client=client, unit_id=unit_id)
    unit_id = int(reading['value'])
    print(f'The meter reports unit id: {unit_id}')
    if not args.set_unit_id:
        return unit_id

    # Note: In a perfect world we would check if the new unit id not used by anyone else,
    # however I have not found a foolproof way to check that
    #
    # Set the new modbus id
    print(f'Setting the unit id to: {args.set_unit_id}')
    reading = modbus_req(args, 'set_unit_id', payload=args.set_unit_id, client=client)
    # Check if the new modbus id is answering
    unit_id = modbus_unit_id(args, client=client, unit_id=args.set_unit_id)
    if not unit_id == args.set_unit_id:
        print('WARNING wait what? The new unit id does not match what we set (how could this have happened?)')
    return unit_id


def modbus_serial(args, client=None):
    """Get the configured serial number of the meter"""
    for register_name in ['serial_no', 'serial_no_bin', 'serial_no_hex']:
        reading = modbus_req(args, register_name, client=client)
        serial_no = reading['value']
        print(f'{register_name}: {serial_no} {reading["info_text"]}')
    if args.set_serial:
        if args.meter_model[:2] != 'EM':
            # It is not a Fineco meter
            print('ERROR it is only possible to change the serial number for Fineco meters.\nExiting!', file=sys.stderr)
            sys.exit(1)
        else:
            # It is a Fineco meter
            if args.set_serial[:2] == '0x':
                # Its hex
                new_serial_value = int(args.set_serial, 16)
            elif args.set_serial[:2] == '0b':
                new_serial_value = int(args.set_serial, 2)
            else:
                # It is neither hex nor binary, then it must be an integer
                new_serial_value = int(args.set_serial)
            # Set the serial number
            print(f'Setting the serial number to: {args.set_serial} / {new_serial_value} (int)')
            reading = modbus_req(args, 'set_serial_no', payload=new_serial_value, client=client)
            modbus_serial(args, client=client)
        
    return serial_no


def main():
    """ The main function """
    # Argument parsing
    parser = argparse.ArgumentParser(prog='energy_meter_setup_tool.py',
                                     description='Read and write to various modbus registers on Fineco energy meters. '
                                                 'E.g. Fineco EM115 DO DC. or Eastron meters (e.g. SDM120)')
    ch_group = parser.add_mutually_exclusive_group()
    dev_group = parser.add_mutually_exclusive_group()
    dev_group.add_argument('-p', '--serial-port', help='Serial port')
    dev_group.add_argument('--host', help='Hostname (if modbus gateway)')
    parser.add_argument('-b', '--baudrate', help='Serial baudrate to use when communicating with modbus rtu using a serial port', default=9600, type=int)
    parser.add_argument('--get-baudrate', help='Get configured serial baudrate of the meter', action='store_true')
    ch_group.add_argument('--set-baudrate', help='Set the serial baudrate', choices=['1200', '2400', '4800', '9600', '19200', '38400'])
    parser.add_argument('--tcp-port', help='Modbus gateway TCP port', default=502, type=int)
    parser.add_argument('-c', '--curious', help='Curious mode. Ask the meter about various registers', action='store_true')
    parser.add_argument('-m', '--meter-model', help='Meter model', choices=['EM115', 'EM737', 'SDM72', 'SDM120', 'SDM230', 'SDM630'], required=True)
    parser.add_argument('--get-relay', help='Get relay state', action='store_true')
    ch_group.add_argument('--set-relay', help='Set relay state', choices=['on', 'off', 'auto', '0', '1'], default=False)
    parser.add_argument('-u', '--unit-id', help='Modbus unit id to use (1-255). This is the "slave id" or "address" of the modbus slave', default='1', type=address_limit)
    parser.add_argument('--get-unit-id', help='Get configured unit id of the meter', action='store_true')
    ch_group.add_argument('--set-unit-id', help='Set modbus unit id (1-255)', type=address_limit, )
    parser.add_argument('--get-serial', help='Get configured serial number of the meter', action='store_true')
    ch_group.add_argument('--set-serial', help='Set serial number. Multiple types are supported: Integers (e.g. "1234"), hexadecimal (e.g. "0x4d2") and binary (e.g. "0b10011010010")', type=str)
    parser.add_argument('-t', '--timeout', help='Timeout in seconds', default=2, type=int)
    args = parser.parse_args()
    if not args.serial_port and not args.host:
        print("ERROR: at least one of the following arguments must be set: --serial-port or --host")
        sys.exit(1)

    print('Starting energy meter setup tool')

    # Connect
    client = connect(args)

    # Voltage test
    voltage_test(args, client=client)

    if args.curious:
        # Fetch some more registers
        readings = modbus_req_alot(args, client=client, printout=True)

    if args.get_relay or args.set_relay:
        state = modbus_relay(args, client=client)

    if args.get_baudrate or args.set_baudrate:
        baudrate, client = modbus_baudrate(args, client=client)

    if args.get_unit_id or args.set_unit_id:
        unit_id = modbus_unit_id(args, client=client)

    if args.get_serial or args.set_serial:
        modbus_serial(args, client=client)

    # Finishing up
    client.close()


if __name__ == '__main__':
    main()
