---
WM-RFC: 0001
Title: World Model Context Protocol (WMCP) — A Latent World Interface for Action-Conditioned Predictive Models
Author: Abdelhamid Bakhta (@AbdelStark)
Status: Draft
Type: Standards Track
Category: Interface
Created: 2026-05-30
Protocol-Version: wmcp/0.2-draft
Requires: BCP 14 (RFC 2119, RFC 8174) [normative keywords]; JSON-RPC 2.0 and JSON / RFC 8259 [wire binding]; the Model Context Protocol (MCP) 2025-11-25 lifecycle, transport, and schema [MCP-compatible wire profile]; DLPack [in-process binding]; Apache Arrow IPC/Flight [arrow data channel]; RFC 8126 [extension registry policies]
License: CC0-1.0
---

## Abstract

This document specifies the **World Model Context Protocol (WMCP)**, a vendor-neutral runtime interface that lets a *planner* — a policy, model-predictive controller, or agent — discover and query an *action-conditioned world model* as a queryable, branchable, latent-space predictor.

Where the Model Context Protocol (MCP) standardizes how AI applications expose tools and context over a common protocol, WMCP standardizes how a decision-making process reaches a predictive model of environment dynamics. It treats **latent state as a first-class, addressable, branchable resource** and **predictive uncertainty** as a first-class field.

WMCP is defined as an **abstract interface** — a verb set, a capability model, a Descriptor, and a set of invariants — independent of how bytes move. It has two conformant **bindings**: an **in-process binding** for local inference and planning, where Latents are live in-memory (CPU/GPU) tensors and the model runs in the planner's own address space with no serialization; and a **wire binding** over JSON-RPC 2.0, with an MCP-compatible profile for remote and multi-tenant serving and a plain JSON-RPC profile for deployments that deliberately do not claim MCP compatibility. A conforming planner targets the abstract interface; a runtime maps that interface to the selected binding and applies negotiated polyfills when optional features are absent, so the planner's algorithm is written once and the binding-specific adapter handles transport and tensor exchange.

WMCP is designed for adoption first: a **small required core**, capability negotiation, and Client-side **polyfills** so a minimal model still works with a sophisticated planner. The intent is to turn today's M×N integration problem — every planner hand-wired to every model — into M+N.

WMCP standardizes the *runtime interaction contract*, not an ontology. It does **not** standardize the latent representation, training objective, architecture, reward function, or robot embodiment taxonomy; those are deliberately out of scope or pushed to extension registries (§19). The modeling paradigm (JEPA-style, diffusion, autoregressive) is unsettled, and freezing it would be premature standardization.

## Motivation

The embodied-AI stack has a mature **data/trace layer** — RLDS canonicalizes Open X-Embodiment, and LeRobot has converged delivery on Parquet+MP4 — but that standardizes *recorded* trajectories, not *runtime queries* against a model. At runtime, every world-model vendor exposes a bespoke surface (NVIDIA Cosmos via NIM/Triton with JSON `controlnet_specs`; other foundation models via their own APIs; JEPA-family research models via ad-hoc Python). A planner that wants to evaluate action sequences across two world models writes two integrations; a model author seeking adoption must court each planner individually. This is the friction MCP removed for tools, and WMCP removes it for world models.

Two deployment regimes must both be first-class, because real systems span them:

- **Local / embedded planning.** A model-predictive or shooting planner running onboard a robot, or in a research loop, advances a model many times per control step at 10–50 Hz. It cannot afford to base64-encode an RGB frame and round-trip JSON each step. The model lives in-process; Latents stay as GPU tensors; branching is a tensor reference; real-time replanning means abandoning a rollout the instant a new sensor frame arrives.
- **Remote / shared serving.** A heavy world model served centrally to many planners, across organizations, with multi-tenancy, quotas, and authentication.

A protocol that addresses only one regime fails the other. WMCP's binding model (§3) lets one model adapter serve both.

The closest existing runtime contract, Gymnasium's `reset()` / `step(action)`, is insufficient: it mutates ground-truth state in place (no latent addressing, no branching), has no runtime capability negotiation across embodiments, and has nowhere to put uncertainty. WMCP fills this runtime gap — above the data/trace standards and below planners and benchmarking harnesses.

**Non-goals.** WMCP does not standardize: (i) the latent representation or model architecture; (ii) model training or data collection (the RLDS/LeRobot layer); (iii) a task or reward specification language (a model's cost, if any, is opaque — §8.10); (iv) weight distribution or licensing; (v) the planning algorithm itself; (vi) cross-model latent portability (§8.8); (vii) a universal robot embodiment ontology (deferred to WM-RFC-0002); (viii) safety validation of actions before execution on physical hardware. These are deliberately out of scope so the interface can stabilize while the science moves.

## 1. Design Principles

- **P1 — Minimal required surface.** The mandatory core is small enough to implement quickly against any model that can encode an observation and advance one step.
- **P2 — Capability negotiation, safe by default.** Servers advertise what they support; a Client treats any unrecognized capability as absent, and a Server ignores unknown optional request fields unless they are named in `requires_extensions` (§2). The protocol grows without breaking either side.
- **P3 — Graceful degradation.** A Client SHOULD polyfill an unsupported optional verb locally where feasible (§5). A minimal model remains usable by an advanced planner.
- **P4 — Binding independence.** Semantics, the Descriptor, capabilities, and invariants are defined once, independent of transport. In-process and wire bindings are equally first-class (§3); a planner's algorithm targets the abstract interface and binding adapters handle transport and tensor exchange.
- **P5 — Control/data plane separation.** Method calls, Handles, and small scalars (the control plane) are decoupled from bulk tensors — observations, **actions**, latents, decoded frames, gradients (the data plane). Bulk data moves over the cheapest channel both sides support (§4). Tensors are never forced through JSON beyond a bounded inline fallback.
- **P6 — Ride existing ecosystems.** Reuse the MCP lifecycle for the MCP-compatible wire profile, DLPack for in-process tensors, Arrow for batched/columnar exchange and alignment with the LeRobot data layer, and ship Gymnasium adapters.
- **P7 — Reward-free by default.** Many current action-conditioned latent world models are reward-free predictors; model-provided costs are optional throughout, and the canonical reward-free objective is latent distance to an encoded goal (§8.10).

## 2. Terminology and Conventions

The key words MUST, MUST NOT, REQUIRED, SHALL, SHALL NOT, SHOULD, SHOULD NOT, RECOMMENDED, MAY, and OPTIONAL are to be interpreted as in BCP 14 (RFC 2119, RFC 8174) when, and only when, they appear in all capitals. Normative keywords are reserved for behavior required for interoperability or safety; aspirational and positioning statements are non-normative notes.

- **Server**: an implementation of the WMCP interface exposing one or more world models. In the in-process binding the Server is an in-memory object; in the wire binding it is a remote process.
- **Client**: a planner, policy, controller, or harness consuming a Server.
- **Binding**: a concrete realization of the abstract interface (in-process or wire).
- **Model**: one action-conditioned predictive model exposed by a Server.
- **Latent**: the Server-internal predictive state rolled forward by the model. Opaque to the Client unless exported.
- **Handle**: an opaque, unguessable, session-scoped identifier naming a Latent. The unit of addressing, branching, and lifecycle. Handles are immutable references; two distinct Handles MAY alias the same immutable Latent (as `wm/fork` produces). A Handle never silently changes the Latent it names.
- **Data Reference (DataRef)**: a tagged descriptor for a bulk tensor payload, selecting a data-plane channel (§4). Observations, actions, latents, decoded frames, and gradients are all tensors and use DataRef.
- **Rollout**: a sequence of `step` operations producing a trajectory of Latents.
- **Scoring path**: any supported way to obtain a cost — a model stage/terminal cost, `wm/evaluate`, client-side scoring over decoded observations (`decode`), or client-side scoring over exported latents (`latentExport`). Goal-directed planning requires at least one (§8.10, §12).
- **World Model Descriptor** (the *Descriptor*): the per-model machine-readable capability and schema manifest returned by `wm/describe` (§7). It is **not** an ML governance Model Card (Mitchell et al., 2019) and carries no training-data or ethics disclosures.
- **Polyfill**: Client-side emulation of an optional verb a Server does not support.

**Conventions.** Shape symbols: B (observation/environment batch), N (candidate action sequences), H (horizon), A (flattened action dimension), Z (latent shape); Δt = 1/`control_hz` is the control period. All scalar objectives in WMCP are **costs** — lower is better and planners minimize. Costs are named explicitly to avoid overloading: `stage_cost` (one step), `cumulative_cost` (Σ stage over a horizon), `cost_per_step` (the un-summed per-step vector), and the terminal/goal `cost` returned by `wm/evaluate`. Non-standard field, capability, method, channel, codec, and error names MUST be namespaced `x-<vendor>/…`, and unknown namespaced names MUST be ignored (P2) unless a request includes `requires_extensions:[name,…]`. A Server that does not understand or did not negotiate any listed extension MUST fail the request with `CAPABILITY_NOT_NEGOTIATED`.

## 3. Execution Modes and Bindings

WMCP is an abstract interface with two normative bindings. Conformance (§12) is defined against the abstract semantics; a binding is conformant iff it preserves the verbs, capability model, and invariants. Binding-specific mechanics MUST NOT change the no-mutation, lifetime, determinism, or cost-orientation semantics.

### 3.1 Abstract interface

The interface comprises the verb set (`describe`, `encode`, `step`, `rollout`, `fork`, `evaluate`, `decode`, `release`, `export`, `import`, `cancel`, `grad`, plus the optional helper `action_project`, §10), the Descriptor (§7), the capability model (§5, §6.1), and the invariants (no-mutation §8.3, seed/determinism §8.2, handle lifetime §8.8). Nothing in the interface presumes a transport.

### 3.2 In-process binding (local inference and planning)

The Server is an object in the Client's address space. `initialize` is **object construction** (load a checkpoint, return an interface object) and returns the same session-capability set and model list a wire `initialize` would. There is no serialization:

- Observations and actions pass as native tensors (PyTorch/JAX/NumPy/CuPy) via the **DLPack** protocol — zero-copy, including on GPU.
- A Handle wraps a live Latent tensor. `wm/export` returns a DLPack capsule (a view, where the framework allows); such views are **ephemeral** and logically read-only (§8.8).
- `wm/fork` returns additional references to the parent's immutable Latent (refcounted) — zero-copy. `wm/step` is **not** copy-on-write: it allocates a new Latent for its prediction (§8.3).
- Calls are synchronous by default, sized for tight control loops. `cancel` is cooperative.
- Gradients MAY flow natively: with a differentiable rollout (§8.9) and a planner and model sharing the same autograd framework, returned tensors stay attached to that framework's graph w.r.t. the input `actions`, so the Client backpropagates with `.backward()`. This is a **same-framework** capability (§8.9); DLPack exchange alone does not preserve an autograd graph.

Python is the canonical reference binding. A native binding (e.g. Rust) is RECOMMENDED for embedded/real-time deployment where GC pauses are unacceptable; it exchanges tensors via the DLPack and Arrow C data interfaces.

### 3.3 Wire binding (remote / shared serving)

The wire binding uses JSON-RPC 2.0 control-plane messages. A Server claiming the **MCP-compatible wire profile** MUST implement the MCP lifecycle (§6.1) and MCP Streamable HTTP transport, and SHOULD also expose stdio for local development. A Server claiming the **plain JSON-RPC wire profile** uses the same method names and §6.1 fields over a transport it names, but MUST NOT describe itself as MCP-compatible.

Control-plane messages carry Handles and small scalars as JSON; bulk tensors travel on a negotiated data channel (§4), referenced from the control plane by DataRef. Bulk tensors MUST NOT be forced through JSON except via the bounded `inline` fallback (subject to `limits.max_inline_bytes`, §4).

When the MCP-compatible profile is used, WMCP MUST follow the MCP lifecycle (§6.1): MCP `initialize` is the first request (carrying `clientInfo`/`serverInfo`); WMCP's semantic version and capabilities are carried inside an `experimental.wmcp` capability object; the Client sends `notifications/initialized` before normal WMCP operation. The MCP transport protocol version (the `MCP-Protocol-Version` header) and the WMCP semantic version (`wmcpVersion`) are **distinct** and negotiated independently. That profile inherits MCP transport, authentication (e.g. OAuth on Streamable HTTP), and observability; WMCP adds no authentication surface of its own. In the MCP-compatible profile MCP's own request cancellation also applies: a `notifications/cancelled` whose `requestId` matches an in-flight streaming `wm/rollout` MUST be treated as equivalent to `wm/cancel` for that request (§8.7), and `wm/cancel`'s `request_id` for a streaming rollout is the JSON-RPC `id` of the originating request — the two are aliases, not competing mechanisms (for task-augmented MCP requests, MCP's `tasks/cancel` request is the corresponding native mechanism).

