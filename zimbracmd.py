from subprocess import PIPE, run
import re
from settings import settings
import time

def ZimbraImportDLs():
    outlist = {}
    # this returns list addresses of all zimbra distrib lists
    starttime = int(time.time())
    out = run('zmprov gadl', stdout=PIPE, stderr=PIPE, shell=True).stdout.decode('utf-8').splitlines()
    for dlist in out:
        outlist[dlist] = []
        tmplist = []
        mboxes = run('zmprov gdl {} zimbraMailAlias zimbraMailForwardingAddress'.format(dlist), stdout=PIPE, stderr=PIPE, shell=True).stdout.decode('utf-8').splitlines()
        for mbox in mboxes:
            if int(time.time()) > starttime + 10:
                print('still running')
                starttime = int(time.time())
            regexDistGrp = '(?<=^zimbraMailForwardingAddress:\s).+'
            match = re.search(regexDistGrp, mbox)
            if match:
                tmplist.append(match.group())       
        outlist[dlist].append(tmplist)
    # returns "{'group@email': [['member@email', 'member2@email']],"
    return outlist

def ZimbraDeleteDL(dlist):
    out = ('ddl {}'.format(dlist))
    return out

def ZimbraDeleteMember(dlist, membermail):
    out = ('rdlm {} {}'.format(dlist, membermail))
    return out

def ZimbraCreateGroup(dlist):
    out = ('cdl {}'.format(dlist))
    return out

def ZimbraAddMailboxToGroup(dlist, membermail):
    out = ('adlm {} {}'.format(dlist, membermail))
    return out