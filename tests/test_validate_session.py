"""Synthetic records test the convergence gate, not any research result."""

import copy
import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "skills/brainstorm/scripts/validate_session.py"
spec = importlib.util.spec_from_file_location("validate_session", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def valid_record():
    source = dict(title="Synthetic source fixture", url="https://arxiv.org/abs/2510.25889", date="Synthetic date fixture", access="full_text", locator="Synthetic fixture only", finding="Test content, not a research claim", limitation="No real study executed")
    proposal = dict(id="P1", author="A", problem="Fixture problem", gap="Fixture gap", key_idea="Fixture mechanism", mechanism="Fixture chain", source_ids=["S1"], implementation="Fixture implementation", risks=["Untested"],
                    transfer=dict(domain="Donor", method="Method", source_ids=["S2"], why_applicable="Assumption", assumptions="Condition", failure_modes="Failure"),
                    novelty=dict(closest_source_ids=["S1"], delta="Fixture delta", uncertainty="Overlap unknown"),
                    test=dict(baseline="Baseline", intervention="Change", controls="Control", metric="Metric", falsifier="No improvement"))
    other = copy.deepcopy(proposal)
    other.update(id="P2", author="B")
    record = dict(schema_version=1, topic="Fixture", scope="Synthetic test only", agents=[dict(role="A", runtime_id="agent-a"), dict(role="B", runtime_id="agent-b")], sources=[dict(source,id="S1",area="target"),dict(source,id="S2",area="transfer")], proposals=[proposal,other], rounds=[dict(number=1,speaker=role,proposal_id="P1",message="Fixture argument",source_ids=["S1"]) for role in ("A","B")], objections=[], final=dict(status="consensus",proposal_id="P1",reason="Fixture decision",remaining_questions=["Untested"],approvals=[]))
    record["final"]["approvals"] = [dict(agent=role,runtime_id=f"agent-{role.lower()}",proposal_id="P1",proposal_sha256=module.fingerprint(proposal),verdict="accept",rationale="Fixture review") for role in ("A","B")]
    return record


class ConvergenceTests(unittest.TestCase):
    def test_valid_consensus(self):
        self.assertEqual(module.validate(valid_record()), [])

    def test_one_agent_cannot_approve_twice(self):
        data = valid_record()
        data["agents"][1]["runtime_id"] = "agent-a"
        self.assertTrue(any("distinct" in e for e in module.validate(data)))

    def test_changed_proposal_invalidates_approvals(self):
        data = valid_record()
        data["proposals"][0]["mechanism"] = "Changed mechanism"
        self.assertTrue(any("stale" in e for e in module.validate(data)))

    def test_open_blocker_prevents_consensus(self):
        data = valid_record()
        data["objections"] = [dict(id="O1",author="B",proposal_id="P1",severity="blocking",claim="Unsupported",reason="Evidence missing",requested_change="Verify",status="open",resolution="")]
        self.assertTrue(any("open blocking" in e for e in module.validate(data)))

    def test_abstract_only_transfer_is_not_full_evidence(self):
        data = valid_record()
        data["sources"][1]["access"] = "abstract_only"
        self.assertTrue(any("full-text transfer" in e for e in module.validate(data)))

    def test_unknown_source_rejected(self):
        data = valid_record()
        data["proposals"][0]["source_ids"] = ["missing"]
        self.assertTrue(any("unknown source" in e for e in module.validate(data)))

    def test_explicit_rejection_prevents_consensus(self):
        data = valid_record()
        data["final"]["approvals"][1]["verdict"] = "reject"
        self.assertTrue(any("rejection" in e for e in module.validate(data)))

    def test_honest_blocked_record_needs_no_fake_agents(self):
        data = dict(schema_version=1,topic="Fixture",scope="No delegation tools",agents=[],sources=[],proposals=[],rounds=[],objections=[],final=dict(status="blocked",proposal_id=None,reason="Independent agents unavailable",approvals=[],remaining_questions=["Enable a supported host"]))
        self.assertEqual(module.validate(data), [])

    def test_unresolved_can_retain_open_objection(self):
        data = valid_record()
        data["final"].update(status="unresolved", approvals=[])
        data["objections"] = [dict(id="O1",author="B",proposal_id="P1",severity="blocking",claim="Untested assumption",reason="Needs test",requested_change="Run comparison",status="open",resolution="")]
        self.assertEqual(module.validate(data), [])

    def test_incorrect_shapes_report_errors(self):
        self.assertTrue(module.validate([]))
        data = valid_record()
        data["sources"] = None
        self.assertTrue(module.validate(data))

    def test_duplicate_source_ids_rejected(self):
        data = valid_record()
        data["sources"].append(copy.deepcopy(data["sources"][0]))
        self.assertTrue(any("duplicate" in e for e in module.validate(data)))

    def test_malformed_nested_values_do_not_raise(self):
        for key, value in (("proposal_id", []), ("proposal_id", {})):
            data = valid_record()
            data["final"][key] = value
            self.assertTrue(module.validate(data))
        data = valid_record()
        data["proposals"][0]["transfer"] = None
        self.assertTrue(module.validate(data))

    def test_missing_independent_initial_proposal_rejected(self):
        data = valid_record()
        data["proposals"].pop()
        self.assertTrue(any("initial proposal" in e for e in module.validate(data)))

    def test_local_full_text_sources_supported(self):
        data = valid_record()
        data["sources"][0]["url"] = "/research/papers/source.pdf"
        self.assertEqual(module.validate(data), [])


if __name__ == "__main__":
    unittest.main()