### 3.4 One adapter, both bindings

A model author implements the abstract interface once; the reference runtime (§16) projects it onto either binding. The same Cosmos or JEPA adapter therefore serves a local planner via DLPack and a remote fleet via JSON-RPC without per-binding model code. This instantiates P4 (binding independence) and is the deployment-level counterpart of the verb-level polyfills (P3, §5): one implementation, every deployment. *(Non-normative: this property is a design goal, realized by the reference runtime, not a conformance requirement on every adapter.)*

## 4. Data References and the Control/Data Plane

Observations (in), actions (in), latents (out via `export`), decoded frames (out via `decode`), and gradients (out via `grad`) are bulk tensors, referenced from control-plane messages by a DataRef and carried on a channel negotiated at `initialize` (`dataChannels`). The negotiated channel set is the intersection of Client and Server support. For Client-to-Server inputs, the Client chooses a negotiated channel in each DataRef; for Server-to-Client outputs, the Server chooses a negotiated channel, preferring the lowest-copy channel compatible with the binding, device, lifetime, and requested codec.

A DataRef is a tagged descriptor:
```jsonc
{
  "channel": "arrow",            // inline | uri | shmem | dlpack | arrow | x-vendor/…
  "codec":   "arrow-ipc/1",      // serialization within the channel (REQUIRED)
  "ref":     "flight://…",       // channel-specific locator (omitted for inline value)
  "dtype":   "f32",              // WMCP dtype alias (table below)
  "shape":   [256, 16, 7],       // non-negative integer dims
  "layout":  "row_major",        // OPTIONAL: row_major (default) | channels_first | channels_last | x-…
  "strides": null,               // OPTIONAL: null = contiguous row-major, else element strides
  "device":  "cuda:0",           // OPTIONAL: cpu | cuda:<i> | rocm:<i> | metal:<i> | x-…
  "byte_order": "le",            // OPTIONAL: le | be — for inline/raw CPU bytes
  "readonly": true,              // OPTIONAL: logical mutability; exported latents are readonly
  "expires_at": null,            // OPTIONAL: data-plane reference expiry (ISO-8601)
  "value":   null,               // inline json-array/1 only: a small JSON numeric array
  "bytes":   null,               // inline wmcp-tensor/1 only: base64 raw tensor bytes
  "metadata": {}                 // OPTIONAL extension map
}
```

| Channel    | Scope                  | Mechanism                                          | Copy cost |
|------------|------------------------|----------------------------------------------------|-----------|
| `inline`   | any (always supported) | base64 bytes (`wmcp-tensor/1`) or a small JSON array (`json-array/1`), up to `max_inline_bytes` | high; small payloads only |
| `uri`      | remote/async           | object-store or file URI the peer fetches; lifetime is declared by `expires_at` or access policy | out-of-band |
| `shmem`    | same host              | POSIX shared memory or **CUDA IPC** handle; ephemeral | near-zero |
| `dlpack`   | in-process             | DLPack capsule / object exposing `__dlpack__`; ephemeral | zero |
| `arrow`    | local or remote        | Arrow IPC Tensor message, or Arrow Flight descriptor/ticket resolving to one | low; aligns with LeRobot |

`inline` MUST be implemented by every binding up to `max_inline_bytes` for both `json-array/1` and `wmcp-tensor/1`. An inline DataRef MUST contain exactly one of `value` (`json-array/1`) or `bytes` (`wmcp-tensor/1`). `value` is a nested JSON array matching `shape` in row-major order (numbers for numeric dtypes, booleans for `bool`). `bytes` is base64 of contiguous raw tensor bytes interpreted by `dtype`, `shape`, `layout`, and `byte_order`; `strides` MUST be `null` or omitted for `wmcp-tensor/1`. Payloads beyond `max_inline_bytes` (the UTF-8 JSON byte length for `value`, decoded byte length for `bytes`) require another negotiated channel and otherwise return `PAYLOAD_TOO_LARGE`. A Client requesting an unavailable channel receives `DATA_CHANNEL_UNAVAILABLE` and SHOULD retry on `inline` (within the bound). The in-process binding uses `dlpack` by default and never base64-encodes.

**Channel vs codec.** A **channel** is how bytes move; a **codec** is how a tensor is serialized within it. `dlpack`/`shmem` are *ephemeral* (in-memory exchange, not storage); `arrow-ipc/1` and `wmcp-tensor/1` are *durable* codecs suitable for export/import (§8.8). For WMCP tensors, `arrow-ipc/1` is the Arrow encapsulated Tensor IPC message for one dense tensor; a DataRef never relies on an ad hoc RecordBatch schema for core tensor exchange. A Server MUST validate an incoming DataRef against the receiving schema and reject a malformed one with `INVALID_TENSOR`.

**Device-buffer synchronization.** For device-resident zero-copy channels (`dlpack`, and `shmem`/CUDA IPC carrying device memory), the producer MUST make the buffer stream-ordered-safe for the consumer before the DataRef is observed: for `dlpack` via the DLPack producer–consumer stream-exchange contract (`__dlpack__(stream=…)`), and for a CUDA IPC buffer by recording an event — or synchronizing the producing stream — that the consumer waits on before its first read. A consumer MUST NOT read a device buffer before this synchronization completes. A producer MAY surface the synchronizing stream or event in DataRef `metadata` (e.g. `metadata.cuda_event`). This applies to the in-process and same-host bindings and is a no-op for host-resident `inline`/`uri`/`arrow` payloads.

**WMCP dtype aliases.** DLPack's C-level dtype is `(code, bits, lanes)`, not a string; WMCP defines string aliases (all `lanes = 1`) and their DLPack mapping. A binding MUST map aliases as follows (DLPack codes: Int=0, UInt=1, Float=2, BFloat=4, Bool=6):

| Alias | DLPack (code, bits) | | Alias | DLPack (code, bits) |
|-------|---------------------|-|-------|---------------------|
| `u8`  | (UInt, 8)           | | `f16` | (Float, 16)         |
| `i32` | (Int, 32)           | | `bf16`| (BFloat, 16)        |
| `i64` | (Int, 64)           | | `f32` | (Float, 32)         |
| `bool`| (Bool, 8)           | | `f64` | (Float, 64)         |

This split lets the *same* control plane be both wire-portable and real-time fast: Handles and scalars are identical across bindings; only the data plane changes.

## 5. Capability Discovery and Graceful Degradation

Capabilities are declared at two scopes: **session/binding** capabilities at `initialize` (§6.1) — `streaming`, `cancel`, the data channels, and `max_inline_bytes` — and **per-model** capabilities in the Descriptor (§7) — `fork`, `rollout`, `batchedRollout`, `evaluate`, `decode`, `latentExport`/`latentImport`, `deterministicReplay`, `commonRandomNumbers`, `grad`, and `differentiable` (with its supported framework(s)). `rollout` means native single-sequence horizon rollout over `[H][A]`; `batchedRollout` means native candidate-batch rollout over `[N][H][A]` and implies `rollout`. This distinction matters for planners because a Server can be efficient for one candidate sequence without being efficient for large shooting batches. The **effective** capability for any operation is the intersection of session capability, the target model's capability, and what the Client requested; anything outside that intersection is unsupported and handled below. If a limit appears at both session and model scope, the effective limit is the stricter value.

For each optional verb a Server omits, a conforming Client runtime SHOULD apply these polyfills before reporting the capability unavailable to the planner:

| Missing verb/capability | Polyfill                                                                                         | Requires                          |
|-------------------------|--------------------------------------------------------------------------------------------------|-----------------------------------|
| `wm/fork`               | Step the same parent Handle repeatedly (non-mutating `step`); vary `seed`/`noise` for independent stochastic samples; `export`+`import` for parallel buffers. | non-mutating `step` (always); `latentImport` for parallel buffers |
| `rollout`               | Loop `wm/step` over the horizon for one sequence, returning the same result shape.                | `step`                            |
| `batchedRollout`        | Loop native `wm/rollout` over candidates, or loop `wm/step` when `rollout` is absent.             | `rollout` or `step`               |
| `wm/evaluate`           | `wm/decode` the terminal Latent and score with a Client metric, or score on exported latents (§8.10). | `decode` or `latentExport`        |
| `wm/decode`             | None. Latents stay opaque; latent-space planning is unaffected. Loses pixel inspection only.       | —                                 |
| `differentiable`/`grad` | Finite-difference gradient: perturb each action dim, re-`rollout`, difference the costs (`O(A·H)` extra rollouts); or fall back to a sampling solver. | `rollout` or `step` + a scoring path |

Because `step` is non-mutating (§8.3, a *core* requirement), a planner can build a search tree by stepping a parent repeatedly **without** `fork`; `fork` is a performance convenience, not a gate. **However, the core gives dynamics expansion only:** a goal-directed planner additionally needs a *scoring path* (§2, §8.10) — a model cost, `evaluate`, `decode`, or `latentExport` — without which a Core-only Server can advance latents but cannot rank them. A Client runtime MUST present a uniform interface regardless of native-vs-polyfilled verbs, and SHOULD expose a `native: bool` per verb for performance-aware planners.

## 6. Session

### 6.1 `initialize`

The first interaction (a request in the wire binding; construction in the in-process binding) negotiates protocol version, session capabilities, and data channels, and lists the available models. **Model-specific capabilities are not authoritative until `wm/describe(model_id)` (§7).**

MCP-compatible wire request (the WMCP payload rides inside MCP `initialize`):
```jsonc
{ "jsonrpc":"2.0", "id":1, "method":"initialize",
  "params": {
    "protocolVersion": "2025-11-25",                  // MCP transport version (header: MCP-Protocol-Version)
    "clientInfo": { "name":"worldforge", "version":"0.4.0" },
    "capabilities": {
      "experimental": { "wmcp": {
        "wmcpVersion": "wmcp/0.2-draft",              // WMCP semantic version (distinct from MCP)
        "client": { "latentImport": true, "streaming": true, "cancel": true },
        "dataChannels": ["shmem","arrow","inline"]
      } } } } }
```
Response (`result`):
```jsonc
{ "protocolVersion": "2025-11-25",
  "serverInfo": { "name":"cosmos-wmcp", "version":"1.2.0" },
  "capabilities": { "experimental": { "wmcp": {
    "wmcpVersion": "wmcp/0.2-draft",
    "binding": "wire", "wire_profile": "mcp",          // wire | in_process; wire_profile: mcp | jsonrpc
    "models": ["cosmos-predict2.5-2b", "vjepa2-wm-base"],
    "sessionCapabilities": { "streaming": true, "cancel": true,
                             "dataChannels": ["shmem","arrow","inline"] },
    "limits": { "max_inline_bytes": 1048576 }
  } } } }
```
After a successful `initialize`, an MCP-compatible Client MUST send `notifications/initialized` before any `wm/*` call. The Client proposes `wmcpVersion`; the Server responds with the (possibly older) version it will speak, which the Client MUST accept or close the session; if no compatible MAJOR exists the Server MUST return an error and the session MUST NOT proceed (§18). If `dataChannels` is omitted, the Client proposes only `inline`; if `client` is omitted, it is the empty capability object. In the in-process binding the constructor returns the same `sessionCapabilities`, `models`, and `limits` object.

Plain JSON-RPC profile `initialize` uses the WMCP payload directly as `params` (`wmcpVersion`, `clientInfo`, optional `client`, optional `dataChannels`) and returns the WMCP response fields directly in `result` (`wmcpVersion`, `serverInfo`, `binding:"wire"`, `wire_profile:"jsonrpc"`, `models`, `sessionCapabilities`, `limits`). It does not use MCP `protocolVersion`, `capabilities.experimental.wmcp`, `notifications/initialized`, or MCP transport headers.

## 7. The World Model Descriptor (`wm/describe`)

`wm/describe(model_id)` returns the per-model **Descriptor**: capabilities, schemas, scoring paths, dynamics, and limits for one model — the runtime analogue of an RLDS dataset spec and the negotiation surface for cross-embodiment use. It is a capability/schema manifest, not an ML governance Model Card.

```jsonc
{
  "model_id": "vjepa2-wm-base",
  "model_version": "1.0.0",
  "wmcpVersion": "wmcp/0.2-draft",
  "bindings": ["in_process", "wire"],
  "capabilities": {                          // PER-MODEL (intersect with session + request, §5)
    "fork": true, "rollout": true, "batchedRollout": true,
    "evaluate": true, "decode": false,
    "latentExport": true, "latentImport": true,
    "deterministicReplay": true, "commonRandomNumbers": true,
    "grad": false, "differentiable": { "in_process": ["torch"] }
  },
  "latent": {
    "kind": "token_sequence",                // global_vector | token_sequence | spatial_grid | opaque
    "exportable": true,
    "codecs": ["arrow-ipc/1", "wmcp-tensor/1", "dlpack"],  // durable first; dlpack ephemeral (§8.8)
    "dtype": "f32", "shape_hint": [196, 768],
    "device_hint": "cuda"
  },
  "observation": {                           // LeRobot/RLDS feature-keyed (§8.4)
    "context_length": 3,                     // # past frames conditioned on; >1 ⇒ non-Markov
    "features": {
      "observation.images.front": { "kind":"image",  "dtype":"u8",  "shape":[3,224,224], "layout":"channels_first", "rate_hz":10 },
      "observation.state":         { "kind":"vector", "dtype":"f32", "shape":[7], "rate_hz":10 }
    }
  },
  "action_space": {                          // §10
    "kind": "box",                           // box | discrete | multidiscrete | dict | x-…
    "dtype": "f32", "shape": [7],
    "low": [-1,-1,-1,-1,-1,-1,-1], "high": [1,1,1,1,1,1,1],
    "control_hz": 10, "dt_s": 0.1, "frameskip": 1,
    "encoding": "raw",                       // raw | latent_action
    "embodiment": "oxe:franka_panda",        // OPTIONAL; absence is conformant
    "semantics": "x-wmcp/raw-normalized"     // OPTIONAL frame/units/control-mode hint
  },
  "scoring": {                               // declares the model's scoring paths (§8.10)
    "cost_orientation": "minimize",
    "stage_cost": false, "terminal_cost": true,
    "evaluate_goal_types": ["latent", "observation"],
    "metric_ids": ["model/default", "l2/normalized"]   // Server-owned metrics (§8.7)
  },
  "dynamics": {
    "stochastic": false,
    "max_horizon": 64,                       // hard cap; HORIZON_EXCEEDED beyond it
    "recommended_horizon": 16,               // soft: fidelity degrades past this (compounding error)
    "uncertainty": [], "requires_seed": false
  },
  "limits": { "max_batch": 256, "max_live_handles": 4096, "default_ttl_ms": 60000, "max_inline_bytes": 1048576 }
}
```

`limits` lets a planner size its search to what the Server will serve; `latent.device_hint` lets an in-process or same-host planner avoid host↔device copies; `scoring` lets a planner discover, before stepping, whether and how it can rank trajectories.

## 8. Methods and Invariants

The verb set, at a glance. "Mutates" is always *no* — state-advancing verbs leave their inputs unchanged and return new Handle(s) only when the method materializes Latents (§8.3). Full request/response schemas are normative in Appendix A.

| Verb | Capability gate | Returns Handle(s) | Idempotent | Summary |
|------|-----------------|:-----------------:|:----------:|---------|
| `wm/describe` | core | no | yes | return the Descriptor (§7) |
| `wm/encode` | core | yes | no | observation(s) / context → Handle(s) |
| `wm/step` | core | yes | no | one action-conditioned transition → new Handle |
| `wm/release` | core | no | yes | free Latents |
| `wm/rollout` | `rollout` or `batchedRollout` | if requested | no | horizon / batched-shooting rollout |
| `wm/fork` | `fork` | yes | no | n references to one Latent |
| `wm/evaluate` | `evaluate` | no | yes | score a Latent against a goal → cost |
| `wm/decode` | `decode` | no | yes | Latent → observation (inspection) |
| `wm/export` / `wm/import` | `latentExport` / `latentImport` | import: yes | export: yes | (de)serialize a Latent |
| `wm/grad` | `grad` | no | yes | vector–Jacobian product `∂objective/∂actions` |
| `wm/cancel` | `cancel` (session) | no | yes | abort an in-flight streaming `rollout` |
| `wm/action_project` | `latentAction` | no | yes | raw action → latent-action space (§10) |

### 8.1 Required core

`initialize`, `wm/describe`, `wm/encode`, `wm/step`, `wm/release`. A Server implementing at least these is **WMCP-Core** compliant (§12). Core provides latent dynamics; goal-directed planning additionally requires a scoring path (§5, §8.10).

### 8.2 Seed, determinism, and noise

A `seed` is a non-negative integer or a decimal string; Servers SHOULD accept decimal strings, since seeds can exceed JSON's safe integer range (2⁵³). Every stochastic latent-producing request carries one optional root seed: `wm/encode.seed`, `wm/step.seed`, or `wm/rollout.noise.seed`. If the model `requires_seed` and no request seed is given, the Server MUST assign one and return it in result `seed`; a Server MAY also echo a supplied seed after normalization.

`deterministicReplay` (per-model) advertises **logical** determinism: with the same `(Handle, action, seed)` and the same model version, hardware class, precision mode, and batch shape, the Server reproduces the same RNG draws and result up to platform floating-point reproducibility. Bitwise equality across differing hardware, precision, or batch shape — e.g. a single `wm/step` versus the same step inside a batched `wm/rollout` — is **not** implied; non-associative floating-point and nondeterministic GPU reductions make it unattainable in general. Without `deterministicReplay`, a repeated call yields an independent draw from the same distribution.

