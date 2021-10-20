# #!/usr/bin/env python
import sqlite3
import adfunctions
import ldap, ldap.modlist
from settings import settings
from importlib import reload
from sqlitecmd import SqliteCreateGroup, SqliteAddMember, SqliteCreateTables
import logging
reload(logging)
logger = logging.getLogger()
logging.basicConfig(format='%(message)s')
logger.setLevel(logging.INFO)

def RunAdToZimbra():
    sqlitecon = sqlite3.connect('db.sqlite')
    SqliteCreateTables(sqlitecon, 'ad')

    conn = ldap.initialize('ldap://' + settings['ADserver'])
    conn.protocol_version = 3
    conn.set_option(ldap.OPT_REFERRALS, 0)
    conn.simple_bind_s(settings['ADuser'], settings['ADpassword'])

    grouplist = adfunctions.listADGroups(conn)
    # looping trought groups from AD
    for group in grouplist:
        grname = group[1].get('mail')[0].decode('utf-8')    
        # create group in zimbra
        logging.info('AD lookup found list %s' % grname)
        # write group to database
        SqliteCreateGroup(grname, sqlitecon, 'ad')
        # list group members
        memberslist = adfunctions.listADGroupMembers(conn, grname)
        if memberslist:
            for member in memberslist[0][1].get('member'):
                member = member.decode('utf-8')
                # get member email
                membermail = adfunctions.listADUserMail(conn, member)
                if membermail[0][1]:
                    membermail = membermail[0][1].get('mail')[0].decode('utf-8')
                    # individual member logging
                    # logging.info('AD found adlm %s %s' % (grname, membermail))
                    # write member to database
                    SqliteAddMember(grname, membermail, sqlitecon, 'ad')
                else: pass # TODO log user in ad that has no 'mail' field
        else: pass # TODO log emty group in ad
    logging.info('AD parsing done...')
    conn.unbind_s()
    sqlitecon.close()