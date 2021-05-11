#!/usr/bin/env python

import ldap
import ldap.modlist as modlist
from settings import settings
import logging

logging.info('Startring')
logging.basicConfig(filename='zimbra-to-ad.log', level=logging.DEBUG,
                    format='%(levelname)s %(funcName)s():%(message)s')

# AD search user
def searchADUserExists(conn, query):
  data = conn.search_s(settings['ADdomain'], ldap.SCOPE_SUBTREE, 'userPrincipalName='+ query , ['sAMAccountName', 'userAccountControl'])
  # userAccountControl: 512 = unlocked, 512+2 = locked
  if data[0][0]:
    lockoutstatus = int(data[0][1].get('userAccountControl')[0].decode('utf-8'))
  if data[0][0] and lockoutstatus != 514:
    return True
  else:
    if not data[0][0]:
      logging.error('searchADUserExists() No data returned on query %s q: %s', data, query)
    return False


# AD search group
def searchADGroupExists(conn, query):
  data = conn.search_s(settings['ADdomain'], ldap.SCOPE_SUBTREE, 'distinguishedName=CN='+ query + ',' + settings['ADsearchOU'] + ',' + settings['ADdomain'], ['sAMAccountName'])
  if data[0][0]:
    return True
  else:
    logging.error('searchADGroupExists() No data returned on query %s q: %s', data, query)
    return False


# AD check user membership
def searchADMembership(conn, ADuser, ADgroup):
  data = conn.search_s(settings['ADdomain'], ldap.SCOPE_SUBTREE, 'userPrincipalName='+ ADuser , ['memberOf'])
  # making list of returned 'memberOf' groups if they were returned by query
  if data[0][1]:
    membershipdata = data[0][1].get('memberOf')
  else: # User is not member of any group
    logging.error('searchADMembership() No data returned on query %s q: %s %s', data, ADuser, ADgroup)
    membershipdata = []
  # converting query string to match output of ad data so I can compare them
  ADgroup = str.encode('CN=' + ADgroup + ',' + settings['ADsearchOU'] + ',' + settings['ADdomain'])
  # return True if ADuser is member of ADgroup
  if ADgroup in membershipdata:
    return True
  else:
    return False


# AD create group
def addADGroup(conn, GroupName,GroupEmail,displayName):
  try:
    distinguishedName = 'CN=' + GroupName + ',' + settings['ADsearchOU'] + ',' + settings['ADdomain']
    attrs = {}
    attrs['objectClass'] = [b'top',b'group']
    attrs['cn'] = str.encode(GroupName)
    attrs['mail'] = str.encode(GroupEmail)
    attrs['description'] = str.encode(displayName)
    attrs['sAMAccountName'] = str.encode(GroupName)
    ldif = modlist.addModlist(attrs)
    conn.add_s(distinguishedName,ldif)
    logging.info('Creating AD group %s', distinguishedName)
    return True
  except ldap.LDAPError as e:
    logging.error('Exception: %s', e)
    return False


def addADMembership(conn, ADuser, ADgroup):
  groupdn = conn.search_s(settings['ADdomain'], ldap.SCOPE_SUBTREE, 'cn='+ ADgroup , ['distinguishedName'])
  groupmember = conn.search_s(settings['ADdomain'], ldap.SCOPE_SUBTREE, 'cn='+ ADgroup , ['member'])
  userdn = conn.search_s(settings['ADdomain'], ldap.SCOPE_SUBTREE, 'userPrincipalName='+ ADuser , ['distinguishedName'])
  userdn = userdn[0][1].get('distinguishedName')[0]
  groupdn = groupdn[0][1].get('distinguishedName')[0].decode('utf-8')
  groupmember = groupmember[0][1].get('member')
  finalmembers = []
  # group may have empty member list
  if groupmember:
    for i in groupmember:
      finalmembers.append(i)
  finalmembers.append(userdn)
  mod_attrs = [( ldap.MOD_REPLACE, 'member', finalmembers)]
  try:
    conn.modify_s(groupdn, mod_attrs)
    return True
  except ldap.LDAPError as e:
    logging.error('Exception: %s', e)
    return False


def listADGroups(conn):
  data = conn.search_s(settings['ADsearchOU'] + ',' + settings['ADdomain'], ldap.SCOPE_SUBTREE, '(cn=*)', ['cn','mail'])
  try:
    if data[0][1]: # if recieved at least one result
      return data
    else: return False
  except IndexError as e:
    logging.error('listADGroups() Exception: %s', e)
    return False


def listADGroupMembers(conn, query):
  data = conn.search_s(settings['ADsearchOU'] + ',' + settings['ADdomain'], ldap.SCOPE_SUBTREE, 'mail=' + query, ['member'])
  try:
    if data[0][1]: # if recieved at least one result
      return data
    else: return False
  except IndexError as e:
    logging.error('listADGroupMembers() Exception: %s', e)
    return False


def listADUserMail(conn, query):
  try: # search name first
    namecut = query.split(',')[0].lstrip('CN=')
    data = conn.search_s(settings['ADdomain'], ldap.SCOPE_SUBTREE, 'name=' + namecut, ['mail'])
    if data[0][0]:
      return data
  except ValueError as e:
    print(e)
  try: # search DN if name lookup failed
    data = conn.search_s(settings['ADdomain'], ldap.SCOPE_SUBTREE, 'distinguishedName=' + query, ['mail'])
    if data[0][0]:
      return data
  except ValueError as e:
    print(e)