**Noise control.** For batched stochastic operations a Client controls sampling via `noise: { "mode": "common" | "independent", "seed"?: <Seed | Seed[]> }`. If `noise` is omitted, the Server uses the model's default stochastic process; if the model `requires_seed`, §8.2 seed assignment still applies. `common` requests **common random numbers** — the same per-step noise realization across all candidates in a batch — so cost differences reflect actions, not sampling noise (the right default for shooting planners). `independent` Monte-Carlos an expectation. A single `seed` is the rollout root seed; for `independent`, `seed` MAY also be a `[N]` vector of per-candidate root seeds. Common random numbers are **not** universally implementable (diffusion samplers, adaptive compute), so they are a per-model capability `commonRandomNumbers`; a Server that cannot honor the requested mode MUST return `DETERMINISM_UNAVAILABLE` rather than silently change sampling semantics. Seeds compose deterministically along a rollout (per-step seeds derived from the root seed and step index).

### 8.3 No-mutation invariant (REQUIRED, core)

After `step(h, a)` (or `rollout` from `h`), any subsequent operation on `h` MUST behave as if that call never occurred, except for TTL refresh and accounting metadata — reproducible under a fixed seed when `deterministicReplay` is set (§8.2), distributionally unchanged otherwise. This is what makes branching possible. It is free for `fork` (Latents are immutable, so forked Handles are shared references, not copies) but **not** for `step`, which necessarily allocates a new Latent for its prediction. Search-tree memory therefore grows with the number of expanded nodes and is bounded by `release`/TTL/quotas (§8.8), not eliminated by sharing.

### 8.4 `wm/encode` — observation(s) → Latent(s)

Observations and context are supplied as a feature-keyed map of DataRefs, following LeRobot/RLDS `observation.*` naming so recorded episodes feed in unchanged.

```jsonc
// params (single frame or, when context_length > 1, an ordered history per feature: oldest → newest)
{ "model_id": "vjepa2-wm-base",
  "context": {
    "observation.images.front": { "channel":"dlpack","codec":"dlpack","ref":"…","dtype":"u8","shape":[3,3,224,224] },
    "observation.state":         { "channel":"dlpack","codec":"dlpack","ref":"…","dtype":"f32","shape":[3,7] }
  },
  "seed": "1234" }
// result
{ "handle": "lat_01J…", "ttl_ms": 60000, "seed": "1234" }
// vectorized: "observations": [ <context map>, … ] → { "handles": [ … ], "ttl_ms": …, "seed": … }
```

`model_id` MAY be omitted when the Server hosts a single model; the returned Handle is bound to that model for every later verb (§8.8); an unknown `model_id` returns `MODEL_NOT_FOUND`. The leading axis of each feature is the history axis (length ≤ `context_length`, oldest → newest); the Server MAY accept a shorter context and pad per its Descriptor. **Temporal model:** one `wm/step` advances one decision period Δt = `dt_s` = 1/`control_hz`; with `frameskip > 1` it advances `frameskip` underlying environment steps per decision.

### 8.5 `wm/step` — single action-conditioned transition (core)

```jsonc
// params — small actions MAY use the inline DataRef form
{ "handle": "lat_01J…",
  "action": { "channel":"inline","codec":"json-array/1","value":[0.02,0.0,-0.01,1.0],"dtype":"f32","shape":[4] },
  "seed": "8830124", "want": ["stage_cost","uncertainty"] }
// result
{ "handle": "lat_02K…", "ttl_ms": 60000, "stage_cost": null, "uncertainty": { "ensemble_std": 0.07 } }
```

Returns a **new** Handle; the input is not mutated (§8.3). If the Server assigned or normalized a seed, the result includes `seed` (§8.2). `want` is an extensible list; defined members: `stage_cost`, `uncertainty` (§11), and `latent` (a DataRef to the new Latent, alongside the Handle). A requested optional member that is unsupported MUST be returned as `null`; a member that was not requested SHOULD be omitted. `stage_cost` is `null` when the model exposes no stage cost (§8.10) — never fabricated.

### 8.6 `wm/rollout` — horizon and batched shooting *(per-model `rollout` / `batchedRollout`)*

```jsonc
// params — actions are bulk: an [N][H][A] or [H][A] tensor by DataRef (not JSON), per P5
{ "handle": "lat_01J…",
  "actions": { "channel":"arrow","codec":"arrow-ipc/1","ref":"flight://…","dtype":"f32","shape":[2,16,7] },
  "noise": { "mode":"common", "seed":"8830124" },
  "want": ["cumulative_cost"],              // and/or "cost_per_step"
  "objective": { "goal": { "type":"latent", "handle":"z_goal" }, "metric_id":"model/default" },  // OPTIONAL (§8.10); needs `evaluate`
  "return_latents": "terminal",             // none | terminal | all
  "stream": true, "differentiable": false,  // §8.9
  "deadline_ms": null }                      // optional anytime budget
// result
{ "terminal_handles": ["lat_a…","lat_b…"],
  "cumulative_cost": { "channel":"inline","codec":"json-array/1","value":[0.12,0.17],"dtype":"f32","shape":[2] },
  "objective_cost":  { "channel":"inline","codec":"json-array/1","value":[0.31,0.24],"dtype":"f32","shape":[2] },
  "cost_per_step": null, "uncertainty": null, "complete": true, "seed": "8830124" }
```

`cumulative_cost` is the per-candidate sum of stage costs (`[N]`); `cost_per_step` is the un-summed `[N][H]`. For a single-sequence `[H][A]` request, `N = 1`. A Server advertising `rollout` MUST accept `[H][A]`; a Server advertising `batchedRollout` MUST accept both `[H][A]` and `[N][H][A]`; a Server without `batchedRollout` MUST reject `[N][H][A]` with `CAPABILITY_NOT_NEGOTIATED`. Terminal/goal cost comes from `wm/evaluate` (§8.7) or — as a round-trip optimization for the dominant shooting pattern — from the OPTIONAL `objective` field: when set, and the model advertises `evaluate`, the Server scores each candidate's terminal Latent against `objective.goal` using the Server-owned `objective.metric_id` (§8.7) and returns `objective_cost` (`[N]`, minimize convention §2), exactly as if `wm/evaluate` had been called on each terminal Handle. `objective` is independent of `want`/`return_latents`, so the planner still composes its overall objective `J = Σ stage + terminal` (§8.10); a goal type or metric the model does not support fails `GOAL_UNSUPPORTED`, and `objective` supplied without the `evaluate` capability fails `CAPABILITY_NOT_NEGOTIATED`. With `stream: true` (the Client MUST have advertised the session `streaming` capability), the Server emits `wm/rollout.partial` notifications — `{ request_id, completed:[indices], cost:[…], done:bool }` whose `params` carry the originating request id; JSON-RPC notifications omit the top-level `id` — then a final response, so a planner can prune early. In partial notifications, `cost` is empty unless a rollout cost was requested and computed; when present it is ordered to match `completed`. A rollout exceeding `max_horizon` MUST fail `HORIZON_EXCEEDED`; `recommended_horizon` is advisory and never enforced. When `deadline_ms` is set (anytime planning for real-time control), the Server MUST return the best results computed by the deadline, marking the remainder incomplete (`complete:false`), rather than overrun. If `complete:false`, the final result MUST include `completed`; every per-candidate result vector or DataRef in that final response is ordered by `completed` and has leading dimension `len(completed)`. If `complete:true`, `completed` MAY be omitted and is implicitly `[0, …, N-1]`. Unsupported native batching → Client loops `wm/rollout` or `wm/step` (§5). The parent Handle is preserved (§8.3). If the Server assigned or normalized a rollout seed, the final result includes `seed` (§8.2).

`return_latents` controls Handle materialization: `none` returns no Latent Handles; `terminal` returns terminal Handles for the completed candidates; `all` returns both terminal Handles and trajectory Handles (`[N][H]`, or `[H]` for an unbatched `[H][A]` request, when `complete:true`). If `complete:false`, `terminal_handles` and `trajectory_handles` follow the `completed` indexing rule above. Handles returned in `trajectory_handles` are live and independently releasable.

### 8.7 `wm/fork`, `wm/evaluate`, `wm/decode`, `wm/cancel`

- `wm/fork` *(per-model `fork`)* `{ "handle":"…", "n":4 }` → `{ "handles":[…] }`. Returns `n` additional Handles aliasing the **same** immutable Latent (refcounted, zero-copy — not successors, not copies); each may then be advanced independently. Per §8.3 the no-mutation invariant already permits branching without it.
- `wm/evaluate` *(per-model `evaluate`)* scores a Latent against a `goal` (tagged union: `latent` | `observation` | `language`; external reward-model goals only via a namespaced extension) using a named `metric_id` → `{ "cost":0.17, "metric_id":"model/default", "uncertainty":null }`, lower being closer. The **Server owns the metric**: for `goal:{type:latent}` only the model can declare which distance or learned scorer its latent geometry supports, via `scoring.metric_ids` (§7). Client-side latent metrics are valid only when the Client explicitly accepts responsibility for their calibration (§8.10). An unsupported goal type or metric returns `GOAL_UNSUPPORTED`. See §8.10.
- `wm/decode` *(per-model `decode`)* `{ "handle":"…", "modalities":["observation.images.front"] }` → frames via DataRef. Inspection / human-in-the-loop / client-side scoring only.
- `wm/cancel` *(session `cancel`)* `{ "request_id": 42 }` aborts an in-flight streaming `rollout`, returning `CANCELLED` for that request. In the MCP-compatible profile an MCP `notifications/cancelled` for the rollout's request id is an equivalent trigger (§3.3). REQUIRED for responsive real-time replanning: on a new observation the planner cancels the stale rollout and re-encodes. In-process, cancellation is cooperative. Latents the aborted call began to produce are released; their Handles thereafter return `INVALID_HANDLE`.

### 8.8 Lifecycle: `wm/release`, `wm/export`, `wm/import`

A Handle is **immutable** (§8.3) and **bound to the model and session that created it**: verbs other than `encode`/`describe` carry no `model_id` and infer the model from the Handle; using a Handle against another model or session MUST fail `INVALID_HANDLE`. Because Latents are immutable, concurrent operations on one Handle are safe. `ttl_ms` is a **sliding** expiry, refreshed on each successful operation that references the Handle; a Server MAY cap absolute lifetime via `limits`.

