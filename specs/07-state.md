# 07 — State

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

Publishers MUST treat request-mode state as publisher-wide. Sensitive data that should be confined to a specific endpoint or backend SHOULD NOT be stored as request state in v1.

Endpoint-scoped request state is reserved for a future protocol version.

Examples include:

- session token for submit endpoints;
- checkout state;
- authenticated form token;
- user-specific submit authorization.

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

A `state_policy` array MUST NOT contain two entries with the same combination of `namespace` and `key`. Duplicate entries cause the manifest to be rejected.

The `state_policy` array MUST NOT contain more than 32 entries.

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

`max_size` is the maximum size, in bytes, of the state value for this item.

It MUST be an integer between 1 and 4096 inclusive.

The protocol's hard ceiling for a state value is 4096 bytes regardless of declared policy. A publisher who declares a smaller `max_size` further restricts itself within the protocol limit.

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

Rejecting a state update does not reject the transaction document. The transaction may still be valid and renderable even if the client refuses the requested state change.

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

State values are opaque byte strings; the client does not parse or interpret their contents (see "value" above). State values MAY contain control characters in the range U+0000 through U+001F or U+007F, line feeds, escape sequences, or any other byte sequence permitted by the wire schema.

When presenting a value to the user during consent or in the chrome's state inspection surfaces, the client MUST NOT render the value as trusted text, markup, terminal control sequences, script, or executable content. The client MUST NOT pass the value to any rendering path that interprets in-band markup or interprets ANSI/VT or other terminal control sequences.

The client MUST display state values in a bounded, escaped, or otherwise neutralized form. Acceptable representations include:

* truncated plain text with non-printable bytes replaced by an escape glyph or a `\xHH`-style escape;
* fully escaped text with control characters and non-printables shown as visible escape sequences;
* hexadecimal encoding of the byte sequence;
* base64 or base64url encoding of the byte sequence;
* any other representation that preserves the property that no byte of the value is rendered as untrusted UI control.

The choice among these representations is implementation-defined. The presentation MUST be visually distinguishable from publisher-supplied document content and MUST NOT be confused with chrome warnings, trust-state indicators, or canary status.

This rule does not change the wire format. The value remains an opaque UTF-8 byte string of up to the smaller of the declared `max_size` and 4096 bytes. Control characters in the value remain permitted on the wire.

The visual treatment MUST clearly distinguish `client_only` and `request` mode. A user MUST be able to identify, before granting consent, whether the item will be transmitted in future submits.

For request-state items, the client MUST explain that the item will be included in future submit requests to the same publisher until it expires, is deleted, or consent is revoked.

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
