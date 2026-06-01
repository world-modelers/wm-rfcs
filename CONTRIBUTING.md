# Contributing

Thank you for helping build open standards for world-model interoperability.
This repository holds **specifications** (WM-RFCs), the **process** that governs
them, and the **tooling** that keeps the corpus consistent. Reference
implementations and schema packages live in separate repositories.

Please read [PROCESS.md](PROCESS.md) and [GOVERNANCE.md](GOVERNANCE.md) first —
they define what an RFC is, how it advances, and how decisions are made. This
document is the practical how-to.

## Ways to contribute

You do not need to write an RFC to contribute meaningfully:

- **Review RFCs in `Review` or `Last Call`.** Concrete, implementation-grounded
  feedback is the single most valuable contribution. Point at the section.
- **Report a spec defect** — an ambiguity, contradiction, or under-specified
  edge case — with the *Spec issue* template.
- **Build and report implementation experience.** "I implemented §8.3 and hit
  X" carries more weight than any abstract argument (GOVERNANCE.md).
- **Improve tooling or docs** — the validator, templates, CI, this guide.
- **Propose a new RFC** (see below).

## Reporting a spec issue

Open an issue with the *Spec issue* template. Cite the RFC and section
(e.g. "WM-RFC-0001 §8.8"), quote the text, and state the ambiguity or
contradiction concretely. Editorial fixes (typos, broken links, formatting)
can skip the issue and go straight to a small PR.

## Proposing a new RFC

1. **Float the idea first** — open an issue with the *RFC proposal* template, or
   start a Discussion. Cross-cutting interoperability concerns belong in an RFC;
   implementation details do not (PROCESS.md, "What belongs in a WM-RFC").
2. **Reserve a number** by asking on your issue; an editor confirms the next
   free `WM-RFC-NNNN`.
3. **Draft** by copying [`rfcs/WM-RFC-0000-template.md`](rfcs/WM-RFC-0000-template.md)
   to `rfcs/WM-RFC-NNNN-<slug>.md`. Keep the preamble; fill in the sections that
   apply and delete the rest.
4. **Validate locally** (see below), then open a PR with `Status: Review`.
5. Iterate through the lifecycle in PROCESS.md.

## Local checks

The only required check is the structural linter, which runs in CI and has no
dependencies:

```bash
python3 tools/validate_rfcs.py
```

It verifies the preamble contract, filename convention, number uniqueness, and
that every RFC is linked from `rfcs/README.md`. Run it before every PR.

## Style

- **Normative language is reserved.** BCP 14 keywords (MUST, SHOULD, MAY, …) are
  for interoperability- or safety-critical behavior only, in all capitals.
  Don't use them for emphasis.
- **No marketing.** Write for an implementer. Prefer precise, testable
  statements over adjectives. If a claim can't be checked, cut or qualify it.
- **Cite prior art accurately.** Distinguish normative references (needed to
  implement) from informative ones (context). Don't overstate relationships to
  existing systems.
- **Specify the smallest thing that achieves interoperability.** Push optional
  behavior to capabilities and extension registries.
- One sentence per line is welcome (it makes diffs and review cleaner) but not
  required.

## Pull requests

- Keep a PR focused on one RFC or one concern.
- Fill in the PR template, including the lifecycle transition you intend
  (e.g. Draft → Review).
- Status transitions to `Last Call`, `Accepted`, `Final`, etc. are performed by
  editors per PROCESS.md, not self-assigned.
- Be responsive to review; resolve threads in the RFC text, not just in
  comments.

## Licensing of contributions

All specification text in this repository is dedicated to the public domain
under CC0-1.0. By contributing, you certify that you can and do release your
contribution under CC0-1.0 and that, to your knowledge, it does not knowingly
infringe third-party rights (CC0 waives copyright, not patents or trademarks).
If you contribute on behalf of an employer, ensure you are authorized to do so.

## Conduct

All participation is governed by the [Code of Conduct](CODE_OF_CONDUCT.md).