- `wm/release` `{ "handles":[…] }` → `{ "released":[…], "unknown":[…] }`. Idempotent for Handles of the same session. Children created by `step`/`fork` are independent Latents; releasing a parent does **not** invalidate them. Servers MUST reclaim Latents past `ttl_ms` even absent an explicit release.
- `wm/export` `{ "handle":"…", "codec":"arrow-ipc/1" }` → a DataRef, valid only if the latent is `exportable`. If `codec` is omitted, the Server selects the first durable codec in `latent.codecs` that it can produce over a negotiated data channel. Exported latents are **logically read-only**; modifying an exported buffer is undefined behavior or grounds for import rejection. **Ephemeral vs durable:** `dlpack`/`shmem` exports are same-process/same-host, in-memory handoffs and MUST NOT be presented as durable storage. **Durable** export/import (caching across sessions, edge↔cloud transfer, benchmark fixtures) MUST use `arrow-ipc/1` or `wmcp-tensor/1` and carry metadata: `model_id`, `model_version`, `latent_schema`, `codec`, `dtype`, `shape`, `layout`, `byte_order`, and an OPTIONAL content hash.
- `wm/import` reverses it → a Handle. The target model is identified by an explicit `model_id` or by durable DataRef metadata; `model_id` MAY be omitted only when the Server hosts a single model or the DataRef metadata identifies exactly one hosted model. It MUST validate the payload against the receiving Descriptor and MUST fail `LATENT_CODEC_MISMATCH` unless `model_id`, `model_version`, `latent_schema`, `codec`, `dtype`, `shape`, and applicable `layout`/`byte_order` all match; a malformed tensor returns `INVALID_TENSOR`; an unknown `model_id` returns `MODEL_NOT_FOUND`. **Cross-model import is out of scope** (§17).

### 8.9 Differentiable rollout and gradients *(per-model `differentiable`, `grad`)*

Gradient-based planners — projected gradient descent, SGD/Adam trajectory optimization, augmented-Lagrangian constrained control — descend `∂J/∂a` for a scalar cost `J` over a rollout. WMCP exposes this without forcing every Server to be differentiable and without transmitting full Jacobians.

**In-process (same-framework autograd transparency).** This is a **same-framework** capability: when the Client requests `differentiable: true`, the planner and model share the autograd framework named in `capabilities.differentiable.in_process` (e.g. `["torch"]`), and the input `actions` tensor requires gradients, the Server MUST return outputs (`stage_cost`/`cumulative_cost`, and any `latent` DataRef) that remain attached to that framework's autograd graph w.r.t. `actions`. The Client differentiates natively (`J.backward()`; read `actions.grad`). Nothing is serialized. DLPack exchange alone does **not** preserve an autograd graph; across frameworks the Client MUST use `wm/grad` or finite differences. Retaining the graph costs memory, so it is opt-in per call.

**Wire / cross-framework (`wm/grad`, a vector–Jacobian product).** A Server advertising `grad` accepts a reverse-mode product:
```jsonc
// params
{ "handle": "lat_01J…",
  "actions": { "channel":"arrow","codec":"arrow-ipc/1","ref":"…","dtype":"f32","shape":[1,16,7] },
  "objective": { "type":"terminal_cost", "goal": { "type":"latent", "handle":"lat_goal…" } },
  // objective.type: cumulative_cost | terminal_cost | latent
  "cotangent": null,                       // REQUIRED (output-shaped) when objective is non-scalar (type:latent)
  "noise": { "mode":"common", "seed":"1234" } }
// result
{ "grad_actions": { "channel":"arrow","codec":"arrow-ipc/1","ref":"…","dtype":"f32","shape":[1,16,7] } }
```
`wm/grad` returns a vector–Jacobian product, never the full Jacobian (reverse mode is what first-order optimizers need; it avoids an `O(H·A·Z)` tensor). For a scalar `objective` the cotangent is implicitly 1 and the result is `∂objective/∂actions`; scalar cost objectives over a horizon are either `cumulative_cost` (sum of stage costs over the supplied actions) or `terminal_cost` (goal/terminal cost at the final Latent). For `objective:{type:latent}` the Client MUST supply a `cotangent` of the terminal Latent's shape, yielding `cotangentᵀ·∂z_terminal/∂actions`. `grad_actions` matches `actions` in shape. A Server without the requested gradient mode returns `GRADIENT_UNAVAILABLE`.

**Degradation.** A gradient-based Client facing neither `differentiable` nor `grad` SHOULD fall back to finite differences (`O(A·H)` extra rollouts) or a sampling solver. Per §5, the planner still runs.

### 8.10 Costs, goals, and the reward-free case

Many action-conditioned world models of current interest are **reward-free**: JEPA-family predictors forecast latents and define no cost. WMCP therefore makes every cost OPTIONAL (P7), declares scoring paths in the Descriptor (`scoring`, §7), and supports two patterns.

**Model-provided cost (optional).** If a model exposes a cost it sets `scoring.stage_cost`/`scoring.terminal_cost`; `wm/step` MAY then return `stage_cost` and `wm/evaluate` a goal `cost`. A model that returns a stage cost MUST have had the goal/task bound at `encode` through a declared observation feature or namespaced conditioning extension (carried in the latent — the goal-conditioned-observation pattern), or otherwise possess a well-defined task-independent cost. **A Server MUST NOT fabricate a cost** when no scoring semantics are available; it returns `null` for an explicitly requested unsupported cost field and otherwise omits that field.

**Planner-computed latent distance (the reward-free default).** The planner encodes the goal observation once (`encode(goal_obs) → z_goal`), rolls candidates out to terminal Latents, and scores each by distance to `z_goal` via `wm/evaluate` with `goal:{type:latent, handle:z_goal}` and a `metric_id` the Server owns (§8.7). Where `evaluate` is unsupported, a `latentExport`-capable planner MAY export terminal and goal latents and apply its own metric, accepting that calibration becomes its responsibility. This is the reward-free control path WMCP makes first-class, and is the contract the stable-worldmodel `get_cost` hook reduces to.

**Aggregation.** `wm/step` → `stage_cost` (one step). `wm/rollout` → `cumulative_cost` (`[N]`, Σ stage over the horizon) and/or `cost_per_step` (`[N][H]`). `wm/evaluate` → the terminal/goal `cost`; `wm/rollout.objective` → `objective_cost` (`[N]`), the same terminal/goal cost folded into the rollout response for shooting batches (§8.6). The planner composes its own objective `J = Σₜ stage(zₜ,aₜ) + terminal(z_H)`. All costs follow the minimize convention (§2).

## 9. Worked Example: one planner, both modes

A receding-horizon shooting planner. The planner body is identical; only construction differs. Full wire messages are in Appendix B.

```text
# In-process (onboard robot, real-time)
server = wmcp.load("vjepa2-wm-base", device="cuda")     # initialize == construction, dlpack data plane

# Remote (shared fleet)
server = wmcp.connect("https://wm.fleet/…")             # MCP initialize + notifications/initialized, arrow plane

# ---- identical from here ----
desc   = server.describe(model)                          # per-model caps + scoring paths (§7)
z_goal = server.encode(goal_obs)                         # reward-free: encode the goal once (§8.10)
h0     = server.encode(obs_t)
loop until done:
  A  = sample N action seqs of length H within desc.action_space, N ≤ desc.limits.max_batch
  res = server.rollout(h0, A, noise={"mode":"common"},
                       objective={"goal":{"type":"latent","handle":z_goal}},  # fold goal scoring in (§8.6); needs `evaluate`
                       return_latents="terminal", stream=True, deadline_ms=control_period_ms)
  costs = res.objective_cost                          # [N]; w/o rollout.objective → batch wm/evaluate the terminals; w/o evaluate → decode/export + client metric (§5, §8.10)
  a* = first action of argmin_i costs[i]
  on new_frame_arrived: server.cancel(inflight_request_id) # abandon stale plan, replan
  execute a* ; obs_{t+1} = observe()
  server.release(res.terminal_handles); h0 = server.encode(obs_{t+1})
```

The planner never branches on binding or on which verbs are native — the runtime (§3.4, §5) hides both. Writing one planner that runs locally or remote, against any conformant world model, is the property the whole RFC exists to deliver.

## 10. Action Space and Embodiment Ontology

`action_space.kind` types the space, following Gymnasium: `box` (continuous; `shape`, `low`, `high`), `discrete` (`n`), `multidiscrete` (`nvec`), `dict` (named sub-spaces), or a namespaced extension. The Descriptor also carries `control_hz`, `dt_s`, and `frameskip` (the temporal model, §8.4), and OPTIONAL `semantics` (frame, units, control mode, normalization).

Embodiment is referenced by namespaced id in `action_space.embodiment`: `oxe:franka_panda` or `lerobot:so101` for physical robots, or `gym:<env_id>` (e.g. `gym:swm/PushT-v1`) for benchmark/control environments. **`embodiment` is OPTIONAL; its absence does not make a model non-conformant.** When absent or in `gym:`, the typed space is self-describing and the Client matches on `kind`/shape/bounds — keeping non-robot world models (locomotion suites, Atari, procedural environments) first-class. The registry of canonical robot ids and default layouts is reserved for WM-RFC-0002.

Encodings: `raw` (values match the space) and `latent_action` (points in a learned latent-action space, the IDM/FDM interface for cross-embodiment transfer; the Server SHOULD expose `wm/action_project` mapping raw actions into that space, gated by `latentAction`). A Client MUST reject an `action_space` it cannot satisfy — by `embodiment` id when present, otherwise by `kind`/shape/bounds — rather than send mis-shaped actions (which the Server rejects with `UNSUPPORTED_ACTION_SPACE`).

## 11. Uncertainty Model

`uncertainty` is an extensible map. Defined keys: `epistemic`, `aleatoric`, `ensemble_std`, `cost_var`, `method`. A Server returns only keys it computes; a Client treats a missing key as "not reported," never zero. For batched methods, scalar uncertainty MAY be repeated as a scalar only when it applies to the whole result; per-candidate or per-step uncertainty MUST be returned as a DataRef with leading shape `[N]` or `[N,H]`. Uncertainty is advisory for planning (risk-aware cost, replan triggers), not a correctness guarantee.

