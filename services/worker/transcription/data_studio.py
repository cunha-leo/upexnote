"""Data Studio PostgreSQL catalogue and safe visual query builder.

Every entry point revalidates the actor in the active database. Identifiers are
resolved against pg_catalog and composed with psycopg2.sql; user input is never
interpolated into SQL. Known secret-bearing columns are masked before leaving
the worker.
"""
from datetime import date, datetime, time
from decimal import Decimal
import hashlib
import json
import re
from uuid import UUID

from psycopg2 import sql

from . import db


_SENSITIVE_PARTS = (
    "password", "passwd", "secret", "token", "api_key", "apikey",
    "private_key", "credential", "salt", "hash", "digest", "totp",
    "provider_id", "provider_scopes",
)
_FILTER_OPS = {"eq", "contains", "starts", "gt", "gte", "lt", "lte", "is_null"}
_BUILDER_OPS = {"select", "insert", "update", "delete", "create_table", "alter_table"}
_CONDITION_OPS = {
    "eq": "=", "ne": "<>", "gt": ">", "gte": ">=", "lt": "<", "lte": "<=",
}
_JOIN_TYPES = {"inner": "INNER JOIN", "left": "LEFT JOIN", "right": "RIGHT JOIN", "full": "FULL JOIN"}
_DDL_TYPES = {
    "text": "TEXT", "varchar": "VARCHAR(255)", "integer": "INTEGER",
    "bigint": "BIGINT", "numeric": "NUMERIC", "boolean": "BOOLEAN",
    "date": "DATE", "timestamptz": "TIMESTAMP WITH TIME ZONE",
    "jsonb": "JSONB", "uuid": "UUID",
}
_NAME = re.compile(r"^[a-z][a-z0-9_]{0,62}$")
_SQL_READ_OPS = {"select", "show", "explain"}
_SQL_MUTATION_OPS = {"insert", "update", "delete", "create", "alter", "drop"}
_SQL_FORBIDDEN = re.compile(
    r"\b(copy|grant|revoke|truncate|vacuum|analyze|cluster|reindex|listen|notify|"
    r"load|call|do|execute|prepare|deallocate|reset|discard|security\s+definer)\b",
    re.IGNORECASE,
)


def _protected(column: str) -> bool:
    lowered = column.lower()
    return any(part in lowered for part in _SENSITIVE_PARTS)


def _json_value(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, (bytes, bytearray, memoryview)):
        return "[binary]"
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    return str(value)


def _sql_without_comments(value):
    """Remove comments while preserving quoted content for safe statement checks."""
    text = str(value or "")
    output, index, quote = [], 0, None
    while index < len(text):
        char = text[index]
        pair = text[index:index + 2]
        if quote:
            output.append(char)
            if char == quote:
                if index + 1 < len(text) and text[index + 1] == quote:
                    output.append(text[index + 1]); index += 1
                else:
                    quote = None
            index += 1
            continue
        if char in {"'", '"'}:
            quote = char; output.append(char); index += 1; continue
        if pair == "--":
            end = text.find("\n", index + 2)
            index = len(text) if end < 0 else end
            output.append("\n")
            continue
        if pair == "/*":
            end = text.find("*/", index + 2)
            if end < 0:
                raise ValueError("unterminated_comment")
            output.append(" ")
            index = end + 2
            continue
        output.append(char); index += 1
    if quote:
        raise ValueError("unterminated_quote")
    return "".join(output).strip()


