# Governance

This project produces open specifications for interoperability between
action-conditioned predictive world models and the planners, controllers, and
agents that query them. Governance exists to keep that process open,
legible, and vendor-neutral — not to govern the research itself.

## Principles

- **Vendor-neutral.** No specification may require a particular vendor's
  product, hosted service, or proprietary format to implement. Extension points
  exist precisely so vendors can differentiate without forking the standard.
- **Rough consensus and running code.** Decisions are made by rough consensus
  among contributors, weighted toward demonstrated implementation experience.
  We adopt the IETF's stance: we reject kings, presidents, and voting; we
  believe in rough consensus and running code. A specification is not Final
  until something implements it.
- **Specify less.** The field is young and the modeling paradigm is unsettled.
  When a choice can be deferred to an extension registry or left to
  implementations, it should be.
- **Everything in the open.** Proposals, discussion, and decisions happen in
  public issues and pull requests. Rationale for every accept/reject decision
  is recorded in the PR.

## Roles

### Contributors

Anyone who opens an issue, comments, or sends a pull request. No prior
affiliation is required. Contributors propose RFCs, review them, and build
implementations. This is the default and most important role.

### Editors

A small group responsible for keeping the process moving and the corpus
consistent. Editors:

- triage incoming proposals and assign RFC numbers;
- shepherd RFCs through the lifecycle (PROCESS.md) and call Last Call;
- judge when rough consensus has been reached and record the decision;
- maintain the index, templates, tooling, and registries;
- merge PRs.

Editors are stewards of *process*, not gatekeepers of *ideas*. An editor's
technical opinion carries no more weight than any other contributor's; their
distinct authority is procedural — declaring consensus, not deciding outcomes.

Editorship is added by consensus of the existing editors, on the basis of
sustained, high-quality contribution. The current editor(s) are listed in
[`.github/CODEOWNERS`](.github/CODEOWNERS).

## How decisions are made

1. Substantive technical decisions are made in the open on the relevant issue
   or PR and resolved by rough consensus (PROCESS.md).
2. An editor declares consensus only after a Last Call period elapses with no
   unresolved blocking objection. A "blocking objection" is a concrete, stated
   technical concern — not a mere preference or a -1 without rationale.
3. If consensus cannot be reached, the default is **no change**: the RFC stays
   in Review, is Rejected, or is Withdrawn, and the reasons are recorded. A
   stalled proposal can be re-opened later with new evidence.
4. Disagreements about process (as opposed to a specific RFC) are resolved by
   the editors, who should err toward transparency and minimal intervention.

## Registries

Several RFCs delegate extensibility to registries (capabilities, codecs,
error codes, embodiment namespaces, and so on), each with a registration policy
in the sense of RFC 8126 (Specification Required, Expert Review, or Private
Use). Until a dedicated maintainer is designated by a future RFC, the editors
administer these registries under the policy each RFC states. The reserved
`x-<vendor>/…` namespace is always available for Private Use without
registration.

## Code of conduct

Participation is governed by the [Code of Conduct](CODE_OF_CONDUCT.md). Editors
are responsible for its enforcement.

## Amending governance

This document changes through the same RFC process it helps define
(PROCESS.md): a pull request, public review, and a Last Call period. Editorial
fixes may be merged directly.
