import logging
import datetime
from .util import decode_ad_guid

# ldap attribute name -> friendly name
ATTR_ALIASES = {
    "info": "notes",
    "mail": "email",
    "telephonenumber": "phone",
    "physicaldeliveryofficename": "office",
    "member": "members",
    "msNPAllowDialin": "dialIn"
}

INV_ALIASES = ATTR_ALIASES.__class__(map(reversed, ATTR_ALIASES.items()))



class LDAPObject:
    LIST_PROPERTIES = ["member", "objectclass"]  # properties that are expected to always be lists

    SPECIAL_ENCODE_PROPERTIES = {
        "objectGUID": decode_ad_guid
    }  # properties that are expected to always be lists

    default_properties = ["cn", "distinguishedName", "samAccountName", "mail",
                          "objectClass", "objectGUID"]

    ACCOUNT_NOT_EXPIRED_TOP = 9223372036854775807

    def __init__(self, attributes={}, ldapwrapper=None):
        """

        :param attributes:
        :param ldapwrapper:
        """
        # Set this attributes for IDE auto-completion primarily.
        self.distinguishedName = None
        self.objectGUID = None
        self.objectGUID__orig = None
        self.expiration = None
        self.description = None
        self.member = []
        self.members = []

        # A list of LDAP attributes that were fetched, used to determine what attributes to fetch during refresh.
        self.fetched_attributes = []

        # Set provided attributes
        self._set(attributes)

        self.ldap = ldapwrapper
        self.lastLogonDate = datetime.datetime(1601, 1, 2)
        self.setup()

    def __str__(self):
        return self.distinguishedName

    def __repr__(self):
        return self.distinguishedName

    def setup(self):
        """
            Called during init. Can be overriden in inherited classes to provided specific setup.
            Called at end of parent init method
        :return: None
        """
        pass

    def decode_val(self, val):

        if type(val) == str or val == None or type(val) == datetime.datetime or type(val) == int:
            # if value is a python friendly type, use that type
            return val
        if type(val) == list:
            # decode every element in list and return new list of strings
            new_list = [v.decode('utf-8') for v in val]
            return new_list
        return val.decode("utf-8")

    def _set(self, attributes={}):
        """
        Sets local object attributes
        :param attributes:
        :return:
        """
        for key, val in attributes.items():
            display_key = None
            key_value = None
            orig_value = -1

            if key.lower() in ATTR_ALIASES:
                display_key = ATTR_ALIASES[key.lower()]

            if key.lower() not in INV_ALIASES and key.lower() not in self.fetched_attributes:
                self.fetched_attributes.append(key)

            if type(val) == list and key not in LDAPObject.LIST_PROPERTIES:
                """
                    All values come in lists, even ones that never have >1 length. 
                    Take the value of the first element only. 
                """
                try:
                    if key in LDAPObject.SPECIAL_ENCODE_PROPERTIES:
                        """
                            certain values are stored in formats not easily
                            human readable, such as binary or hex. GUID is one such example. 
                            Thus we need to decode it differently, and then we store the 
                            original value in <name>__orig
                        """
                        key_value = LDAPObject.SPECIAL_ENCODE_PROPERTIES[key](val=val[0])
                        orig_value = val[0]
                    else:
                        key_value = self.decode_val(val[0])
                except Exception as e:
                    logging.critical("Error decoding"+str(key)+ str(val[0].hex())+str(e))
                    raise ValueError("Error decoding"+str(key)+ str(val[0].hex())+str(e))
            elif val is None and key in LDAPObject.LIST_PROPERTIES:  # if ldap return an empty(None) property, but we want it to be a list, set internal valu to an empty list.
                key_value = []
            else:
                # if, for whatever reason its not a list, set the raw value
                key_value = self.decode_val(val)

            self.__setattr__(key, key_value)
            if orig_value != -1:
                self.__setattr__(key + "__orig", val[0])

            if display_key:
                """
                 also set the friendly display_key attribute to the same. 
                 Some ldap attributes are just different words thanw hat people 
                 think they are. IE: AD GUI displays "Notes", but the actual 
                 attribute name is "info"
                """
                if type(key_value) == list:
                    key_value = key_value.copy()
                self.__setattr__(display_key, key_value)

    def set_attr(self, key, value):
        self.ldap.set_attr(self, key, value)
        self._set({key: value})

    @property
    def lastLogon(self):
        return self.lastLogonDate

    @lastLogon.setter
    def lastLogon(self, value):
        """
            AD stores lastLogon as an integer representing units of 100 nanoseconds since 1/1/1601
            this setter converts it a usable datetime object
        :param value:
        :return:
        """
        if type(value) is str:
            begin = datetime.datetime(1601, 1, 2)
            s = int(value) / 10000000
            self.lastLogonDate = begin + datetime.timedelta(seconds=s)

    @property
    def is_disabled(self):
        return self.userAccountControl == '514'

    @property
    def is_expired(self):
        return self.expiration is None or self.expiration < datetime.datetime.now()

    def delete_object(self, confirmed=False):
        """
        Deletes this object.

        TODO - current issue deleting delete protected objects in AD.

        :param confirmed: Doesn't ask for stdin input for validation
        :return: <bool:success>, <str:message>
        """
        if not confirmed:
            answer = input("Are you sure you want to delete " + str(self) + "?[y/n]")
            if answer.lower() != "y":
                print("not deleting")
                return
        if not self.distinguishedName or len(self.distinguishedName) == 0:
            print("Invalid distinguished name")
            return False

        result, message = self.ldap.delete_object(self.distinguishedName)
        if result:
            print("Deleted", self.distinguishedName)
            return True, message
        else:
            print("Error deleting", self.distinguishedName, message)
            return False, message

    def move(self, target_ou):
        """

        :param target_ou: OU object
        :return:
        """
        if type(target_ou) != OU:
            print("Target OU should be of type OU instead of ", type(target_ou))
            return

        self.ldap.move_object(self.distinguishedName, target_ou)

    def refresh(self):
        self.plog(logging.debug,
                  "refreshing " + str(self) + "of type" + str(self.__class__.__name__) + "with guid" +
                  str(self.objectGUID) + " and orig guid " + str(self.objectGUID__orig) + "fetching props" +
                  str(self.__dict__.keys()))

        new = self.ldap.get_guid(guid=self.objectGUID__orig, properties=self.fetched_attributes,
                                 object_class=self.__class__.__name__.lower())
        if len(new) == 1:
            return new[0]
        raise ValueError("Error refreshing object", self.distinguishedName, new)

    def plog(self, level, message):
        self.ldap.plog(level, message)


