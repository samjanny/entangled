# 07 - State

State is the mechanism by which a publisher asks the client to persist per-user information across visits, without relying on undeclared ambient identifiers such as cookies or browser storage.

Entangled v1 defines two state modes:

- **client-only state**, which remains local to the client and is never attached automatically to network requests;
- **request state**, which remains stored by the client but may be attached automatically to submit requests after explicit user consent.

State is declared by the publisher in the manifest, updated only through signed transaction documents, displayed and controlled by the client, and revocable by the user.

## Design principles

State in Entangled is bound by four principles, each enforced by the protocol or required of conforming clients.

**State is client-stored.** State items live on the user's device, in storage owned by the client. The publisher does not receive state merely because the user reads a document. The publisher can observe state only when the client transmits request state as part of a submit, after user consent.

**State is publisher-scoped.** State items are bound to a `K_publisher.pub`, not to a carrier address. A publisher who rotates `K_origin` or migrates carriers retains access to the same state items. A different publisher, identified by a different `K_publisher.pub`, cannot read or write state items belonging to another publisher.

**State is consented.** The client requires explicit user consent before committing any state item. Manifest declaration of state policy is not consent. Consent is granted by the user when the publisher first attempts to write a specific item.

**State is bounded.** The publisher declares, in the manifest, every state item the site is authorized to use, with maximum size, maximum lifetime, mode, and purpose for each. State items have hard ceilings even if the publisher does not declare tighter limits.

## State modes

Entangled v1 defines two state modes. The mode of a state item is declared by the publisher in the manifest's `state_policy`.

### Client-only state

Client-only state is stored by the client and is never attached automatically to network requests.

It may inform local rendering decisions made by the client, such as choosing one block over another based on a stored preference. It is not transmitted to the publisher's server.

Examples include:

- language preference;
- display preference;
- reduced-motion preference;
- local reading position;
- client-side filtering preference.

### Request state

Request state is stored by the client and may be attached automatically to submit requests after explicit user consent.

Request state is never attached to manifest fetches or content document fetches in Entangled v1. It is attached only to submit request bodies, as defined in §09.

Once the user consents to a request-state item, the client includes that item in future submit requests to the same `K_publisher.pub` until one of the following occurs:

- the state item expires;
- the user deletes the item;
- the user revokes consent;
- the publisher deletes the item through a signed transaction update;
- the client is operating in a stateless or session-only mode whose lifetime has ended.

Request state is publisher-wide, not endpoint-private.

The client attaches every non-expired consented request-state item for the current publisher to every submit request to that publisher, regardless of which submit endpoint the user is interacting with. There is no endpoint-level scoping in v1.

**Security implication.** Because all non-expired request-state items are attached to every submit, any transaction endpoint receiving a submit also receives every request-state secret - including session tokens, authorization tokens, and any other credentials stored as request state. A publisher operating multiple transaction endpoints with different trust levels MUST assume that every endpoint sees every request-state value. This means that a less-trusted or auxiliary endpoint has access to the same credentials as the publisher's most sensitive endpoint. Publishers MUST NOT store credentials whose exposure must be limited to a single endpoint as request state in v1. Where endpoint-level credential isolation is required, the publisher SHOULD use out-of-band mechanisms or defer the functionality until endpoint-scoped request state is available.

Publishers MUST treat request-mode state as publisher-wide. Sensitive data that should be confined to a specific endpoint or backend MUST NOT be stored as request state in v1.

Endpoint-scoped request state is reserved for a future protocol version.

Examples of appropriate request-state uses - where publisher-wide visibility is acceptable:

- session token for submit endpoints where all endpoints share a trust boundary;
- checkout state;
- user-specific submit authorization where all transaction endpoints are equally trusted.

The two modes share storage and consent mechanisms. They differ only in whether the client may transmit the value as part of submit requests.

The intent of the two-mode design is to make every form of state explicit, declared, visible, and revocable. Entangled does not silently track readers through ambient state. Reading content does not transmit state to the publisher. Submit actions may carry consented request state.

## State policy in the manifest

The manifest's `state_policy` field, defined in §06, is a JSON array declaring every individual state item the site is authorized to use.

A site that does not use state declares:

