# World Model RFCs

**Open, vendor-neutral specifications for action-conditioned predictive world
models — and how planners query them in latent space.**

[![Specs: CC0-1.0](https://img.shields.io/badge/specs-CC0--1.0-blue.svg)](https://creativecommons.org/publicdomain/zero/1.0/)
[![Process: WM-RFC](https://img.shields.io/badge/process-WM--RFC-success.svg)](PROCESS.md)
[![RFCs](https://img.shields.io/badge/RFCs-1%20draft-informational.svg)](rfcs/README.md)

This repository is where the community designs the *interoperability layer* for
world models: the runtime contracts, data formats, and registries that let an
independently built planner query an independently built world model without a
bespoke integration for every pair. The work is organized as **WM-RFCs** —
versioned, reviewable specification documents — following a process modeled on
the IETF RFC, Python PEP, and Rust RFC traditions.

It is a standards effort, not a framework. There is no library to install here.
There are specifications, the process that ratifies them, and the tooling that
keeps them consistent.

---

## The problem

The embodied-AI stack has matured from the bottom up. There are solid standards
for *recorded* data — RLDS canonicalizes Open X-Embodiment, and LeRobot has
converged delivery on Parquet + MP4. What is missing is a standard for
*runtime* interaction with a **model of dynamics**.

Today every world model exposes a bespoke surface: NVIDIA Cosmos through
NIM/Triton, other foundation models through their own APIs, JEPA-family research
models through ad-hoc Python. A planner that wants to evaluate action sequences
against two world models writes two integrations. A model author who wants reach
courts each planner individually. This is an **M × N integration problem** — the
same friction the Model Context Protocol (MCP) removed for tools.

The goal of this project is to collapse M × N to **M + N**: write a planner once
against a common interface, and it runs against any conformant world model,
whether that model lives in-process on a robot or behind an API in a datacenter.

```
  before:  M planners  ✕  N models   →   M·N bespoke integrations
  after:   M planners  +  N models    →   one shared contract
```

## What we standardize — and what we don't

The field's modeling paradigm is unsettled (JEPA-style joint-embedding
prediction, diffusion, autoregressive token models, world models built on frozen
visual features). Freezing that science would be premature standardization. So
the scope is deliberately narrow: **we standardize the interaction contract — an
ABI, not an ontology.**

**In scope** — the runtime interface: how a planner discovers a model's
capabilities, encodes observations into latent state, advances that state under
candidate actions, branches it non-destructively, scores it against a goal, and
reads back uncertainty — across both an in-process binding (live tensors, no
serialization) and a wire binding (remote, multi-tenant serving). Plus the data
formats, error model, and extension registries that interoperability requires.

**Out of scope** — the latent representation, model architecture, training
objective, data collection (the RLDS/LeRobot layer already covers it), the
reward or task-specification language, the planning algorithm itself,
cross-model latent portability, a universal embodiment ontology, and on-robot
safety validation. These are left to implementations or pushed to extension
registries so the interface can stabilize while the research moves.

This split — a small required core, capability negotiation, and graceful
degradation so a minimal model still works with a sophisticated planner — is
what makes a standard adoptable rather than aspirational.

## The RFCs

| #    | Title | Status | Summary |
|------|-------|--------|---------|
| [0001](rfcs/WM-RFC-0001-wmcp.md) | World Model Context Protocol (WMCP) | Draft | A latent-space runtime interface for action-conditioned predictive models: a verb set, a capability/Descriptor model, and invariants (no-mutation, determinism, handle lifetime), with both an in-process and an MCP-compatible wire binding. |

The full index, including reserved and planned numbers, is in
[`rfcs/README.md`](rfcs/README.md). The complete reference list and relation to
prior work are in WM-RFC-0001 §15 and §20.

## How it works

1. **Float an idea** — open an issue or discussion. Cross-cutting
   interoperability concerns become RFCs; implementation details do not.
2. **Reserve a number** and draft from
   [`rfcs/WM-RFC-0000-template.md`](rfcs/WM-RFC-0000-template.md).
3. **Open a PR.** It moves through the lifecycle —
   `Draft → Review → Last Call → Accepted → Final` — by **rough consensus and
   running code**: a Standards Track RFC is not Final until an independent
   reference implementation exists.

The full lifecycle, preamble contract, and numbering rules are in
[PROCESS.md](PROCESS.md). Who decides, and how, is in [GOVERNANCE.md](GOVERNANCE.md).

## Get involved

You do not need to write an RFC to contribute. The most valuable contributions
are **implementation-grounded review** ("I implemented §8.3 and hit X") and
**precise defect reports** (an ambiguity or contradiction, cited to the section).
See [CONTRIBUTING.md](CONTRIBUTING.md) for how to review, report, and propose.

Every RFC carries a machine-readable preamble checked in CI by a dependency-free
linter — run it locally before any PR:

```bash
python tools/validate_rfcs.py
```

## Relation to existing standards

WM-RFCs are designed to ride existing ecosystems rather than reinvent them:

- **MCP (Model Context Protocol)** — the wire binding is an MCP-compatible
  extension, reusing its lifecycle, JSON-RPC framing, capability negotiation,
  transport, and authentication. WMCP adds what MCP has no need for: latent
  state as a branchable resource, uncertainty as a first-class field, and an
  in-process binding.
- **Gymnasium** — `reset()`/`step()` generalized to branchable,
  non-destructive, latent-addressed dynamics with capability negotiation.
- **RLDS / Open X-Embodiment / LeRobot** — complementary data-layer standards.
  WM-RFCs reuse their `observation.*` feature naming and embodiment conventions
  rather than inventing a second vocabulary.
- **DLPack / Apache Arrow** — adopted for zero-copy in-process tensors and
  columnar/remote bulk transport, keeping the data plane aligned with the
  LeRobot layer.
- **LSP (Language Server Protocol)** — the precedent for "one semantic contract,
  in-process or over a pipe."

## Repository layout

```
.
├── README.md                     # you are here
├── PROCESS.md                    # the RFC lifecycle, numbering, preamble contract
├── GOVERNANCE.md                 # roles, decision model, registries
├── CONTRIBUTING.md               # how to review, report, and propose
├── rfcs/
│   ├── README.md                 # the RFC index
│   ├── WM-RFC-0000-template.md   # template for new RFCs
│   └── WM-RFC-0001-wmcp.md       # WMCP
└── tools/
    └── validate_rfcs.py          # dependency-free structural linter (runs in CI)
```

## License

All specification text in this repository is dedicated to the public domain
under [CC0-1.0](https://creativecommons.org/publicdomain/zero/1.0/), so anyone
can implement, fork, or build on these standards without restriction. By
contributing you agree to release your contribution under CC0-1.0; see
[CONTRIBUTING.md](CONTRIBUTING.md#licensing-of-contributions).

## Citation

```bibtex
@misc{wmcp2026,
  title        = {World Model Context Protocol (WMCP): A Latent World Interface
                  for Action-Conditioned Predictive Models},
  author       = {Bakhta, Abdelhamid},
  howpublished = {WM-RFC-0001, World Model RFCs},
  year         = {2026},
  note         = {\url{https://github.com/world-modelers/wm-rfcs}}
}
```