def _raw_sql_plan(value):
    statement = _sql_without_comments(value)
    if not statement:
        raise ValueError("sql_required")
    structure, quote = [], None
    index = 0
    while index < len(statement):
        char = statement[index]
        if quote:
            structure.append(" ")
            if char == quote:
                if index + 1 < len(statement) and statement[index + 1] == quote:
                    structure.append(" "); index += 1
                else:
                    quote = None
            index += 1
            continue
        if char in {"'", '"'}:
            quote = char; structure.append(" "); index += 1; continue
        structure.append(char); index += 1
    structural_sql = "".join(structure)
    chunks = [item.strip() for item in structural_sql.split(";") if item.strip()]
    if len(chunks) != 1:
        raise ValueError("single_statement_required")
    statement = statement.rstrip().rstrip(";").rstrip()
    structural_sql = structural_sql.rstrip().rstrip(";").rstrip()
    match = re.match(r"^\s*([a-z]+)", structural_sql, re.IGNORECASE)
    operation = match.group(1).lower() if match else ""
    if operation == "with":
        # CTEs may hide mutations. Keep v0.26 deterministic and explicitly safe.
        raise ValueError("cte_not_supported")
    if operation not in _SQL_READ_OPS | _SQL_MUTATION_OPS:
        raise ValueError("operation_not_allowed")
    if _SQL_FORBIDDEN.search(structural_sql):
        raise ValueError("operation_not_allowed")
    if operation in {"update", "delete"} and not re.search(r"\bwhere\b", structural_sql, re.IGNORECASE):
        raise ValueError("conditions_required")
    if operation == "create" and not re.match(
            r"^\s*create\s+(table|index|unique\s+index|view|materialized\s+view|schema)\b",
            structural_sql, re.IGNORECASE):
        raise ValueError("operation_not_allowed")
    if operation == "alter" and not re.match(
            r"^\s*alter\s+(table|index|view|materialized\s+view|schema)\b",
            structural_sql, re.IGNORECASE):
        raise ValueError("operation_not_allowed")
    if operation == "drop" and not re.match(
            r"^\s*drop\s+(table|index|view|materialized\s+view|schema)\b",
            structural_sql, re.IGNORECASE):
        raise ValueError("operation_not_allowed")
    return statement, operation, operation in _SQL_MUTATION_OPS


def sql_editor(actor_id, data):
    """Preview or execute one protected PostgreSQL statement from the SQL editor."""
    conn = db.connect()
    try:
        with conn.cursor() as cur:
            denied = _guard(cur, actor_id)
            if denied:
                return denied
            statement, operation, mutation = _raw_sql_plan(data.get("sql"))
            plan_hash = hashlib.sha256(statement.encode("utf-8")).hexdigest()
            if not data.get("execute"):
                return {"ok": True, "preview": True, "mutation": mutation,
                        "operation": operation, "sql": statement, "plan_hash": plan_hash}
            if mutation and str(data.get("plan_hash") or "") != plan_hash:
                return {"ok": False, "error": "confirmation_required"}
            cur.execute("SET LOCAL statement_timeout = '15s'")
            cur.execute(statement)
            if cur.description:
                columns = [item[0] for item in cur.description]
                fetched = cur.fetchmany(501)
                rows = []
                for row in fetched[:500]:
                    rows.append({
                        column: ("[protected]" if _protected(column) and value is not None else _json_value(value))
                        for column, value in zip(columns, row)
                    })
                conn.rollback()
                return {"ok": True, "operation": operation, "columns": columns, "rows": rows,
                        "truncated": len(fetched) > 500}
            affected = max(0, cur.rowcount)
            db.audit(conn, actor_id, f"data_studio_sql_{operation}", "sql_editor", None, {
                "operation": operation, "affected": affected,
                "sql_digest": plan_hash, "statement_count": 1,
            })
        conn.commit()
        return {"ok": True, "operation": operation, "affected": affected}
    except ValueError as exc:
        conn.rollback()
        return {"ok": False, "error": str(exc)}
    except Exception:
        conn.rollback()
        raise
    finally:
        db.close_connection(conn)


def _guard(cur, actor_id):
    if not db.is_admin_user(cur, actor_id):
        return {"ok": False, "error": "forbidden"}
    if db.storage_mode() != "vps":
        return {"ok": False, "error": "postgres_required"}
    return None


def _object(cur, schema_name, table_name, privilege="SELECT"):
    access = sql.SQL("pg_catalog.pg_get_userbyid(c.relowner) = current_user") if privilege == "ALTER" else sql.SQL(
        "has_table_privilege(c.oid, %s)")
    query = sql.SQL("""
        SELECT c.relkind, a.attname
          FROM pg_catalog.pg_class c
          JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
          JOIN pg_catalog.pg_attribute a ON a.attrelid = c.oid
         WHERE n.nspname = %s AND c.relname = %s
           AND c.relkind IN ('r', 'p', 'v', 'm')
           AND a.attnum > 0 AND NOT a.attisdropped
           AND {}
         ORDER BY a.attnum
    """).format(access)
    params = (schema_name, table_name) if privilege == "ALTER" else (schema_name, table_name, privilege)
    cur.execute(query, params)
    rows = cur.fetchall()
    return {"kind": rows[0][0], "columns": [row[1] for row in rows]} if rows else None


