import unittest

from stopreplay_analysis import AnalysisError
from stopreplay_analysis.recon_profile import SCHEMA_VERSION, project_recon_facts


# Rows shaped exactly like stopreplay_db.Storage.get_facts output, with values that
# match stopreplay_collect seed.py / extract.py conventions. Synthetic.
def fact(fid, claim, category, **changes):
    row = {"id": fid, "subject": "julius", "claim": claim, "category": category,
           "source_run": "recon", "source_ref": "seed:julius", "confidence": 0.9,
           "assertable": True, "assertable_why": "operator-supplied seed",
           "sensitivity": "public", "corroboration": [], "status": "active",
           "superseded_by": None}
    row.update(changes)
    return row


FACTS = [
    fact("f1", "full_name: Julius Muth", "other"),
    fact("f2", "company_domain: revel8.ai", "other"),
    fact("f3", "Co-founder and Co-CEO sales at revel8", "role"),
    fact("f4", "linkedin_profile: https://linkedin.com/in/julius", "contact",
         source_ref="https://linkedin.com/in/julius", confidence=0.7,
         assertable_why="profile page on linkedin"),
    fact("f5", "date_of_birth: 1990-01-01", "other", sensitivity="private"),
    fact("f6", "github_token: ghp_xxx", "credential", sensitivity="sensitive",
         assertable=False, assertable_why="unverified"),
]
SOURCES = {
    "seed:julius": {"source_ref": "seed:julius", "origin": "file_upload",
                    "publisher": "operator-supplied", "locator": "operator-supplied seed",
                    "excerpt": "Julius Muth, revel8.ai Co-founder and Co-CEO sales", "url": None},
    "https://linkedin.com/in/julius": {"source_ref": "https://linkedin.com/in/julius",
                                       "origin": "social_post", "url": "https://linkedin.com/in/julius",
                                       "locator": None, "publisher": None, "excerpt": "Julius Muth"},
}


class ReconProfileTests(unittest.TestCase):
    def project(self, facts=FACTS, sources=SOURCES, **kwargs):
        return project_recon_facts(facts, sources, source_run="recon", **kwargs)

    def assert_error(self, fn):
        with self.assertRaises(AnalysisError) as caught:
            fn()
        self.assertEqual(caught.exception.code, "invalid_input")

    def test_identity_attributes_are_parsed_and_attributed(self):
        julius = self.project()["subjects"]["julius"]
        self.assertEqual(julius["identity"]["full_name"][0]["value"], "Julius Muth")
        self.assertEqual(julius["identity"]["company_domain"][0]["value"], "revel8.ai")
        linkedin = julius["identity"]["linkedin_profile"][0]
        self.assertEqual(linkedin["value"], "https://linkedin.com/in/julius")
        self.assertEqual(linkedin["source"]["origin"], "social_post")
        self.assertTrue(linkedin["source"]["resolved"])

    def test_prose_role_keeps_full_claim_without_a_key(self):
        role = next(a for a in self.project()["subjects"]["julius"]["attributes"] if a["category"] == "role")
        self.assertIsNone(role["key"])
        self.assertEqual(role["value"], "Co-founder and Co-CEO sales at revel8")

    def test_collection_assertability_is_preserved_not_recomputed(self):
        julius = self.project()["subjects"]["julius"]
        usable_ids = {r["fact_id"] for r in julius["usable_with_attribution"]}
        # f1 full_name, f2 domain, f3 role, f4 linkedin are assertable/public/active.
        self.assertEqual(usable_ids, {"f1", "f2", "f3", "f4"})
        for row in julius["usable_with_attribution"]:
            self.assertTrue(row["assertable"])
            self.assertEqual(row["withheld_reasons"], [])

    def test_restricted_facts_are_segregated_and_never_usable(self):
        julius = self.project()["subjects"]["julius"]
        restricted = {r["fact_id"]: r["withheld_reasons"] for r in julius["restricted"]}
        self.assertEqual(set(restricted), {"f5", "f6"})
        self.assertIn("restricted_sensitivity", restricted["f5"])
        self.assertIn("credential_category", restricted["f6"])
        usable_ids = {r["fact_id"] for r in julius["usable_with_attribution"]}
        self.assertTrue({"f5", "f6"}.isdisjoint(usable_ids))

    def test_non_assertable_fact_is_withheld_with_reason(self):
        rows = [fact("f7", "company_page: https://revel8.ai/team", "other",
                     assertable=False, assertable_why="namesake match")]
        julius = project_recon_facts(rows, SOURCES, source_run="recon")["subjects"]["julius"]
        row = julius["identity"]["company_page"][0]
        self.assertFalse(row["usable_with_attribution"])
        self.assertEqual(row["withheld_reasons"], ["collection_not_assertable"])
        self.assertEqual(julius["usable_with_attribution"], [])

    def test_superseded_status_is_withheld(self):
        rows = [fact("f8", "CTO at revel8", "role", status="superseded")]
        row = project_recon_facts(rows, SOURCES, source_run="recon")["subjects"]["julius"]["attributes"][0]
        self.assertFalse(row["usable_with_attribution"])
        self.assertIn("status_superseded", row["withheld_reasons"])

    def test_missing_source_marks_provenance_unresolved(self):
        julius = project_recon_facts(FACTS, {}, source_run="recon")["subjects"]["julius"]
        role = next(a for a in julius["attributes"] if a["category"] == "role")
        self.assertFalse(role["source"]["resolved"])
        self.assertIn("source_unresolved", role["withheld_reasons"])
        self.assertEqual(julius["usable_with_attribution"], [])

    def test_subject_filter_and_multiple_subjects(self):
        tom = fact("f9", "full_name: Tom Example", "other", subject="tom")
        result = project_recon_facts(FACTS + [tom], SOURCES, source_run="recon")
        self.assertEqual(set(result["subjects"]), {"julius", "tom"})
        only = project_recon_facts(FACTS + [tom], SOURCES, source_run="recon", subject="julius")
        self.assertEqual(set(only["subjects"]), {"julius"})
        self.assertEqual(only["subject_filter"], "julius")

    def test_schema_marker_and_json_safe(self):
        import json
        result = self.project()
        self.assertEqual(result["schema_version"], SCHEMA_VERSION)
        json.dumps(result)

    def test_invalid_rows_are_rejected(self):
        for rows in [[fact("f1", "x", "role"), fact("f1", "y", "role")],      # duplicate id
                     [fact(None, "x", "role")],                                # missing id
                     [fact("fx", "x", "mood")],                                # bad category
                     [fact("fx", " ", "role")],                               # empty claim
                     [fact("fx", "x", "role", source_run="other")],           # wrong run
                     [fact("fx", "x", "role", source_ref="")]]:               # no source_ref
            with self.subTest(rows=rows):
                self.assert_error(lambda: project_recon_facts(rows, SOURCES, source_run="recon"))
        self.assert_error(lambda: project_recon_facts(FACTS, SOURCES, source_run=" "))


if __name__ == "__main__":
    unittest.main()
