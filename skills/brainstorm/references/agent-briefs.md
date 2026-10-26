# Agent briefs

The coordinator fills in the problem, constraints, and run directory below. Naming two roles does not create independent agents.

## Shared independent-search brief

You are research agent {A or B}. Read the brainstorm skill and the user's brief below. Work independently before seeing the other agent's proposal. Do not spawn further agents or alter project code. Use your own scratch file under {run-dir}/{A or B}/; the coordinator alone writes the canonical session record.

User's research intention: {brief}
Constraints and available observations: {constraints}

Investigate primary target-domain literature and at least one relevant donor domain. Return:

1. A short mechanism-based history, including the nearest competing method.
2. Verified source entries: exact title, stable URL, publication/version date, section/code locator, demonstrated finding, and limitations. Identify full-text versus abstract-only access.
3. One strongest idea: problem, gap, key mechanism, transfer argument, assumptions that might fail, implementation, nearest prior work, and falsifiable minimum test.
4. The strongest reason your own idea could be wrong.

Do not treat a review, simulation-only evaluation, or offline reward computation as online policy learning. Do not report proposed experiments as completed. If a citation or supposed gap cannot be verified, say so. Stop after this first independent pass and wait for the coordinator.

## Debate turn

Read {proposal ID and content} and the other agent's specific claims. Address the scientific mechanism, not writing style. Return a concise message with:

- Claim or assumption challenged, by proposal ID.
- Strongest objection or counterexample, with sources and scope.
- A repair or stronger alternative with a concrete cross-domain mechanism.
- What changed in your position and what is still blocking agreement.

When revising, say exactly what changed and provide the new immutable proposal. If no improvement is supported, retain uncertainty instead of adding components speculatively. Ask the coordinator to find missing decisive evidence when needed.

## Final independent review

Review this exact proposal: {proposal ID, full proposal, SHA-256 fingerprint}.

Check mechanism, closest prior art, transfer assumptions, minimum test, unresolved objections, and citation scope. Acceptance means “a coherent hypothesis worth testing,” not “a proven method.” Return:

- ACCEPT or REJECT.
- The exact proposal ID and fingerprint supplied above.
- Your rationale, decisive source IDs, remaining empirical risks, and any blocking objection.

Do not accept merely because the other agent accepted. A changed proposal needs a new review.