class OU(LDAPObject):
    default_properties = ["ou", "distinguishedName", "name", "objectClass", "objectGUID"]

    @staticmethod
    def create(distinguishedName, samAccountName):
        return OU(attributes={"distinguishedName": [distinguishedName]})

    def get_children(self):
        return self.ldap.get_ou_children(dn=self.distinguishedName)


class Group(LDAPObject):
    default_properties = ["cn", "distinguishedName", "samAccountName",
                          "member", "mail", "objectClass", "objectGUID",
                          "name", "description"]

    SCOPE_GLOBAL = 2
    SCOPE_UNIVERSAL = 8
    SCOPE_DOMAIN_LOCAL = 4
    TYPE_SECURITY = -2147483648
    TYPE_DISTRIBUTION = 0

    @staticmethod
    def get_group_type_mask(scope=SCOPE_GLOBAL, type=TYPE_SECURITY):
        return scope + type

    def fetch_members(self, recursion_depth=0):
        """

        :param recursive: When True, the list is flattened to include recursive groups,
                it will replace recursed Group objects, with their members. So as long
                as the the recursive depth is <= max_depth, list would only contain Users
                If recursive=False or recursion > max_depth, the group will contain Group
                objects of the un-recursed level
                This will perforrm an ldap query for each member that is a group.

                When recursion_depth = 0, it is the same as self.members except that
                if a member is a Group, it will refresh that object (perform ldap query).
        :return: list
        """
        member_list = []
        # Retrive all direct members
        members = self.ldap.get_users_dns(dn_list=self.member)
        for member in members:
            if type(member) == Group:
                new_member = self.ldap.get_guid(member.objectGUID__orig, properties=Group.default_properties)
                new_member = new_member[0]  # TODO - error check length
                if recursion_depth == 0:  # if we reached recursion depth, add and continue
                    member_list.append(new_member)
                    continue
                child_members = new_member.fetch_members(recursion_depth=recursion_depth - 1)
                member_list = member_list + child_members
            else:
                member_list.append(member)
        return member_list

    def add_member(self, user):
        return self.ldap.group_add_member(user, self)

    def remove_member(self, user):
        return self.ldap.group_remove_member(user, self)


