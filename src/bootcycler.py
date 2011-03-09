#!/usr/bin/python
###############################################################################
# name: bootcycler.py
# auth: korsnick
# date: 1/18/2011

import sys
import pexpect
import time
import datetime
#import pdb


###############################################################################
# FUNCTIONS

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


def comment (px, str):
    
    """This pretty prints comments into the logfile.
    It takes a pexpect object and comment string"""

    px.logfile.write('\n')
    px.logfile.write('///////////////////////////////////////////////////////////////////////////////\n')
    px.logfile.write('/ %s / %s\n' %(datetime.datetime.now(), str))
    px.logfile.write('///////////////////////////////////////////////////////////////////////////////\n')
    return
    
###############################################################################

# read in machine specific settings from the config file
#cfg = parse_config(sys.argv[1])
print 'Reading config file...'
cfg = parse_config('/home/ppk/IBM/jupiter/bootcycler/bootcycler.cfg')

# connect to FSP
print 'Connecting to FSP %s...' %cfg['machine']
fsp = pexpect.spawn('telnet %s' %cfg['machine'], timeout=None)
fout_fsp = file('fsp.log', 'w')
fsp.logfile = fout_fsp
fsp.expect('jioc09a login: ')
fsp.sendline('root')
fsp.expect('Password: ')
fsp.sendline('FipSroot')
fsp.expect(cfg['fsp_prompt'])

# main cycle
run = 1
while (True):
    
    # query the state of the machine
    fsp.sendline('smgr mfgState')
    state = fsp.expect(['standby', 'ipling', 'runtime', 'powering off'])
    
    if state == 0:  # standby
        print 'Run %s: FSP in standby.' %run
        # boot up
        print 'Run %s: booting...' %run
        comment(fsp, 'MESSAGE / Run %s: booting up...' %run )
        fsp.sendline('istep')
        fsp.expect(cfg['fsp_prompt'])
        
    elif state == 1:    # ipling
        print 'Run %s: ipling...' %run
        time.sleep(10)
        
    elif state == 2:    # runtime
        print 'Run %s: FSP in runtime.' %run
        
        # set up tunnel
        print 'Run %s: setting up tunnel...' %run
        vtty = pexpect.spawn('ssh -l %s %s vtty-fsp %s -timeout=0 -setuponly'
                             %(cfg['user'], cfg['host'], cfg['machine']),
                             timeout=None)
        fout_vtty = file('vtty.log', 'a')
        vtty.logfile = fout_vtty
        vtty.expect ('password: ')
        vtty.sendline(cfg['password'])
        comment (vtty, 'MESSAGE / Run %s: setting up phyp tunnel...' %run)
        vtty.expect(pexpect.EOF)
        vtty.close()
        
        # connect to tunnel
        # all this crap is required because it's impossible
        # to get a phyp prompt reliably
        i = 1
        while i == 1:
            print 'Run %s: connecting to PHYP...' %run
            phyp = pexpect.spawn('telnet %s 30002' %cfg['machine'],
                                 timeout=None)
            fout_phyp = file('phyp.log', 'a')
            phyp.logfile = fout_phyp
            i = phyp.expect(['phyp # ', '0x0'])
            if i == 1:
                phyp.close()
                time.sleep(1)
        
        # wait for the partition to boot
        print 'Run %s: waiting for partition to boot...' %run
        ping = pexpect.spawn('ping %s' %cfg['partition'],
                             timeout=None)
        ping.expect('time=')
        ping.close()
        
        print 'Run %s: partition is pinging now...' %run
        time.sleep(30)  # wait a bit more
        
        # ok, it's booted now
        print 'Run %s: partition is up, grabbing xmfr...' %run
        comment(phyp, 'MESSAGE / Run %s' %run)
        phyp.sendline('xmfr')
        phyp.expect('phyp # ')
        phyp.close()
        
        # ok got the data, reboot the machine
        print 'Run %s: rebooting machine...' %run
        comment(fsp, 'MESSAGE / Run %s: rebooting machine...' %run)
        fsp.sendline('plckIPLRequest 0xA08')
        fsp.expect(cfg['fsp_prompt'])

        run += 1

    elif state == 3:    # powering off
        print 'FSP is powering off...'
        time.sleep(40)
        
    