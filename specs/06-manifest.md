# 06 - Manifest

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

All fields listed above are required. The optional top-level fields `migration_pointer` and `content_root` MAY appear in addition to the required fields (see "`migration_pointer`" and "`content_root`" below). No other fields are permitted.

Optional top-level fields are part of the closed schema: only fields explicitly listed by this section as required or optional may appear. A document containing any other top-level field is rejected.

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

A manifest whose `publisher_pubkey` does not match the already established publisher identity for the current site or origin triggers the changed/mismatch trust state defined in §10.

## `origin`

`origin` declares the carrier endpoint for which this manifest is authoritative.

It is a JSON object with three required fields and one optional field:

```json
{
  "carrier": "tor-v3",
  "address": "<56-character-onion-address>.onion",
  "origin_pubkey": "<base64url, 32 bytes>",
  "not_after": "2027-05-10T00:00:00Z"
}
```

`carrier`, `address`, and `origin_pubkey` are required. `not_after` is optional. No other fields are permitted.

### `origin.carrier`

`carrier` is an ASCII string identifying the carrier profile.

Entangled v1 fully specifies only:

```json
"carrier": "tor-v3"
```

A conforming Entangled v1.0 client MUST reject any manifest whose `origin.carrier` is not exactly `"tor-v3"`.

The values `"i2p"` and `"yggdrasil"` are reserved for draft carrier profiles. They are not v1.0-conformant values, and a v1.0 client MUST reject manifests declaring them, until their address-to-key binding rules are specified byte-for-byte under a future protocol version.

Note: implementations MAY experimentally support additional carrier profiles outside Entangled v1.0 conformance, for example for prototyping or research. Such support is not part of v1.0 validation, MUST NOT be enabled by default in a v1.0-conformant client, and does not change the rejection rule above for v1.0 conformance.

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

### `origin.not_after`

`origin.not_after` is an OPTIONAL field declaring the UTC instant after which the publisher commits that this carrier endpoint is no longer authoritative for the site under `K_publisher`.

When present, it is encoded in the same RFC 3339 UTC form required for `updated`:

```text
YYYY-MM-DDTHH:MM:SSZ
```

Other RFC 3339 forms are not permitted, including numeric UTC offsets, fractional seconds, and leap-second values.

When absent, the field is omitted from the JSON object. The JSON literal `null` is not permitted, per §04 no-`null` discipline. An absent `not_after` declares no publisher-side expiration of the origin binding; the origin remains authoritative as long as it satisfies the manifest's canary and anti-downgrade rules.

Constraints when present:

* `origin.not_after` MUST be strictly later than `canary.issued_at`. An expiration at or before issuance is ill-formed.
* `origin.not_after` SHOULD be strictly later than `canary.next_expected`. An expiration that falls within or before the committed canary window narrows the origin's usable lifetime below the canary cycle and signals an imminent retirement; this is permitted but discouraged.
* `origin.not_after` MUST NOT be more than 5 years (157680000 seconds) after `canary.issued_at`. The 5-year ceiling bounds the maximum window during which a compromised `K_origin` can serve cached clients of an unrotated origin; it does not bound publisher-driven rotation, which remains the publisher's discretion within that ceiling.

A manifest carrying `origin.not_after` outside these constraints is rejected as `E_ORIGIN_INVALID` (§11).

The 5-year ceiling is evaluated per manifest, relative to that manifest's own `canary.issued_at`. Each manifest's `origin.not_after` is checked against the `canary.issued_at` carried in the same signed manifest payload; the check does not refer to any prior manifest's `canary.issued_at` or to a first-declared `not_after`. When the publisher rotates the canary, the new manifest carries a later `canary.issued_at`, and the 5-year window slides forward with it: the publisher MAY re-issue `origin.not_after` up to 5 years from the new `canary.issued_at`. The same origin block re-published across successive rotations may therefore carry a `not_after` whose absolute instant advances with each rotation, and the effective lifetime of a continuously-rotated origin is not bounded by any single ceiling.