class Computer(LDAPObject):
    default_properties = ["cn", "distinguishedName", "samAccountName",
                          "mail", "objectClass", "objectGUID",
                          "name", "description", "operatingSystem",
                          "memberOf"]


class User(LDAPObject):
    default_properties = ["samAccountName", "distinguishedName", "cn",
                          "title", "description", "mail", "company",
                          "department", "displayName", "givenName",
                          "lastLogon", "disabled", "memberOf",
                          "pwdLastSet", "manager", "telephoneNumber",
                          "userAccountControl", "accountExpires",
                          "objectClass", "objectGUID", "sn", "manager",
                          "info", "msNPAllowDialin"]

    def setup(self):
        self.setup_alias()

    def setup_alias(self):
        self.set_email = self.set_mail

    def add_to_group(self, group):
        return self.ldap.group_add_member(self, group)

    def remove_from_group(self, group):
        return self.ldap.group_remove_member(self, group)

    def set_mail(self, value):
        self.set_attr("mail", value)

    def set_manager(self, value):
        """

        :param value: must be DN or user object
        :return:
        """
        if type(value) != str:
            value = value.distinguishedName
        self.set_attr("manager", value)

    def set_name(self, first=None, last=None):
        if not first and not last:
            return

        attrs = {}

        if first:
            attrs["givenName"] = first
        if last:
            attrs["sn"] = last
        self.ldap.set_attrs(self, attrs)

    def set_description(self, value):
        self.set_attr("description", value)

    def append_description(self, value):
        if "description" in self.__dict__:
            value = self.description + value
        self.set_attr("description", value)

    def prepend_description(self, value):
        if "description" in self.__dict__:
            value = value + self.description
        self.set_attr("description", value)

    def set_office(self, value):
        self.set_attr("physicalDeliveryOfficeName", value)

    def set_phone(self, value):
        self.set_attr("telephoneNumber", value)

    def set_initials(self, value):
        self.set_attr("initials", value)

    def set_title(self, value):
        self.set_attr("title", value)

    def set_department(self, value):
        self.set_attr("department", value)

    def set_company(self, value):
        self.set_attr("company", value)

    def set_notes(self, value):
        self.set_attr("info", value)

    def disable(self):
        self.ldap.set_attr(self, "userAccountControl", "514")

    def enable(self):
        self.ldap.set_attr(self, "userAccountControl", "512")

    def set_expiration(self, time):
        """
        :param time: python datetime or None to clear it
        :return:
        """
        if time is None:
            time = 0
        self.ldap.set_object_expiration(dn=self.distinguishedName, date=time)

    def reset_password(self, new_password):
        self.plog(logging.info, "Reseting pw for" + self.distinguishedName)
        try:
            self.ldap.set_password(dn=self.distinguishedName,
                                   password=new_password)
            return True
        except Exception as e:
            print("Failed to reset password for", self.distuishedName)
            return False
