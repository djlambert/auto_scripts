#!/usr/bin/python

###############################################################################
# name: switch_inject.py
# auth: korsnick
# date: 03/2011

import sys
import pexpect
import csv
import time
import datetime
#import pdb
 
from atf_funcs import *
 
###############################################################################
# FUNCTIONS
def phyp_cmd(px, command):
    
    """ Does the main work of getting a prompt and sending the commands.
    Takes a pexpect object and a command string to send."""
    
    print '  -%s' %command
    #if after_inject:
    #    log_comment(px, 'POST-INJECT / %s' %command)
    #else:
    #    log_comment(px, 'PRE-INJECT / %s' %command)
    px.sendline(command)
     
    # getting this prompt can be flaky for some reason so loop unit we get it
    px.expect('phyp # ')
    while px.before.strip() == 'Could not parse a macro name':
        phyp.sendline(command)
        phyp.expect('phyp # ')


def get_srcs(px):
    px.sendline('errl -l ')
    
###############################################################################
   
#pdb.set_trace()

# read in machine specific settings from the config file
print '\n* Reading config file'
#cfg = parse_config(sys.argv[1])
#cfg = parse_config('/home/ppk/ibm/falcon/bfsp067/bfsp067.cfg')
#cfg = parse_config('/home/ppk/IBM/jupiter/jioc09a/jioc09a.cfg')j
cfg = parse_config('/home/ppk/ibm/testing/falcon/pfd3nb17/pfd3nb17.cfg')

# check LID version
#print '* Checking LID version'
#lid = parse_config('lid.log')

# has the inject happened yet
#after_inject = False

# show config settings to user
print '* Current Settings:'
print '  -machine: %s' %cfg['machine']
#print '  -lid: %s' %lid['lid']
#print '  -hub: %s' %cfg['hubnumber']
#print '  -phb: %s' %cfg['phbnumber']

# connect to FSP
print '* Connecting to FSP %s' %cfg['machine']
fsp = pexpect.spawn('telnet %s' %cfg['machine'], timeout=None)
fout_fsp = file('./logs/fsp.log', 'w')
fsp.logfile = fout_fsp
fsp.expect('login: ')
fsp.sendline('root')
fsp.expect('Password: ')
fsp.sendline('FipSroot')
fsp.expect(cfg['fsp_prompt'])

# set up PHYP tunnel
print '* Setting up PHYP tunnel'
vtty = pexpect.spawn('ssh -l %s %s vtty-fsp %s -timeout=0 -setuponly'
                     %(cfg['user'], cfg['aix'], cfg['machine']), timeout=None)
vtty.expect ('password: ')
vtty.sendline(cfg['password'])
fout_vtty = file('./logs/vtty.log', 'w')
vtty.logfile = fout_vtty
vtty.expect(pexpect.EOF)
vtty.close()

# connect to an AIX machine (like dumbo)
print '* Connecting to %s' %cfg['aix']
aixbox = pexpect.spawn('telnet %s' %cfg['aix'], timeout=None)
fout_aixbox = file('./logs/aix.log', 'w')
aixbox.logfile = fout_aixbox
aixbox.expect('login: ')
aixbox.sendline(cfg['user'])
aixbox.expect('Password: ')
aixbox.sendline(cfg['password'])
aixbox.expect(cfg['aix_prompt'])


# setup CSV file parser to read in each test case from listing file
#inputFile = open(sys.argv[2], 'rb')
inputFile = open('/home/ppk/ibm/testing/falcon/pfd3nb17/switch/switchcases.csv', 'rb')
parser = csv.reader(inputFile)

# loop through each testcase in the listing file
# opening the connection needs to be inside the loop in case the CEC is rebooted (ala GXE's)
for to_be_run, case_name, threshold, cmd in parser:

    # remove any whitespace
    to_be_run = to_be_run.strip()

    if to_be_run == '1':
        
        # clean up the rest
        case_name = case_name.strip()
        threshold = threshold.strip()
        cmd = cmd.strip()
        
        print '* Running test case: %s' %case_name
        
        # connect to tunnel
        # all this crap is required because it's impossible to get a phyp prompt reliably
        i = 1
        while i == 1:
            print '* Connecting to PHYP'
            phyp = pexpect.spawn('telnet %s 30002' %cfg['machine'], timeout=None)
            i = phyp.expect(['phyp # ', '0x0'])
            if i == 1:
                phyp.close()
                time.sleep(1)
        
        # record the input and output from the phyp session
        fout_phyp = file('./traces/%s' %case_name, 'w')
        phyp.logfile = fout_phyp
        
        # clear the SRCs before each test
        print '* Clearing SRCs'
        clear_srcs(fsp)
        
        # --- BEGIN ---
        phyp.logfile.write('/////////////////////////////////////////////////////////////////////////////////////////\n')
        phyp.logfile.write('/ TESTCASE: %s\n' %case_name)
        phyp.logfile.write('/ MACHINE: %s\n' %cfg['machine'])
        #phyp.logfile.write('/ LID: %s\n' %lid['lid'])
        phyp.logfile.write('/ THRESHOLD: %s\n' %threshold)
        phyp.logfile.write('/ START: %s\n' %datetime.datetime.now())
        phyp.logfile.write('/////////////////////////////////////////////////////////////////////////////////////////\n')

        # inject. repeat as necessary if there's a threshold
        for x in range(int(threshold)):
            print '* Inject #%s' %(x+1)
            phyp_cmd(phyp, cmd)
            time.sleep(5)

        print '* Collecting diagnostic data (takes a while)...'
        aixbox.sendline('sys_capture pfd3nb17.austin -fnmcmdfile /afs/rchland.ibm.com/usr7/xman/ftc/v7r3m0/falcon/test_istreams/capture_xm_diagnostic_data_v7r3.phyp -header -logfile /afs/rchland.ibm.com/usr7/xman/ftc/v7r3m0/falcon/actual_results/%s_xm_diagnostic_data' %case_name)
        aixbox.expect(cfg['aix_prompt'])

        print '* Collecting result data (takes a while)...'
        aixbox.sendline('sys_capture pfd3nb17.austin -fnmcmdfile /afs/rchland.ibm.com/usr7/xman/ftc/v7r3m0/falcon/test_istreams/capture_xm_switch_error_results_v7r3.phyp -header -logfile /afs/rchland.ibm.com/usr7/xman/ftc/v7r3m0/falcon/actual_results/%s_xm_switch_error_results' %case_name)
        aixbox.expect(cfg['aix_prompt'])

        print '* Collecting the error log (takes a while)...'
        aixbox.sendline('sys_capture pfd3nb17.austin -errl -header -logfile /afs/rchland.ibm.com/usr7/xman/ftc/v7r3m0/falcon/actual_results/%s_errl' %case_name)
        aixbox.expect(cfg['aix_prompt'])

        phyp.close()

        # see if user wants to continue
        q = raw_input('Run next case, y/n? ')
        if q == 'n': break

print '* Finished!'

# cleanup
aixbox.close()
fsp.close()