```json
"state_policy": []
````

The field is required even when empty.

Each entry in `state_policy` describes exactly one `(namespace, key)` state item:

```json
{
  "namespace": "session",
  "key": "auth",
  "mode": "request",
  "max_size": 512,
  "max_lifetime": 86400,
  "purpose": "Authenticate submit requests after login."
}
```

All six fields are required. No additional fields are permitted.

A `state_policy` array MUST NOT contain two entries with the same combination of `namespace` and `key`. Duplicate entries cause the manifest to be rejected with `E_SCHEMA_DUPLICATE_ENTRY` (§11).

The `state_policy` array MUST NOT contain more than 32 entries.

### Submit budget satisfiability

A manifest's `state_policy` MUST be satisfiable under the §09 submit body budget partition: the aggregate worst-case encoded wire contribution of all request-mode entries, computed as if every request-mode entry held a `value` of exactly its declared `max_size`, MUST NOT exceed `state_budget` defined in §09 ("Submit body budget partition").

Aggregate encoded wire contribution is the sum, across all `state_policy` entries whose `mode` is `request`, of the bytes that entry would contribute to the `request_state` array of a submit body when its retained `value` is at the declared `max_size`. The contribution includes the entry's JSON object structure (braces, member names, colons, and quoting around the `namespace`, `key`, and `value` strings), the `namespace` and `key` string values (which contain only slug characters and therefore require no JSON escaping), the `value` counted at its declared `max_size` as a raw UTF-8 byte length, and one array-delimiter comma per inter-entry boundary. The `value` is counted at its raw `max_size` and is NOT escape-expanded for this aggregate: the aggregate is an envelope-level bound computed from the declared policy alone, and `max_size` is a raw UTF-8 byte length (§07 `max_size`). Client-only entries (`mode = "client_only"`) do not contribute to this aggregate, since client-only state is never transmitted in submit bodies.

A manifest whose `state_policy` aggregate exceeds `state_budget` is rejected at Stage 5 manifest schema validation as `E_SUBMIT_BUDGET` (§11), with `details.component = "state"`. The check is deterministic and computable from the manifest payload alone; it does not depend on the client's current retained state.

Because the `value` is counted at its raw `max_size`, this aggregate is a *necessary* condition on the declared `state_policy`, not a *sufficient* one. It guarantees that a policy whose retained values stay within their raw UTF-8 `max_size` and contain no JSON-escaped characters fits the budget; it does not guarantee that every concrete submit fits, because a retained `value` containing `"`, `\`, or control characters in U+0000 through U+001F expands when JSON-escaped on the wire and can exceed its raw `max_size` contribution. The submit-time wire budget is enforced by the runtime `E_STATE_TRANSMIT_BUDGET` rule below, which measures the actual JSON-escaped wire bytes of the retained values. The two checks form a deliberate two-level partition: the Stage 5 aggregate rejects a policy that could never be satisfiable even with well-formed values, and the runtime check rejects an individual `set` whose actual retained state, escaping included, would overflow the wire budget.

This invariant is distinct from the runtime client-side `E_STATE_TRANSMIT_BUDGET` rule below ("Request-state transmit budget"). The satisfiability invariant ensures that no conforming publisher can declare a `state_policy` under which even the worst-case retained request-state load would overflow the submit budget; it rejects the manifest at validation. The transmit budget rule ensures that, given a satisfiable policy, the client never accumulates retained state that overflows; it rejects an individual `set` operation at runtime.

Under a single conforming and satisfiable `state_policy` evaluated in isolation, the runtime rule is unreachable: retained request-state is bounded by the sum of `max_size` across `mode = request` entries, which the satisfiability invariant has already bounded to `state_budget`. The runtime rule remains required as a backstop against three scenarios in which retained state can exceed what the *current* policy alone would permit:

1. **Cross-policy / cross-version accumulation.** State entries are retained against the publisher identity, not the manifest version that authorized them (§07 retention rules). When a publisher revises `state_policy` between rotations - adding entries, widening `max_size`, or replacing one entry with another - retained entries from the prior policy may coexist with retained entries from the new policy during the transition window. The aggregate retained at a moment in time can exceed what the new policy alone bounds, even if both the prior policy and the new policy were individually satisfiable. The runtime check rejects a `set` that would push the in-transition aggregate over the cap.
2. **Partial implementations.** A client that implements the runtime rule but not the satisfiability invariant (an older or incomplete implementation) processes an over-budget manifest at the runtime layer only; the runtime rule prevents the deadlock in that implementation.
3. **Implementation-defined storage extensions.** A client that retains state with rules looser than the v1.0 minimum (for example, a client that preserves session-token state across publisher-policy revisions for user-experience reasons) may carry retained state that the current `state_policy` would not itself permit; the runtime rule bounds the resulting aggregate independently of how the retained set was assembled.

