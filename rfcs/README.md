# WM-RFC Index

This directory holds the World Model RFCs. Each RFC is a single Markdown file
named `WM-RFC-NNNN-<slug>.md` with a machine-readable preamble (validated by
[`tools/validate_rfcs.py`](../tools/validate_rfcs.py)). See
[PROCESS.md](../PROCESS.md) for the lifecycle and
[WM-RFC-0000-template.md](WM-RFC-0000-template.md) for the template.

Numbers are assigned on first PR and never reused. `0000` is reserved for the
template. Status reflects the lifecycle stage at the last merge to `main`.

## Standards Track

| #    | Title | Category | Status | Author |
|------|-------|----------|--------|--------|
| [0001](WM-RFC-0001-wmcp.md) | World Model Context Protocol (WMCP) — A Latent World Interface for Action-Conditioned Predictive Models | Interface | Draft | Abdelhamid Bakhta ([@AbdelStark](https://github.com/AbdelStark)) |

## Process & Informational

_None yet._

## Reserved / planned

These identifiers are referenced by accepted RFCs but not yet drafted. A
reference here is a placeholder, not a commitment to content or timeline.

| #    | Working title | Referenced by |
|------|---------------|---------------|
| 0002 | Embodiment & action-semantics registry | WM-RFC-0001 §10, §17, §19 |
