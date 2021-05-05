#!/usr/bin/env python
from lindap import LDAPWrapper
from settings import settings

# AD connection
ld = LDAPWrapper(domain=settings['ADdomain'], user=settings['ADuser'],
  passw=settings['ADpassword'], server=settings['ADserver'],
  ldaps=True,
  read_only=False)

# AD create group
#ou = ou_results[0] # See OU section if you need info on getting OU objects
#ld.create_group(name="name2", description="desc2", parent_ou=ou)  

# AD search group
group_search_results = ld.get_group("name*") # wildcard *, always returns array
group = group_search_results[0]