def _safe_name(value):
    value = str(value or "")
    if not _NAME.fullmatch(value):
        raise ValueError("invalid_identifier")
    return value


def _condition_sql(item, sources):
    source = int(item.get("source", 0))
    if source < 0 or source >= len(sources):
        raise ValueError("invalid_source")
    column = str(item.get("column") or "")
    if column not in sources[source]["columns"] or _protected(column):
        raise ValueError("invalid_column")
    operator = str(item.get("operator") or "eq")
    field = sql.SQL("{}.{}").format(sql.Identifier(f"t{source}"), sql.Identifier(column))
    if operator == "is_null":
        return sql.SQL("{} IS NULL").format(field), []
    if operator == "is_not_null":
        return sql.SQL("{} IS NOT NULL").format(field), []
    if operator == "contains":
        return sql.SQL("{}::text ILIKE %s").format(field), [f"%{item.get('value', '')}%"]
    if operator == "starts":
        return sql.SQL("{}::text ILIKE %s").format(field), [f"{item.get('value', '')}%"]
    if operator not in _CONDITION_OPS:
        raise ValueError("invalid_operator")
    return sql.SQL("{} {} %s").format(field, sql.SQL(_CONDITION_OPS[operator])), [item.get("value")]


def _where(data, sources):
    parts, params = [], []
    for index, item in enumerate((data.get("conditions") or [])[:20]):
        fragment, values = _condition_sql(item, sources)
        if index:
            connector = "OR" if str(item.get("connector")).lower() == "or" else "AND"
            parts.append(sql.SQL(connector))
        parts.append(fragment)
        params.extend(values)
    return (sql.SQL(" WHERE ") + sql.SQL(" ").join(parts), params) if parts else (sql.SQL(""), [])