Both rules are therefore required: the satisfiability invariant prevents publishers from declaring an unsatisfiable contract; the runtime rule is a defense-in-depth backstop for cross-policy accumulation, partial implementations, and looser-than-minimum retention behavior.

This invariant bounds the deadlock vector in which a compromised `K_runtime` repeatedly issues `set` operations that fill state to the policy's declared maxima: under a satisfiable policy, even a maximally-filled retained state remains within `state_budget`, and the resulting minimal submit body remains within the 64 KiB cap.

### `namespace`

`namespace` is an ASCII slug identifying a logical group of state items.

It is an organizational tool, not a privacy boundary. All namespaces declared by the same publisher are within the same publisher state scope.

The value MUST:

* consist of one or more ASCII characters in the range `[a-z0-9_-]`;
* begin with `[a-z0-9]`;
* not exceed 64 characters in length.

### `key`

`key` is an ASCII slug identifying a single state item within the namespace.

The value MUST satisfy the same syntax rules as `namespace`.

The full storage key is:

```text
K_publisher.pub + namespace + key
```

### `mode`

`mode` declares the state mode. Permitted values are exactly:

* `"client_only"`
* `"request"`

A state policy entry whose `mode` is not one of these exact values causes the manifest to be rejected.

The mode applies to all set operations the publisher may issue against this `(namespace, key)` combination. Publishers cannot change a state item's mode through transaction documents; the mode is fixed by the manifest policy currently authorizing the item.

### `max_size`

`max_size` is the maximum size of the state value for this item, measured as the raw UTF-8 byte length of the value: the number of bytes the value occupies when encoded as UTF-8, before any JSON string escaping is applied. It is not the JSON-escaped wire length. A value's `max_size` admissibility is therefore determined by the value's own UTF-8 bytes and does not depend on serializing the value into a submit body first. (For a language whose native string length is not a UTF-8 byte count, this is `len(value.encode("utf-8"))` or the equivalent: a UTF-16 code-unit count or a Unicode code-point count is not conformant.)

It MUST be an integer between 1 and 4096 inclusive.

The protocol's hard ceiling for a state value is 4096 raw UTF-8 bytes regardless of declared policy. A publisher who declares a smaller `max_size` further restricts itself within the protocol limit.

