#!/usr/bin/env python
from settings import settings
import adfunctions
import ldap, ldap.modlist
import re
import logging

from importlib import reload
reload(logging)
logger = logging.getLogger()
logging.basicConfig(filename='zimbra-to-ad.log', filemode='w', format='%(name)s - %(levelname)s - %(message)s')

distGrpData = {}
distGrpCount = len(distGrpData)


# sould match start of new section in dump file
def matchDistGrp(line):
    regexDistGrp = '(?<=^#\sdistributionList\s).+(?=\smemberCount)'
    match = re.search(regexDistGrp, line)
    if match:
        # accessing global data structures
        global distGrpCount
        # updating counter if new group found
        distGrpCount = len(distGrpData)
        # data insertion
        distGrpData[distGrpCount] = {'GroupName': match.group()}
        # distGrpData initiated so here is empty list so I can add Members here later
        distGrpData[distGrpCount]['Members'] = []

    # tries to match email of dist group
    regexDistGrpEmail = '(?<=mail:\s)\S{1,}@\S{2,}\.\S{2,}$'
    match = re.search(regexDistGrpEmail, line)
    if match:
        distGrpData[distGrpCount]['GroupEmail'] = match.group()

    #tries to match 'displayName' of dist group
    regexCN = '(?<=^displayName:\s)[\w\s\d]+$'
    match = re.search(regexCN, line)
    if match:
        distGrpData[distGrpCount]['displayName'] = match.group()

    # tries to match email of member in dist group
    regexMemberMail = '^\S{1,}@\S{2,}\.\S{2,}$'
    match = re.search(regexMemberMail, line)
    if match:
        # appends data to list
        distGrpData[distGrpCount]['Members'].append(match.group())


def memberCheck(conn, member, group):
    # check if member is from managed domain name
    regexMemberCheck = settings['regexMemberCheck']
    match = re.search(regexMemberCheck, member)
    if match:
        if adfunctions.searchADUserExists(conn, member) is True and adfunctions.searchADMembership(conn, member, group) is False:
            return True
        else:
            logging.info('User exists and is in group already or disabled u: %s (g: %s)', member, group)
            return False
    else:
        logging.warning('Member email is not from allowed domain: u: %s d: %s', member, regexMemberCheck)
        return False

# opens file and loops trough lines
with open(settings['ZimbraDumpFile'], 'r') as textfile:
    for line in textfile:
        line = line.strip()
        matchDistGrp(line)


conn = ldap.initialize('ldap://' + settings['ADserver'])
conn.protocol_version = 3
conn.set_option(ldap.OPT_REFERRALS, 0)
conn.simple_bind_s(settings['ADuser'], settings['ADpassword'])

for i in distGrpData:
    if distGrpData[i].get('Members'):
        grname = distGrpData[i].get('GroupName')
        grdispname = distGrpData[i].get('displayName')
        members = distGrpData[i].get('Members')
        gremail = distGrpData[i].get('GroupEmail')
        if not grdispname:
            logging.warning('Group with no displayName, defaulting (g: %s)', grname)
            grdispname = 'REnameME'
        if grname and not adfunctions.searchADGroupExists(conn, grname):
            adfunctions.addADGroup(conn, grname,gremail,grdispname)
        for member in members:
            if memberCheck(conn, member, grname):
                logging.info('Adding %s to %s', member, grname)
                adfunctions.addADMembership(conn, member, grname)
    else:
        # TODO log group with no members and skip it
        logging.warning('Group in Zimbra dump with empty member list  %s, skipping', distGrpData[i])
        pass
    

# kill AD connection to free some memory 
conn.unbind_s()