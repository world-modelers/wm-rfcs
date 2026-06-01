# The WM-RFC Process

This document defines how a World Model RFC (WM-RFC) is proposed, discussed,
and ratified. It is itself a Process document and is governed by the same
rules it describes. It is modeled on mature, well-understood processes — IETF
RFCs / BCP 14, Python PEPs, Rust RFCs, and the Ethereum EIP process — adapted
to a young, fast-moving research field.

The guiding principle: **standardize the interaction contract, not the
science.** RFCs here describe interfaces, wire formats, registries, and
processes that let independently built world models and planners interoperate.
They do not prescribe model architectures, training objectives, or research
direction. When in doubt, specify less.

## What belongs in a WM-RFC

A WM-RFC is appropriate when a change is *cross-cutting* — when it affects how
independent implementations interoperate and therefore needs durable, written
consensus. Examples: a new protocol verb, a wire format, a capability or error
code, a registry policy, or a change to this process.

A WM-RFC is **not** needed for: a reference-implementation bug fix, internal
refactors, documentation, or anything an implementation can decide unilaterally
without affecting interoperability. Use a normal issue or PR for those.

## RFC types

| Type | Purpose | Normative spec? |
|------|---------|-----------------|
| **Standards Track** | An interface, wire format, registry, or other artifact implementations must agree on. | Yes |
| **Process** | A change to governance, the RFC process, or project policy (like this document). | Sometimes |
| **Informational** | Guidance, design notes, or surveys that inform the ecosystem without mandating behavior. | No |

Standards Track RFCs additionally carry a **Category**:

- **Interface** — runtime/programmatic contracts (e.g. WMCP, WM-RFC-0001).
- **Data** — on-disk or on-the-wire data formats and schemas.
- **Registry** — the policy and content of an extension registry (e.g. an
  embodiment ontology).
- **Meta** — RFCs about the RFC corpus itself.

## Status lifecycle

```
        ┌─────────┐
        │  Draft  │  author is writing; not yet seeking consensus
        └────┬────┘
             ▼
        ┌─────────┐
        │ Review  │  open PR; community + editors discuss
        └────┬────┘
             ▼
        ┌───────────┐
        │ Last Call │  final comment period (≥14 days), no unresolved blockers
        └────┬──────┘
             ▼
        ┌──────────┐
        │ Accepted │  consensus reached; awaiting reference implementation
        └────┬─────┘
             ▼
        ┌────────┐
        │ Final  │  ratified and stable (Standards Track)
        └────────┘

   Living      — continuously updated by policy (e.g. a registry RFC)
   Rejected    — consensus was not to adopt
   Withdrawn   — author retracted before acceptance
   Superseded  — replaced by a later RFC (see Superseded-By)
   Deprecated  — formerly Final, scheduled for removal at the next MAJOR
```

- **Draft** — work in progress. May live in a branch or a draft PR. No
  consensus is claimed.
- **Review** — the RFC is a PR open for discussion. Editors triage it within a
  reasonable window. Substantive comments are resolved in-thread or in the RFC.
- **Last Call** — an editor announces a Final Comment Period of at least
  **14 calendar days**. The PR is labeled `last-call`. If a new blocking
  concern surfaces, the RFC returns to **Review**.
- **Accepted** — rough consensus (see GOVERNANCE.md) was reached. For Standards
  Track, the design is frozen pending a reference implementation and
  conformance evidence.
- **Final** — Standards Track only. Requires at least one **independent
  reference implementation** and passing conformance evidence for any
  testable assertions. A Final RFC is stable per its own versioning rules.
- **Living** — for RFCs that are updated continuously by an explicit policy
  (registries). Changes follow the policy stated in the RFC, not a re-vote.
- **Rejected / Withdrawn / Superseded / Deprecated** — terminal or historical
  states. Rejected and Superseded RFCs are kept in the repository for the
  record; nothing is deleted.