## 12. Conformance

A Server claims a profile **per binding and per model** (e.g. "WMCP-Planning, in-process and wire, for `vjepa2-wm-base`"). The assertions in this section are normative for the claim; a published conformance suite (reference: WorldForge, §16) MUST verify at least the following and MUST NOT weaken these assertions. Until such a suite is published, these assertions are the source of truth. "Within tolerance" means within the platform floating-point tolerance of §8.2.

**WMCP-Core** (`initialize`, `wm/describe`, `wm/encode`, `wm/step`, `wm/release`): latent dynamics only.
- **C1.** `initialize` returns a `wmcpVersion` the suite accepts, session capabilities, a model list, and `limits.max_inline_bytes`; an MCP-compatible Server completes the `notifications/initialized` handshake.
- **C2.** `wm/describe` returns a well-formed Descriptor: required fields present; per-model `capabilities`, `scoring`, `latent.kind`, and `action_space.kind` in their enums; every action bound typed; `batchedRollout` is absent or implies `rollout`.
- **C3.** `wm/encode` of a conforming observation returns a live Handle; an unknown `model_id` returns `MODEL_NOT_FOUND`; a malformed tensor returns `INVALID_TENSOR`.
- **C4 (no-mutation).** `wm/step(h, a)` returns a Handle ≠ `h`; a subsequent `wm/step(h, a')` is unaffected by the first, verified by equality within tolerance against `step(h, a')` issued before the first call.
- **C5 (determinism).** With `deterministicReplay`, `wm/step(h, a, seed)` repeated on the same device/precision/batch agrees within tolerance; without it, repeats are distributionally consistent over a sample. A requested `noise.mode`/`deterministicReplay` the model lacks returns `DETERMINISM_UNAVAILABLE`, never silent downgrade.
- **C6 (lifecycle).** After `wm/release(h)`, operations on `h` return `INVALID_HANDLE`; a Handle past `ttl_ms` returns `EXPIRED_HANDLE`; a Handle from another session is rejected.
- **C7 (extensibility).** Unknown capabilities and unknown optional request fields are ignored, not errored (P2), unless named in `requires_extensions`, in which case the request fails `CAPABILITY_NOT_NEGOTIATED`.

**WMCP-Planning** = Core + ≥1 scoring path (model cost, `evaluate`, `decode`, or `latentExport`):
- **PL1 (scoring exists).** At least one declared scoring path returns or enables a finite cost for a rolled-out candidate. For `decode` or `latentExport` paths, the suite supplies a deterministic Client metric and verifies that the required data are returned.
- **PL2 (metric sanity).** When `evaluate` declares `latent` goals, `wm/evaluate(z_goal, {type:latent, handle:z_goal})` is the minimal cost over a neighborhood of `z_goal` (a goal scores best against itself).

**WMCP-BatchedPlanning** = Planning + native `wm/rollout` over `[N][H][A]` tensors:
- **BP1 (batched ≡ sequential).** `wm/rollout(h, A)` returns terminal Handles agreeing, within tolerance, with looping `wm/step`; any supported requested rollout cost tensors (`cumulative_cost`, `cost_per_step`) agree with the equivalent sequential computation and have the declared shapes.
- **BP2 (common random numbers).** With `commonRandomNumbers` and `noise.mode="common"`, two identical candidates in one batch yield identical results within tolerance.

**Layered profiles:** **WMCP-Inspectable** (+`decode`); **WMCP-LatentPortable** (+ durable same-model `export`/`import` via a non-ephemeral codec — `export`→`import` round-trips to an equivalent Handle within tolerance, and a differing `model_version` returns `LATENT_CODEC_MISMATCH`); **WMCP-DifferentiablePlanning** (+ in-process same-framework autograd, whose `∂cost/∂actions` matches finite differences within tolerance, or wire `wm/grad`, likewise). The `inline` data channel is mandatory in every binding.

## 13. Error Model

JSON-RPC standard errors still apply: malformed JSON and invalid request structure use JSON-RPC's standard error codes (for example `-32700`, `-32600`, `-32601`, `-32602`). WMCP domain errors use JSON-RPC error objects (wire) / typed exceptions (in-process) carrying the numeric `code`, a `message`, and OPTIONAL `data`, reserving `-32000…-32099`:

| Code   | Name                       | Meaning                                  |
|--------|----------------------------|------------------------------------------|
| -32001 | INVALID_HANDLE             | unknown Handle, or used cross-model/session |
| -32002 | EXPIRED_HANDLE             | Handle past its TTL                      |
| -32003 | UNSUPPORTED_ACTION_SPACE   | action does not match the Descriptor     |
| -32004 | HORIZON_EXCEEDED           | rollout longer than `max_horizon`        |
| -32005 | LATENT_CODEC_MISMATCH      | export/import codec, schema, or version clash |
| -32006 | LIMIT_EXCEEDED             | batch or live-handle quota exceeded      |
| -32007 | CAPABILITY_NOT_NEGOTIATED  | method needs an unadvertised capability  |
| -32008 | DATA_CHANNEL_UNAVAILABLE   | requested channel unsupported              |
| -32009 | CANCELLED                  | request aborted via `wm/cancel`          |
| -32010 | MODEL_NOT_FOUND            | unknown `model_id`                       |
| -32011 | INVALID_TENSOR             | dtype, shape, layout, or payload invalid |
| -32012 | PAYLOAD_TOO_LARGE          | inline/channel payload exceeds limit     |
| -32013 | GOAL_UNSUPPORTED           | goal type or metric unsupported          |
| -32014 | DETERMINISM_UNAVAILABLE    | requested seed/noise semantics unsupported |
| -32015 | GRADIENT_UNAVAILABLE       | requested gradient mode unsupported      |

The `data` object MAY carry `{ handle?, request_id?, retryable: bool, detail? }`. `LIMIT_EXCEEDED` and transient transport failures are retryable after backoff; `DATA_CHANNEL_UNAVAILABLE` and `PAYLOAD_TOO_LARGE` are retryable only after changing channel or payload size. Other WMCP domain errors are terminal for that request — the Client MUST re-establish the precondition (re-encode, renegotiate, reshape) before retrying. Because creating verbs are non-idempotent (§14), a Client retrying a transport failure SHOULD assume the original may have succeeded and reconcile Handles.

## 14. Operational and Security Considerations

- **Trust model differs by binding.** In-process, the Server shares the Client's address space; it is not a sandbox, and security is the host's responsibility. The MCP-compatible wire profile inherits MCP transport authentication (e.g. OAuth) and adds no new authentication surface; plain JSON-RPC deployments MUST specify their own transport authentication and authorization policy.
- **MCP transport hardening.** A Server claiming the MCP-compatible Streamable HTTP profile MUST follow MCP transport security requirements, including `Origin` validation; local deployments SHOULD bind only to localhost, and non-local deployments SHOULD require authentication.
- **Handle scoping.** Handles MUST be unguessable and session-scoped; a Server MUST reject a Handle from another session.
- **Resource exhaustion.** `fork` and batched `rollout` amplify load; Servers MUST enforce advertised `limits` (live handles, batch, data-plane, `max_inline_bytes`) and fail fast (`LIMIT_EXCEEDED`, `PAYLOAD_TOO_LARGE`).
- **Data-plane lifetime.** `shmem`/`cuda_ipc` segments MUST be reclaimed on `release`, `cancel`, or TTL; a leaked IPC handle is a host resource leak.
- **URI data-plane fetches (SSRF).** A Server that fetches a `uri`-channel DataRef MUST restrict fetches to an explicit scheme/host allowlist, enforce a maximum content length (rejecting larger payloads with `PAYLOAD_TOO_LARGE`), and validate the declared content type (rejecting a mismatch with `INVALID_TENSOR`); it MUST NOT follow a `uri` to internal or link-local addresses unless explicitly allowlisted. `uri` payloads SHOULD be access-scoped to the session or the explicit exported-object lifetime.
- **Untrusted imports.** An imported Latent (`wm/import`) is untrusted input: a Server MUST validate it against the Descriptor (codec, dtype, shape, version → `INVALID_TENSOR`/`LATENT_CODEC_MISMATCH`) and MUST NOT assume it is in-distribution; a malformed or adversarial latent is an attack surface over the wire.
- **Wire gradient latency.** `wm/grad` makes gradient-based planning well-defined over the wire, but each optimizer step pays a network round-trip; prefer the in-process binding for gradient solvers, or batch several `grad` queries per round-trip.
- **Idempotency on retry.** `encode`, `step`, `rollout`, and `fork` create Latents and are **not** idempotent; on a transport retry a wire Client may receive duplicate Handles and SHOULD release the extras. `release`, `describe`, and `export` are idempotent.
- **Observation privacy.** Latents and decoded frames may encode sensitive observation content; in multi-tenant serving, `export`/`decode` access SHOULD be scoped and audited.

## 15. Relation to Prior Work

- **MCP** — WMCP's preferred wire profile is an MCP-compatible extension reusing MCP's lifecycle, JSON-RPC framing, capability negotiation, transport, and authentication. It diverges by making latent state a branchable resource, adding uncertainty as a core field, separating control and data planes for bulk tensors, and adding an in-process binding MCP has no need for.
- **LSP (Language Server Protocol)** — the precedent for "one semantic contract, runs in-process or over a pipe." WMCP follows the same separation of interface from transport.
- **Gymnasium** — generalized to branchable, non-destructive, latent-addressed dynamics with runtime capability negotiation; `action_space.kind` mirrors Gym spaces. A reference adapter wraps any WMCP Server as a (vectorized) Gym environment and vice versa.
- **DLPack / Apache Arrow** — adopted for the in-process and batched/columnar data planes; Arrow aligns with the LeRobot data layer, and Arrow Flight is the natural remote bulk channel.
- **RLDS / Open X-Embodiment / LeRobot** — complementary data-layer standards; WMCP reuses their `observation.*` feature naming and embodiment conventions rather than inventing a second ontology.
- **stable-worldmodel** — an in-process, reward-free, MPC-centric world-model research platform whose `model.get_cost(info_dict, action_candidates)` ↔ `solver` boundary is a concrete instance of the interface WMCP standardizes. Its `PlanConfig` (`horizon`, `receding_horizon`, `history_len`, `action_block`, warm-start) maps onto Descriptor planning defaults and rollout parameters; WMCP's in-process binding and reward-free design (§8.10) formalize how such platforms already operate.

