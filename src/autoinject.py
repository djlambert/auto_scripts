#!/usr/bin/python

################################################################################
# name: autoinject.py
# auth: korsnick
# date: 12/2010

import sys
import pexpect
import csv
import time
import datetime
#import pdb
 
################################################################################
# FUNCTIONS
def parse_config(filename):
    
    """ this function reads in the configuration settings for each machine to test """
    
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

    """add two hexadecimal string values and return as such"""
    
    result = hex(long(hex1, 16) + long(hex2, 16))
    
    # trim the stupid L off the end
    if result[-1] == 'L': result = result[:-1]
    
    return result

def comment(px, str):
    
    """This pretty prints comments into the logfile. It takes a pexpect object and comment string"""
    
    px.logfile.write('\n')
    px.logfile.write('/////////////////////////////////////////////////////////////////////////////////////////\n')
    px.logfile.write('/ %s\n' %str)
    px.logfile.write('/////////////////////////////////////////////////////////////////////////////////////////\n')
    return

def phboffset (baseaddress, phbnumber):
    
    """ adds correct phb offset to the hub's base address """
    
    if phbnumber == '0':  return hex_add(baseaddress, '0x080000')
    if phbnumber == '1':  return hex_add(baseaddress, '0x090000')
    if phbnumber == '2':  return hex_add(baseaddress, '0x0A0000')
    if phbnumber == '3':  return hex_add(baseaddress, '0x0B0000')
    if phbnumber == '4':  return hex_add(baseaddress, '0x0C0000')
    if phbnumber == '5':  return hex_add(baseaddress, '0x0D0000')

def execute(px, command):
    
    """ does the main work of getting a prompt and sending the commands """
    
    print '  -%s' %command
    if after_inject:
        comment(px, 'POST-INJECT / %s' %command)
    else:
        comment(px, 'PRE-INJECT / %s' %command)
    px.sendline(command)
     
    # getting this prompt can be flaky for some reason so loop unit we get it
    px.expect('phyp # ')
    while px.before.strip() == 'Could not parse a macro name':
        phyp.sendline(command)
        phyp.expect('phyp # ')
    
################################################################################
   
#pdb.set_trace()

# read in machine specific settings from the config file
print '\n* Reading config file'
cfg = parse_config(sys.argv[1])
#cfg = parse_config('/home/ppk/ibm/falcon/bfsp067/bfsp067.cfg')
#cfg = parse_config('/home/ppk/IBM/jupiter/jioc09a/jioc09a.cfg')j
#cfg = parse_config('/home/ppk/ibm/falcon/pfd3nb24/pfd3nb24.cfg')

# check LID version
print '* Checking LID version'
lid = parse_config('lid.log')

# has the inject happened yet
after_inject = False

# show config settings to user
print '* Current Settings:'
print '  -machine: %s' %cfg['machine']
print '  -lid: %s' %lid['lid']
print '  -hub: %s' %cfg['hubnumber']
print '  -phb: %s' %cfg['phbnumber']

# set up phyp tunnel
print '* Setting up tunnel'
vtty = pexpect.spawn('ssh -l %s %s vtty-fsp %s -timeout=0 -setuponly' %(cfg['user'], cfg['host'], cfg['machine']))
vtty.expect ('password: ')
vtty.sendline(cfg['password'])
fout_vtty = file('.vtty.log', 'w')
vtty.logfile = fout_vtty
vtty.expect(pexpect.EOF)
vtty.close()

# setup CSV file parser to read in each test case from listing file
inputFile = open(sys.argv[2], 'rb')
parser = csv.reader(inputFile)

# loop through each testcase in the listing file
# opening the connection needs to be inside the loop in case the CEC is rebooted (ala GXE's)
for to_be_run, case_name, is_phb, offset, bits in parser:

    # remove any whitespace
    to_be_run = to_be_run.strip()

    if to_be_run == '1':
        
        # clean up the rest
        case_name = case_name.strip()
        is_phb = is_phb.strip()
        offset = offset.strip()
        bits = bits.strip()
        address = cfg['hub_base_addr'].strip()
        
        print '* Running test case: %s' %case_name
        
        # connect to tunnel
        # all this crap is required because it's impossible to get a phyp prompt reliably
        i = 1
        while i == 1:
            print '* Telnetting to PHYP'
            phyp = pexpect.spawn('telnet %s 30002' %cfg['machine'], timeout=None)
            i = phyp.expect(['phyp # ', '0x0'])
            if i == 1:
                phyp.close()
                time.sleep(1)
        
        # record the input and output from the phyp session
        fout_phyp = file('./traces/%s' %case_name, 'w')
        phyp.logfile = fout_phyp
        
        # setup address and offsets 
        if is_phb == 'yes': address = phboffset(address, cfg['phbnumber'])
        address = (hex_add(address, offset)[2:]).zfill(16)
        
        # BEGIN
        phyp.logfile.write('/////////////////////////////////////////////////////////////////////////////////////////\n')
        phyp.logfile.write('/ TESTCASE: %s\n' %case_name)
        phyp.logfile.write('/ MACHINE: %s\n' %cfg['machine'])
        phyp.logfile.write('/ LID: %s\n' %lid['lid'])
        phyp.logfile.write('/ START: %s\n' %datetime.datetime.now())
        phyp.logfile.write('/////////////////////////////////////////////////////////////////////////////////////////\n')

        # start sending the commands to phyp
        print '* Sending commands'
        
        execute(phyp, 'xmfr')
        execute(phyp, 'xmdumptrace -hub %s -ctrl -detail 2' %cfg['hubnumber'])
        execute(phyp, 'xmdumptrace -b %s -detail 2' %cfg['phb_hex'])
        execute(phyp, 'xmdumpbuserrors %s' %cfg['bus_drc'])
        execute(phyp, 'xmdumpp7iocregs -hub all -lem')
        execute(phyp, 'xmquery -q allrio -d 2')
        execute(phyp, 'xmquery -q allslots -d 2')
        execute(phyp, 'xmquery -q allslots -d 1')
        
        # INJECT
        phyp.logfile.write('\n')
        phyp.logfile.write('/////////////////////////////////////////////////////////////////////////////////////////\n')
        phyp.logfile.write('/////////////////////////////////////////////////////////////////////////////////////////\n')
        execute(phyp,'xmwritememory %s %s' %(address, bits))
        time.sleep(10)
        after_inject = True
        phyp.logfile.write('\n')
        phyp.logfile.write('/////////////////////////////////////////////////////////////////////////////////////////\n')
        phyp.logfile.write('/////////////////////////////////////////////////////////////////////////////////////////\n')
        
        execute(phyp, 'xmdumptrace -hub %s -ctrl -detail 2' %cfg['hubnumber'])
        execute(phyp, 'xmdumptrace -b %s -detail 2' %cfg['phb_hex'])
        execute(phyp, 'xmdumpbuserrors %s' %cfg['bus_drc'])
        execute(phyp, 'xmdumpp7iocregs -hub all -lem')
        execute(phyp, 'xmquery -q allrio -d 2')
        execute(phyp, 'xmquery -q allslots -d 2')
        execute(phyp, 'xmquery -q allslots -d 1')
        execute(phyp, 'xmfr')

        phyp.close()

        # see if user wants to continue
        q = raw_input('Run next case, y/n? ')
        if q == 'n': break
        
