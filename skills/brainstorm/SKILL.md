---
name: brainstorm
description: Develop research ideas through independent literature searches and evidence-based debate between two agents. Use when a user proposes a research direction and wants critical discussion, cross-domain mechanisms, and a concrete, testable proposal explained top-down.
---

# Brainstorm

Turn a research intention into one defensible, testable proposal through two real agents. The main agent coordinates; A and B both research, propose, challenge, and revise. Agreement means a worthwhile hypothesis to test, not an experimentally proven result.

## Start

1. Extract the user's objective, target domain, observations/resources, and constraints. Ask only for information that changes the decision; continue independent work while waiting. Record assumptions explicitly. Match the user's language.
2. Create a fresh `output/brainstorm/<topic-slug>/` directory in the user's workspace, preserving previous sessions. Keep `session.json` as the structured record and `report.md` as the readable result. Read [the record format](references/session-format.md) before writing the record.
3. Use the host's actual subagent tools to create exactly two research agents with separate contexts when possible. Read [the agent briefs](references/agent-briefs.md). Record their real runtime IDs. Do not create user-owned chats, invoke a paid API, or change multi-agent settings merely to implement this skill. If independent agents are unavailable, report that requirement as blocked; never stage a single-agent conversation as two independent reviewers.

## Independent research, before debate

Give both agents the same problem and constraints, but do not show either one's initial proposal to the other until both return initial research notes. A emphasizes mechanism and feasible transfer; B emphasizes nearest prior art, competing explanations, and an independently useful alternative. These are complementary search lenses, not predetermined conclusions.

- Each agent searches the target literature and at least one plausible donor field independently. Prefer original papers, official implementations, and authoritative datasets. Share citations after the independent pass and avoid repeatedly opening the same sources.
- Build a short history: prior problem -> key mechanism -> implementation -> demonstrated result -> remaining limitation. Group by mechanisms, not a list of paper names. Distinguish training from evaluation, simulation from logged replay or learned world models, and native-policy updates from separate residual controllers.
- Read primary passages supporting central claims. Verify titles, authors, version/date, and the actual contents of user-supplied files; filenames are not identities. Link a section/figure/code location where possible. Mark abstract-only and inaccessible evidence. Do not infer implementation or negative results from a search snippet.
- An agent's first proposal must contain a causal mechanism, an unresolved problem grounded in the nearest prior work, and a cross-domain transfer argument. Explain what transfers, why its assumptions hold, and where the analogy breaks. If evidence is missing, keep the proposal provisional rather than inventing support.

## Debate and revision

1. A presents its strongest proposal. B identifies the most consequential contradiction, unsupported inference, implementation obstacle, or already-existing equivalent, and offers a concrete repair or a stronger alternative backed by sources.
2. A responds to the specific objection: accept and revise, reject with evidence, or narrow the claim. Give every revision a new immutable proposal ID. A must also evaluate B's independently developed alternative at least once before selecting the final direction; both agents can change positions.
3. Continue focused exchanges. Each response names the claim it changes, evidence IDs, the proposed repair, and what remains uncertain. Prefer one or two decisive objections over stylistic criticism. Do not reward disagreement for its own sake, prestige, or confident wording.
4. The coordinator routes concise messages between the same agents, updates the shared record, and consolidates duplicate evidence. Agents may relay through the coordinator when direct messaging is unavailable. Do not expand the team without user authorization.
5. Default to at most six critique/revision exchanges unless the user supplies another budget. An exchange is one substantive critique and its reply; initial research and final sign-offs do not count. Stop earlier on genuine agreement. If progress stalls for two exchanges, seek a decisive source, change the hypothesis, or formulate the discriminating experiment. At the limit, report `unresolved` with the exact disputed claim and next test; never manufacture consensus to meet a round limit. Missing essential tools or evidence can produce `blocked`.

## Proposal requirements

Every serious candidate must specify:

- **Problem and gap:** observed failure, what the nearest work already solves, and what remains unverified. A plausible gap is not proof that no one has studied it; search for counterexamples.
- **Key idea and mechanism:** one sentence, then the chain explaining how the intervention changes the failure. “Use RL,” “add a critic,” or “use an LLM” is insufficient.
- **Transfer evidence:** donor-domain method and source, matching assumptions, changed conditions, and failure modes. Distinguish a demonstrated result from an inference about the target domain.
- **Implementation:** input, output/action, modified components, trained/frozen parameters, data, loss/reward, and runtime cost at the level the field permits. Do not confuse a testable design with implemented code.
- **Minimum experiment:** strongest relevant baseline, intervention, controlled variables, metric, and a result that would falsify the mechanism. Add ablations that distinguish competing causes; do not start expensive experiments without authorization.
- **Novelty boundary and risks:** closest prior work, actual delta, confounders, feasibility constraints, and evidence still needed. Do not promise acceptance at a venue.

## Convergence gate

Before declaring `consensus`, both real agents must independently review the exact same final proposal and explicitly accept it with a rationale. Neither silence nor the coordinator's judgment counts as acceptance.

- Recheck nearest competing work and decisive target/donor evidence.
- Close blocking objections with concrete resolutions, or document why a discarded objection no longer applies. Keep residual risks visible; agreeing to test a hypothesis does not resolve an empirical uncertainty.
- Calculate the final proposal fingerprint with the bundled validator. Send the proposal and fingerprint to each agent. Record actual approvals tied to that fingerprint; revise and re-approve if the proposal changes.
- Run `python3 <skill-dir>/scripts/validate_session.py <run-dir>/session.json`. Repair record errors before claiming completion. This checks consistency, not citation truth, actual agent independence, or scientific merit.

## Explain the result top-down

Write `report.md` and a self-contained response in this order, expanding detail only as useful:

1. Decision: one-sentence key idea, why it is promising, and `consensus`, `unresolved`, or `blocked` status.
2. Big picture: problem -> prior approach -> remaining gap -> proposed mechanism. Define unfamiliar terms.
3. Evidence: compact literature-flow table with links, scope, and limitations; separate established facts, transfer arguments, and untested hypotheses.
4. Debate: strongest objection, how the idea changed, alternative considered, and remaining disagreement. Summarize the argument rather than dumping every message.
5. Concrete design and minimum experiment, baselines, falsification criteria, risks, and next actions.

Source claims next to the statements they support. Use diagrams only when they clarify the mechanism. Keep raw tool traces, full papers, secrets, and unrelated project data out of the report. Creating this analysis does not authorize emailing people, publishing it, pushing repositories, or running the proposed study.
