#!/usr/bin/python

import sys
import pexpect
import datetime

print '* Connecting to dumbo...'
shell = pexpect.spawn('ssh korsnick@dumbo.rchland.ibm.com')
shell.expect ('password: ')
shell.sendline('c0wboyss')
shell.expect('2.05b')
fout_shell = file('chksys.log', 'w')
shell.logfile = fout_shell

print '* Running lidupdate %s -chksys' %sys.argv[1]
shell.sendline('lidupdate %s -chksys' %sys.argv[1])
shell.expect('Lid directory   :')
f = open('lid.log', 'w')
f.write('timestamp = %s\n' %datetime.datetime.now())
print 'lid = %s' %shell.buffer
f.write('lid = %s\n' %shell.buffer)
f.close()

shell.close()


# this test runs when this code is used as a standalone program,
# but not as an imported module of another program,
# then the namespace will be apple (name of module) and not __main__
#if __name__ == '__main__':
