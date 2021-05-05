"""
    Basic helper functions
"""
import time
import uuid
import logging

import OpenSSL


def retry_fetch(func):
    """
    Will retry the function up to 3 times when its result length === 0
    Used to retry an ldap user query. AD Synchronization can cause
    false negatives for newly (within moments) created users
    :param func:
    :return:
    """
    def inner(*args, **kwargs):
        tries = 0
        while tries < 3:
            result = func(*args, **kwargs)
            if len(result) > 0:
                return result
            time.sleep(1)
            tries += 1
    return inner


def plog(*args, **kwargs):
    """
    prints and calls the provided function.
    :param args: [0]=Print, [1]=logging function
    :param kwargs: sent to logging
    :return:
    """
    if args[0]:
        print(**kwargs)
    args[1](**kwargs)


def decode_ad_guid(val):
    """
    Decode the AD provided guid to a string.

    :param val: the bytes provided from the ldap query
    :return: str:Value you see when viewing the guid in the DC gui
    """
    return str(uuid.UUID(bytes_le=bytes.fromhex(val.hex())))


def ssl_test(hostname, port=636, require_trust=True):
    import ssl, socket

    if require_trust:
        ctx = ssl.create_default_context()
    else:
        ctx = ssl._create_unverified_context()

    with ctx.wrap_socket(socket.socket(), server_hostname=hostname) as s:
        try:
            s.connect((hostname, port))
            cert = s.getpeercert()
        except ssl.SSLError as e:
            if "CERTIFICATE_VERIFY_FAILED" in str(e):
                cert = ssl.get_server_certificate( (hostname,port)  )
                print(cert)
                x509 = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, cert)
                print(x509.get_issuer())
                print(x509.get_subject())
                print(x509.get_serial_number())
                print(x509.get_notBefore())
                print(x509.get_notAfter())
            logging.critical("It appears SSL/TLS on "+hostname+":"+str(port) +
                             " is open, but there was an issue finishing the connection."+str(e))
            return False

    return True