import unittest

from transcription import data_studio


class DataStudioSafetyTests(unittest.TestCase):
    def test_secret_bearing_column_names_are_protected(self):
        for name in (
            "password_hash", "code_hash", "token_digest", "totp_secret",
            "api_key", "provider_id", "credential_value",
        ):
            with self.subTest(name=name):
                self.assertTrue(data_studio._protected(name))

    def test_regular_business_columns_remain_visible(self):
        for name in ("id", "email", "created_at", "ticket_number", "status"):
            with self.subTest(name=name):
                self.assertFalse(data_studio._protected(name))

    def test_identifiers_accept_only_safe_postgresql_names(self):
        self.assertEqual(data_studio._safe_name("customer_events"), "customer_events")
        for name in ("Customer", "drop table", "a.b", "x;delete", ""):
            with self.subTest(name=name), self.assertRaises(ValueError):
                data_studio._safe_name(name)

    def test_update_and_delete_require_conditions(self):
        class Cursor:
            def execute(self, _query, _params):
                self._rows = [("r", "id"), ("r", "status")]
            def fetchall(self):
                return self._rows

        for operation in ("update", "delete"):
            payload = {"operation": operation, "schema": "public", "table": "tasks"}
            if operation == "update":
                payload["values"] = [{"column": "status", "value": "done"}]
            with self.subTest(operation=operation), self.assertRaisesRegex(ValueError, "conditions_required"):
                data_studio._build_plan(Cursor(), payload)

    def test_cross_schema_join_is_a_parameterized_select_plan(self):
        class Cursor:
            def execute(self, _query, params):
                columns = ["id", "customer_id"] if params[1] == "orders" else ["id", "name"]
                self._rows = [("r", column) for column in columns]
            def fetchall(self):
                return self._rows

        operation, _query, params, mutation, target = data_studio._build_plan(Cursor(), {
            "operation": "select", "schema": "sales", "table": "orders",
            "fields": [{"source": 0, "column": "id"}, {"source": 1, "column": "name"}],
            "joins": [{"schema": "crm", "table": "customers", "type": "left",
                       "left_source": 0, "left_column": "customer_id", "right_column": "id"}],
            "conditions": [{"source": 1, "column": "name", "operator": "contains", "value": "Acme"}],
            "sort": {"source": 0, "column": "id", "direction": "desc"},
            "limit": 100,
        })
        self.assertEqual((operation, mutation, target), ("select", False, "sales.orders"))
        self.assertEqual(params, ["%Acme%", 100])
        self.assertIn("DESC", str(_query))

    def test_sql_editor_accepts_one_safe_statement(self):
        statement, operation, mutation = data_studio._raw_sql_plan(
            "SELECT id, status FROM public.tasks WHERE status = 'open';"
        )
        self.assertEqual(operation, "select")
        self.assertFalse(mutation)
        self.assertIn("public.tasks", statement)
        quoted, operation, mutation = data_studio._raw_sql_plan(
            "SELECT 'semicolon; and COPY are data, not commands' AS example;"
        )
        self.assertEqual(operation, "select")
        self.assertFalse(mutation)
        self.assertIn("semicolon;", quoted)

    def test_sql_editor_requires_preview_for_mutations_and_where_for_mass_changes(self):
        statement, operation, mutation = data_studio._raw_sql_plan(
            "UPDATE public.tasks SET status = 'done' WHERE id = 42"
        )
        self.assertEqual(operation, "update")
        self.assertTrue(mutation)
        self.assertTrue(statement.startswith("UPDATE"))
        for query in (
            "DELETE FROM public.tasks",
            "UPDATE public.tasks SET status = 'done'",
            "SELECT 1; SELECT 2",
            "TRUNCATE public.tasks",
            "CREATE FUNCTION dangerous() RETURNS void AS $$ BEGIN END $$ LANGUAGE plpgsql",
        ):
            with self.subTest(query=query), self.assertRaises(ValueError):
                data_studio._raw_sql_plan(query)

    def test_saved_query_parameters_ignore_casts_and_quoted_text(self):
        query = (
            "SELECT ':literal' AS sample, id FROM public.tasks "
            "WHERE created_at >= :start_date::date AND owner_id = :owner_id "
            "OR reviewer_id = :owner_id"
        )
        self.assertEqual(
            data_studio._named_parameters(query),
            ["start_date", "owner_id"],
        )

    def test_saved_query_parameters_are_bound_without_interpolation(self):
        query = "SELECT * FROM public.tasks WHERE owner_id=:owner AND status=:status OR assignee_id=:owner"
        bound, values = data_studio._bind_named_parameters(
            query, {"owner": "7", "status": "open"},
        )
        self.assertEqual(bound.count("%s"), 3)
        self.assertNotIn("open", bound)
        self.assertEqual(values, ["7", "open", "7"])
        with self.assertRaisesRegex(ValueError, "parameter_required:status"):
            data_studio._bind_named_parameters(query, {"owner": "7"})


if __name__ == "__main__":
    unittest.main()
