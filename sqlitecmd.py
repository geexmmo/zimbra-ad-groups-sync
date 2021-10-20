def SqliteCreateTables(db_con, mod):
    cur = db_con.cursor()
    cur.execute("DROP TABLE IF EXISTS '{}_lists'".format(mod))
    cur.execute("DROP TABLE IF EXISTS '{}_members'".format(mod))
    cur.execute("CREATE TABLE '{}_lists' ('id' INTEGER PRIMARY KEY AUTOINCREMENT, 'dlistname' text, UNIQUE(dlistname))".format(mod))
    cur.execute("CREATE TABLE '{}_members' ('mailbox' text, 'dlistid' int)".format(mod))
    db_con.commit()


def SqliteCreateGroup(groupname, db_con, mod):
    cur = db_con.cursor()
    cur.execute("INSERT INTO '{}_lists' ('dlistname') VALUES ('{}')".format(mod, groupname))
    db_con.commit()

def SqliteDeleteGroup(groupname, db_con, mod):
    cur = db_con.cursor()
    id = SqliteGetGroupId(groupname, db_con, mod)
    cur.execute("DELETE FROM '{}_lists' WHERE id = {}".format(mod, id))
    cur.execute("DELETE FROM '{}_members' WHERE dlistid = {}".format(mod, id))
    db_con.commit()


def SqliteGetGroupId(groupname, db_con, mod):
    cur = db_con.cursor()
    data = cur.execute("SELECT id FROM '{}_lists' WHERE dlistname = '{}'".format(mod, groupname)).fetchone()
    if data:
        (id,) = data
    else: id = False
    return id

def SqliteAddMember(groupname, memberemail, db_con, mod):
    cur = db_con.cursor()
    id = SqliteGetGroupId(groupname, db_con, mod)
    cur.execute("INSERT OR IGNORE INTO {}_members VALUES ('{}', '{}')".format(mod, memberemail, id))
    db_con.commit()

def SqliteDeleteMember(groupname, memberemail, db_con, mod):
    cur = db_con.cursor()
    id = SqliteGetGroupId(groupname, db_con, mod)
    cur.execute("DELETE FROM {}_members WHERE mailbox = '{}' AND dlistid = {} ".format(mod, memberemail, id))
    db_con.commit()

def SqliteListAllGroups(db_con, mod):
    cur = db_con.cursor()
    cur.execute("SELECT * FROM {}_lists".format(mod))
    datalist = cur.fetchall()
    return datalist

def SqliteListGroupMembers(id,db_con, mod):
    cur = db_con.cursor()
    cur.row_factory = lambda cur, row: row[0]
    cur.execute("SELECT mailbox FROM {}_members WHERE dlistid = {}".format(mod, id))
    datalist = cur.fetchall()
    return datalist
