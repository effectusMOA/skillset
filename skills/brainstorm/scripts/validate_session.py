#!/usr/bin/env python3
"""Validate debate-record consistency, not the truth of research claims.

Standard library only. Exit 0 for a valid record and 1 for errors.
"""

import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse


def fingerprint(proposal):
    payload = json.dumps(proposal, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate(data):
    errors = []

    def obj(value, path):
        if not isinstance(value, dict):
            errors.append(f"{path}: expected an object")
            return {}
        return value

    def items(value, path):
        if not isinstance(value, list):
            errors.append(f"{path}: expected a list")
            return []
        return value

    def text(value, path):
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{path}: expected non-empty text")
            return ""
        return value

    def choice(value, allowed, path):
        if not isinstance(value, str) or value not in allowed:
            errors.append(f"{path}: expected one of {sorted(allowed)}")

    def texts(record, keys, path):
        for key in keys:
            text(record.get(key), f"{path}.{key}")

    def index(records, path, key="id"):
        result = {}
        for n, value in enumerate(records):
            record = obj(value, f"{path}[{n}]")
            identity = text(record.get(key), f"{path}[{n}].{key}")
            if identity in result:
                errors.append(f"{path}: duplicate {key} {identity}")
            if identity:
                result[identity] = record
        return result

    data = obj(data, "session")
    if data.get("schema_version") != 1 or isinstance(data.get("schema_version"), bool):
        errors.append("schema_version: expected 1")
    texts(data, ("topic", "scope"), "session")
    agents = index(items(data.get("agents"), "agents"), "agents", "role")
    sources = index(items(data.get("sources"), "sources"), "sources")
    proposals = index(items(data.get("proposals"), "proposals"), "proposals")
    rounds = items(data.get("rounds"), "rounds")
    objections = index(items(data.get("objections"), "objections"), "objections")
    final = obj(data.get("final"), "final")
    status = final.get("status")
    choice(status, {"consensus", "unresolved", "blocked"}, "final.status")
    text(final.get("reason"), "final.reason")
    approvals = items(final.get("approvals"), "final.approvals")
    for n, question in enumerate(items(final.get("remaining_questions"), "final.remaining_questions")):
        text(question, f"final.remaining_questions[{n}]")

    if status != "blocked" and set(agents) != {"A", "B"}:
        errors.append("agents: exactly A and B are required")
    if set(agents) - {"A", "B"}:
        errors.append("agents: only A and B are supported")
    runtime_ids = []
    for role, agent in agents.items():
        runtime_ids.append(text(agent.get("runtime_id"), f"agents.{role}.runtime_id"))
    if len(runtime_ids) != len(set(runtime_ids)):
        errors.append("agents: runtime IDs must be distinct")

    for sid, source in sources.items():
        texts(source, ("title", "url", "date", "locator", "finding", "limitation"), f"sources.{sid}")
        location = source.get("url", "")
        if isinstance(location, str):
            parsed = urlparse(location)
            if not ((parsed.scheme in {"http", "https"} and parsed.netloc) or Path(location).is_absolute()):
                errors.append(f"sources.{sid}.url: expected HTTP(S) URL or absolute local path")
            if status == "consensus" and parsed.hostname in {"example.org", "example.com", "example.net"}:
                errors.append(f"sources.{sid}.url: example URLs are not evidence")
        choice(source.get("access"), {"full_text", "abstract_only", "unavailable"}, f"sources.{sid}.access")
        choice(source.get("area"), {"target", "transfer"}, f"sources.{sid}.area")

    def refs(value, path):
        result = []
        for n, sid in enumerate(items(value, path)):
            sid = text(sid, f"{path}[{n}]")
            if sid not in sources:
                errors.append(f"{path}: unknown source {sid}")
            else:
                result.append(sid)
        return result

    for pid, proposal in proposals.items():
        prefix = f"proposals.{pid}"
        choice(proposal.get("author"), {"A", "B"}, f"{prefix}.author")
        texts(proposal, ("problem", "gap", "key_idea", "mechanism", "implementation"), prefix)
        refs(proposal.get("source_ids"), f"{prefix}.source_ids")
        transfer = obj(proposal.get("transfer"), f"{prefix}.transfer")
        texts(transfer, ("domain", "method", "why_applicable", "assumptions", "failure_modes"), f"{prefix}.transfer")
        refs(transfer.get("source_ids"), f"{prefix}.transfer.source_ids")
        novelty = obj(proposal.get("novelty"), f"{prefix}.novelty")
        texts(novelty, ("delta", "uncertainty"), f"{prefix}.novelty")
        refs(novelty.get("closest_source_ids"), f"{prefix}.novelty.closest_source_ids")
        test = obj(proposal.get("test"), f"{prefix}.test")
        texts(test, ("baseline", "intervention", "controls", "metric", "falsifier"), f"{prefix}.test")
        for n, risk in enumerate(items(proposal.get("risks"), f"{prefix}.risks")):
            text(risk, f"{prefix}.risks[{n}]")

    speakers = set()
    for n, value in enumerate(rounds):
        turn = obj(value, f"rounds[{n}]")
        number = turn.get("number")
        if not isinstance(number, int) or isinstance(number, bool) or number < 1:
            errors.append(f"rounds[{n}].number: expected positive integer")
        speaker = turn.get("speaker")
        choice(speaker, {"A", "B"}, f"rounds[{n}].speaker")
        if isinstance(speaker, str):
            speakers.add(speaker)
        text(turn.get("message"), f"rounds[{n}].message")
        pid = text(turn.get("proposal_id"), f"rounds[{n}].proposal_id")
        if pid not in proposals:
            errors.append(f"rounds[{n}]: unknown proposal {pid}")
        refs(turn.get("source_ids"), f"rounds[{n}].source_ids")

    for oid, objection in objections.items():
        prefix = f"objections.{oid}"
        choice(objection.get("author"), {"A", "B"}, f"{prefix}.author")
        texts(objection, ("claim", "reason", "requested_change"), prefix)
        if not isinstance(objection.get("proposal_id"), str) or objection.get("proposal_id") not in proposals:
            errors.append(f"{prefix}: unknown proposal")
        choice(objection.get("severity"), {"blocking", "nonblocking"}, f"{prefix}.severity")
        choice(objection.get("status"), {"open", "resolved", "not_applicable"}, f"{prefix}.status")
        if objection.get("status") != "open":
            text(objection.get("resolution"), f"{prefix}.resolution")
        if status == "consensus" and objection.get("severity") == "blocking" and objection.get("status") == "open":
            errors.append(f"{prefix}: open blocking objection prevents consensus")

    selected = final.get("proposal_id")
    selected_valid = isinstance(selected, str) and selected in proposals
    if selected is not None and not selected_valid:
        errors.append("final.proposal_id: unknown proposal")
    if status != "blocked" and not selected_valid:
        errors.append("final.proposal_id: selected proposal required")

    approval_agents = set()
    for n, value in enumerate(approvals):
        approval = obj(value, f"final.approvals[{n}]")
        role = approval.get("agent")
        choice(role, {"A", "B"}, f"final.approvals[{n}].agent")
        if isinstance(role, str):
            if role in approval_agents:
                errors.append(f"final.approvals: duplicate reviewer {role}")
            approval_agents.add(role)
        texts(approval, ("runtime_id", "proposal_id", "proposal_sha256", "rationale"), f"final.approvals[{n}]")
        choice(approval.get("verdict"), {"accept", "reject"}, f"final.approvals[{n}].verdict")
        if isinstance(role, str) and approval.get("runtime_id") != agents.get(role, {}).get("runtime_id"):
            errors.append(f"final.approvals[{n}]: reviewer runtime ID does not match")
        pid = approval.get("proposal_id")
        if pid != selected:
            errors.append(f"final.approvals[{n}]: approval is not for the selected proposal")
        if isinstance(pid, str) and pid in proposals and approval.get("proposal_sha256") != fingerprint(proposals[pid]):
            errors.append(f"final.approvals[{n}]: stale proposal fingerprint; obtain a new review")
        if status == "consensus" and approval.get("verdict") != "accept":
            errors.append(f"final.approvals[{n}]: rejection prevents consensus")

    if status == "consensus" and not errors:
        if approval_agents != {"A", "B"} or len(approvals) != 2:
            errors.append("consensus requires one explicit approval each from A and B")
        if speakers != {"A", "B"}:
            errors.append("consensus requires recorded debate contributions from both agents")
        if {p.get("author") for p in proposals.values()} != {"A", "B"}:
            errors.append("consensus requires an initial proposal from each agent")
        if isinstance(selected, str) and selected in proposals:
            proposal = proposals[selected]
            target_refs = proposal.get("source_ids", [])
            transfer_refs = proposal.get("transfer", {}).get("source_ids", [])
            closest_refs = proposal.get("novelty", {}).get("closest_source_ids", [])
            for ids, area, label in ((target_refs, "target", "target"), (transfer_refs, "transfer", "transfer")):
                verified = any(sources.get(sid, {}).get("access") == "full_text" and sources.get(sid, {}).get("area") == area for sid in ids if isinstance(sid, str))
                if not verified:
                    errors.append(f"consensus requires full-text {label} evidence for the selected proposal")
            if not closest_refs:
                errors.append("consensus requires identified nearest prior work")
            elif not any(sources.get(sid, {}).get("access") == "full_text" for sid in closest_refs):
                errors.append("consensus requires full-text review of nearest prior work")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session", type=Path)
    parser.add_argument("--fingerprint", metavar="PROPOSAL_ID")
    args = parser.parse_args()
    try:
        data = json.loads(args.session.read_text(encoding="utf-8"))
        if args.fingerprint:
            proposals = {p["id"]: p for p in data["proposals"]}
            print(fingerprint(proposals[args.fingerprint]))
            return 0
        errors = validate(data)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"ERROR: {exc}")
        return 1
    for error in errors:
        print(f"ERROR: {error}")
    if errors:
        return 1
    print(f"Valid session: {data['final']['status']} (structural checks only)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
