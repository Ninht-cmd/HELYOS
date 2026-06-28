"""Tests fumée de l'API. Ignorés si FastAPI/httpx ne sont pas installés
(le cœur reste vérifiable sans la couche serveur — Local First)."""

import unittest

try:
    from fastapi.testclient import TestClient

    from jarvis_kernel.main import create_app

    _HAS_API = True
except Exception:  # ImportError ou dépendance manquante
    _HAS_API = False


@unittest.skipUnless(_HAS_API, "FastAPI non installé (couche serveur optionnelle)")
class TestApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(create_app())

    def test_health(self):
        r = self.client.get("/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "ok")

    def test_levels(self):
        r = self.client.get("/governance/levels")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()), 6)  # A0..A5

    def test_agents_lists_observer(self):
        r = self.client.get("/agents")
        names = [a["name"] for a in r.json()]
        self.assertIn("observer", names)

    def test_intent_delete_without_backup_denied(self):
        r = self.client.post("/intent", json={
            "action_type": "delete", "granted_level": "A5", "has_backup": False,
        })
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["decision"], "deny")
        self.assertEqual(body["rule"], "GR-1")
        self.assertFalse(body["allowed"])

    def test_intent_read_allowed(self):
        r = self.client.post("/intent", json={
            "action_type": "read", "granted_level": "A0",
        })
        self.assertEqual(r.json()["decision"], "allow")

    def test_intent_invalid_action_type(self):
        r = self.client.post("/intent", json={"action_type": "nope"})
        self.assertEqual(r.status_code, 400)

    def test_audit_records_after_intent(self):
        self.client.post("/intent", json={"action_type": "read", "granted_level": "A0"})
        r = self.client.get("/governance/audit?limit=5")
        self.assertEqual(r.status_code, 200)
        self.assertGreaterEqual(len(r.json()), 1)


if __name__ == "__main__":
    unittest.main()