def _build_plan(cur, data):
    operation = str(data.get("operation") or "select").lower()
    if operation not in _BUILDER_OPS:
        raise ValueError("invalid_operation")
    schema_name, table_name = str(data.get("schema") or ""), str(data.get("table") or "")

    if operation == "create_table":
        _safe_name(schema_name); _safe_name(table_name)
        cur.execute("""
            SELECT EXISTS (
                SELECT 1 FROM pg_catalog.pg_namespace n
                 WHERE n.nspname = %s AND has_schema_privilege(n.oid, 'CREATE')
            )
        """, (schema_name,))
        if not cur.fetchone()[0]:
            raise ValueError("schema_not_found_or_forbidden")
        columns = (data.get("columns") or [])[:40]
        if not columns:
            raise ValueError("columns_required")
        definitions = []
        for item in columns:
            name, type_key = _safe_name(item.get("name")), str(item.get("type") or "")
            if type_key not in _DDL_TYPES:
                raise ValueError("invalid_data_type")
            definition = sql.SQL("{} {}").format(sql.Identifier(name), sql.SQL(_DDL_TYPES[type_key]))
            if item.get("primary"):
                definition += sql.SQL(" PRIMARY KEY")
            elif not item.get("nullable", True):
                definition += sql.SQL(" NOT NULL")
            definitions.append(definition)
        query = sql.SQL("CREATE TABLE {}.{} ({})").format(
            sql.Identifier(schema_name), sql.Identifier(table_name), sql.SQL(", ").join(definitions))
        return operation, query, [], True, f"{schema_name}.{table_name}"

    privilege = "SELECT" if operation == "select" else operation.upper()
    if operation == "alter_table":
        privilege = "ALTER"
    base = _object(cur, schema_name, table_name, privilege)
    if not base:
        raise ValueError("object_not_found_or_forbidden")
    sources = [{"schema": schema_name, "table": table_name, **base}]

    if operation == "select":
        joins = (data.get("joins") or [])[:8]
        join_sql = []
        for index, item in enumerate(joins, 1):
            joined = _object(cur, str(item.get("schema") or ""), str(item.get("table") or ""), "SELECT")
            if not joined:
                raise ValueError("join_object_not_found")
            left_source = int(item.get("left_source", 0))
            left_column, right_column = str(item.get("left_column") or ""), str(item.get("right_column") or "")
            if left_source < 0 or left_source >= len(sources) or left_column not in sources[left_source]["columns"] or right_column not in joined["columns"]:
                raise ValueError("invalid_join")
            sources.append({"schema": str(item["schema"]), "table": str(item["table"]), **joined})
            join_type = _JOIN_TYPES.get(str(item.get("type") or "inner"), "INNER JOIN")
            join_sql.append(sql.SQL("{} {}.{} AS {} ON {}.{} = {}.{}").format(
                sql.SQL(join_type), sql.Identifier(item["schema"]), sql.Identifier(item["table"]),
                sql.Identifier(f"t{index}"), sql.Identifier(f"t{left_source}"), sql.Identifier(left_column),
                sql.Identifier(f"t{index}"), sql.Identifier(right_column)))
        selected = []
        for item in (data.get("fields") or [])[:100]:
            source, column = int(item.get("source", 0)), str(item.get("column") or "")
            if source < 0 or source >= len(sources) or column not in sources[source]["columns"] or _protected(column):
                raise ValueError("invalid_column")
            alias = f"{sources[source]['table']}.{column}"
            selected.append(sql.SQL("{}.{} AS {}").format(
                sql.Identifier(f"t{source}"), sql.Identifier(column), sql.Identifier(alias)))
        if not selected:
            selected = [sql.SQL("{}.{}").format(sql.Identifier("t0"), sql.Identifier(c))
                        for c in base["columns"] if not _protected(c)]
        where_sql, params = _where(data, sources)
        query = sql.SQL("SELECT {} FROM {}.{} AS {} {}{} LIMIT %s").format(
            sql.SQL(", ").join(selected), sql.Identifier(schema_name), sql.Identifier(table_name),
            sql.Identifier("t0"), sql.SQL(" ").join(join_sql), where_sql)
        sort = data.get("sort") or {}
        sort_source, sort_column = int(sort.get("source", 0)), str(sort.get("column") or "")
        if sort_column:
            if sort_source < 0 or sort_source >= len(sources) or sort_column not in sources[sort_source]["columns"] or _protected(sort_column):
                raise ValueError("invalid_sort")
            direction = "DESC" if str(sort.get("direction") or "").lower() == "desc" else "ASC"
            # Insert ORDER BY before the LIMIT already composed above.
            query = sql.SQL("SELECT {} FROM {}.{} AS {} {}{} ORDER BY {}.{} {} LIMIT %s").format(
                sql.SQL(", ").join(selected), sql.Identifier(schema_name), sql.Identifier(table_name),
                sql.Identifier("t0"), sql.SQL(" ").join(join_sql), where_sql,
                sql.Identifier(f"t{sort_source}"), sql.Identifier(sort_column), sql.SQL(direction))
        params.append(min(500, max(1, int(data.get("limit") or 100))))
        return operation, query, params, False, f"{schema_name}.{table_name}"

    if operation in {"insert", "update"}:
        values = data.get("values") or []
        clean = [(str(item.get("column") or ""), item.get("value")) for item in values]
        if not clean or any(column not in base["columns"] or _protected(column) for column, _ in clean):
            raise ValueError("invalid_values")
        if operation == "insert":
            query = sql.SQL("INSERT INTO {}.{} ({}) VALUES ({})").format(
                sql.Identifier(schema_name), sql.Identifier(table_name),
                sql.SQL(", ").join(sql.Identifier(column) for column, _ in clean),
                sql.SQL(", ").join(sql.Placeholder() for _ in clean))
            return operation, query, [value for _, value in clean], True, f"{schema_name}.{table_name}"
        where_sql, where_params = _where(data, sources)
        if not where_params and not (data.get("conditions") or []):
            raise ValueError("conditions_required")
        query = sql.SQL("UPDATE {}.{} AS t0 SET {}{}").format(
            sql.Identifier(schema_name), sql.Identifier(table_name),
            sql.SQL(", ").join(sql.SQL("{} = %s").format(sql.Identifier(column)) for column, _ in clean),
            where_sql)
        return operation, query, [value for _, value in clean] + where_params, True, f"{schema_name}.{table_name}"

    if operation == "delete":
        where_sql, params = _where(data, sources)
        if not (data.get("conditions") or []):
            raise ValueError("conditions_required")
        query = sql.SQL("DELETE FROM {}.{} AS t0{}").format(
            sql.Identifier(schema_name), sql.Identifier(table_name), where_sql)
        return operation, query, params, True, f"{schema_name}.{table_name}"

    action = str(data.get("alter_action") or "")
    column = _safe_name(data.get("column"))
    if action == "add_column":
        type_key = str(data.get("data_type") or "")
        if type_key not in _DDL_TYPES:
            raise ValueError("invalid_data_type")
        query = sql.SQL("ALTER TABLE {}.{} ADD COLUMN {} {}").format(
            sql.Identifier(schema_name), sql.Identifier(table_name), sql.Identifier(column), sql.SQL(_DDL_TYPES[type_key]))
    elif action == "rename_column":
        if column not in base["columns"]:
            raise ValueError("invalid_column")
        query = sql.SQL("ALTER TABLE {}.{} RENAME COLUMN {} TO {}").format(
            sql.Identifier(schema_name), sql.Identifier(table_name), sql.Identifier(column),
            sql.Identifier(_safe_name(data.get("new_name"))))
    elif action == "drop_column":
        if column not in base["columns"] or _protected(column):
            raise ValueError("invalid_column")
        query = sql.SQL("ALTER TABLE {}.{} DROP COLUMN {}").format(
            sql.Identifier(schema_name), sql.Identifier(table_name), sql.Identifier(column))
    else:
        raise ValueError("invalid_alter_action")
    return operation, query, [], True, f"{schema_name}.{table_name}"


