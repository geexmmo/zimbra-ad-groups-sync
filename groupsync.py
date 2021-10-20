import sqlite3
from settings import settings
from zimbracmd import ZimbraImportDLs
from sqlitecmd import SqliteCreateTables, SqliteCreateGroup, SqliteGetGroupId, SqliteAddMember, SqliteListAllGroups, SqliteListGroupMembers
from sqlitecmd import SqliteListAllGroups, SqliteDeleteMember, SqliteDeleteGroup
from zimbracmd import ZimbraCreateGroup, ZimbraAddMailboxToGroup, ZimbraDeleteMember, ZimbraDeleteDL
from adtozimbra import RunAdToZimbra
import argparse
import sys
import logging
from importlib import reload

reload(logging)
logger = logging.getLogger()
logging.basicConfig(format='%(message)s')
logger.setLevel(logging.INFO)

sqlitecon = sqlite3.connect('db.sqlite')

parser = argparse.ArgumentParser(description="setting script flags")
parser.add_argument(
"-zm",
"--zm",
action='store_true',
default=False,
help="resync zm list state to database (long process for about 5m for 60~ lists)",
)
args = parser.parse_args()
if args.zm:
    logging.info('got --zm, parsing zm lists')
    # making sql database for zimbra
    SqliteCreateTables(sqlitecon, 'zm')
    # looping trough result of ZimbraImportDLs() to populate database
    dlistdict = ZimbraImportDLs()
    for dlist in dlistdict:
        SqliteCreateGroup(dlist, sqlitecon, 'zm')
        logging.info('zm dlist to db: {}'.format(dlist))
        for mbox in dlistdict[dlist][0]:
            SqliteAddMember(dlist, mbox, sqlitecon, 'zm')
            logging.info('zm mbox to db: {} dlist: {}'.format(mbox, dlist))
# at this point we got 2 databases one from zimbra and one from ad (from `import adtozimbra`)
# got to compare them of what ad thinks it truth and modify zimbras database accordingly
try: 
    zmGroups = SqliteListAllGroups(sqlitecon, 'zm')
    RunAdToZimbra()
    adGroups = SqliteListAllGroups(sqlitecon, 'ad')
except:
    logging.error('Exiting on error, no zm database?')
    sys.exit(1)
#
# ad to zm
# got AD group and member luist
# looping through ad groups to check if same groups exist in zm
# |---if not - creating groups and populating them with users from ad
# |---if group exists in zm | looping trough its users
#                           |--- if zm group user not exists in ad group - removing users from zm 
#                           |--- if ad group user not exists in zm group - adding user to zm
#                           |--- if zm group user exists in ad group - do nothing
finalcmd = []
for group in adGroups:
    adid, adgroupname = group
    admembers = SqliteListGroupMembers(adid, sqlitecon, 'ad')
    zmid = SqliteGetGroupId(adgroupname, sqlitecon, 'zm')
    if adgroupname not in settings['IgnoredGroups']:
        # group exists in zm and ad, check if members matching up
        # zmid will be False if not
        if zmid:
            # members from zm in group `adgroupname` are here
            zmmembers = SqliteListGroupMembers(zmid, sqlitecon, 'zm')
            for membermail in zmmembers:
                # member in zm but not in ad
                # TODO: members should by synced in sqlite also to avoid long parses of zimprov
                if membermail not in admembers:
                    logging.info('{} should be deleted from {}'.format(membermail, adgroupname))
                    finalcmd.append(ZimbraDeleteMember(adgroupname, membermail))
                    SqliteDeleteMember(adgroupname,membermail,sqlitecon,'zm')
            for membermail in admembers:
                if membermail not in zmmembers:
                    logging.info('{} not in zm, adding to {}'.format(membermail, adgroupname))
                    finalcmd.append(ZimbraAddMailboxToGroup(adgroupname, membermail))
                    SqliteAddMember(adgroupname,membermail,sqlitecon,'zm')
        else:
            logging.info('{} does not exist in zm, creating from ad'.format(adgroupname))
            finalcmd.append(ZimbraCreateGroup(adgroupname))
            SqliteCreateGroup(adgroupname, sqlitecon,'zm')
            for membermail in admembers:
                finalcmd.append(ZimbraAddMailboxToGroup(adgroupname, membermail))
                SqliteAddMember(adgroupname,membermail,sqlitecon,'zm')
    else:
        logging.info('group {} ignored as it is in IgnoreList'.format(adgroupname))

#
# zm to ad check
# if groups exist in zimbra but not ad - they gets removed
for group in zmGroups:
    zmid, zmgroupname = group
    adid = SqliteGetGroupId(zmgroupname, sqlitecon, 'ad')
    if adid:
        pass
    else:
        logging.warning('group {} does not exist in ad, removing...'.format(zmgroupname))
        finalcmd.append(ZimbraDeleteDL(zmgroupname))
        SqliteDeleteGroup(zmgroupname,sqlitecon,'zm')

sqlitecon.close()
# Outputs zimbra batch commands to file for further execution
textfile = open(settings['ZimbraDumpFile'], "w")
for element in finalcmd:
    textfile.write(element + "\n")
textfile.close()