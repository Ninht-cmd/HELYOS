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

    def test_jarvis_routes_portfolio_question(self):
        r = self.client.post("/jarvis", json={"message": "où en sont mes business ?"})
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["intent"], "portefeuille")
        self.assertIn("HELYOS Services", body["text"])

    def test_jarvis_dangerous_action_is_governed(self):
        r = self.client.post("/jarvis", json={
            "message": "supprime toute la base clients", "granted_level": "A5",
        })
        body = r.json()
        self.assertEqual(body["intent"], "action_dangereuse")
        self.assertTrue(body["governed"])
        self.assertEqual(body["decision"], "deny")
        self.assertEqual(body["rule"], "GR-1")

    def test_jarvis_rejects_empty_message(self):
        r = self.client.post("/jarvis", json={"message": ""})
        self.assertEqual(r.status_code, 422)  # min_length=1 (validation Pydantic)

    def test_jarvis_rejects_invalid_granted_level(self):
        # un niveau inconnu = 400 explicite, pas une rétrogradation silencieuse en A1
        r = self.client.post("/jarvis", json={"message": "bonjour", "granted_level": "A9"})
        self.assertEqual(r.status_code, 400)
        r = self.client.post("/intent", json={"action_type": "read", "granted_level": "banane"})
        self.assertEqual(r.status_code, 400)

    def test_events_limit_zero_does_not_dump_everything(self):
        # le piège history[-0:] : limit=0 doit renvoyer au plus 1 entrée, pas tout
        self.client.post("/intent", json={"action_type": "read", "granted_level": "A0"})
        self.client.post("/intent", json={"action_type": "read", "granted_level": "A0"})
        r = self.client.get("/events?limit=0")
        self.assertLessEqual(len(r.json()), 1)
        r = self.client.get("/governance/audit?limit=0")
        self.assertLessEqual(len(r.json()), 1)

    def test_portfolio_detail_and_task_completion(self):
        detail = self.client.get("/portfolio/detail").json()
        helyos = next(b for b in detail if b["name"].startswith("HELYOS Services"))
        before = helyos["open_tasks"]
        self.assertGreater(before, 0)
        prefix = next(t["task"] for t in helyos["tasks"] if not t["done"])[:30]
        r = self.client.post("/portfolio/complete-task", json={
            "business": helyos["name"], "task_prefix": prefix,
        })
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["open_tasks"], before - 1)
        # l'événement de pointage est tracé sur le bus
        names = [e["name"] for e in self.client.get("/events?limit=20").json()]
        self.assertIn("portfolio.task_done", names)

    def test_connectors_map_is_honest(self):
        r = self.client.get("/connectors")
        self.assertEqual(r.status_code, 200)
        by_name = {c["name"]: c for c in r.json()}
        self.assertEqual(by_name["tradingview"]["status"], "forbidden")
        self.assertIn("ADR-0010", by_name["tradingview"]["detail"])
        # non configuré => le statut le dit et liste ce qu'il faut fournir
        if by_name["shopify"]["status"] == "not_configured":
            self.assertIn("HELYOS_SHOPIFY", by_name["shopify"]["requires"])

    def test_connectors_sync_is_governed_and_survives_unconfigured(self):
        # hermétique : le transport GitHub est remplacé (aucun réseau en test)
        ctx = self.client.app.state.kernel
        gh = next(c for c in ctx.connectors if c.name == "github")
        gh.transport = lambda u, h: {"stargazers_count": 4, "forks_count": 1}

        r = self.client.post("/connectors/sync")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["decision"], "allow")  # lecture A1 : autorisée et tracée
        by_name = {res["name"]: res for res in body["results"]}
        self.assertFalse(by_name["shopify"]["ok"])   # pas configuré -> pas de mensonge
        self.assertTrue(by_name["github"]["ok"])     # public -> métriques réelles
        folio = {b["name"]: b for b in self.client.get("/portfolio").json()}
        os_biz = next(v for k, v in folio.items() if "open-source" in k)
        self.assertEqual(os_biz["metrics"]["stars"], 4)

    def test_complete_task_unknown_business_404(self):
        r = self.client.post("/portfolio/complete-task", json={
            "business": "N'existe pas", "task_prefix": "peu importe",
        })
        self.assertEqual(r.status_code, 404)

    def test_portfolio_returns_real_state_no_invented_metrics(self):
        r = self.client.get("/portfolio")
        self.assertEqual(r.status_code, 200)
        items = r.json()
        self.assertGreaterEqual(len(items), 4)
        by_name = {i["name"]: i for i in items}
        helyos = by_name["HELYOS Services (automatisation admin)"]
        # honnêteté : les revenus amorcés sont à 0, pas des pourcentages inventés
        self.assertEqual(helyos["metrics"]["revenue_eur"], 0)


if __name__ == "__main__":
    unittest.main()
