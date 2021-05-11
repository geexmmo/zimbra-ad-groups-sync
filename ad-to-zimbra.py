#!/usr/bin/env python
import adfunctions
import ldap, ldap.modlist
from settings import settings
from importlib import reload
import logging
reload(logging)
logger = logging.getLogger()
logging.basicConfig(filename='ad-to-zimbra.log', filemode='w', format='%(message)s')

conn = ldap.initialize('ldap://' + settings['ADserver'])
conn.protocol_version = 3
conn.set_option(ldap.OPT_REFERRALS, 0)
conn.simple_bind_s(settings['ADuser'], settings['ADpassword'])

grouplist = adfunctions.listADGroups(conn)
# looping trought groups from AD
for group in grouplist:
    grname = group[1].get('mail')[0].decode('utf-8')    
    # create group in zimbra
    logging.warning('cdl %s' % grname)
    # list group members
    memberslist = adfunctions.listADGroupMembers(conn, grname)
    if memberslist:
        for member in memberslist[0][1].get('member'):
            member = member.decode('utf-8')
            # get member email
            membermail = adfunctions.listADUserMail(conn, member)
            if membermail[0][1]:
                membermail = membermail[0][1].get('mail')[0].decode('utf-8')
                logging.warning('adlm %s %s' % (grname, membermail))
            else: pass # TODO log user in ad that has no 'mail' field
    else: pass # TODO log emty group in ad
    
conn.unbind_s()