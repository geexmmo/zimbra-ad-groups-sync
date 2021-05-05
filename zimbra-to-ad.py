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
        distGrpCount = len(distGrpData)
        print('Processing group', match.group())
        distGrpData[distGrpCount] = {'MailList': match.group()}
        # 
        distGrpData[distGrpCount]['members'] = []

    regexDistGrpEmail = '(?<=\w\W\s)\S{1,}@\S{2,}\.\S{2,}$'
    match = re.search(regexDistGrpEmail, line)
    if match:
        print(match.group())
        distGrpData[distGrpCount]['ListEmail'] = match.group()

    regexCN = '(?<=^cn:\s)[\w\s\d]+$'
    match = re.search(regexCN, line)
    if match:
        distGrpData[distGrpCount]['CN'] = match.group()

    regexMemberMail = '^\S{1,}@\S{2,}\.\S{2,}$'
    match = re.search(regexMemberMail, line)
    if match:
        distGrpData[distGrpCount]['members'].append(match.group())

with open('zimbra-test.txt', 'r') as textfile:
    for line in textfile:
        line = line.strip()
        matchDistGrp(line)

print(distGrpData)
for i in distGrpData:
    print('test', distGrpData[i].get('members'))