def visual_query(actor_id, data):
    """Preview or execute a server-validated visual plan.

    SQL values are always parameters. Mutation previews contain placeholders,
    never private values. Execution requires the exact preview hash.
    """
    conn = db.connect()
    try:
        with conn.cursor() as cur:
            denied = _guard(cur, actor_id)
            if denied:
                return denied
            operation, query, params, mutation, target = _build_plan(cur, data)
            preview = query.as_string(conn)
            value_digest = hashlib.sha256(json.dumps(
                params, sort_keys=True, default=str, ensure_ascii=False).encode()).hexdigest()
            plan_hash = hashlib.sha256(json.dumps({
                "operation": operation, "target": target, "sql": preview,
                "param_count": len(params), "value_digest": value_digest,
            }, sort_keys=True).encode()).hexdigest()
            if not data.get("execute"):
                return {"ok": True, "preview": True, "mutation": mutation,
                        "operation": operation, "target": target, "sql": preview, "plan_hash": plan_hash}
            if mutation and str(data.get("plan_hash") or "") != plan_hash:
                return {"ok": False, "error": "confirmation_required"}
            cur.execute(query, params)
            if operation == "select":
                columns = [item[0] for item in cur.description]
                rows = [{column: _json_value(value) for column, value in zip(columns, row)}
                        for row in cur.fetchall()]
                return {"ok": True, "operation": operation, "columns": columns, "rows": rows}
            affected = max(0, cur.rowcount)
            db.audit(conn, actor_id, f"data_studio_{operation}", target, None, {
                "operation": operation, "target": target, "affected": affected,
                "sql_shape": preview, "parameter_count": len(params),
            })
        conn.commit()
        return {"ok": True, "operation": operation, "target": target, "affected": affected}
    except ValueError as exc:
        conn.rollback()
        return {"ok": False, "error": str(exc)}
    except Exception:
        conn.rollback()
        raise
    finally:
        db.close_connection(conn)


