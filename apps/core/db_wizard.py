"""PostgreSQL connect / create-role helpers for the setup wizard."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import quote_plus

import psycopg
from psycopg import sql

RESERVED_PREFIXES = {"CVE", "BDU"}


@dataclass
class DbParams:
    host: str
    port: int
    name: str
    user: str
    password: str
    sslmode: str = "prefer"

    def as_url(self) -> str:
        return (
            f"postgres://{quote_plus(self.user)}:{quote_plus(self.password)}"
            f"@{self.host}:{self.port}/{self.name}?sslmode={self.sslmode}"
        )


def _conninfo(
    p: DbParams,
    *,
    dbname: Optional[str] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
) -> str:
    return (
        f"host={p.host} port={p.port} dbname={dbname or p.name} "
        f"user={user or p.user} password={password if password is not None else p.password} "
        f"sslmode={p.sslmode} connect_timeout=5"
    )


def test_connection(p: DbParams) -> tuple[bool, str]:
    try:
        with psycopg.connect(_conninfo(p)) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.execute(
                    "SELECT has_database_privilege(current_user, current_database(), 'CREATE')"
                )
                can_create = cur.fetchone()[0]
        msg = "Подключение успешно."
        if not can_create:
            msg += " Внимание: нет права CREATE в базе — миграции могут не пройти."
        return True, msg
    except Exception as e:
        return False, _friendly_error(e)


def create_role_and_database(
    *,
    host: str,
    port: int,
    superuser: str,
    super_password: str,
    db_name: str,
    role_name: str,
    role_password: str,
    sslmode: str = "prefer",
) -> tuple[bool, str, Optional[DbParams]]:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,62}", role_name):
        return False, "Некорректное имя пользователя БД.", None
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,62}", db_name):
        return False, "Некорректное имя базы данных.", None
    admin = DbParams(host, port, "postgres", superuser, super_password, sslmode)
    try:
        with psycopg.connect(_conninfo(admin), autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role_name,))
                if not cur.fetchone():
                    cur.execute(
                        sql.SQL("CREATE USER {} WITH PASSWORD {}").format(
                            sql.Identifier(role_name), sql.Literal(role_password)
                        )
                    )
                else:
                    cur.execute(
                        sql.SQL("ALTER USER {} WITH PASSWORD {}").format(
                            sql.Identifier(role_name), sql.Literal(role_password)
                        )
                    )
                cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
                if not cur.fetchone():
                    cur.execute(
                        sql.SQL("CREATE DATABASE {} OWNER {} ENCODING 'UTF8'").format(
                            sql.Identifier(db_name), sql.Identifier(role_name)
                        )
                    )
                cur.execute(
                    sql.SQL("GRANT ALL PRIVILEGES ON DATABASE {} TO {}").format(
                        sql.Identifier(db_name), sql.Identifier(role_name)
                    )
                )
        with psycopg.connect(_conninfo(admin, dbname=db_name), autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql.SQL("GRANT ALL ON SCHEMA public TO {}").format(sql.Identifier(role_name))
                )
                cur.execute(
                    sql.SQL(
                        "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO {}"
                    ).format(sql.Identifier(role_name))
                )
                cur.execute(
                    sql.SQL(
                        "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO {}"
                    ).format(sql.Identifier(role_name))
                )
        target = DbParams(host, port, db_name, role_name, role_password, sslmode)
        ok, msg = test_connection(target)
        if ok:
            return (
                True,
                "УЗ и база созданы, проверка входа прошла успешно. Пароль суперпользователя не сохраняется.",
                target,
            )
        return False, f"Создано, но проверка входа не удалась: {msg}", None
    except Exception as e:
        return False, _friendly_error(e), None


def write_database_url_to_env(database_url: str, env_path: Path | str) -> None:
    env_path = Path(env_path)
    lines: list[str] = []
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()
    out: list[str] = []
    found = False
    for line in lines:
        if line.startswith("DATABASE_URL="):
            out.append(f"DATABASE_URL={database_url}")
            found = True
        else:
            out.append(line)
    if not found:
        out.append(f"DATABASE_URL={database_url}")
    env_path.write_text("\n".join(out) + "\n", encoding="utf-8")


def validate_local_prefix(prefix: str) -> tuple[bool, str]:
    prefix = (prefix or "").strip().upper()
    if not re.fullmatch(r"[A-Z0-9]{2,16}", prefix):
        return False, "Префикс: 2–16 символов, латиница/цифры."
    if prefix in RESERVED_PREFIXES:
        return False, f"Префикс {prefix} зарезервирован."
    return True, prefix


def _friendly_error(exc: Exception) -> str:
    text = str(exc)
    low = text.lower()
    if "password authentication failed" in low:
        return "Неверный пароль или пользователь PostgreSQL."
    if "does not exist" in low and "database" in low:
        return "База данных не существует."
    if "connection refused" in low or "could not connect" in low:
        return "PostgreSQL не запущен или недоступен по указанному host/port."
    if "permission denied" in low:
        return "Недостаточно прав у учётной записи PostgreSQL."
    return f"Ошибка PostgreSQL: {text}"


# Compatibility aliases used by views_setup
test_connection = test_connection
create_role_and_database = create_role_and_database
write_database_url_to_env = write_database_url_to_env
validate_local_prefix = validate_local_prefix
DbParams = DbParams