This is intentional. The ceiling bounds the maximum window during which a compromised `K_origin` can serve cached clients of an *unrotated* origin: the window is anchored to the most recent canary the client can have verified, so a stale origin that stops rotating cannot extend its `not_after` past 5 years from its last `issued_at`. A publisher that keeps rotating is, by construction, demonstrating liveness with each new `canary.issued_at`, and the protocol does not cap how long a live, continuously-rotated origin may remain authoritative. A publisher seeking a bounded total origin lifetime regardless of rotation enforces that as an operational policy (it simply stops advancing `not_after` past its chosen absolute instant); the protocol does not impose it.

#### Client behavior

When `origin.not_after` is present and the client's clock (subject to the clock-skew tolerance in §10) is strictly later than the declared instant, the manifest is treated as origin-expired:

* the manifest MUST NOT be accepted as current. The client refuses to render publisher-controlled content under this manifest.
* the diagnostic is `E_ORIGIN_EXPIRED` (§11).
* anti-downgrade still applies: the expired manifest does not become a downgrade target for newer manifests, and a newer manifest from the same `K_publisher.pub` (whether at the same address or via a verified `migration_pointer`) supersedes it under the standard anti-downgrade rule.

An origin-expired manifest does not invalidate cryptographically valid signatures over historical content authorized under that origin's prior publication cycles, subject to the historical-content rules in §10.

`origin.not_after` is a publisher-declared commitment, not a substitute for `K_origin` rotation. A publisher who wishes to retire an origin MUST publish a new manifest with a different `K_origin` (typically alongside a `migration_pointer` from the old origin to the new) and SHOULD do so before the declared `not_after` instant. After the instant, clients with no successor knowledge fall back to out-of-band recovery, as for any origin loss without prior `migration_pointer`.

### Single-origin rule

In Entangled v1, a manifest declares exactly one origin.

A publisher who controls multiple carrier endpoints publishes a separate manifest per endpoint, each signed by the same `K_publisher`.

Multi-origin manifests are not part of Entangled v1 and may be considered in a future version.

### Multi-origin publication cadence

This subsection does not introduce a new enforcement mechanism. It makes explicit a publisher requirement that follows from the existing anti-downgrade rule.

A publisher operating multiple origins under the same `K_publisher.pub` publishes one manifest per origin. Each manifest is single-origin, as defined above.

Publisher history and anti-downgrade are keyed by `K_publisher.pub`, not by carrier origin (see "Caching and publisher history" below and §08). Once a client has observed a verified manifest with canary `issued_at = T_new` for a given `K_publisher.pub`, any later manifest from any origin for the same `K_publisher.pub` whose canary `issued_at` is strictly older than `T_new` is rejected as non-current under that rule.

If a publisher wants its multiple origins to remain acceptable as current by clients that support publisher history, the publisher MUST keep canary `issued_at` values monotonically non-decreasing across all such origins. Equivalently, when the publisher refreshes the canary, the new manifest is deployed to every origin under the same `K_publisher.pub` before clients can begin observing the newer `issued_at`.

If origins drift out of sync, clients that have already seen a newer canary on one origin will reject the older manifest from another origin until that origin publishes a manifest with `issued_at` at least equal to the newest observed value. Anti-downgrade rejection is the existing client behavior; this subsection only names its consequence for multi-origin operators.

Operators of multiple origins should treat manifest publication as an atomic or near-atomic multi-origin deployment step. The requirement does not change the wire format, the single-origin manifest rule, or the anti-downgrade rule.

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

Each entry has a label and a path within the site.

Example:

```json
"navigation": [
  { "label": "Home", "path": "/" },
  { "label": "Articles", "path": "/articles" },
  { "label": "About", "path": "/about" }
]
```

Each navigation entry MUST have exactly two fields:

* `label`, a UTF-8 string;
* `path`, a same-site path.

No additional fields are permitted.

`label` MUST satisfy:

* it is a UTF-8 string;
* it MUST NOT exceed 100 bytes when encoded as UTF-8;
* it MUST NOT contain control characters in the range U+0000 through U+001F or the value U+007F.

