"""Tests du moteur de licence / entitlements (mécanisme de monétisation)."""

import time
import unittest

from jarvis_kernel.licensing import (
    COMMUNITY,
    LicenseError,
    require,
    sign_license,
    verify_license,
)

SECRET = "secret-de-test"


class TestLicense(unittest.TestCase):
    def test_sign_verify_roundtrip(self):
        key = sign_license({"licensee": "ACME", "features": ["pro"]}, SECRET)
        ent = verify_license(key, SECRET)
        self.assertEqual(ent.licensee, "ACME")
        self.assertTrue(ent.has("pro"))
        self.assertFalse(ent.has("enterprise"))

    def test_wildcard_feature(self):
        key = sign_license({"licensee": "ALL", "features": ["*"]}, SECRET)
        self.assertTrue(verify_license(key, SECRET).has("anything"))

    def test_tamper_detection(self):
        key = sign_license({"licensee": "X", "features": ["pro"]}, SECRET)
        body, sig = key.split(".")
        forged = sign_license({"licensee": "X", "features": ["enterprise"]}, "autre-secret")
        forged_body = forged.split(".")[0]
        with self.assertRaises(LicenseError):
            verify_license(f"{forged_body}.{sig}", SECRET)  # corps modifié, sig d'origine

    def test_wrong_secret(self):
        key = sign_license({"licensee": "X", "features": ["pro"]}, SECRET)
        with self.assertRaises(LicenseError):
            verify_license(key, "mauvais-secret")

    def test_expired(self):
        key = sign_license(
            {"licensee": "X", "features": ["pro"], "expires": time.time() - 10}, SECRET
        )
        with self.assertRaises(LicenseError):
            verify_license(key, SECRET)

    def test_unreadable_key(self):
        with self.assertRaises(LicenseError):
            verify_license("pas-une-cle", SECRET)

    def test_require_guard(self):
        key = sign_license({"licensee": "X", "features": ["pro"]}, SECRET)
        ent = verify_license(key, SECRET)
        require(ent, "pro")  # ne lève pas
        with self.assertRaises(LicenseError):
            require(ent, "enterprise")

    def test_community_has_nothing(self):
        self.assertFalse(COMMUNITY.has("pro"))
        with self.assertRaises(LicenseError):
            require(COMMUNITY, "pro")


if __name__ == "__main__":
    unittest.main()