The economic argument is the adoption argument: M planners × N models of bespoke integration collapses to M+N once both sides speak WMCP — and the binding model means M+N holds whether deployment is local, same-host, or remote.

## 16. Reference Implementation

The planned reference implementation, **WorldForge**, is expected to provide: the abstract interface plus both binding projections from a single adapter (§3.4); a Client runtime with the §5 polyfill layer and §4 data-channel negotiation; Server adapters wrapping a diffusion-family and a JEPA-family model; the conformance suite for §12; and Gymnasium + LeRobot bridges, plus a stable-worldmodel adapter (`encode`/`rollout`/`evaluate` ↔ `get_cost`/`action_candidates`, both directions). A native (Rust) in-process binding targets embedded/real-time deployment.

*Roadmap (non-normative).* Publish WM-RFC-0001 as an interface draft; ship a JSON Schema / TypeSpec package for the Descriptor, DataRef, action schema, error object, and method params/results; build the stable-worldmodel in-process adapter and a fake deterministic test model first; add a JEPA adapter with reward-free latent-goal planning, then an MCP-compatible wire adapter; defer CUDA IPC, Arrow Flight, and gradients to a later conformance milestone (define them, mark them optional). Badges "WMCP-Core/Planning/BatchedPlanning/Inspectable/LatentPortable/DifferentiablePlanning" are awarded per binding and per model by passing the §12 assertions.

## 17. Open Questions

1. **Second-order and dynamics Jacobians.** §8.9 defines first-order gradients. Second-order methods (iLQR/DDP) want per-step dynamics Jacobians `∂z_{t+1}/∂(z_t, a_t)`; exposing/transporting these efficiently (structured `want`, block-sparse VJPs) is open.
2. **Cross-architecture latent portability.** `wm/import` across *different* models needs a latent interlingua or learned adapters; out of scope here.
3. **Cross-host shared latents.** `cuda_ipc` is same-host; an efficient cross-host device-buffer channel (RDMA, Arrow Flight with device buffers) is open.
4. **Cross-model benchmark comparability.** A shared goal/metric vocabulary for comparing costs across models with different metrics and geometries.
5. **Action-semantics / embodiment registry** (§10, WM-RFC-0002) — governance and content.
6. **Multi-agent / shared world state** beyond single-agent forking.
7. **Formal schema artifacts** — JSON Schema or TypeSpec for the Descriptor and DataRef, generated from and kept in sync with Appendix A.

## 18. Versioning and Compatibility

Stable protocol versions use `wmcp/MAJOR.MINOR`; pre-1.0 draft versions MAY append `-draft` (this document: `wmcp/0.2-draft`). The protocol version is negotiated at `initialize` (§6.1) and is distinct from the MCP transport version. Rules:

- A **MINOR** increment is backward-compatible: it MAY add optional verbs, capabilities, `want` members, channels, codecs, error codes, or Descriptor fields. Peers sharing a MAJOR version MUST interoperate at the lower MINOR, ignoring unknown additions (P2).
- A **MAJOR** increment MAY break: removing/renaming a verb or field, changing a required field's type, tightening an invariant, or changing the meaning of a value. Servers MAY support multiple MAJOR versions and select per `initialize`.
- **Breaking change**, normatively, is any change that could cause a previously-conformant peer to fail a §12 assertion it previously passed. All else is non-breaking.
- **Deprecation.** A feature MAY be deprecated in a MINOR release and removed no earlier than the next MAJOR; deprecated features remain functional until removal, surfaced out-of-band, never by changing behavior.
- The **required core** (§8.1) and invariants (§8.2, §8.3, §8.8) are stability anchors and MUST NOT change within a MAJOR version.

*0.1 → 0.2-draft is a pre-1.0 breaking revision* (actions move to DataRef; per-model capabilities; MCP-aligned lifecycle; explicit `stage_cost`/`cumulative_cost`/`cost_per_step`; new error codes). Pre-1.0 drafts carry no stability guarantee.

## 19. Extension Registries

WMCP is extensible at defined points, each with a registration policy in the sense of RFC 8126. The `x-<vendor>/…` prefix (§2) is permanently reserved for **Private Use** and needs no registration; other values follow the stated policy. Unknown registered or namespaced values MUST be ignored by default (P2), but MUST fail with `CAPABILITY_NOT_NEGOTIATED` when named in `requires_extensions` (§2).

| Registry | Examples | Policy |
|----------|----------|--------|
| Session capabilities | `streaming`, `cancel` | Specification Required |
| Model capabilities | `fork`, `rollout`, `batchedRollout`, `evaluate`, `decode`, `latentExport`/`latentImport`, `deterministicReplay`, `commonRandomNumbers`, `grad`, `differentiable`, `latentAction` | Specification Required |
| Data channels | `inline`, `uri`, `shmem`, `dlpack`, `arrow` | Specification Required |
| Codecs | `json-array/1`, `wmcp-tensor/1`, `arrow-ipc/1`, `dlpack` | Specification Required |
| dtype aliases | `u8`, `i32`, `i64`, `bool`, `f16`, `bf16`, `f32`, `f64` | Specification Required |
| `want` members | `stage_cost`, `cumulative_cost`, `cost_per_step`, `uncertainty`, `latent` | Specification Required |
| Noise modes | `common`, `independent` | Specification Required |
| Goal types | `latent`, `observation`, `language`, `x-<vendor>/…` | Specification Required |
| Uncertainty keys | `epistemic`, `aleatoric`, `ensemble_std`, `cost_var`, `method` | Expert Review |
| Latent kinds | `global_vector`, `token_sequence`, `spatial_grid`, `opaque` | Expert Review |
| Action-space kinds | `box`, `discrete`, `multidiscrete`, `dict` | Expert Review |
| Metric ids | `model/default`, `l2/normalized` | Expert Review |
| Embodiment namespaces | `oxe:`, `lerobot:`, `gym:` | Specification Required (WM-RFC-0002) |
| Error codes (`-32000…-32099`) | §13 | Specification Required |

A future WM-RFC SHOULD designate a maintainer (a neutral working group or hub under GOVERNANCE.md) to administer these registries and the embodiment ontology (WM-RFC-0002).

## 20. References

**Normative.**
- Bradner, S. *Key words for use in RFCs to Indicate Requirement Levels.* RFC 2119 / BCP 14, 1997.
- Leiba, B. *Ambiguity of Uppercase vs Lowercase in RFC 2119 Key Words.* RFC 8174 / BCP 14, 2017.
- Cotton, M., Leiba, B., and T. Narten. *Guidelines for Writing an IANA Considerations Section in RFCs.* RFC 8126 / BCP 26, 2017.
- *JSON-RPC 2.0 Specification.* JSON-RPC Working Group, 2010.
- Bray, T. (ed.) *The JavaScript Object Notation (JSON) Data Interchange Format.* RFC 8259, 2017.
- *Model Context Protocol Specification.* MCP contributors, version 2025-11-25.
- *DLPack: Open In-Memory Tensor Structure.* dmlc, version in force at publication.
- *Apache Arrow Columnar Format, IPC, C Data Interface, and Flight.* Apache Software Foundation.

**Informative.**
- *Language Server Protocol Specification.* Microsoft, 2016–.
- Towers, M. et al. *Gymnasium.* Farama Foundation, 2024.
- O'Neill, A. et al. (Open X-Embodiment Collaboration). *Open X-Embodiment: Robotic Learning Datasets and RT-X Models.* arXiv:2310.08864, 2023.
- Ramos, R., Cadene, R. et al. *LeRobot.* Hugging Face, 2024–.
- Zhou, G. et al. *DINO-WM: World Models on Pre-trained Visual Features.* arXiv:2411.04983, 2024.
- Sobal, V. et al. *PLDM: Pixel-space Latent Dynamics Models.* 2025.
- Balestriero, R., LeCun, Y. *LeJEPA / SIGReg: Isotropic-Gaussian latent regularization.* 2025.
- Meta FAIR. *V-JEPA 2: Self-Supervised Video Models Enable Understanding, Prediction and Planning.* arXiv:2506.09985, 2025.
- Bruce, J. et al. (DeepMind). *Genie: Generative Interactive Environments.* arXiv:2402.15391, 2024.
- Hafner, D. et al. *Mastering Diverse Domains through World Models (DreamerV3).* arXiv:2301.04104, 2023.
- Hansen, N. et al. *TD-MPC2: Scalable, Robust World Models for Continuous Control.* arXiv:2310.16828, 2023.
- NVIDIA. *Cosmos World Foundation Model Platform for Physical AI.* arXiv:2501.03575, 2025.
- *LeWorldModel: Stable End-to-End Joint-Embedding Predictive Architecture from Pixels.* arXiv:2603.19312, 2026.
- Maes, L., Le Lidec, Q., Haramati, D., Massaudi, N., Scieur, D., LeCun, Y., Balestriero, R. *stable-worldmodel: Reproducible World Modeling Research and Evaluation.* arXiv:2602.08968, 2026.
- Mitchell, M. et al. *Model Cards for Model Reporting.* FAT* 2019.

## Appendix A — Normative Message Schemas

These schemas are normative; inline JSON in §6–§8 is illustrative. Notation: `field: type (req|opt[, default]) — note`. A binding MUST preserve these names, types, and optionality; the in-process binding maps each method to a call whose arguments and return carry the same fields (no JSON). Shared types:

- **Handle** = string (opaque, unguessable, session-scoped).
- **Seed** = non-negative integer or decimal string (§8.2).
- **DataRef** = the object of §4 (`channel`, `codec`, exactly one non-null payload locator/value among `ref`/`value`/`bytes`, `dtype`, `shape`, optional `layout`/`strides`/`device`/`byte_order`/`readonly`/`expires_at`/`metadata`).
- **FeatureMap** = object mapping a LeRobot `observation.*` key → DataRef.
- **Goal** = `{type:"latent", handle:Handle}` | `{type:"observation", observation:FeatureMap}` | `{type:"language", text:string}` | `{type:"x-…", …}`.
- **Noise** = `{ mode:"common"|"independent", seed?:Seed|Seed[] }` (`Seed[]` length `N`). **Cost** = number (minimized, §2).
- **RequestCommon** = optional `requires_extensions:string[]`; a binding MUST allow it on every `wm/*` request and apply §2 extension failure semantics before executing the method.