`path` MUST satisfy the path syntax defined in §02 for content document `path` values, including the reservation of `/manifest.json`.

The label is rendered in the chrome navigation control. The path is a relative path within the same site. Cross-host, cross-origin, cross-carrier, and absolute URLs are forbidden in navigation entries.

The `navigation` array is top-level navigation, not a complete content inventory. Entangled v1 does not define a machine-readable full-site index, sitemap, or content enumeration mechanism. A publisher who wishes to expose an archive or index page may publish it as an ordinary `content` document linked from `navigation`; that page is composed from the block types defined in §03. Clients MUST NOT infer that `navigation` enumerates all content available on the site.

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

## `migration_pointer`

`migration_pointer` is the publisher's signed announcement that the site is being migrated to a new carrier endpoint under the same `K_publisher`.

It addresses the case where a publisher rotates `K_origin`, replaces the carrier endpoint, or migrates between carrier endpoints, without losing identity continuity for clients that have only the old endpoint cached.

### Optionality

`migration_pointer` is an OPTIONAL top-level field. Following the "absent values are encoded by omitting the field" rule of §04, a manifest with no migration to announce omits the field entirely. The JSON literal `null` is not permitted as a value for `migration_pointer`, in keeping with the no-`null` rule of §04.

### Value when present

When a migration is announced, the field is present and contains exactly two members: `successor_origin` and `announced_at`. No other fields are permitted.

```json
"migration_pointer": {
  "successor_origin": {
    "carrier": "tor-v3",
    "address": "<56-character-onion-address>.onion",
    "origin_pubkey": "<base64url, 32 bytes>"
  },
  "announced_at": "2026-05-10T00:00:00Z"
}
```

### `successor_origin`

`successor_origin` declares the carrier endpoint to which the publisher is migrating.

It has exactly three fields: `carrier`, `address`, and `origin_pubkey`. These three fields share the schema, validation rules, and carrier-value constraints of the manifest's top-level `origin.carrier`, `origin.address`, and `origin.origin_pubkey` defined above, including the address-to-key binding rule. The optional `origin.not_after` field is not part of `successor_origin`: a migration announcement is a pointer to a successor whose own manifest, fetched and verified at Stage 9, carries that successor's own `origin.not_after` declaration if any. No other fields are permitted in `successor_origin`.

`successor_origin.carrier` MUST equal `origin.carrier`. Cross-carrier migration is not part of Entangled v1.0 because v1.0 fully specifies only the Tor v3 carrier profile; cross-carrier announcements would require destination-carrier binding rules that v1.0 does not define.

`successor_origin.address` MUST differ from `origin.address`. A migration_pointer that points back to the announcing origin is ill-formed.

For Tor v3, the client MUST verify, before treating the announcement as valid, that `successor_origin.address` decodes to a public key equal to `successor_origin.origin_pubkey` (the same binding rule as for `origin`, defined in §05). This is an announcement-internal check on the two declared fields of `successor_origin`; it does not require fetching the successor and is evaluated when the announcing manifest is validated. A failure is rejected as `E_MIGRATION_INVALID` (§11) with `details.reason = "successor_key_mismatch"`. It is distinct from the fetch-time successor checks in §10 ("Origin migration"), which compare the fetched successor manifest's own `origin` fields against the announced `successor_origin` and fail as `E_MIGRATION_MISMATCH`.

### `announced_at`

`announced_at` is the UTC timestamp at which the publisher composed the announcement, in the same RFC 3339 form required for `updated`:

```text
YYYY-MM-DDTHH:MM:SSZ
```

Other RFC 3339 forms are not permitted, including numeric UTC offsets, fractional seconds, and leap-second values.

`announced_at` MUST NOT be later than the manifest's `updated` field. The announcement cannot be newer than the manifest that carries it.

`announced_at` MAY be earlier than `updated` when the publisher pre-composed an announcement before the final manifest signature. Successive manifests that carry the same migration announcement MAY repeat the same `announced_at` across refreshes.

### Authority and binding

