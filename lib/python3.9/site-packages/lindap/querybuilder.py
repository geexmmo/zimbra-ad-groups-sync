"""
    Builds the ldap query strings
"""
PERSON = "(&(objectclass=person)"  # Note missing
PERSON_SAM = "(&(objectclass=person)(samAccountName=[sam]))"
PERSON_TITLE_EXACT = "(&(objectclass=person)(title=[title]))"
PERSON_TITLE_LIKE = "(&(objectclass=person)(title=*[title]*))"
PERSON_DESCRIPTION_LIKE = "(&(objectclass=person)(description=*[description]*))"
PERSON_FN_LN = "(&(objectclass=person)(givenName=[fname])(sn=[lname]))"
PERSON_EMAIL = "(&(objectclass=person)(email=[email])"
PERSON_MEMBEROF = "(&(objectCategory=user)(memberOf=cn=[cn]]))"

GROUP_NAME = "(&(objectCategory=group)(cn=[cn]))"

OU_NAME = "(&(objectclass=organizationalUnit)(ou=*[ou]*))"

SEARCH_BASES = {
    "user": "([oper](objectclass=Person)",
    "ou": "([oper](objectclass=organizationalUnit)",
    "group": "([oper](objectclass=group)",
    "computer": "([oper](objectclass=computer)",
    "all": "([oper](objectclass=*)",
    "none": "([oper]",
    "*": "([oper](objectclass=*)",
}


def add_disabled(query, is_disabled):
    if is_disabled:
        return "(userAccountControl:1.2.840.113556.1.4.803:=2)"  # disabled users
    return "(!(userAccountControl:1.2.840.113556.1.4.803:=2))"  # not disabled


def encode_ad_guid(query, val):
    val = val.hex()
    encoded = '\\' + '\\'.join(val[i:i + 2] for i in range(0, len(val), 2))
    # print('encoding v', encoded)
    return "(objectGUID=" + encoded + ")"


def gen_membership_query(query, values):
    # TODO - Doc: don't return the original query or append to it. Its meant to be a reference.
    res = ""
    for value in values:
        res += "(distinguishedName=" + value + ")"
    # print("member ship query", query)
    # time.sleep(30)
    return res


def gen_dialin_query(query, value):
    if value:
        return "(msNPAllowDialin=TRUE)"
    return "(msNPAllowDialin=FALSE)"


ATTRS = {
    "cn": "(cn=[cn])",
    "title": "(title=[title])",
    "sam": "(samAccountName=[sam])",
    "ou": "(ou=[ou])",
    "disabled": add_disabled,
    "lastLogonBefore": "(lastLogon<=[lastLogonBefore])",
    "lastLogonAfter": "(lastLogon>=[lastLogonAfter])",
    "givenName": "(givenName=[givenName])",
    "department": "(department=[department])",
    "mail": "(mail=[mail])",
    "sn": "(sn=[sn])",
    "distinguishedName": "(distinguishedName=[distinguishedName])",
    "objectGUID": encode_ad_guid,
    "members": gen_membership_query,
    # "members" isn't an ldap attribute, this is intentional so we can generate a
    #    custom query that doesnt conflict the the real 'member' attribute name
    "dialIn": gen_dialin_query
}


def builder(base, attrs, operator="&"):
    """
    Builds very basic ldap queries, suitable for the most common ldap get operations
    ( <& || |> (objectClass=) (property=value) )"
    :param base:
    :param attrs:
    :param operator:
    :return:
    """
    if base not in SEARCH_BASES:
        raise ValueError("Invalid base key " + str(base))

    query = SEARCH_BASES[base].replace("[oper]", operator)
    for key, val in attrs.items():
        if isinstance(ATTRS[key],str):
            if not isinstance(val, str):
                query += ATTRS[key].replace("[" + key + "]", repr(val))
            else:
                query += ATTRS[key].replace("[" + key + "]", val)
        else:
            query += ATTRS[key](query, val)
    query += ")"
    return query  # TODO - log all built queries?