The submit-body budget partition in §09 measures wire bytes, where a value containing characters that JSON must escape (`"`, `\`, or control characters in U+0000 through U+001F) occupies more wire bytes than its raw UTF-8 length. The per-value `max_size` cap is on the raw value; the wire-byte accounting is the budget partition's concern (§09 "Submit body budget partition"), and the runtime `E_STATE_TRANSMIT_BUDGET` check below enforces the wire-byte ceiling against the actual retained values.

### `max_lifetime`

`max_lifetime` is the maximum permitted TTL, in seconds, for set operations on this state item.

It MUST be an integer between:

* `300` seconds, 5 minutes;
* `7776000` seconds, 90 days.

Set operations specifying a TTL longer than `max_lifetime` are rejected by the client.

### `purpose`

`purpose` is a human-readable explanation of why the publisher requires this state item.

It is a UTF-8 string. It MUST NOT exceed 200 bytes when encoded as UTF-8. It MUST NOT contain control characters in the range U+0000 through U+001F or the value U+007F.

The purpose is displayed by the client to the user during the consent prompt, alongside the namespace, key, mode, maximum size, maximum lifetime, and whether the item will be transmitted in submit requests.

The protocol does not validate the truthfulness of the purpose. A publisher who states a misleading purpose makes a representation to the user; the protocol's role is to ensure the representation is declared and shown, not to verify its accuracy.

The purpose MUST be plain text. It is not HTML, Markdown, or any other markup language.

## State updates in transaction documents

A transaction document carries zero or more state update operations in its `state_updates` field, defined in §02.

`state_updates` is a JSON array. The array MUST be present in every transaction document and MUST contain between 0 and 32 entries.

If the transaction document does not request state changes, `state_updates` is an empty array:

```json
"state_updates": []
```

Each entry in the array is a state update operation. Entangled v1 defines two operation forms:

* `set`;
* `delete`.

A state update operation that does not match one of these forms is rejected.

## Set operation

A set operation requests that the client store or replace a state item.

```json
{
  "op": "set",
  "namespace": "session",
  "key": "auth",
  "value": "...",
  "ttl": 86400
}
```

A set operation has exactly five fields:

* `op`;
* `namespace`;
* `key`;
* `value`;
* `ttl`.

No other fields are permitted.

### `op`

`op` is the ASCII string:

```json
"set"
```

### `namespace` and `key`

`namespace` and `key` MUST satisfy the same syntax rules as in `state_policy`.

The combination `(namespace, key)` MUST be declared in the current manifest's `state_policy`.

A set operation referencing an undeclared `(namespace, key)` combination causes the transaction document to be rejected.

### `value`

`value` is a UTF-8 string carrying the state item's content.

It MUST NOT exceed the smaller of:

* the `max_size` declared for `(namespace, key)` in the current manifest's `state_policy`;
* 4096 bytes, the protocol's absolute ceiling.

The value is opaque to the client. The client stores it as a UTF-8 byte sequence. It does not parse or interpret the value's contents.

If the publisher needs to encode structured data, it serializes that structure into the string at the application layer. The client MUST NOT interpret the value as JSON, markup, script, or executable content.

`value` MAY contain control characters. The client treats the entire value as opaque data and MUST NOT render it as trusted UI without escaping or other safe display handling defined by the client.

### `ttl`

`ttl` is the number of seconds for which the state item is valid after the client commits the set operation.

It MUST be an integer satisfying all of the following:

* at least `300`;
* at most the `max_lifetime` declared for `(namespace, key)`;
* at most `7776000`.

The client computes:

```text
expires_at = now + ttl
```

at commit time and stores it alongside the state value.

A set operation does not change the mode of the state item. The mode is fixed by the manifest's `state_policy`.

## Delete operation

A delete operation requests that the client remove a state item.

```json
{
  "op": "delete",
  "namespace": "session",
  "key": "auth"
}
```

A delete operation has exactly three fields:

* `op`;
* `namespace`;
* `key`.

No other fields are permitted.

### `op`

`op` is the ASCII string:

```json
"delete"
```

### `namespace` and `key`

`namespace` and `key` MUST satisfy the same syntax rules as in set operations.

The combination `(namespace, key)` MUST be declared in the current manifest's `state_policy`.

A delete operation referencing a `(namespace, key)` combination for which no state item exists is a no-op.

### Effect

A delete operation removes the state item identified by:

```text
K_publisher.pub + namespace + key
```

from the client's state store.

Delete operations do not require user consent, because they remove data rather than storing new data or increasing transmission surface.

## Consent model

The client MUST obtain explicit user consent before committing any state set operation, regardless of mode.

A set operation in a transaction document is a request, not a command. The client MAY perform other actions in response to the transaction, including rendering the response blocks, before, during, or after consent is decided.

Rejecting a state update on consent, storage, or transmit-budget grounds does not reject the transaction document. The transaction may still be valid and renderable even if the client refuses the requested state change.

This rule is distinct from rejection of the transaction document itself on schema or policy grounds. The failure taxonomy for state updates is:

* **Schema failure.** A `state_updates` entry that violates the operation schema defined in this section - wrong field set, malformed value, unknown `op` - rejects the entire transaction document during Stage 5 of the validation pipeline (§10).
* **Policy failure.** A set operation referencing a `(namespace, key)` combination not declared in the current manifest's `state_policy` (see "namespace and key" above) rejects the entire transaction document. The same applies to a set operation whose `value` exceeds the policy's `max_size` or whose `ttl` exceeds the policy's `max_lifetime`.
* **Consent failure.** The user declines the consent prompt for a set operation, or remembered-consent state does not authorize the operation. The state operation is rejected; the transaction document remains valid and renderable.
* **Storage failure.** The client cannot commit the state operation because the per-publisher storage cap (see "Storage limits" above) would be exceeded, or a local write fails. The state operation is rejected; the transaction document remains valid and renderable.
* **Transmit-budget failure.** A request-mode set operation would make future submit transmission impossible under the 64 KiB submit-body cap because the retained request state would no longer fit even in an otherwise-empty submit. The state operation is rejected; the transaction document remains valid and renderable.

Schema and policy failures are hard-fail on the document; consent, storage, and transmit-budget failures are soft-fail on the individual state operation. The protocol enforces this distinction so that a publisher cannot prevent the rendering of a transaction response by requesting state the client refuses to store, and conversely so that a malformed or out-of-policy state update is not silently dropped.

## Consent presentation

When the client receives a transaction document containing one or more set operations, the client presents the user with, for each set operation:

* the publisher identity, shown as the PIP or a condensed form of it;
* the `namespace` and `key`;
* the `mode`, either client-only or request;
* a safe representation of the value the publisher proposes to store, as defined below;
* the proposed TTL;
* the `purpose` string from the manifest's `state_policy`;
* whether the value will be sent automatically with future submit requests;
* a control to accept or reject this specific set operation.

Consent presentation occurs in client-controlled UI, in the chrome region defined by Pillar C and §10. It MUST NOT be controllable, replaceable, hidden, or styled by publisher-controlled content.

### Safe display of opaque state values

State values are opaque UTF-8 strings; the client does not parse or interpret their contents (see "value" above). State values MAY contain control characters in the range U+0000 through U+001F or U+007F, line feeds, escape sequences, or any other Unicode scalar values permitted by the wire schema. The wire form is JSON UTF-8 text; non-UTF-8 byte sequences are not transmissible.

When presenting a value to the user during consent or in the chrome's state inspection surfaces, the client MUST NOT render the value as trusted text, markup, terminal control sequences, script, or executable content. The client MUST NOT pass the value to any rendering path that interprets in-band markup or interprets ANSI/VT or other terminal control sequences.

The client MUST display state values in a bounded, escaped, or otherwise neutralized form. Acceptable representations include:

* truncated plain text with non-printable bytes replaced by an escape glyph or a `\xHH`-style escape;
* fully escaped text with control characters and non-printables shown as visible escape sequences;
* hexadecimal encoding of the byte sequence;
* base64 or base64url encoding of the byte sequence;
* any other representation that preserves the property that no byte of the value is rendered as untrusted UI control.

The choice among these representations is implementation-defined. The presentation MUST be visually distinguishable from publisher-supplied document content and MUST NOT be confused with chrome warnings, trust-state indicators, or canary status.

This rule does not change the wire format. The value remains an opaque UTF-8 string whose UTF-8 encoding is at most the smaller of the declared `max_size` and 4096 bytes. Control characters in the value remain permitted on the wire.

The visual treatment MUST clearly distinguish `client_only` and `request` mode. A user MUST be able to identify, before granting consent, whether the item will be transmitted in future submits.

For request-state items, the client MUST explain that the item will be included in future submit requests to the same publisher - across every submit endpoint under that publisher's identity, not only the current form or endpoint - until it expires, is deleted, or consent is revoked. Request-state scope in Entangled v1 is publisher-wide; endpoint-scoped request state is not part of v1.

If the user rejects a set operation, the client MUST NOT commit it.

If the user accepts a set operation, the client commits it as defined in this section.

## Remembered consent

The client MAY offer the user the option to remember the consent decision for the same publisher, namespace, key, and mode combination.

If the user accepts this option:

* subsequent set operations matching the same publisher, namespace, key, and mode MAY be committed without further prompting;
* the new operation MUST remain within the bounds declared by the current manifest's `state_policy`;
* changes to the stored value are permitted under remembered consent;
* changes to namespace, key, or mode require a new consent decision;
* the client MUST provide a user-accessible mechanism to revoke remembered consent.

The client MUST NOT remember consent across publishers. Each `K_publisher.pub` is a distinct consent scope.

## Consent for delete operations

A delete operation does not store new data and does not increase the user's transmission surface. It removes data the client already holds.

The client MAY commit delete operations without prompting for consent.

## Mode change

If a publisher changes the mode of an existing `(namespace, key)` combination in a new manifest revision, for example from `client_only` to `request`, the client MUST NOT silently reinterpret existing stored state under the new mode.

Existing entries retain the mode they had at commit time until they expire, are deleted, or are overwritten by a new set operation accepted under the new policy.

New set operations under the changed mode require a fresh consent prompt that explicitly discloses the mode change.

## Storage and retrieval

The client maintains a state store keyed by:

```text
K_publisher.pub + namespace + key
```

Each entry stores:

* the value, as a UTF-8 string;
* the `expires_at` timestamp computed at commit time;
* the mode at the time of commit;
* the consent timestamp;
* any remembered-consent flags.

State entries are persisted across client sessions, subject to the user's overall control of the client's storage, unless the client is operating in stateless mode.

## Retrieval for rendering

State entries may be retrieved by the client's rendering pipeline to inform local rendering decisions.

They are not retrievable by the publisher's server through manifest fetches or content-document fetches.

A content document does not itself access state values during rendering. The client may use state values to adapt presentation, for example by choosing one language variant over another based on a stored language preference. This adaptation is client behavior, not publisher-supplied code execution.

## Retrieval for submits

In Entangled v1, request state is publisher-wide for submit requests.

When the user initiates a submit to a transaction endpoint, the client retrieves all non-expired state items for the same `K_publisher.pub` whose stored mode is `request` and includes them in the submit request body.

The wire format of submit requests, including the `request_state` field, is defined in §09.

Request state MUST NOT be attached to:

* manifest fetches;
* content document fetches;
* navigation requests;
* image fetches;
* any request other than submit requests.

Client-only state items are never included in submit request bodies, regardless of consent state.

## Request-state transmit budget

Request-mode state is retained so that the client can attach it automatically to future submits. A conforming client MUST ensure that retained request-mode state never makes even an otherwise-empty submit body untransmittable under the 64 KiB limit in §09.

For this purpose, define the **minimal submit body** for a publisher as the submit body object the client would transmit with:

* `fields` equal to the empty object `{}`;
* `request_state` equal to all non-expired retained request-mode state items for that `K_publisher.pub`, in the wire form defined by §09;
* `request_id` equal to any syntactically valid 22-character request identifier. The particular value is irrelevant because every valid `request_id` has the same wire length.

The client MUST compute the byte length of the exact UTF-8 JSON byte sequence it would transmit for this minimal submit body. That byte length MUST NOT exceed 64 KiB.

The client MUST NOT silently drop, truncate, or omit retained request-mode state items in order to satisfy this requirement. If committing a request-mode `set` operation would cause the minimal submit body to exceed 64 KiB, the client MUST reject that state operation, leave previously retained state unchanged, and report `E_STATE_TRANSMIT_BUDGET` (§11). The transaction document requesting the state change remains valid and renderable.

This rule applies only to request-mode state. Client-only state is not counted toward the transmit budget because it is never attached to network requests.

This rule bounds state-induced submit deadlock. It does not guarantee that every possible user input in `fields` fits within the submit-body cap; submit-time local validation of user-entered fields remains required by §03 and §09.

## Expiration

The client MUST treat state items as expired and remove them when the current time is at or after `expires_at`.

The client MAY remove expired items lazily, when next accessed, or eagerly, during periodic cleanup.

Expired state MUST NOT be used for rendering decisions and MUST NOT be included in submit requests.

## Storage limits

The client enforces a per-publisher storage cap independent of declared `state_policy`.

The cap MUST be at least sufficient to store the maximum allowed state per the current policy, calculated as the sum of `max_size` across all declared policy entries, but MAY be larger.

When the cap is reached, the client MUST refuse new set operations that would exceed the cap and SHOULD inform the user. The client MAY suggest that the user clear state for the publisher.

## Storage scope

State entries are bound to `K_publisher.pub`.

They are accessible to any verified manifest declaring a `state_policy` that authorizes the relevant `(namespace, key)`, regardless of the carrier origin from which that manifest was fetched.

A publisher who rotates `K_origin` or migrates carriers retains access to existing state entries through the publisher identity. The client uses the publisher history defined in §06 to resolve state access across origin migrations.

A different `K_publisher.pub` has no access to the state entries of another publisher.

## Chrome indication

The client MUST indicate, in chrome, when a site has active state.

The client MUST distinguish between:

* active client-only state;
* active request state.

The presence of request state MUST be visually distinguishable from the presence of client-only state.

The user MUST be able to inspect, at any time:

* the list of state items currently stored for the publisher;
* for each item: namespace, key, mode, `expires_at`, and purpose;
* whether a request-state item is sent with future submit requests;
* a control to delete each item individually;
* a control to delete all state for the publisher;
* a control to revoke remembered consent.

This inspection interface lives in chrome. It MUST NOT be replaceable, hidable, or modifiable from publisher-controlled content.

## Client behavior on policy changes

A publisher MAY change `state_policy` between manifest revisions. The protocol does not require state policies to be monotonic across cycles.

When the client observes a new manifest with changed `state_policy`:

* existing state entries for `(namespace, key)` combinations still declared in the new policy MUST remain accessible until their natural `expires_at`;
* existing state entries for `(namespace, key)` combinations no longer declared in the new policy MUST be retained for local user inspection and deletion until their natural `expires_at`, but MUST NOT be used for rendering decisions, MUST NOT be included in submit requests, and MUST NOT receive new set operations;
* existing state entries whose stored size exceeds the new `max_size` for their `(namespace, key)` MUST remain stored until their natural `expires_at`, but MUST NOT be overwritten by a new value exceeding the new limit;
* existing state entries whose remaining TTL exceeds the new `max_lifetime` for their `(namespace, key)` MUST retain their original `expires_at`; the client does not retroactively shorten existing consented state;
* existing state entries whose mode in the new policy differs from the mode at commit time MUST retain their original commit-time mode for the lifetime of the entry. New set operations after the policy change require fresh consent reflecting the new mode.

These rules ensure that a publisher cannot use policy changes to silently upgrade existing client-only state into request state, hide existing stored state from the user, or retroactively alter the terms under which the user consented.

Policy changes affect future set operations and future request inclusion. They do not silently rewrite previously consented entries.

The client MAY display a notice when policy changes affect future state behavior, particularly when a previously declared `(namespace, key)` is removed from the policy or when the mode of a `(namespace, key)` changes.

## State and runtime-key rotation

When the client observes a new manifest authorizing a different `K_runtime` than the one that authorized state entries currently in storage, the following applies:

* existing request-state entries whose authorizing `K_runtime` has been superseded MUST be marked as `runtime_superseded` in client storage;
* `runtime_superseded` request-state entries MUST NOT be included in submit requests;
* `runtime_superseded` request-state entries MUST be retained for user inspection and deletion until their natural `expires_at`;
* the client MUST display a chrome notice informing the user that request-state entries from a previous publication cycle have been suspended due to key rotation;
* if the new manifest's `state_policy` re-declares the same `(namespace, key)` combinations, the publisher MAY install fresh values through new transaction documents signed by the new `K_runtime`; these are independent entries and require fresh consent.

The rationale is that `K_runtime` compromise (§05) allows an attacker to plant request-state items - including session tokens and authorization credentials - with TTLs up to 90 days. Without this rule, such items survive rotation and are transmitted in submit requests to the publisher's backends, extending the effective compromise window far beyond the rotation boundary. Suspending transmit eligibility on rotation ensures that rotation actually bounds the exposure of request-state credentials.

Client-only state entries are not affected by this rule because they are never transmitted to the publisher.

## Stateless mode

A conforming client MAY support a stateless mode in which:

* the state store does not persist across sessions;
* set operations are committed only in memory for the lifetime of the session;
* delete operations are committed only against in-memory state;
* consent prompts behave normally during the session;
* request state in submit requests is sent only when the user has consented within the same session.

A client supporting stateless mode MUST make the mode user-selectable and MUST display its current state in chrome.

The client does not send an explicit protocol signal indicating stateless mode. A publisher may infer reduced persistence from user behavior or from the absence of expected request state, but stateless mode is not directly advertised by the protocol.

## What this section does not cover

This section defines the state policy schema, the two state modes, the state update operations, the consent model, and storage semantics.

It does not define:

* the manifest envelope or signing (see §06);
* the document envelope rules or transaction document schema beyond the state update specifics introduced here (see §02);
* block types that publishers may use to display state-related information in content (see §03);
* canonicalization rules (see §04);
* key roles, signing primitives, or verification chain (see §05);
* the canary structure (see §08);
* the wire format of submit requests, including how `request_state` is included in the request body (see §09);
* the full client verification pipeline, including consent UX layout, state confirmation flow, and chrome rendering rules (see §10);
* error codes for state policy violations and consent-related errors (see §11).
