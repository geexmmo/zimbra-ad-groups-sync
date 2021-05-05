"""
    Basic helper functions
"""
import time
import uuid


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
