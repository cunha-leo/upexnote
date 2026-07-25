"""Data Studio read-only PostgreSQL catalogue and table preview.

Every entry point revalidates the actor in the active database. Identifiers are
resolved against pg_catalog and composed with psycopg2.sql; user input is never
interpolated into SQL. Known secret-bearing columns are masked before leaving
the worker.
"""
from datetime import date, datetime, time
from decimal import Decimal
from uuid import UUID

from psycopg2 import sql

from . import db


_SENSITIVE_PARTS = (
    "password", "passwd", "secret", "token", "api_key", "apikey",
    "private_key", "credential", "salt", "hash", "digest", "totp",
    "provider_id", "provider_scopes",
)
_FILTER_OPS = {"eq", "contains", "starts", "gt", "gte", "lt", "lte", "is_null"}


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


def _guard(cur, actor_id):
    if not db.is_admin_user(cur, actor_id):
        return {"ok": False, "error": "forbidden"}
    if db.storage_mode() != "vps":
        return {"ok": False, "error": "postgres_required"}
    return None


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
        return {"ok": True, "mode": "vps", "read_only": True, "schemas": schemas}
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
