# ADR 004: Tool Interface Vectorisation

**Status:** Open — pending empirical validation

## Context

Agent tool interfaces can be designed to accept either a single input or a list of inputs (vectorised). The primary motivation for vectorisation is latency: if the model batches multiple queries into one call, fewer round trips through the agent loop are needed.

The counter-argument is that modern agent frameworks support parallel tool calls — the model emits multiple tool calls in a single response turn and the framework executes them concurrently. If that holds, vectorisation adds interface complexity (partial failure handling, batched output parsing) without a latency benefit.

There is a secondary case where vectorisation is genuinely useful regardless of framework behaviour: when the underlying operation is more efficient in batch mode (e.g. a single embedding API call for N strings). That case is out of scope here; this ADR concerns only the latency-reduction motivation.

We have not yet verified whether Google ADK executes parallel tool calls concurrently or serially.

## Decision

Proceed with **single-item tool interfaces** for now.

If empirical testing shows that Google ADK serialises parallel tool calls, we will revisit and introduce vectorised interfaces for the tools most likely to be called in parallel (e.g. product search, memory retrieval).

## Open question

Does Google ADK execute multiple tool calls emitted in a single model response concurrently or serially?

**To test:** construct a scenario where the model naturally emits two independent tool calls in one turn (e.g. two product searches). Instrument each tool with a timestamp on entry and exit. If the execution windows overlap, ADK is concurrent; if they are sequential, ADK is serial.

If ADK is serial, the latency cost of N tool calls is N × (tool latency + model latency). Vectorisation would then be worth the interface complexity for high-frequency tools.

## Considered alternatives

### Vectorised interfaces from the start
Rejected as premature. Vectorised interfaces complicate error handling (partial batch failure), output parsing, and tool specs without a proven benefit in this framework. If ADK is already concurrent, the complexity is pure overhead.

### Vectorised interfaces only for known-concurrent tools
Rejected as too speculative — we do not yet have a basis for predicting which tools the model will call in parallel.
