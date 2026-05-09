# Agent Capability Specification

## Overview

This document defines the in-scope and out-of-scope capabilities for the demo customer support agent. The agent is a text-based conversational assistant for an e-commerce grocery and gourmet food store. It handles product discovery, purchase management, and post-purchase support for a single customer session.

This spec is the reference for tool and sub-agent design. Capabilities are described in terms of user-visible behaviour only — implementation details are deferred to individual tool and sub-agent specs.

## In-scope capabilities

### Product discovery

**Semantic product search**
Find products matching a natural-language description or stated need. The agent interprets the user's intent and returns ranked candidates. Results include enough detail (title, price, rating) for the user to decide which products warrant further exploration.

**What's popular**
Surface highly-rated products within a category. Useful when a user is browsing rather than searching — for example, when buying a gift or exploring a new category.

**Product recommendations**
Surface products that tend to be bought alongside a particular product. Useful for discovering complementary or contextually related items the user may not have thought to search for.

**Substitution suggester**
When a user is dissatisfied with a product or a suitable match cannot be found, propose alternatives from the catalogue. The agent should explain why the substitute is a reasonable match given the user's stated needs.


### Product intelligence

**Product detail**
Retrieve the full listing for a specific product: title, price, ratings, store, features, and structured attributes. The primary tool for answering questions about a specific item before purchase.

**Review summariser**
Summarise customer reviews for a product into a concise summary of strengths, weaknesses, and recurring themes. Saves the user from reading dozens of individual reviews and surfaces signals that raw ratings do not capture (e.g. taste vs. packaging complaints). 

**Dietary assessor**
Evaluate a product's suitability for a stated dietary requirement (e.g. gluten-free, vegan, nut-free, low-sodium) based on its listed features and attributes. The agent must always advise the user to verify against the physical product label for allergy-critical decisions — this capability is a convenience filter, not a safety guarantee.

**Price comparator**
Given a product, find similar items in the catalogue and compare them by price and rating. Helps users make value judgements and discover alternatives they may not have found through search.

### Personalisation

**Customer memory**
Store, retrieve, and remove facts about a customer's preferences, dietary needs, household, and past conversations. Memory persists across sessions and informs the agent's behaviour throughout the interaction without requiring the user to repeat themselves.

**Preference-aware recommendations**
Proactively suggest products based on the customer's stored preferences and the current context of the conversation. Distinct from search in that the agent takes initiative rather than responding to an explicit query.


### Order management

**Basket management**
Add, modify, and remove line items from the current order. Supports quantity changes and removal of all items at once.

**Checkout**
Complete the purchase for the current basket, confirming the order and clearing the active session basket.

**Order history**
Retrieve a customer's past orders, including items purchased, quantities, and order dates. Supports return/refund requests and reordering.

**Reorder**
Rebuild a previous order into the current basket with a single step, optionally allowing the user to review and adjust before checkout.

**Return and refund initiator**
Handle return and refund requests for past orders within a defined policy. The agent applies the policy consistently, informs the user of the outcome, and records the request.

Policy (for this iteration):
- Items must be returned within 30 days of the order date
- Items must be unopened and in original condition
- One return request per order line
- Refunds are issued to the original payment method; no cash alternatives

---

## Out-of-scope capabilities

The following were considered and explicitly excluded from this iteration.

| Capability | Reason excluded |
|---|---|
| Basket nutritional summary | Nutritional data is not reliably available in the product catalogue. Approximate or missing data would make this misleading. |
| Delivery estimate | No fulfilment backend exists in the demo environment. Estimates could not be grounded in real data. |
| Category browser | The agent is text-based. Hierarchical category navigation is better suited to a faceted UI; in conversation it produces poor UX, so this would be left for productionisation. |
| Query escalation to a human agent | There is no human support tier in the demo environment. The agent should handle all requests within its capabilities or decline gracefully. |
