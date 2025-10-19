#!/usr/bin/env python3

import argparse
import itertools
import json
import os
import re
import socket
import subprocess

sql_dir = "databases/sql"
go_path = os.environ["GOPATH"]
code_dir = "."
mysql_host = os.environ.get("MYSQL_HOST", "localhost")
mysql_port = os.environ.get("MYSQL_PORT", default="3306")
mysql_root_password = os.environ.get("MYSQL_ROOT_PASSWORD", "")
postgres_host = os.environ.get("POSTGRES_HOST", "localhost")
d_env = dict(os.environ, MYSQL_PWD=f"{mysql_root_password}")
all_dbs = {}
all_users = {}


def need_migration(ci_file):
    with open(ci_file) as f:
        ci = json.load(f)
    for task in ci.get("BeforeTest", []):
        if task["TYPE"] == "migrate_mysql":
            if task.get("MigrateSQLDir", ""):
                return True
    return False


def get_services(folders):
    concise = lambda f: f
    return sorted(list(set(map(concise, itertools.chain(*(get_service(folder) for folder in folders))))))


def get_service(folder):
    f = folder
    while f != code_dir:
        db = os.path.join(f, "scripts/db.json")
        if os.path.isfile(db) and need_migration(db):
            return [f]
        f = os.path.dirname(f)
    return [root for root, dirs, files in os.walk(folder)
            if "db.json" in files and need_migration(os.path.join(root, "scripts/db.json"))]


def get_sql_files(folder):
    return sorted([os.path.join(root, f)
                   for root, dirs, files in os.walk(folder)
                   for f in files
                   if re.match(r".*\.sql$", f)])


def run_mysql(cmd):
    subprocess.check_call(
        ["mysql", "-uroot", "-h", mysql_host, "-P", mysql_port,"-e", cmd], env=d_env
    )


def run_postgres(name, cmd, isfile=False):
    subprocess.check_call(["psql", "-U", "postgres", "-h", postgres_host, "-w", "-d", name, ("-f" if isfile else "-c"), cmd])


# This is the old legacy way of doing things
def init_tables(db):
    print("Creating schemas for %s ..." % db["name"])
    sql_folder = os.path.join(sql_dir, db["sql_dir"]) if "sql_dir" in db else sql_dir

    sqls = get_sql_files(sql_folder)
    errors = []
    for sql in sqls:
        with open(sql) as f:
            content = f.read()
        p = subprocess.Popen(
            [
                "mysql",
                "-uroot",
                "-h",
                mysql_host,
                "-P",
                mysql_port,
                db["name"]
            ],
            stdin=subprocess.PIPE,
            env=d_env
        )
        p.communicate(input=str.encode(re.sub(r"^--\s*\+migrate Down[\s\S]*", r"", content, flags=re.M)))
        if p.returncode != 0:
            errors.append(sql)

    print("Imported %d sql files" % (len(sqls) - len(errors)))
    if errors:
        print(">> Failed to import these sql files: \n\t%s" % "\n\t".join(errors))
        exit(-2)


# This is the new versioned mysql route
def migrate_mysql_tables(db, action):
    sql_folder = db["sql_dir"]
    db_dir = os.path.dirname(os.path.dirname(sql_folder))
    conf_file = os.path.join(sql_folder, "dbconfig.yml")

    command = {"init":"up", "down-to-bottom": "down"}.get(action, action)
    p = subprocess.check_call(["sql-migrate", command, "-config=" + conf_file] + (
        ["-limit=0"] if action == "down-to-bottom" else []), cwd=db_dir)
    if p:
        print ("Error applying schema for %s" % db["name"])
        # One probable cause could be miss-configuration of config
        mysql_migration_warning_message()
        exit(-1)


def migrate_postgres_tables(db):
    [run_postgres(db["name"], f, True)
            for f in get_sql_files(db["sql_dir"])]


# This will run any specified data population
def populate_database(db):
    if ("populate_dir" in db) and (db["populate_dir"] != ""):
        print("Populating database with %s" % db["populate_dir"][len(code_dir) + 1:])
        with open(db["populate_dir"]) as f:
            subprocess.check_call(
                [
                    "mysql",
                    "-uroot",
                    "-h",
                    mysql_host,
                    "-P",
                    mysql_port,
                    db["name"]
                ],
                stdin=f,
                env=d_env
            )
    else:
        print("No data population configured for %s" % db["name"])