def catalog(actor_id):
    """Return schemas, relations, columns and foreign keys visible to the DB user."""
    conn = db.connect()
    try:
        with conn.cursor() as cur:
            denied = _guard(cur, actor_id)
            if denied:
                return denied
            cur.execute("""
                SELECT n.nspname AS schema_name,
                       c.relname AS object_name,
                       CASE c.relkind
                         WHEN 'r' THEN 'table' WHEN 'p' THEN 'partitioned_table'
                         WHEN 'v' THEN 'view' WHEN 'm' THEN 'materialized_view'
                       END AS object_type,
                       GREATEST(c.reltuples::bigint, 0) AS estimated_rows
                  FROM pg_catalog.pg_class c
                  JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
                 WHERE c.relkind IN ('r', 'p', 'v', 'm')
                   AND n.nspname <> 'information_schema'
                   AND n.nspname NOT LIKE 'pg\\_%' ESCAPE '\\'
                   AND has_schema_privilege(n.oid, 'USAGE')
                   AND has_table_privilege(c.oid, 'SELECT')
                 ORDER BY n.nspname, c.relname
            """)
            object_cols = [column[0] for column in cur.description]
            objects = [dict(zip(object_cols, row)) for row in cur.fetchall()]

            cur.execute("""
                SELECT n.nspname AS schema_name, c.relname AS object_name,
                       a.attname AS column_name,
                       pg_catalog.format_type(a.atttypid, a.atttypmod) AS data_type,
                       NOT a.attnotnull AS nullable,
                       pg_get_expr(ad.adbin, ad.adrelid) AS column_default,
                       EXISTS (
                         SELECT 1 FROM pg_catalog.pg_index i
                          WHERE i.indrelid = c.oid AND i.indisprimary
                            AND a.attnum = ANY(i.indkey)
                       ) AS primary_key,
                       a.attnum AS ordinal
                  FROM pg_catalog.pg_attribute a
                  JOIN pg_catalog.pg_class c ON c.oid = a.attrelid
                  JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
                  LEFT JOIN pg_catalog.pg_attrdef ad
                    ON ad.adrelid = a.attrelid AND ad.adnum = a.attnum
                 WHERE c.relkind IN ('r', 'p', 'v', 'm')
                   AND a.attnum > 0 AND NOT a.attisdropped
                   AND n.nspname <> 'information_schema'
                   AND n.nspname NOT LIKE 'pg\\_%' ESCAPE '\\'
                   AND has_schema_privilege(n.oid, 'USAGE')
                   AND has_table_privilege(c.oid, 'SELECT')
                 ORDER BY n.nspname, c.relname, a.attnum
            """)
            column_cols = [column[0] for column in cur.description]
            columns = [dict(zip(column_cols, row)) for row in cur.fetchall()]

            cur.execute("""
                SELECT src_ns.nspname AS schema_name, src.relname AS object_name,
                       src_col.attname AS column_name,
                       dst_ns.nspname AS target_schema, dst.relname AS target_table,
                       dst_col.attname AS target_column, con.conname AS constraint_name
                  FROM pg_catalog.pg_constraint con
                  JOIN pg_catalog.pg_class src ON src.oid = con.conrelid
                  JOIN pg_catalog.pg_namespace src_ns ON src_ns.oid = src.relnamespace
                  JOIN pg_catalog.pg_class dst ON dst.oid = con.confrelid
                  JOIN pg_catalog.pg_namespace dst_ns ON dst_ns.oid = dst.relnamespace
                  JOIN LATERAL unnest(con.conkey, con.confkey)
                       WITH ORDINALITY AS keys(src_num, dst_num, ord) ON TRUE
                  JOIN pg_catalog.pg_attribute src_col
                       ON src_col.attrelid = src.oid AND src_col.attnum = keys.src_num
                  JOIN pg_catalog.pg_attribute dst_col
                       ON dst_col.attrelid = dst.oid AND dst_col.attnum = keys.dst_num
                 WHERE con.contype = 'f'
                   AND src_ns.nspname <> 'information_schema'
                   AND src_ns.nspname NOT LIKE 'pg\\_%' ESCAPE '\\'
                   AND has_table_privilege(src.oid, 'SELECT')
                 ORDER BY src_ns.nspname, src.relname, con.conname, keys.ord
            """)
            relation_cols = [column[0] for column in cur.description]
            relations = [dict(zip(relation_cols, row)) for row in cur.fetchall()]

            cur.execute("""
                SELECT schemaname AS schema_name, tablename AS object_name,
                       indexname AS index_name, indexdef AS definition
                  FROM pg_catalog.pg_indexes
                 WHERE schemaname <> 'information_schema'
                   AND schemaname NOT LIKE 'pg\\_%' ESCAPE '\\'
                 ORDER BY schemaname, tablename, indexname
            """)
            index_cols = [column[0] for column in cur.description]
            indexes = [dict(zip(index_cols, row)) for row in cur.fetchall()]

        by_object = {}
        for item in objects:
            item["estimated_rows"] = int(item.get("estimated_rows") or 0)
            item["columns"] = []
            item["relations"] = []
            item["indexes"] = []
            by_object[(item["schema_name"], item["object_name"])] = item
        for column in columns:
            column["protected"] = _protected(column["column_name"])
            target = by_object.get((column.pop("schema_name"), column.pop("object_name")))
            if target:
                target["columns"].append(column)
        for relation in relations:
            target = by_object.get((relation.pop("schema_name"), relation.pop("object_name")))
            if target:
                target["relations"].append(relation)
        for index in indexes:
            target = by_object.get((index.pop("schema_name"), index.pop("object_name")))
            if target:
                target["indexes"].append(index)

        schemas = []
        for item in objects:
            schema = next((entry for entry in schemas if entry["name"] == item["schema_name"]), None)
            if schema is None:
                schema = {"name": item["schema_name"], "objects": []}
                schemas.append(schema)
            clean = dict(item)
            clean.pop("schema_name", None)
            schema["objects"].append(clean)
        return {"ok": True, "mode": "vps", "read_only": False, "schemas": schemas}
    finally:
        db.close_connection(conn)


