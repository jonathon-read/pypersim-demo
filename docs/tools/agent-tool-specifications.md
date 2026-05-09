# Agent Tool Specification

**Purpose:** Define a consistent human-readable format for describing agent-executable tools covering: inputs, outputs, behaviour, and usage rules.
This standard is for **design, documentation, and review**.
Machine schemas (e.g. JSON Schema) are derived from it, not the other way around.

## 1) Scope
Applies to all tools an agent may invoke (read, write, decision-support).
Out of scope: implementation details, transport (HTTP, gRPC), and vendor-specific function-calling formats.

## 2) Format
- **File type:* YAML
- **One tool per file**
- **Location**: demo/docs/tools
- **Naming**: `snake_case`
  
## 3) Required structure
```yaml
name: <snake_case identified>
version: 1

purpose: >
    1-2 sentences describing the user-visible outcome.
    Do not mention APIs, databases, or implementation.

inputs:
    - name: <string>
      type: <type>
      required: <bool>
      description: <what it represents>

outputs:
    - name: <string>
      type: <type>
      nullable:  <bool>
      description: <what it represents>

idempotency: <bool>

logic:
    - <ordered step>
    - <descision or rule>
    - <branching behaviour>

failure_modes:
    - code: <snake_case error code>
      description: <trigger condition>
      handling: <what caller should do>

usage_guidelines:
    when_to_use:
        - <user-driven trigger>
        - <internal reasoning trigger>
    when_not_to_use:
        - <explicit exclusion>
    disambiguation:
        - <what to do in corner cases>

examples:
    - input: {...}
      output: {...}
```

## 4) Optional fields
```yaml
assumptions:
    - <data freshness, availability, etc.>

constraints:
    latency_ms: <integer>
    consistency: eventual | strong
    visiblity: <what must not be exposed> 

side_effects:
    - <side effect>

composition:
    typically_before:
        - <other tool>
    typically_after:
        - <other tool>

observability:
    logs:
        - <event_name>
    metrics:
        - <metric_name>
```

## 5) Field semantics
- **purpose**: What the user gets, not how it is implemented
- **inputs/outputs**: Stable contract. Names must be clearly distinct and consistent across tools (e.g. product_id everywhere)
- **logic**: Ordered, externally observable behaviour. Must include at least one decision/rule. Avoid code-level detail.
- **failure_modes**: Exhaustive, named conditions visible to the caller. No generic "error/failed".
- **usage_guidelines**: When the agent should/should not call the tool, including how to resolve missing or ambiguous inputs
- **side_effects**: Any state change (e.g. reservation/mutation).
- **constraints**: Non-functional guarantees/limits relevant to the caller

## 6) Minimimal example

```yaml
name: check_product_availability
version: 1

purpose: >
  Determine whether a product can be purchased in a given store
  and provide substitutes if not available.

inputs:
  - name: product_id
    type: string
    required: true
    description: Unique product identifier
  - name: store_id
    type: string
    required: true
    description: Store identifier

outputs:
  - name: available
    type: boolean
    description: Whether the product is purchasable
    nullable: false
  - name: stock_level
    type: integer
    description: Approximate units available
    nullable: true
  - name: substitutes
    type: list[string]
    description: Alternative product_ids
    nullable: true

idempotency: false

logic:
  - Validate product_id and store_id
  - Retrieve inventory for the store
  - If stock below threshold, mark as unavailable for online purchase
  - If unavailable, retrieve substitute products

failure_modes:
  - code: product_not_found
    description: product_id does not exist
    handling: ask user to clarify product or search
  - code: store_not_found
    description: store_id does not exist
    handling: ask user to select a valid store
  - code: inventory_unavailable
    description: inventory service not reachable
    handling: retry or inform temporary issue

usage_guidelines:
  when_to_use:
    - User asks if an item is in stock
    - Agent must confirm availability before checkout
  when_not_to_use:
    - Availability already confirmed in current session
    - Query is about pricing only
  disambiguation:
    - If product_id missing, call product_search first
    - If store_id missing, ask the user

examples:
  - input:
      product_id: "12345"
      store_id: "store_001"
    output:
      available: false
      stock_level: 0
      substitutes: ["67890"]
```

## 7) Non-goals
- Not a replacement for runtime schemas or API specs
- Not a place for implementaiton details or code
- Not a workflow engine or planning language
  
## 8) Adoption
- All new tools **must** include an ATS.
- Changes to tools require updating the spec in the same PR.