def create_and_grant_mysql(name, user, password, sql_dir):
    if name not in all_dbs:
        run_mysql("DROP DATABASE IF EXISTS %s; CREATE DATABASE %s;" % (name, name))
        all_dbs[name] = sql_dir
        print("Created database %s" % name)
    else:
        if sql_dir != all_dbs[name]:
            print("Database %s has different directories for migration '%s' vs '%s'" % (name, all_dbs[name], sql_dir))
            exit(-4)
        print("Database %s has been created before; skip" % name)

    if user in all_users and password != all_users[user]:
        print("Database username %s has different passwords '%s' and '%s'" % (user, all_users[user], password))
        exit(-5)

    if user == "root":
        print("root is not allowed as a database username.")
        exit(-6)

    all_users[user] = password

    def get_ips():
        result = ["127.0.0.1", "localhost"]
        try:
            result.append(socket.gethostbyname(socket.gethostname()))
        except socket.gaierror:
            pass
        return result

    # use the update syntax for MySQL 8.x while keeping backwards compatibility
    for host in get_ips():
        run_mysql("CREATE USER IF NOT EXISTS '%s'@'%s' IDENTIFIED BY '%s';" % (user, host, password))
        run_mysql("GRANT ALL PRIVILEGES ON %s.* TO '%s'@'%s';" % (name, user, host))
    run_mysql("FLUSH PRIVILEGES;")


def create_and_grant_postgres(name):
    run_postgres("postgres", "DROP DATABASE IF EXISTS %s;" % name)
    run_postgres("postgres", "CREATE DATABASE %s OWNER postgres;" % name)
    print("Create postgres %s" % name)


def can_connect_mysql(cmd):
    """This method will check if we connect to MySQL.
    It uses current env vars, like rest of the code."""
    try:
        subprocess.check_output(
            [
                "mysql",
                "-uroot",
                "-h",
                mysql_host,
                "-P",
                mysql_port,
                "-e",
                cmd
            ],
            env=d_env
        )
    except subprocess.CalledProcessError:
        # in case of non-zero exit from subprocess this will happen, which would mean we failed to connect.
        return False
    return True

def mysql_migration_warning_message():
    print("\n\n"
          "NOTE: This script assumes that you are using the default MySQL installation.\n"
          "If you have changed MySQL's root password, you will see `Access Denied` error messages from MySQL.\n"
          "In such case try setting the following env vars to their appropriate values:\n\n"
          "MYSQL_HOST\n"
          "MYSQL_PORT\n"
          "MYSQL_USER\n"
          "MYSQL_PASSWORD\n"
          "MYSQL_ROOT_PASSWORD\n")
    exit(-4)

def migrate_mysql(db, action):
    # Check if we cannot talk to MySQL print the warning and exit
    if can_connect_mysql("clear") is False:
        mysql_migration_warning_message()

    skip = db["name"] in all_dbs

    if action == "test":
        for a in ("create", "up", "down-to-bottom", "up", "datapop"):
            migrate_mysql_with_skip(db, a, skip)
    else:
        migrate_mysql_with_skip(db, action, skip)


def migrate_mysql_with_skip(db, action, skip):
    print("=> %s: " % action, end="")
    if action in ("init", "create"):
        create_and_grant_mysql(db["name"], db["user"], db["password"], db["sql_dir"])

    if not skip and action in ("init", "up", "down", "down-to-bottom", "status"):
        migrate_mysql_tables(db, action)

    if action in ("init", "datapop"):
        populate_database(db)


def migrate_postgres(db, action):
    if action in ("init", "test"):
        migrate_postgres_tables(db)


def init_service(service, max_len, action):
    os.chdir(os.path.join(code_dir, service))

    prefix = 30 + (max_len - len(service)) // 2
    suffix = 60 + max_len - len(service) - prefix
    print("-" * prefix + service + "-" * suffix)

    with open("./scripts/db.json") as f:
        ci = json.load(f)

    # perform versioned creation of databases and run their sql
    [migrate_mysql(dict(
        name=task["DBName"],
        user=task["TestUser"],
        password=task["TestPassword"],
        populate_dir=re.sub(r"\$CODE_DIR", code_dir, task.get("PopulateSQL", "")),
        sql_dir=re.sub(r"\$CODE_DIR", code_dir, task["MigrateSQLDir"])), action)
        for task in ci.get("BeforeTest", [])
        if task["TYPE"] == "migrate_mysql" and "MigrateSQLDir" in task]

    [migrate_postgres(dict(
        name=task["DBName"],
        sql_dir=re.sub(r"\$CODE_DIR", code_dir, task["MigrateSQLDir"])), action)
        for task in ci.get("BeforeTest", [])
        if task["TYPE"] == "migrate_postgres"]


def init(folders, action):
    services = get_services(folders)
    max_len = max([len(s) for s in services] + [0])
    for service in services:
        init_service(service, max_len, action)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate databases.")
    parser.add_argument("paths", nargs="*", default=[""])
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-up", "--up", action="store_const", const="up", dest="action")
    group.add_argument("-down", "--down", action="store_const", const="down", dest="action")
    group.add_argument("-status", "--status", action="store_const", const="status", dest="action")
    group.add_argument("-create", "--create", action="store_const", const="create", dest="action")
    group.add_argument("-datapop", "--datapop", action="store_const", const="datapop", dest="action")
    group.add_argument("-test", "--test", action="store_const", const="test", dest="action")

    args = parser.parse_args()

    print("~~~ Start to initialize mysql/postgres databases ~~~")

    init([os.path.realpath(os.path.join(code_dir, p)) for p in args.paths], args.action)

    print("~~~ End to initialize mysql/postgres databases ~~~")
