# 06 — Manifest

The manifest is the signed document by which a publisher declares the current authorization state of an Entangled site.

It is signed by `K_publisher` and contains the site-level bindings required by the client to verify content and transaction documents: publisher identity, carrier origin, runtime key, canary state, navigation, state policy, and refresh policy.

The manifest is fetched from the canonical path `/manifest.json` on every Entangled site. A valid manifest is required before a client can verify or render any other document from that site.

## Manifest envelope

The manifest is a flat JSON object whose fields are the signed payload, plus a top-level `sig` field carrying the Ed25519 signature.

```json
{
  "spec_version": "1.0",
  "kind": "manifest",
  "publisher_pubkey": "<base64url, 32 bytes>",
  "origin": {
    "carrier": "tor-v3",
    "address": "<56-character-onion-address>.onion",
    "origin_pubkey": "<base64url, 32 bytes>"
  },
  "canary": { },
  "state_policy": [],
  "navigation": [],
  "min_refresh_interval": 86400,
  "updated": "2026-05-07T00:00:00Z",
  "sig": "..."
}
```

All fields listed above are required. No other fields are permitted.

The signed payload is the manifest object with the `sig` field removed. The signature input is:

```text
"ENTANGLED-v1 manifest" || 0x00 || JCS(manifest minus sig)
```

The `sig` field is encoded as 86 ASCII characters of base64url representing 64 bytes, with no padding.

Field-by-field semantics follow.

## `spec_version`

`spec_version` is the Entangled protocol version targeted by this manifest.

Entangled v1 manifests declare:

```json
"spec_version": "1.0"
```

A client implementing Entangled v1.0 MUST reject any manifest whose `spec_version` is not exactly `"1.0"`.

Specification document patch releases do not change this field. For example, a corrective specification release such as `v1.0.1` does not cause manifests to declare `"1.0.1"`.

## `kind`

`kind` is the document kind discriminator.

For manifests, `kind` is exactly:

```json
"kind": "manifest"
```

The discriminator allows a client parsing a JSON object to identify the expected schema before applying full validation.

A manifest whose `kind` is not exactly `"manifest"` is rejected.

## `publisher_pubkey`

`publisher_pubkey` is the public key of `K_publisher`, encoded as 43 ASCII characters of base64url representing 32 bytes, with no padding.

This key is the publisher identity key for the site. It is the key from which the Publisher Identity Phrase (PIP) is derived, as defined in §05.

`publisher_pubkey` is not by itself a trust anchor. The client MUST compare it against the publisher identity established by one of the trust-state mechanisms defined in §10:

* a user-confirmed PIP;
* a previous TOFU pin;
* or a first-contact candidate identity being presented to the user.

A manifest whose `publisher_pubkey` does not match the already established publisher identity for the current site entry or origin triggers the changed/mismatch trust state defined in §10.

## `origin`

`origin` declares the carrier endpoint for which this manifest is authoritative.

It is a JSON object with exactly three fields:

```json
{
  "carrier": "tor-v3",
  "address": "<56-character-onion-address>.onion",
  "origin_pubkey": "<base64url, 32 bytes>"
}
```

No additional fields are permitted.

### `origin.carrier`

`carrier` is an ASCII string identifying the carrier profile.

Entangled v1 fully specifies only:

```json
"carrier": "tor-v3"
```

A v1 conforming client MUST reject any manifest whose `origin.carrier` is not `"tor-v3"`, unless the client implements an explicitly named future carrier profile.

The values `"i2p"` and `"yggdrasil"` are reserved for draft carrier profiles. They are not part of Entangled v1 conformance until their address-to-key binding rules are specified byte-for-byte.

### `origin.address`

`address` is the canonical carrier address at which the site is reachable.

For `tor-v3`, this is the 56-character lowercase base32 onion address followed by `.onion`.

The value MUST NOT include:

* a URL scheme;
* a port;
* a path;
* a query string;
* a fragment.

Valid shape:

```text
abcdefghijklmnopqrstuvwxyz234567abcdefghijklmnopqrstuvwxyz234567.onion
```

The exact Tor v3 address validation and key binding rules are defined in §05.

### `origin.origin_pubkey`

`origin_pubkey` is the public key of `K_origin`.

For `tor-v3`, it is encoded as 43 ASCII characters of base64url representing 32 bytes, with no padding.

The client MUST verify that `origin.origin_pubkey` matches the public key encoded by the Tor v3 onion address in `origin.address`, using the Tor v3 binding rules defined in §05.

### Single-origin rule

In Entangled v1, a manifest declares exactly one origin.

A publisher who controls multiple carrier endpoints publishes a separate manifest per endpoint, each signed by the same `K_publisher`.

Multi-origin manifests are not part of Entangled v1 and may be considered in a future version.

