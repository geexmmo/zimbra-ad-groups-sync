import datetime
import inspect
import logging

import ldap
from ldap import modlist
from ldap.controls import SimplePagedResultsControl
from . import querybuilder as QueryBuilder
from .classes import OU, Computer, User, Group, LDAPObject


# which properties to print even more verbose information about. Intended for development.
from .util import retry_fetch

DEBUG_PROPERTY = ["members", "member"]


class LDAPWrapper:
    """
        Just a basic wrapper around Ldap, a grouping of friendly helper functions.
    """
    COMPUTER = "computer"
    USER = "user"
    GROUP = "group"
    OU = "ou"

    QUERY_PERSON_SAM = "(&(objectclass=person)(samAccountName=[sam]))"
    QUERY_OU_ALL = "(objectclass=organizationalUnit)"
    QUERY_OU_SEARCH = "(&(objectclass=organizationalUnit)(ou=*[ou]*))"
    QUERY_OU_EXACT = "(&(objectclass=organizationalUnit)(ou=[ou]))"

    AD_BASE_DATE = datetime.datetime(1601, 1, 1, 0, 0)

    ERR_DELETE_NONLEAF = "Cant delete a non-leaf node. You may be trying to delete an object with children."
    ERR_DELETE_INSUF = "You may have insufficient access to perform this delete action or you're trying to delete a protected object."

    ERR_CREATE_EXISTS = "The object already exists"
    ERR_CREATE_NOSUCHOBJECT = "There is no such object"

    ERR_LDAP_READONLY = "LDAP SDK set to read only"

    def __init__(self, domain, user, passw, server=None, read_only=True, ldaps=False, verbose=False, page_size=250):
        """

        :param domain: domain of server
        :param user:  bind user
        :param passw: password for bind user
        :param server: server to connect to, if none supplied domain is used
        :param read_only: whether or not to skip things that make changes, for safety
        :param ldaps: whether to use tls/ssl
        :param verbose:
        :param page_size: max results to be returned by server, will make subsequent queries until no more pages available
        """
        self.read_only = read_only
        self.domain = domain
        self.user = user + "@" + domain
        self.passw = passw
        self.verbose = verbose
        self.page_size = page_size
        self.ldaps = ldaps
        if server is None:
            self.server = domain
        else:
            self.server = server

        self.set_dn_from_domain()

        if not self.ldaps:
            self.conn = ldap.initialize('ldap://' + self.server)  # the IP address
        else:
            self.setup_ldaps()

        self.conn.protocol_version = ldap.VERSION3
        self.conn.set_option(ldap.OPT_REFERRALS, 0)
        try:
            self.conn.simple_bind_s(self.user, passw)
        except ldap.SERVER_DOWN as e:
            logging.critical("Error initialization connection, the server seems to be down.")


    def print_info(self):
        print("read only: ", self.read_only)
        print("domain: ", self.domain)
        print("bind user: ", self.user)
        print("page size: ", self.page_size)
        print("LDAPS: ", self.ldaps)
        print("Server: ", self.server)

    @staticmethod
    def test_creds(domain, user, passw, server=None, ldaps=False):
        """
        test credentials with an uninitialized LDAPWrapper object
        :param domain:
        :param user:
        :param passw:
        :param server:
        :param ldaps:
        :return:
        """
        domain = domain
        user = user + "@" + domain
        passw = passw
        if server is None:
            server = domain

        if not ldaps:
            conn = ldap.initialize('ldap://' + server)  # the IP address

        conn.protocol_version = ldap.VERSION3
        conn.set_option(ldap.OPT_REFERRALS, 0)
        try:
            conn.simple_bind_s(user, passw)
            return True
        except:
            return False

    def auth(self, user, passw):
        # print("testing pass|",passw,"|for ", user)
        if not user or len(user) == 0:
            return False
        try:
            if not self.ldaps:
                conn = ldap.initialize('ldap://' + self.server)  # the IP address
            else:
                conn = ldap.initialize('ldaps://' + self.server + ':636')
                conn.set_option(ldap.OPT_REFERRALS, 0)
                conn.set_option(ldap.OPT_PROTOCOL_VERSION, 3)
                # l.set_option(ldap.OPT_X_TLS_CACERTFILE, os.getcwd() + "/cacert.pem")
                conn.set_option(ldap.OPT_X_TLS, ldap.OPT_X_TLS_DEMAND)
                conn.set_option(ldap.OPT_X_TLS_DEMAND, True)
                conn.set_option(ldap.OPT_DEBUG_LEVEL, 255)

            conn.protocol_version = ldap.VERSION3
            conn.set_option(ldap.OPT_REFERRALS, 0)
            conn.simple_bind_s(user + "@" + self.domain, passw)
            return True
        except Exception as e:
            if self.verbose:
                print(e)
            print("Exception ", e)
            return False
        finally:
            conn.unbind_s()

    def setup_ldaps(self):
        ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
        l = ldap.initialize('ldaps://' + self.server + ':636')
        l.set_option(ldap.OPT_REFERRALS, 0)
        l.set_option(ldap.OPT_PROTOCOL_VERSION, 3)
        # l.set_option(ldap.OPT_X_TLS_CACERTFILE, os.getcwd() + "/cacert.pem")
        l.set_option(ldap.OPT_X_TLS, ldap.OPT_X_TLS_DEMAND)
        l.set_option(ldap.OPT_X_TLS_DEMAND, True)
        l.set_option(ldap.OPT_DEBUG_LEVEL, 255)
        self.conn = l

    def set_dn_from_domain(self):
        sections = self.domain.split(".")
        base = ""
        for section in sections:
            base += "dc=" + section + ","
        base = base[:-1]
        self.base_dn = base
        return base

    @staticmethod
    def debug_property(key, value, message):
        if key in DEBUG_PROPERTY:
            print(inspect.stack()[1].function, "->:DEBUG:", key, " -> ", value, ":", message)

    def query(self, query_string, properties=("samAccountName", "distinguishedName", "cn"), base_dn=None,
              cast_results=False):

        self.plog(logging.debug, "perming ldap query:" + query_string)
        for prop in properties:
            LDAPWrapper.debug_property("", prop, "Attempting to search for property with query:" + query_string)

        if not base_dn:
            base_dn = self.base_dn

        page_control = SimplePagedResultsControl(True, size=self.page_size, cookie='')
        response = self.conn.search_ext(base_dn, ldap.SCOPE_SUBTREE, query_string, properties,
                                        serverctrls=[page_control])

        result_pages = []
        pages = 0

        while True:
            pages += 1
            rtype, rdata, rmsgid, serverctrls = self.conn.result3(response, 1)
            # print("q data:", rdata)
            result_pages.extend(rdata)
            controls = [control for control in serverctrls if
                        control.controlType == SimplePagedResultsControl.controlType]

            if not controls:
                # print('The server ignores RFC 2696 control')
                break
            if not controls[0].cookie:
                break
            page_control.cookie = controls[0].cookie
            page_control.criticality = False
            response = self.conn.search_ext(base_dn, ldap.SCOPE_SUBTREE, query_string, properties,
                                            serverctrls=[page_control])

        valid_results = []
        for result in result_pages:
            if result[0] is None:
                # print("Empty result ", result)
                continue

            final_obj = {}

            for expected_key in properties:  # for each property that was requested
                if expected_key == "samAccountName":  # Correct the supplied attribute text to the ldap expected attribute name
                    expected_key = "sAMAccountName"
                if expected_key == "expiration":
                    expected_key = "accountExpires"

                if expected_key in result[1].keys():
                    if expected_key == "sAMAccountName":  # translate the ldap attribute to the user requested key name
                        final_obj["samAccountName"] = result[1][expected_key]  # use it in the final object

                    elif expected_key == "accountExpires":  # add a more friendly, "expiration" key with python date # time
                        final_obj["expiration"] = self.adtime_datetime(int(result[1][expected_key][0].decode('utf-8')))
                        final_obj["accountExpires"] = int(result[1][expected_key][0].decode('utf-8'))
                    else:
                        final_obj[expected_key] = result[1][expected_key]  # use it in the final object
                else:  # otherwise, create key and set it to none
                    # print("Failed to retrieve attribute", expected_key)
                    # if it exists in the ldap object and doesn't have the __ inteneral keyword
                    # TODO - doc details of above comment
                    if "__" not in expected_key:
                        final_obj[expected_key] = None
                self.debug_property(expected_key, final_obj.get(expected_key, ""),
                                    "Value set from query: " + query_string)

            # print("Result ", final_obj)
            valid_results.append(final_obj)

        if not cast_results:
            return valid_results

        casted_results = []
        for result in valid_results:
            obj = self.dict_to_object(result)
            casted_results.append(obj)

        return casted_results

    def dict_to_object(self, result):
        objclass = result['objectClass']
        classes = [c.decode('utf') for c in objclass]
        if 'organizationalUnit' in classes:
            obj = OU(ldapwrapper=self, attributes=result)
        elif "computer" in classes:
            obj = Computer(ldapwrapper=self, attributes=result)
        elif 'person' in classes and 'user' in classes:
            obj = User(ldapwrapper=self, attributes=result)
        elif 'group' in classes:
            obj = Group(ldapwrapper=self, attributes=result)
        else:
            print("ERR: Unkown object class set", classes)
        return obj

    def datetime_adtime(self, value):
        delta = value - LDAPWrapper.AD_BASE_DATE
        return int(
            delta.total_seconds() * 10000000)  # convert datetime to the AD unit of time for the lastLogon Attribute

    def adtime_datetime(self, value):
        """
        convert long integer to python datetime
        :param value:
        :return:
        """
        if value == 0 or value == LDAPObject.ACCOUNT_NOT_EXPIRED_TOP:
            return None

        delta = datetime.timedelta(seconds=value / 10000000)
        date = LDAPWrapper.AD_BASE_DATE + delta
        return date

    def set_object_expiration(self, date, dn):
        if date is not None and date is not 0:
            ad_time = self.datetime_adtime(date)
        else:
            ad_time = 0
        self.modify_attribute(dn=dn, action=ldap.MOD_REPLACE, attribute="accountExpires", values=[str(ad_time)])

    def clear_object_expiration(self, dn):
        self.modify_attribute(dn=dn, action=ldap.MOD_REPLACE, attribute="accountExpires", values=[str(0)])

    def modify_attribute(self, dn, action, attribute, values):
        if self.read_only:
            raise PermissionError("Attempting a write operation with read_only safety turned on")

        attribute_values = []
        for v in values:
            if type(v) == str:
                attribute_values.append(v.encode("utf-8"))
            else:
                attribute_values.append(v)

        return self.conn.modify_s(
            dn, [(action, attribute, attribute_values)]
        )

    def user_exists(self, username):
        query = LDAPWrapper.QUERY_PERSON_SAM.replace("[sam]", username)
        user = self.query(query)
        if len(user) == 0:
            return False
        user = user[0]

        if 'sAMAccountName' in user:
            user = user['samAccountName'][0].decode("utf-8")

        return str(user).lower() == str(username).lower()

    def get_object(self, attrs, obj_class, properties):
        query = QueryBuilder.builder(obj_class, attrs)
        results = []
        query_result = self.query(query, properties=properties)
        for entry in query_result:
            e = self.dict_to_object(entry)
            results.append(e)
        return results

    def get_computer(self, name):
        attrs = {
            "cn": name,
        }
        return self.get_object(attrs, LDAPWrapper.COMPUTER, Computer.default_properties)

    def get_group(self, name):
        attrs = {
            "cn": name,
        }
        return self.get_object(attrs, LDAPWrapper.GROUP, Group.default_properties)

    def get_users_dns(self, dn_list):
        attrs = {
            "members": dn_list
        }
        query = QueryBuilder.builder("none", attrs, operator="|")
        results = []
        query_result = self.query(query, properties=User.default_properties)

        for entry in query_result:
            e = self.dict_to_object(entry)
            results.append(e)
        return results

    @retry_fetch
    def get_user(self, sam="", title="", disabled=None, lastLogonBefore=None,
                 firstname="", lastname="", email="", department="",
                 employee_type="", description="", company="",
                 search_attrs={}, properties=[]):

        """

        :param sam:
        :param title:
        :param disabled:
        :param lastLogonBefore:
        :param firstname:
        :param lastname:
        :param email:
        :param department:
        :param employee_type:
        :param description:
        :param company:
        :param search_attrs: extra search attributes directly mapped to ldap attributes
        :param properties:  the ldap attributes/properties to gather from user
        :return: User[]
        """
        attrs = {}

        if len(employee_type) > 0:
            attrs["employeeType"] = employee_type

        if len(description) > 0:
            attrs["description"] = description

        if len(company) > 0:
            attrs["company"] = company

        if len(sam) > 0:
            attrs["sam"] = sam

        if len(title) > 0:
            attrs["title"] = title

        if disabled is not None:
            attrs["disabled"] = disabled

        if lastLogonBefore is not None:
            attrs["lastLogonBefore"] = self.datetime_adtime(lastLogonBefore)

        if len(firstname) > 0:
            attrs["givenName"] = firstname

        if len(lastname) > 0:
            attrs["sn"] = lastname

        if len(email) > 0:
            attrs["mail"] = email

        if len(department) > 0:
            attrs["department"] = department

        if len(title) > 0:
            attrs["title"] = title

        attrs = {**attrs, **search_attrs}

        query = QueryBuilder.builder("user", attrs)

        results = []
        query_result = self.query(query, properties=User.default_properties + properties)

        for entry in query_result:
            u = User(ldapwrapper=self, attributes=entry)
            if u.samAccountName is None:
                logging.WARNING("Found a user account with None as SamAccountName.", u.__dict__)
            results.append(u)
        return results

    def get_guid(self, guid, object_class="*", properties=LDAPObject.default_properties):
        attrs = {
            "objectGUID": guid
        }
        query = QueryBuilder.builder(object_class, attrs)

        results = []
        query_result = self.query(query, properties=properties)

        for entry in query_result:
            u = self.dict_to_object(entry)
            results.append(u)
        return results

    def get_distinguished_name(self, dn, object_class="*", properties=LDAPObject.default_properties):
        attrs = {
            "distinguishedName": dn
        }
        query = QueryBuilder.builder(object_class, attrs)

        results = []
        query_result = self.query(query, properties=properties)

        for entry in query_result:
            u = self.dict_to_object(entry)
            results.append(u)
        return results

    def get_ou(self, ou="", search_attrs={}, properties=[]):
        attrs = {}

        if len(ou) > 0:
            attrs["ou"] = ou

        attrs = {**attrs, **search_attrs}

        query = QueryBuilder.builder("ou", attrs)
        results = self.query(query, properties=OU.default_properties + properties)

        ous = []
        for result in results:
            ou = OU(result, ldapwrapper=self)
            ous.append(ou)

        return ous

    def get_ou_children(self, dn, child_class="all",
                        properties=["cn", "samAccountName", "distinguishedName", "objectClass"]):
        query = QueryBuilder.builder(base=child_class, attrs={})
        results = self.query(query_string=query, properties=properties, base_dn=dn,
                             cast_results=True)
        valid_results = [r for r in results if r.distinguishedName.lower() != dn.lower()]

        return valid_results

    def group_add_members(self, users, group):
        for user in users:
            try:
                self.group_add_member(user, group)
            except ldap.ALREADY_EXISTS as e:
                logging.info(str(user) + " already in group " + str(group))
                pass

    def group_add_member(self, user, group):
        self.modify_attribute(group.distinguishedName, ldap.MOD_ADD, "member", [user.distinguishedName])

    def group_remove_member(self, user, group):
        if not self.read_only:
            self.modify_attribute(group.distinguishedName, ldap.MOD_DELETE, "member", [user.distinguishedName])

    def delete_object(self, dn):
        try:
            if self.read_only:
                return True, "Object WOULD HAVE BEEN DELETE, but I'm in read only mode."
            else:
                self.conn.delete_s(dn)
        except ldap.UNWILLING_TO_PERFORM:
            return False, "Server is unwilling to perform this delete action"
        except ldap.INSUFFICIENT_ACCESS:
            return False, LDAPWrapper.ERR_DELETE_INSUF
        except ldap.SERVER_DOWN:
            return False, "Server is not reachable"
        except ldap.NOT_ALLOWED_ON_NONLEAF:
            return False, LDAPWrapper.ERR_DELETE_NONLEAF

        return True, "Object Deleted " + dn

    @staticmethod
    def encode_password(passw):
        return '"{}"'.format(passw).encode('utf-16-le')

    def set_password(self, dn, password):
        if not self.read_only:
            self.modify_attribute(dn, ldap.MOD_REPLACE, "unicodePwd", [LDAPWrapper.encode_password(password)])

    def move_object(self, dn, target_ou):
        new_name = dn.split(",")[:1][0]

        if not self.read_only:
            self.conn.rename_s(dn, new_name, target_ou.distinguishedName)

    def create_group(self, name, description=None, parent_ou=None, fetch_after_creation=True):
        if not parent_ou:
            base = self.base_dn
        else:
            base = parent_ou.distinguishedName

        new_dn = "cn=" + name + "," + base

        user_attrs = {}

        user_attrs['objectclass'] = [b'top', b'group']
        user_attrs['cn'] = [bytes(name, 'utf-8')]
        user_attrs['name'] = [bytes(name, 'utf-8')]

        if description:
            user_attrs['description'] = [bytes(description, 'utf-8')]

        user_attrs['groupType'] = [bytes(str(Group.get_group_type_mask()), "utf-8")]
        user_ldif = modlist.addModlist(user_attrs)

        if not self.read_only:
            self.conn.add_s(new_dn, user_ldif)
            if not fetch_after_creation:
                return True
            fetch = self.get_group(name=name)

            if len(fetch) == 1:  # return the single user when thers only 1 match
                fetch = fetch[0]
            return fetch

    def create_ou(self, name, parent_ou=None):
        if not parent_ou:
            base = self.base_dn
        else:
            base = parent_ou.distinguishedName

        new_dn = "ou=" + name + "," + base

        user_attrs = {}

        user_attrs['objectclass'] = [b'top', b'organizationalUnit']

        user_ldif = modlist.addModlist(user_attrs)

        if not self.read_only:
            try:
                self.conn.add_s(new_dn, user_ldif)
                created_ou = self.get_distinguished_name(dn=new_dn, object_class="ou", properties=OU.default_properties)
                return created_ou[0], "Created ou " + new_dn

            except ldap.ALREADY_EXISTS:
                return None, LDAPWrapper.ERR_CREATE_EXISTS + ":" + new_dn
            except ldap.NO_SUCH_OBJECT as e:
                return None, LDAPWrapper.ERR_CREATE_NOSUCHOBJECT + ":Could be the parent ou is non-existant=" + str(
                    parent_ou) + ": when creating ou " + name
        return None, LDAPWrapper.ERR_LDAP_READONL

    def create_user(self, ou, user_attrs={}, fetch_after_creation=True):
        """

        :param ou: OU object for which to create the user
        :param user_attrs: attribute dictionary
        :param fetch_after_cration: perform an ldap query to verify user was successfully created and
            return fetched results. Generates an extra ldap call.
        :return:
        """

        # so it doesn't mess with original properties during the encoding
        user_attrs = user_attrs.copy()

        if type(ou) != OU:
            raise ValueError("Invalid OU type: ", type(ou))

        if "name" in user_attrs:
            user_attrs["cn"] = [user_attrs["name"]]
            del user_attrs["name"]

        required_attrs = ("samAccountName", "cn", "givenName", "password")

        for attr in required_attrs:
            if attr not in user_attrs:
                raise ValueError("Missing ", attr, "in list of user attributes. Required: ", required_attrs)

        password = user_attrs["password"]
        del user_attrs["password"]

        for k, v in user_attrs.items():
            user_attrs[k] = self.encode(v)

        user_attrs['objectclass'] = [b'top', b'person', b'organizationalPerson', b'user']
        dn = b"cn=" + user_attrs["cn"][0] + b"," + bytes(ou.distinguishedName, encoding="utf-8")
        user_attrs['userAccountControl'] = [b'512']
        # turn off Force user to change password on next logon
        user_attrs['pwdLastSet'] = [b'-1']
        user_attrs['unicodePwd'] = LDAPWrapper.encode_password(password)
        # username and samaccount name
        user_attrs['userPrincipalName'] = [
            user_attrs["samAccountName"][0] + b"@" + bytes(self.domain, encoding="utf-8")]

        user_ldif = modlist.addModlist(user_attrs)

        logging.debug("Creating user " + str(user_attrs) + " in ou " + str(ou))
        if self.verbose:
            print("Creating user ", user_attrs)

        try:
            if not self.read_only:
                self.conn.add_s(dn.decode("utf-8"), user_ldif)
                if not fetch_after_creation:
                    return True
                fetch = self.get_user(sam=user_attrs["samAccountName"][0].decode('utf-8'))

                if len(fetch) == 1:  # return the single user when thers only 1 match
                    fetch = fetch[0]
                return fetch

            else:
                print("Would have creating user", user_attrs)
                return True

        except ldap.INSUFFICIENT_ACCESS as e:
            print("Error creating user. Not enough access", e)
            return None
        except ldap.UNWILLING_TO_PERFORM as e:
            if "problem 5003" in str(e):
                print("Refused to create, invalid attribute", e)
                return None
            else:
                raise ldap.UNWILLING_TO_PERFORM
        except ldap.ALREADY_EXISTS as e:
            print("User already exists ", dn)
            return None

    def encode(self, value):
        if type(value) == list:
            return [bytes(value[0].encode("utf-8"))]
        return [bytes(value.encode("utf-8"))]

    def set_attrs(self, obj, attributes):
        """
        sets multiple attributes at once
        :param obj:obj to be the DN or an object with a .distinguishedName attributed
        :param attribute: dict: key->value of attributes
        :return:
        """
        if type(obj) != str:
            dn = obj.distinguishedName
        else:
            dn = obj

        self.plog(logging.debug, "Setting " + dn + " " + str(attributes))
        mod_attrs = []

        for attr in attributes.keys():
            mod_attrs.append((ldap.MOD_REPLACE, attr, self.encode(attributes[attr])))

        if self.read_only == False:
            self.conn.modify_s(dn, mod_attrs)

    def set_attr(self, obj, attribute, value):
        """
        sets a single attribute
        :param obj:to be the DN or an object with a .distinguishedName attributed
        :param attribute: str:name of attr
        :param value: str:value of str
        :return:
        """
        if type(obj) != str:
            dn = obj.distinguishedName
        else:
            dn = obj

        self.plog(logging.debug, "Setting " + dn + " " + attribute + "" + str(value))
        mod_attrs = [(ldap.MOD_REPLACE, attribute, self.encode(value))]
        if self.read_only == False:
            self.conn.modify_s(dn, mod_attrs)

    def plog(self, level, message):
        """
        Adds call stack and print to stdout if verbose set.
        :param level:
        :param message:
        :return:
        """
        stack = [s.function + "->" for s in inspect.stack()][2:]
        stack.reverse()
        stack = ''.join(stack)[:-2] + ":"
        message = ''.join(stack) + message  # add caller func to begning of message
        if self.verbose:
            print(message)
        level(message)
