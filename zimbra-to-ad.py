#!/usr/bin/env python
import re

# mailLists = {'MailList':'','ListEmail':'','CN':'','maillist':[]}
mailLists = {}
mailListslen = len(mailLists)
# tempMemberList = {}
# testlist = []
# tempMemberCount = 0

def matchMailList(line):
    regexMailList = '(?<=^#\sstartNewlist:\s)[\w\s\d]+(?=\smembers)'
    match = re.search(regexMailList, line)
    if match:
        # accessing variables and structures
        global mailListslen
        # global tempMemberCount
        # global tempMemberList
        # global testlist
        mailListslen = len(mailLists)
        # if tempMemberList:
        #     print('last members', tempMemberList)
        print('Processing group', match.group())
        # first 'MailList' added to data structure
        mailLists[mailListslen] = {'MailList': match.group()}
        mailLists[mailListslen]['maillist'] = []
        # resetting member list for new iteration
        # tempMemberCount = 0
        # tempMemberList = {} 

    regexMailListEmail = '(?<=\w\W\s)\S{1,}@\S{2,}\.\S{2,}$'
    match = re.search(regexMailListEmail, line)
    if match:
        print(match.group())
        mailLists[mailListslen]['ListEmail'] = match.group()

    regexCN = '(?<=^cn:\s)[\w\s\d]+$'
    match = re.search(regexCN, line)
    if match:
        mailLists[mailListslen]['CN'] = match.group()

    regexMemberMail = '^\S{1,}@\S{2,}\.\S{2,}$'
    match = re.search(regexMemberMail, line)
    if match:
        # print('memlist', tempMemberList)
        # print('memcount', tempMemberCount)
        # print('maillist', mailLists)
        # print('maillistlen', mailListslen)
        mailLists[mailListslen]['maillist'].append(match.group())
        # tempMemberList[tempMemberCount]['maillist'].append(match.group())
        # testlist.append(match.group())
        # tempMemberCount += 1

with open('zimbra-test.txt', 'r') as textfile:
    for line in textfile:
        line = line.strip()
        matchMailList(line)

# mailLists[mailListslen] = {'MailList': match.group()}
print(mailLists)
for i in mailLists:
    print('test', mailLists[i].get('maillist'))