### Fetch-origin binding

The client MUST verify that the carrier endpoint from which the manifest was fetched matches the `origin` declared in the manifest.

For Tor v3, this means:

* the fetched address equals `origin.address` in canonical form;
* the public key encoded by that onion address equals `origin.origin_pubkey`.

Failure of origin matching or carrier-specific binding rejects the manifest with the origin-mismatch error defined in §11.

## `canary`

`canary` is the canary structure for the site.

It includes, at minimum, the current `runtime_pubkey` authorized to sign content and transaction documents for the current publication cycle.

The full canary schema, freshness rules, expiration behavior, and lifecycle are defined in §08.

The manifest signature covers the canary because the canary is part of the manifest payload. The canary is not signed independently in Entangled v1.

## `state_policy`

`state_policy` is a JSON array declaring which state IDs the site is authorized to use, and the maximum lifetime for each declared state item.

The full schema and semantics of state policy are defined in §07.

If the site does not use state, `state_policy` is an empty array:

```json
"state_policy": []
```

The field is required even when empty.

## `navigation`

`navigation` is a JSON array declaring the site's top-level navigation entries.

Each entry has an ASCII label and a path within the site.

Example:

```json
"navigation": [
  { "label": "Home", "path": "/" },
  { "label": "Articles", "path": "/articles" },
  { "label": "About", "path": "/about" }
]
```

Each navigation entry MUST have exactly two fields:

* `label`, a string;
* `path`, a string beginning with `/`.

No additional fields are permitted.

The label is rendered in the chrome navigation control. The path is a relative path within the same site. Cross-host, cross-origin, cross-carrier, and absolute URLs are forbidden in navigation entries.

A manifest MAY declare an empty navigation array:

```json
"navigation": []
```

The field is required even when empty.

## `min_refresh_interval`

`min_refresh_interval` is the minimum number of seconds the client SHOULD wait between manifest re-fetches under normal conditions.

The value MUST be an integer between 300 and 604800 inclusive.

That is:

* minimum: `300` seconds, five minutes;
* maximum: `604800` seconds, one week.

The default in worked examples is:

```json
"min_refresh_interval": 86400
```

The client MAY refresh sooner than `min_refresh_interval` when:

* the user explicitly requests a refresh;
* the canary is approaching expiration;
* the canary has expired;
* manifest verification failed and the client is retrying;
* the trust state changed;
* the client needs to resolve a changed/mismatch state;
* the client has reason to believe its cached manifest is stale.

The client MUST NOT use `min_refresh_interval` to suppress canary-expiration checks, anti-downgrade checks, trust-state warnings, or explicit user refresh actions.

Aggressive refresh patterns by misconfigured clients are a potential denial-of-service vector against the publisher. Clients SHOULD respect `min_refresh_interval` during normal operation unless one of the exceptional conditions above applies.

## `updated`

`updated` is the timestamp at which the manifest payload was prepared, in RFC 3339 format with the `Z` suffix indicating UTC.

Example:

```json
"updated": "2026-05-07T00:00:00Z"
```

Only this timestamp form is permitted:

```text
YYYY-MM-DDTHH:MM:SSZ
```

Other RFC 3339 forms are not permitted, including:

* numeric UTC offsets;
* fractional seconds;
* leap-second values.

The client MAY display `updated` for diagnostic purposes, such as showing manifest age in the chrome.

The client MUST NOT use `updated` as the primary freshness or anti-downgrade signal. The authoritative freshness and anti-downgrade signal is the canary's `issued_at`, as defined in §08 and applied in §10.

A manifest whose `updated` is more than the allowed clock-skew tolerance in the future relative to the client's clock is rejected. Clock-skew tolerance is defined in §10.

## `sig`

`sig` is the Ed25519 signature over the manifest signature input as defined in §05.

It is encoded as 86 ASCII characters of base64url representing 64 bytes, with no padding.

The `sig` field is outside the signed payload. The signed payload is the manifest object with the `sig` field removed, JCS-canonicalized, and prefixed with the manifest context string and a null-byte separator. The exact signature input formula is defined in §05.

## Field validation

The client validates the manifest according to the closed-schema discipline defined in §02.

A valid manifest satisfies all of the following:

* all required fields are present;
* no additional fields are present;
* each field has the required type;
* each string field is valid UTF-8;
* each string field satisfies its field-specific syntax;
* each numeric field is an integer within its permitted range;
* each nested object has exactly the fields permitted by its schema;
* each array satisfies its maximum length and entry schema.

A manifest that fails any of these checks is rejected. Error codes are defined in §11, and validation order is defined in §10.

## Manifest size limits

Manifests are bounded in size to limit parser exposure and per-fetch overhead.

The following limits apply:

* the total manifest envelope MUST NOT exceed 64 KiB on the wire;
* the `navigation` array MUST NOT exceed 32 entries;
* the `state_policy` array MUST NOT exceed 16 entries;
* individual string fields MUST NOT exceed 1 KiB unless a stricter or more specific limit is defined for that field;
* `origin.address`, `publisher_pubkey`, `origin.origin_pubkey`, `spec_version`, `kind`, `sig`, and timestamp fields are limited by their field-specific syntax.

The 64 KiB byte cap is enforced before JSON parsing. A response that exceeds 64 KiB is rejected without parsing.

Parser resource-limit enforcement is defined in §10.

## Caching and publisher history

The client maintains two related records:

* a manifest cache, keyed by carrier origin;
* publisher history, keyed by `K_publisher.pub`.

This distinction is required because Entangled identity is publisher-rooted, not address-rooted. A publisher may rotate `K_origin`, change address, replace servers, or migrate carriers while preserving the same `K_publisher`.

### Manifest cache

The manifest cache stores the most recently verified manifest fetched from a specific carrier origin.

For Tor v3, the carrier-origin cache key is the canonical `.onion` address from which `/manifest.json` was fetched.

A cached manifest is used to verify content and transaction documents fetched from the same carrier origin.

A cache miss for a carrier origin requires the client to fetch and verify `/manifest.json` before rendering content from that origin.

A cached manifest is no longer current for that origin when any of the following occurs:

* `min_refresh_interval` has elapsed since the manifest was fetched;
* the canary's `next_expected` has passed;
* the user explicitly clears the cache;
* the trust state changes and the client invalidates affected entries;
* the client has observed a newer manifest for the same `K_publisher.pub` with a strictly later canary `issued_at`.

### Publisher history

Publisher history stores the newest verified publication state the client has observed for a given `K_publisher.pub`.

At minimum, publisher history records:

* `K_publisher.pub`;
* the newest verified canary `issued_at`;
* the corresponding `runtime_pubkey`;
* the carrier origin from which that state was observed;
* the trust state associated with the publisher identity.

Publisher history is used for anti-downgrade checks across origin rotation and carrier migration.

A client MUST NOT accept a manifest as current if it has a canary `issued_at` strictly older than the newest verified canary `issued_at` already observed for the same `K_publisher.pub`, unless the client is explicitly treating the older material as historical content under the rules in §10.

This prevents an attacker controlling an old carrier endpoint from presenting an earlier manifest as current after the client has already observed a newer manifest for the same publisher identity.

### Historical manifests

A manifest that is older than the newest verified manifest for the same `K_publisher.pub` is not current.

A client MAY use an older verified manifest to verify historical content, but it MUST NOT present content verified under that older manifest as current publication after observing a newer manifest for the same publisher identity.

Historical-content behavior, warnings, and rendering requirements are defined in §10.

## Manifest lifecycle

The publisher generates a manifest during a publisher ceremony.

The high-level lifecycle is:

1. Compose the manifest object with:

   * `spec_version`;
   * `kind`;
   * `publisher_pubkey`;
   * current `origin`;
   * current `canary`, including a fresh `runtime_pubkey`;
   * `state_policy`;
   * `navigation`;
   * `min_refresh_interval`;
   * current UTC `updated`.

2. Treat the manifest object without `sig` as the signed payload. At this point, `sig` has not yet been added.

3. Compute:

```text
   payload_jcs = JCS(signed_payload)
```

4. Compute:

```text
   signature_input = "ENTANGLED-v1 manifest" || 0x00 || payload_jcs
```

5. Compute:

```text
   sig = Ed25519.sign(K_publisher_priv, signature_input)
```

6. Add the `sig` field to the manifest object.

7. Deploy the manifest at:

```text
   /manifest.json
```

8. Make the corresponding `K_runtime_priv` available to the publishing infrastructure according to the operator's key-custody procedure.

The manifest is replaced, not amended, on every publication cycle.

Old manifests do not remain authoritative once a newer manifest with a strictly later canary `issued_at` has been fetched and verified by the client for the same `K_publisher.pub`.

Old manifests may still be useful for verifying historical content, subject to the historical-content rules in §10.

## What this section does not cover

This section defines the manifest envelope, payload, field semantics, validation rules, caching semantics, and lifecycle.

It does not define:

* the canary structure in detail (see §08);
* state policy schema and consent semantics (see §07);
* block types or document content (see §02 and §03);
* canonicalization rules (see §04);
* key roles, signing primitives, domain separation, or PIP derivation (see §05);
* carrier-specific origin binding details beyond the high-level requirement (see §05);
* client verification pipeline order, error precedence, chrome behavior, trust state behavior, or historical-content rendering (see §10 and §11).