# Session record

Keep one JSON object. Record real messages and approvals; never fabricate IDs or signatures. Every revision gets a new proposal ID; retain earlier proposals. Content fields use concise prose in the user's language.

```json
{
  "schema_version": 1,
  "topic": "Research question",
  "scope": "Objective, constraints, and explicit assumptions",
  "agents": [
    {"role": "A", "runtime_id": "actual independent agent ID"},
    {"role": "B", "runtime_id": "another actual independent agent ID"}
  ],
  "sources": [
    {
      "id": "S1", "title": "Exact title", "url": "https://example.org/paper", "date": "Publication/version date",
      "access": "full_text", "area": "target", "locator": "Section or code location",
      "finding": "Demonstrated result and its scope", "limitation": "Relevant limitation"
    }
  ],
  "proposals": [
    {
      "id": "P1", "author": "A", "problem": "Observed problem", "gap": "Remaining gap",
      "key_idea": "One-sentence mechanism", "mechanism": "Causal chain",
      "source_ids": ["S1"],
      "transfer": {
        "domain": "Donor field", "method": "Mechanism being transferred",
        "source_ids": ["S2"], "why_applicable": "Matching conditions",
        "assumptions": "Required conditions", "failure_modes": "Where the analogy breaks"
      },
      "implementation": "Inputs, outputs, changes, trained parameters, data, objectives and costs",
      "novelty": {"closest_source_ids": ["S1"], "delta": "Actual change", "uncertainty": "Unverified overlap"},
      "test": {
        "baseline": "Relevant comparison", "intervention": "One discriminating change",
        "controls": "Variables held fixed", "metric": "Observable outcome",
        "falsifier": "Result that contradicts the proposed mechanism"
      },
      "risks": ["Remaining empirical uncertainty"]
    }
  ],
  "rounds": [
    {"number": 1, "speaker": "A", "proposal_id": "P1", "message": "Argument", "source_ids": ["S1"]},
    {"number": 1, "speaker": "B", "proposal_id": "P1", "message": "Specific critique and repair", "source_ids": ["S2"]}
  ],
  "objections": [
    {
      "id": "O1", "author": "B", "proposal_id": "P1", "severity": "blocking",
      "claim": "Claim challenged", "reason": "Contradiction or missing evidence",
      "requested_change": "Concrete repair", "status": "open", "resolution": ""
    }
  ],
  "final": {
    "status": "unresolved", "proposal_id": "P1", "reason": "Current decision",
    "approvals": [], "remaining_questions": ["Question needing evidence"]
  }
}
```

This illustrates the format, not a valid completed session: S2 must be a real source, and both agents must contribute initial proposals. Never copy example.org as evidence.

## Allowed values and blocked sessions

- Source `access`: `full_text`, `abstract_only`, `unavailable`; `area`: `target`, `transfer`.
- `url` may be a stable HTTP(S) source URL or the absolute path of a user-provided local document. Keep its exact title and a section/page locator either way.
- Proposal/turn `author` or `speaker`: `A` or `B`.
- Objection `severity`: `blocking`, `nonblocking`; `status`: `open`, `resolved`, `not_applicable`. Resolved or discarded objections need a substantive `resolution`. A discarded objection names the changed scope or abandoned candidate instead of dismissing the criticism.
- Final `status`: `consensus`, `unresolved`, `blocked`.
- `blocked` may have empty agent/source/proposal/round lists when tools are absent. State the blocker in `final.reason`; `final.proposal_id` is null if no proposal exists. Do not fabricate a debate to satisfy validation.
- `unresolved` permits provisional evidence and scientific disagreement.

## Approvals and fingerprint

Calculate the final proposal's SHA-256 over canonical JSON:

```bash
python3 <skill-dir>/scripts/validate_session.py <run-dir>/session.json --fingerprint P3
```

Send that exact proposal and fingerprint to both agents. After each agent actually responds, record:

```json
{
  "agent": "A", "runtime_id": "actual agent ID", "proposal_id": "P3",
  "proposal_sha256": "fingerprint supplied to the reviewer",
  "verdict": "accept", "rationale": "Independent acceptance rationale"
}
```

For `consensus`, require distinct agent IDs, both initial proposals and debate messages, A and B approving the same unchanged proposal, no open blocking objections, and full-text target/transfer and nearest-prior-work evidence for that proposal. Then run validation without `--fingerprint`.

The validator checks record consistency only. It cannot prove a source was read, an ID is real, the debate was independent, or the claim is true. Retain actual tool messages as provenance.