def table_data(actor_id, data):
    """Read one validated table/view page with a small safe filter vocabulary."""
    schema_name = str(data.get("schema") or "")
    table_name = str(data.get("table") or "")
    page = max(1, int(data.get("page") or 1))
    page_size = min(100, max(10, int(data.get("page_size") or 50)))
    sort_column = str(data.get("sort") or "")
    sort_direction = "DESC" if str(data.get("direction") or "").lower() == "desc" else "ASC"
    filters = data.get("filters") if isinstance(data.get("filters"), list) else []

    conn = db.connect()
    try:
        with conn.cursor() as cur:
            denied = _guard(cur, actor_id)
            if denied:
                return denied
            cur.execute("""
                SELECT a.attname
                  FROM pg_catalog.pg_attribute a
                  JOIN pg_catalog.pg_class c ON c.oid = a.attrelid
                  JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
                 WHERE n.nspname = %s AND c.relname = %s
                   AND c.relkind IN ('r', 'p', 'v', 'm')
                   AND a.attnum > 0 AND NOT a.attisdropped
                   AND has_table_privilege(c.oid, 'SELECT')
                 ORDER BY a.attnum
            """, (schema_name, table_name))
            columns = [row[0] for row in cur.fetchall()]
            if not columns:
                return {"ok": False, "error": "object_not_found"}

            conditions, params = [], []
            for item in filters[:8]:
                column = str(item.get("column") or "")
                operator = str(item.get("operator") or "eq")
                value = item.get("value")
                if column not in columns or _protected(column) or operator not in _FILTER_OPS:
                    continue
                identifier = sql.Identifier(column)
                if operator == "is_null":
                    conditions.append(sql.SQL("{} IS NULL").format(identifier))
                elif operator == "contains":
                    conditions.append(sql.SQL("{}::text ILIKE %s").format(identifier))
                    params.append(f"%{value}%")
                elif operator == "starts":
                    conditions.append(sql.SQL("{}::text ILIKE %s").format(identifier))
                    params.append(f"{value}%")
                else:
                    symbol = {"eq": "=", "gt": ">", "gte": ">=", "lt": "<", "lte": "<="}[operator]
                    conditions.append(sql.SQL("{} {} %s").format(identifier, sql.SQL(symbol)))
                    params.append(value)

            select_columns = [
                sql.SQL("%s AS {}").format(sql.Identifier(column)) if _protected(column)
                else sql.Identifier(column)
                for column in columns
            ]
            for column in columns:
                if _protected(column):
                    params.insert(0, "[protected]")
            query = sql.SQL("SELECT {} FROM {}.{}").format(
                sql.SQL(", ").join(select_columns),
                sql.Identifier(schema_name),
                sql.Identifier(table_name),
            )
            if conditions:
                query += sql.SQL(" WHERE ") + sql.SQL(" AND ").join(conditions)
            if sort_column in columns and not _protected(sort_column):
                query += sql.SQL(" ORDER BY {} {} NULLS LAST").format(
                    sql.Identifier(sort_column), sql.SQL(sort_direction)
                )
            query += sql.SQL(" LIMIT %s OFFSET %s")
            params.extend([page_size + 1, (page - 1) * page_size])
            cur.execute(query, params)
            result_columns = [item[0] for item in cur.description]
            fetched = cur.fetchall()

        has_more = len(fetched) > page_size
        rows = [
            {column: _json_value(value) for column, value in zip(result_columns, row)}
            for row in fetched[:page_size]
        ]
        return {
            "ok": True, "read_only": True, "schema": schema_name, "table": table_name,
            "columns": result_columns, "rows": rows, "page": page,
            "page_size": page_size, "has_more": has_more,
        }
    finally:
        db.close_connection(conn)
