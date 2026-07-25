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


if __name__ == "__main__":
    unittest.main()
