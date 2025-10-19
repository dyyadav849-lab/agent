#!/usr/bin/env python3

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

sql_dir = "databases/sql"
code_dir = "."
postgres_host = os.environ.get("POSTGRES_HOST", "localhost")
all_dbs = {}


def need_migration(ci_file: str) -> bool:
    with Path(ci_file).open() as f:
        ci = json.load(f)
    return any(
        task["TYPE"] == "migrate_postgres" and task.get("MigrateSQLDir", "")
        for task in ci.get("BeforeTest", [])
    )


def get_services(folders: List[str]) -> List[str]:
    return sorted({f for folder in folders for f in get_service(folder)})


def get_service(folder: str) -> List[str]:
    f = Path(folder)
    while str(f) != code_dir:
        db = f / "scripts/db.json"
        if db.is_file() and need_migration(str(db)):
            return [str(f)]
        f = f.parent

    return [
        str(Path(root))
        for root, _, files in os.walk(folder)
        if "db.json" in files and need_migration(str(Path(root) / "scripts/db.json"))
    ]


def get_sql_files(folder: str) -> List[str]:
    return sorted(
        [
            str(Path(root) / f)
            for root, _, files in os.walk(folder)
            for f in files
            if f.endswith(".sql")
        ]
    )


def validate_sql_command(cmd: str) -> bool:
    """
    Validates the SQL command to prevent execution of untrusted input.
    Only allows a specific set of SQL commands.
    """
    allowed_commands = [
        "SELECT",
        "INSERT",
        "UPDATE",
        "DELETE",
        "CREATE",
        "ALTER",
        "DROP",
        "GRANT",
        "REVOKE",
    ]
    cmd_upper = cmd.strip().upper()
    return any(cmd_upper.startswith(keyword) for keyword in allowed_commands)


def run_postgres(name: str, cmd: str, *, isfile: bool = False) -> None:
    if isfile:
        command = ["psql", "-U", "", "-h", postgres_host, "-w", "-d", name, "-f", cmd]
    else:
        if not validate_sql_command(cmd):
            err_msg = f"Invalid or potentially dangerous SQL command detected: {cmd}"
            raise ValueError(err_msg)
        command = ["psql", "-U", "", "-h", postgres_host, "-w", "-d", name, "-c", cmd]

    subprocess.check_call(command)  # noqa: S603


def migrate_postgres_tables(db: Dict[str, Any], action: str) -> None:
    sql_files = get_sql_files(db["sql_dir"])

    if action == "up":
        for sql_file in sql_files:
            with Path(sql_file).open() as file:
                sql_commands = file.read()
            up_commands = re.findall(
                r"-- \+migrate Up((?:.|\n)*?)-- \+migrate Down", sql_commands
            )

            for command in up_commands:
                run_command(db["name"], command, sql_file)

    if action == "down":
        for sql_file in reversed(sql_files):
            with Path(sql_file).open() as file:
                sql_commands = file.read()
            down_commands = re.findall(r"-- \+migrate Down((?:.|\n)*)", sql_commands)

            for command in down_commands:
                run_command(db["name"], command, sql_file)


def run_command(db_name: str, command: str, sql_file: str) -> None:
    try:
        run_postgres(db_name, command.strip())
    except subprocess.CalledProcessError as e:
        err_msg = f"Error applying schema for {db_name} using file {sql_file}: {e}"
        raise subprocess.CalledProcessError(e.returncode, err_msg) from e
    except ValueError as e:
        err_msg = f"Security issue with command in file {sql_file}: {e!s}"
        raise ValueError(err_msg) from e


def create_and_grant_postgres(name: str) -> None:
    run_postgres("postgres", f"DROP DATABASE IF EXISTS {name};")
    run_postgres("postgres", f"CREATE DATABASE {name};")
    print(f"Create postgres {name}", file=sys.stderr)


def migrate_postgres(db: Dict[str, Any], action: str) -> None:
    if action in ("init", "create"):
        create_and_grant_postgres(db["name"])

    if action in ("init", "up", "down", "down-to-bottom", "status"):
        migrate_postgres_tables(db, action)


def init_service(service: str, max_len: int, action: str) -> None:
    os.chdir(str(Path(code_dir) / service))

    prefix = 30 + (max_len - len(service)) // 2
    suffix = 60 + max_len - len(service) - prefix
    print("-" * prefix + service + "-" * suffix, file=sys.stderr)

    with Path("./scripts/db.json").open() as f:
        ci = json.load(f)

    [
        migrate_postgres(
            {
                "name": task["DBName"],
                "sql_dir": re.sub(r"\$CODE_DIR", code_dir, task["MigrateSQLDir"]),
            },
            action,
        )
        for task in ci.get("BeforeTest", [])
        if task["TYPE"] == "migrate_postgres"
    ]


def init(folders: List[str], action: str) -> None:
    services = get_services(folders)

    max_len = max([len(s) for s in services] + [0])
    for service in services:
        init_service(service, max_len, action)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate databases.")
    parser.add_argument("paths", nargs="*", default=[""])
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-up", "--up", action="store_const", const="up", dest="action")
    group.add_argument(
        "-down", "--down", action="store_const", const="down", dest="action"
    )
    group.add_argument(
        "-status", "--status", action="store_const", const="status", dest="action"
    )
    group.add_argument(
        "-create", "--create", action="store_const", const="create", dest="action"
    )
    group.add_argument(
        "-test", "--test", action="store_const", const="test", dest="action"
    )

    args = parser.parse_args()

    print("~~~ Start to initialize postgres databases ~~~", file=sys.stderr)

    init([Path(code_dir).joinpath(p).resolve() for p in args.paths], args.action)

    print("~~~ End to initialize postgres databases ~~~", file=sys.stderr)