A pre-1.0 Standards Track RFC may be merged in **Draft** or **Review** status
to establish a shared baseline before the ecosystem is mature enough to ratify
it. WM-RFC-0001 is such a draft. Merging a draft does not imply consensus to
finalize; it makes the text citable and reviewable.

## Lifecycle steps

1. **Discuss first.** Open a GitHub issue using the *RFC proposal* template, or
   raise the idea in Discussions. Early feedback prevents wasted drafting.
2. **Reserve a number.** Comment on your issue to request the next free
   `WM-RFC-NNNN`. An editor confirms it. Numbers are assigned in order and never
   reused.
3. **Draft.** Copy `rfcs/WM-RFC-0000-template.md` to
   `rfcs/WM-RFC-NNNN-<slug>.md`, set `Status: Draft`, and write. Run
   `python3 tools/validate_rfcs.py` locally.
4. **Open a PR.** Set `Status: Review`. The PR description should summarize the
   proposal and link the discussion. CI runs the structural linter.
5. **Review.** Editors and the community comment. Resolve substantive feedback
   in the RFC text. There is no fixed minimum, but expect iteration.
6. **Last Call.** When discussion converges, an editor moves the RFC to
   `Status: Last Call` and starts the ≥14-day FCP.
7. **Decision.** Absent unresolved blocking objections, an editor merges the PR
   with `Status: Accepted` (or `Final`, if a reference implementation and
   conformance evidence already exist). Otherwise the RFC returns to Review,
   is Rejected, or is Withdrawn — always with a written rationale recorded in
   the PR.
8. **Finalize (Standards Track).** Once an independent reference implementation
   and conformance evidence exist, a follow-up PR moves the RFC to `Final`.

## The preamble contract

Every RFC begins with a header block fenced by `---` lines. `tools/validate_rfcs.py`
enforces it in CI.

```
---
WM-RFC: 0001                      # zero-padded 4 digits; matches the filename
Title: ...                        # short and descriptive
Author: Full Name (@handle)       # one or more, comma-separated
Status: Draft                     # see lifecycle above
Type: Standards Track             # Standards Track | Process | Informational
Category: Interface               # Standards Track only: Interface | Data | Registry | Meta
Created: 2026-05-30               # ISO-8601 date
Protocol-Version: wmcp/0.2-draft  # OPTIONAL
Requires: BCP 14; ...             # OPTIONAL: WM-RFC numbers or external specs
Replaces: 0000                    # OPTIONAL
Superseded-By: 0000               # OPTIONAL; REQUIRED when Status is Superseded
License: CC0-1.0
---
```

Required headers: `WM-RFC`, `Title`, `Author`, `Status`, `Type`, `Created`,
`License`. Standards Track RFCs also require `Category`.

## Numbering and files

- Files live in `rfcs/` as `WM-RFC-NNNN-<slug>.md`, slug lowercase-hyphenated.
- `WM-RFC-0000` is the template.
- Numbers are permanent. A Superseded RFC keeps its number; the replacement
  gets a new one and a `Replaces:` header.

## Normative language

RFCs use BCP 14 (RFC 2119 / RFC 8174) keywords — MUST, SHOULD, MAY, and their
negatives — **only in all capitals** and **only** for behavior required for
interoperability or safety. Aspirational or positioning statements are
non-normative notes and must not use these keywords.

## Versioning of ratified specifications

A Standards Track RFC that defines a protocol carries its own protocol version
(e.g. `wmcp/MAJOR.MINOR`) and states its compatibility rules in a Versioning
section. The RFC's lifecycle status (above) and the protocol's version number
are independent: a Final RFC may still version its protocol forward under its
own MINOR/MAJOR rules. A change that would break a previously conformant
implementation requires a new MAJOR and, typically, a new or revised RFC.

## Changing this process

This document is a Process RFC in spirit. Material changes follow the same
lifecycle: a PR, a review, and a Last Call. Editorial fixes (typos, broken
links) may be merged directly.
