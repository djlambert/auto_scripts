#!/usr/bin/python

###############################################################################
# name: atf_funcs.py
# auth: korsnick
# date: 2/2011
# desc: this is a collection of helper functions used by the Automated Test
#       Framework

def parse_config(filename):
    
    """ this function reads in the configuration
    settings for each machine to test """
    
    COMMENT_CHAR = '#'
    OPTION_CHAR =  '='
    options = {}
    f = open(filename)
    for line in f:
        # First, remove comments:
        if COMMENT_CHAR in line:
            # split on comment char, keep only the part before
            line, comment = line.split(COMMENT_CHAR, 1)
        # Second, find lines with an option=value:
        if OPTION_CHAR in line:
            # split on option char:
            option, value = line.split(OPTION_CHAR, 1)
            # strip spaces:
            option = option.strip()
            value = value.strip()
            # store in dictionary:
            options[option] = value
    f.close()
    return options


def hex_add(hex1, hex2):

    """Add two hexadecimal string values and return as such"""
    
    result = hex(long(hex1, 16) + long(hex2, 16))
    
    # trim the stupid L off the end
    if result[-1] == 'L': result = result[:-1]
    
    return result


def log_comment(px, str):
    
    """This pretty prints comments into the logfile.
    Takes a pexpect object and comment string"""
    
    px.logfile.write('\n')
    px.logfile.write('/////////////////////////////////////////////////////////////////////////////////////////\n')
    px.logfile.write('/ %s\n' %str)
    px.logfile.write('/////////////////////////////////////////////////////////////////////////////////////////\n')
    return


def phb_offset (baseaddress, phbnumber):
    
    """ adds correct phb offset to the hub's base address """
    
    if phbnumber == '0':  return hex_add(baseaddress, '0x080000')
    if phbnumber == '1':  return hex_add(baseaddress, '0x090000')
    if phbnumber == '2':  return hex_add(baseaddress, '0x0A0000')
    if phbnumber == '3':  return hex_add(baseaddress, '0x0B0000')
    if phbnumber == '4':  return hex_add(baseaddress, '0x0C0000')
    if phbnumber == '5':  return hex_add(baseaddress, '0x0D0000')
    
    
def clear_srcs (px_fsp):
    
    """ Clears all SRCs on the FSP. Pass it the pexpect object connected
    to the FSP you want to clear. """
    
    px_fsp.sendline('errl --purge')
    px_fsp.expect('$')
    