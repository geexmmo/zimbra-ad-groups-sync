#!/usr/bin/env python
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
        distGrpData[distGrpCount] = {'MailList': match.group()}
        # distGrpData initiated so here is empty list so I can add members here later
        distGrpData[distGrpCount]['members'] = []

    # tries to match email of dist group
    regexDistGrpEmail = '(?<=\w\W\s)\S{1,}@\S{2,}\.\S{2,}$'
    match = re.search(regexDistGrpEmail, line)
    if match:
        print(match.group())
        distGrpData[distGrpCount]['ListEmail'] = match.group()

    # tries to match 'cn' of dist group
    regexCN = '(?<=^cn:\s)[\w\s\d]+$'
    match = re.search(regexCN, line)
    if match:
        distGrpData[distGrpCount]['CN'] = match.group()

    # tries to match email of member of dist group
    regexMemberMail = '^\S{1,}@\S{2,}\.\S{2,}$'
    match = re.search(regexMemberMail, line)
    if match:
        # appends data to list
        distGrpData[distGrpCount]['members'].append(match.group())

# opens file and loops trough lines
with open('zimbra-test.txt', 'r') as textfile:
    for line in textfile:
        line = line.strip()
        matchDistGrp(line)

# distGrpData is the result of previous loop and it has following structure:
# {0: {'MailList': 'name1', 'members': ['e@mail'], 'CN': 'cn1', 'ListEmail': 'gr1@emai.l'},
# {1: {'MailList': 'name2', 'members': ['e@mail'], 'CN': 'cn2', 'ListEmail': 'gr2@emai.l'},

print(distGrpData)
for i in distGrpData:
    print('test', distGrpData[i].get('members'))