The migration announcement is part of the manifest payload covered by the manifest signature. Because the manifest is signed by `K_publisher`, only the legitimate publisher can announce a successor origin. An attacker holding `K_origin_priv` for the announcing origin but not `K_publisher_priv` cannot forge a migration announcement.

The successor origin is not validated by `K_publisher` directly; the announcement is. Confirmation that the successor origin is operated by the same publisher requires the client to fetch the successor's manifest and verify that its `publisher_pubkey` matches the announcing manifest's `publisher_pubkey`. Client behavior for this verification, and for the trust-state implications, is defined in §10.

### Effect on the announcing manifest

The presence of a `migration_pointer` does not invalidate the announcing manifest. Until the publisher stops publishing on the announcing origin, the announcing manifest remains current for that origin. The migration announcement is a hint plus a signed binding; it is not a self-decommissioning instruction.

A publisher who wants the announcing origin to stop being current eventually stops refreshing the canary on it. The canary then expires (see §08), and clients' standard expiration behavior applies.

### Multi-origin caveat

`migration_pointer` does not authorize a publisher to operate multiple origins simultaneously. The single-origin rule in this section continues to apply to each manifest: the announcing manifest declares one origin, and the successor manifest declares one origin. The announcement is a directional pointer between two single-origin manifests, not a multi-origin declaration.

Multi-origin operation under the same `K_publisher` is governed by the publisher-profile rules in §10 and the publication cadence rules above; `migration_pointer` is one mechanism for the publisher to bring clients of the old origin into a publisher-profile relationship with the new origin without out-of-band PIP exchange.

## `content_root`

`content_root` is the publisher's commitment to the current content state of the site.

### Optionality

`content_root` is an OPTIONAL top-level field. Following the "absent values are encoded by omitting the field" rule of §04, a manifest whose publisher does not use the content index mechanism omits the field entirely. The JSON literal `null` is not permitted as a value for `content_root`, in keeping with the no-`null` rule of §04.

### Value when present

When present, `content_root` is a string of the form:

```text
sha-256:<base64url>
```

using the same encoding as `image.sha256` (§03) and `request_hash` (§02): a literal prefix `sha-256:` (eight lowercase ASCII characters including the trailing colon) followed by the base64url encoding (RFC 4648 Section 5) of the 32-byte SHA-256 digest, with no padding, exactly 43 ASCII characters. The total string length is exactly 51 ASCII characters.

The value is the SHA-256 digest of the exact response body bytes of `/content_index.json` served from the same carrier origin. The content index format is defined in §02. The fetch is defined in §09. Client verification is defined in §10.

### Semantics

`content_root` is part of the signed manifest payload and is covered by the `K_publisher` signature. It commits the publisher to a specific set of `(path, seq, hash)` triples. Only a publisher with `K_publisher_priv` can produce or modify this commitment. An attacker holding only `K_runtime_priv` cannot forge, alter, or roll back content at paths listed in the content index.

Content at paths not listed in the content index is not covered by `content_root` and is protected only by the `K_runtime` signature, as for content in manifests without `content_root`.

### Ceremony interaction

`content_root` is updated at each publisher ceremony (canary rotation). The publisher computes the content index from the current set of published content documents, hashes it, and includes the hash as `content_root` in the manifest being signed. Between ceremonies, the content index and the content at indexed paths are frozen: the publisher MUST NOT serve content at indexed paths with a different `seq` or body hash than what the index declares. New content at paths not in the index may be published between ceremonies using `K_runtime` alone.

This preserves the `K_publisher`-offline model: the publisher key is used only during ceremonies, not for individual content updates.

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
* the `state_policy` array MUST NOT exceed 32 entries;
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

Publisher history also detects equal-`issued_at` conflicts: a manifest with the same canary `issued_at` as a previously verified manifest for the same `K_publisher.pub` but with a different signed payload triggers `E_CANARY_CONFLICT` (see §08 and §11).

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
   * current UTC `updated`;
   * `migration_pointer`, included only when announcing a migration to a successor origin; otherwise omitted;
   * `content_root`, included only when the publisher commits to a content index; otherwise omitted.

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