**initialize** — req: `wmcpVersion: string`, `clientInfo:{name,version}`, `client: object (opt,{})`, `dataChannels: string[] (opt,["inline"])` (carried under MCP `capabilities.experimental.wmcp` on the wire). res: `wmcpVersion`, `serverInfo:{name,version}`, `binding:"wire"|"in_process"`, `wire_profile:"mcp"|"jsonrpc" (req when binding="wire")`, `models: string[]`, `sessionCapabilities: object`, `limits:{max_inline_bytes,…}`. MCP-compatible Clients MUST then send `notifications/initialized`.

**wm/describe** — req: `model_id: string (opt if single model)`. res: the Descriptor (§7), including per-model `capabilities`, `scoring`, `observation`, `action_space`, `latent`, `dynamics`, `limits`.

**wm/encode** — req: exactly one of `context: FeatureMap` (leading axis = history ≤ `context_length`) or `observations: FeatureMap[]` (batch B); `model_id: string (opt)`; `seed: Seed (opt)`. res: `handle: Handle` (or `handles: Handle[]`), `ttl_ms: int`, `seed: Seed (if assigned or normalized)`.

**wm/step** — req: `handle: Handle`, `action: DataRef` (inline `json-array/1` allowed for small actions), `seed: Seed (opt)`, `want: string[] (opt, [])`. res: `handle: Handle`, `ttl_ms: int`, `seed: Seed (if assigned or normalized)`, plus requested: `stage_cost: Cost|null`, `uncertainty: object|null`, `latent: DataRef|null`.

**wm/rollout** *(model cap `rollout` or `batchedRollout`)* — req: `handle: Handle`, `actions: DataRef` (`[H][A]` with `rollout`; `[N][H][A]` also allowed with `batchedRollout`), `noise: Noise (opt)`, `want: string[] (opt,["cumulative_cost"])`, `return_latents:"none"|"terminal"|"all" (opt,"terminal")`, `stream: bool (opt,false)`, `differentiable: bool (opt,false)`, `deadline_ms: int (opt)`. res: `terminal_handles: Handle[]|null`, `trajectory_handles: Handle[][]|Handle[]|null`, `cumulative_cost: DataRef|null`, `cost_per_step: DataRef|null`, `uncertainty: object|null`, `complete: bool` (false iff truncated by `deadline_ms`), `completed: int[] (req iff complete=false)`, `seed: Seed|Seed[] (if assigned or normalized)`. Stream notification `wm/rollout.partial`: `{ request_id, completed:int[], cost:number[], done:bool }`.

**wm/fork** *(model cap `fork`)* — req: `handle: Handle`, `n: int (opt,1)`. res: `handles: Handle[]`.

**wm/evaluate** *(model cap `evaluate`)* — req: `handle: Handle`, `goal: Goal`, `metric_id: string (opt, "model/default")`, `want: string[] (opt,["cost"])`; `cost` is always returned and `uncertainty` may be requested. res: `cost: Cost`, `metric_id: string`, `uncertainty: object|null (opt)`. Unsupported goal/metric → `GOAL_UNSUPPORTED`.

**wm/decode** *(model cap `decode`)* — req: `handle: Handle`, `modalities: string[] (opt, all)`. res: FeatureMap (per modality, a DataRef).

**wm/release** — req: `handles: Handle[]`. res: `released: Handle[]`, `unknown: Handle[]`.

**wm/export** *(model cap `latentExport`)* — req: `handle: Handle`, `codec: string (opt)`. If omitted, the default is the first durable codec in `latent.codecs` compatible with the negotiated data channels. res: a DataRef (`readonly:true`; durable codecs carry the §8.8 metadata).

**wm/import** *(model cap `latentImport`)* — req: `data: DataRef`, `model_id: string (opt per §8.8)`, `model_version: string (opt if in data.metadata)`, `latent_schema: string (opt if in data.metadata)`. res: `handle: Handle`. Errors `MODEL_NOT_FOUND` / `LATENT_CODEC_MISMATCH` / `INVALID_TENSOR`.

**wm/grad** *(model cap `grad`)* — req: `handle: Handle`, `actions: DataRef`, `objective:{type:"cumulative_cost"|"terminal_cost"|"latent"[, goal:Goal]} (opt,{type:"cumulative_cost"})`, `cotangent: DataRef|null (req when objective type is latent)`, `noise: Noise (opt)`. res: `grad_actions: DataRef` (shape of `actions`). Unsupported mode → `GRADIENT_UNAVAILABLE`.

**wm/cancel** *(session cap `cancel`)* — req: `request_id: int|string`. res: `cancelled: bool`. Releases Latents the aborted call began to produce (§8.7).

**wm/action_project** *(model cap `latentAction`)* — req: `action: DataRef`. res: latent-action `DataRef` (§10).

## Appendix B — Example Session (wire trace, MCP-compatible)

A reward-free MPC cycle. Tensor payloads are shown as DataRef placeholders.

```jsonc
→ {"jsonrpc":"2.0","id":1,"method":"initialize","params":{
     "protocolVersion":"2025-11-25","clientInfo":{"name":"worldforge","version":"0.4.0"},
     "capabilities":{"experimental":{"wmcp":{"wmcpVersion":"wmcp/0.2-draft",
        "client":{"streaming":true,"cancel":true},"dataChannels":["arrow","inline"]}}}}}
← {"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2025-11-25","serverInfo":{"name":"vjepa2-wmcp","version":"0.9.0"},
     "capabilities":{"experimental":{"wmcp":{"wmcpVersion":"wmcp/0.2-draft","binding":"wire","wire_profile":"mcp",
        "models":["vjepa2-wm-base"],"sessionCapabilities":{"streaming":true,"cancel":true,"dataChannels":["arrow","inline"]},
        "limits":{"max_inline_bytes":1048576}}}}}}
→ {"jsonrpc":"2.0","method":"notifications/initialized"}

→ {"jsonrpc":"2.0","id":2,"method":"wm/describe","params":{"model_id":"vjepa2-wm-base"}}
← {"jsonrpc":"2.0","id":2,"result":{ /* Descriptor: capabilities{evaluate,rollout,batchedRollout,…},
       scoring{terminal_cost:true,evaluate_goal_types:["latent"],metric_ids:["model/default"]},
       latent{kind:"token_sequence",metric via metric_ids}, action_space{kind:"box",…}, limits{…} */ }}

→ {"jsonrpc":"2.0","id":3,"method":"wm/encode","params":{
     "context":{"observation.images.front":{"channel":"arrow","codec":"arrow-ipc/1","ref":"arrow://goal","dtype":"u8","shape":[3,224,224]}}}}
← {"jsonrpc":"2.0","id":3,"result":{"handle":"z_goal","ttl_ms":60000}}

→ {"jsonrpc":"2.0","id":4,"method":"wm/encode","params":{
     "context":{"observation.images.front":{"channel":"arrow","codec":"arrow-ipc/1","ref":"arrow://obs_t","dtype":"u8","shape":[3,224,224]}}}}
← {"jsonrpc":"2.0","id":4,"result":{"handle":"h0","ttl_ms":60000}}

→ {"jsonrpc":"2.0","id":5,"method":"wm/rollout","params":{"handle":"h0",
     "actions":{"channel":"arrow","codec":"arrow-ipc/1","ref":"arrow://A","dtype":"f32","shape":[4,16,7]},
     "noise":{"mode":"common","seed":"8830124"},
     "objective":{"goal":{"type":"latent","handle":"z_goal"},"metric_id":"model/default"},
     "want":[],"return_latents":"terminal","stream":true,"deadline_ms":40}}
← {"jsonrpc":"2.0","method":"wm/rollout.partial","params":{"request_id":5,"completed":[0,1],"cost":[],"done":false}}
← {"jsonrpc":"2.0","id":5,"result":{"terminal_handles":["leaf_0","leaf_1","leaf_2","leaf_3"],
     "objective_cost":{"channel":"inline","codec":"json-array/1","value":[0.12,0.21,0.17,0.34],"dtype":"f32","shape":[4]},"complete":true}}
   // costs returned in the rollout — pick argmin (leaf_0), execute its first action. (Batched wm/evaluate
   // over handles[] is the path for scoring forked/imported latents this rollout did not produce.)

→ {"jsonrpc":"2.0","id":6,"method":"wm/release","params":{"handles":["leaf_0","leaf_1","leaf_2","leaf_3","h0"]}}
← {"jsonrpc":"2.0","id":6,"result":{"released":["leaf_0","leaf_1","leaf_2","leaf_3","h0"],"unknown":[]}}
   // re-encode the next observation and repeat; z_goal is kept across the loop.
```

## Appendix C — Handle and Session Lifecycle

**Session.** `Uninitialized → Initialized` on a successful `initialize` (and, on the MCP-compatible wire profile, after the Server receives `notifications/initialized`); `wm/*` calls before that MUST fail. `Initialized → Closed` on transport close (wire) or object disposal (in-process); Closed releases all session Latents.

**Handle.** Created `Live` by `wm/encode`, `wm/step`, `wm/rollout` (`return_latents ≠ "none"`), `wm/fork`, or `wm/import`. While `Live` it is immutable (§8.3) and may be referenced by any read/advance verb; each successful reference slides its TTL (§8.8). It leaves `Live` by: explicit `wm/release` → `Released`; TTL elapse without reference → `Expired`; `wm/cancel` of the producing rollout, for Latents that call began to produce → `Released`; session close → `Released`.

Any verb on a `Released` Handle returns `INVALID_HANDLE`; on an `Expired` Handle, `EXPIRED_HANDLE`. A Handle presented to a different model or session returns `INVALID_HANDLE` (§8.8). There is no `Live → Live` mutation: advancing a `Live` Handle always yields a *new* Handle and leaves the original `Live` — the no-mutation invariant, checked as conformance assertion C4.

## Copyright

This document is placed in the public domain via CC0-1.0.
