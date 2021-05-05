#!/usr/bin/env python
from settings import settings
import re

distGrpData = {}
distGrpCount = len(distGrpData)

# sould match start of new section in dump file
def matchDistGrp(line):
    regexDistGrp = '(?<=^#\sstartNewlist:\s)[\w\s\d]+(?=\smembers)'
    match = re.search(regexDistGrp, line)
    if match:
        # accessing variables and structures
        global distGrpCount
        # updating counter if new group found
        distGrpCount = len(distGrpData)
        print('Processing group', match.group())
        # data insertion
        distGrpData[distGrpCount] = {'GroupName': match.group()}
        # distGrpData initiated so here is empty list so I can add Members here later
        distGrpData[distGrpCount]['Members'] = []

    # tries to match email of dist group
    regexDistGrpEmail = '(?<=\w\W\s)\S{1,}@\S{2,}\.\S{2,}$'
    match = re.search(regexDistGrpEmail, line)
    if match:
        print(match.group())
        distGrpData[distGrpCount]['GroupEmail'] = match.group()

    # tries to match 'cn' of dist group
    regexCN = '(?<=^cn:\s)[\w\s\d]+$'
    match = re.search(regexCN, line)
    if match:
        distGrpData[distGrpCount]['CN'] = match.group()

    # tries to match email of member in dist group
    regexMemberMail = '^\S{1,}@\S{2,}\.\S{2,}$'
    match = re.search(regexMemberMail, line)
    if match:
        # appends data to list
        distGrpData[distGrpCount]['Members'].append(match.group())

def memberCheck(member):
    # check if member is from managed domain name
    regexMemberCheck = '^\S+@(dcb.kg|doscredobank.kg)$'
    match = re.search(regexMemberCheck, member)
    if match:
        return True
    else:
        # TODO log this error
        pass

# opens file and loops trough lines
print(settings['ZimbraDumpFile'])
with open(settings['ZimbraDumpFile'], 'r') as textfile:
    for line in textfile:
        line = line.strip()
        matchDistGrp(line)

# distGrpData is the result of previous loop and it has following structure:
# {0: {'GroupName': 'name1', 'Members': ['e@mail'], 'CN': 'cn1', 'GroupEmail': 'gr1@emai.l'},
# {1: {'GroupName': 'name2', 'Members': ['e@mail'], 'CN': 'cn2', 'GroupEmail': 'gr2@emai.l'},

for i in distGrpData:
    grname = distGrpData[i].get('GroupName')
    # AD GROUP - search and create if not exist
    # TODO
    if grname:
        print('Creating group: ', grname)
    members = distGrpData[i].get('Members')
    for member in members:
        # AD GROUP - fetch user and membership and take appropriate action
        # TODO
        if memberCheck(member):
            print('adding user: ', member, 'to: ', grname)