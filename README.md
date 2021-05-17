# zimbra-ad-groups-sync
Is a set of scripts that can help you to synchronize AD groups Zimbra's distribution lists.

Different scripts works different directions:
***zimbra-to-ad.py*** - will gather distribution lists including its members and will create new AD enteties based on information gathered
***ad-to-zimbra.py*** - will parse AD group information and populate Zimbra's distribution lists file accordingly.

# Requirements
### Python packages:
`pip install python-ldap`

or
	
`pip install -r requirements.txt`

### System
python-ldap may require python or ldap development headers, pip installation will fail with error if this is the case.

On Debian/Ubuntu:
`sudo apt-get install libsasl2-dev python-dev libldap2-dev libssl-dev`

RedHat/CentOS:
`sudo yum install python-devel openldap-devel`
# Scripts
## settings.py
*settings.py* should be modified according to your AD setup, other scripts are heavily dependent on correct configuration supplied in this file.
`ADdomain` is your domain DC 
`ADsearchOU` is the place where group search will be performed in ad-to-zimbra.py and group creation in zimbra-to-ad.py
`ZimbraDumpFile` is zmprov group dump for zimbra-to-ad.py, it's creatinon will be described further in this document.
`regexMemberCheck` is used in zimbra-to-ad.py to filter out members from domains that does not exist in AD deployment.

## ad-to-zimbra.py
ad-to-zimbra.py gets information out of AD and creates batch file for zmprov
Already existing data in zimbra will be left intact, only new groups or group memers are added.
Users without mail field are skipped.

*There is a little hack in user DN search for members in OU's wich names contains special symbols in their DN, Users DN is cut to conents of it's CN part with hope that it really contains user's name, if first search fails - another one is lauched for user's 'name' field.*

## zimbra-to-ad.py
zimbra-to-ad.py gets information of existing groups in Zimbra from Zimbra's zmprov dump file (ZimbraDumpFile), creation of this file described in troubleshooting part. ZimbraDumpFile is simply a list of existing Distribution groups and members for each group.
Script loops trough it and tries to create similar groups populated with members in AD.


# Setup and troubleshooting
#### Creating ZimbraDumpFile for zimbra-to-ad.py
From zimbra host as user zimbra run:
`zmprov gadl -v > /opt/zimbra/zimbra-adgroup-sync/zimbra-test.txt`

#### If you are using Python's virtual environment to install python-ldap
Crontab job may fail if any of required packages or python versions is not avaiable outside virtual environment.

You may use this simple bash script, just change second line to match you environment.
*syncDL.sh example*
```bash
    #!/bin/bash
    cd /opt/zimbra/zimbra-adgroup-sync/
    source bin/activate
    python ad-to-zimbra.py
```

#### Running batch file generated by ad-to-zimbra.py:
 Final result of running ad-to-zimbra.py is a ***ad-to-zimbra.log*** file, it containts commands that can be understood by and structured to be compalable with **zmprov** from zimbra distribution.

You may run batch import as *root* - or *su* into and run it as user *zimbra*

 Example as zimbra
 `zmprov -f commands.zmp`
 
 Piping whole file as root user
 `cat commands.zmp | su - zimbra -c zmprov`

User *zimbra* may lack neccesary permissions to create output files and logs
```bash
chown -R zimbra:zimbra /opt/zimbra/zimbra-adgroup-sync/
```

Example crontab
*This will run syncDL.sh and run batch import every 4 hours*
```bash
0 */4 * * * /opt/zimbra/zimbra-adgroup-sync/syncDL.sh && zmprov -f /opt/zimbra/zimbra-adgroup-sync/ad-to-zimbra.log
```