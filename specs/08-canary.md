# 08 - Canary

The canary is the structure within the manifest by which the publisher attests, on a recurring basis, that the site is operating under publisher control and authorizes the current operational signing key.

The canary serves two roles simultaneously:

1. **Warrant canary.** A periodic, signed statement in which the publisher attests certain conditions, typically along the lines of having not been compromised, coerced, or compelled to act against users. The protocol does not, and cannot, verify whether the attestation is true. What the protocol provides is a visible failure condition when the publisher cannot, or will not, sign on schedule. The signal is structural, not semantic: failure to produce a fresh canary by the committed deadline is the protocol-level warning condition.

2. **Runtime authorization.** The canary declares the `runtime_pubkey` authorized to sign `content` and `transaction` documents for the current publication cycle.

These two roles are unified in v1: refreshing the canary requires a publisher ceremony involving `K_publisher`, and the same ceremony rotates `K_runtime`. A site that fails to refresh its canary therefore both stops maintaining a fresh publisher-control attestation and stops authorizing new content as current publication without warning.

The canary is part of the manifest payload. The manifest signature, produced by `K_publisher`, covers the canary. The canary is not signed independently in Entangled v1.

## Canary structure

The canary is a JSON object with the following fields:

```json
{
  "runtime_pubkey": "<base64url, 32 bytes>",
  "issued_at": "2026-05-07T00:00:00Z",
  "next_expected": "2026-06-07T00:00:00Z",
  "statement": "...",
  "freshness_proof": "..."
}
````

The fields `runtime_pubkey`, `issued_at`, `next_expected`, and `statement` are required.

The field `freshness_proof` is optional. When omitted, the field is absent from the JSON object; an empty string or null value is not permitted.

No other fields are permitted in the canary object.

### `runtime_pubkey`

`runtime_pubkey` is the public key of `K_runtime`, the operational signing key authorized for the current publication cycle.

It is encoded as 43 ASCII characters of base64url representing 32 bytes, with no padding.

This is the key against which the client verifies `content` and `transaction` document signatures during the publication cycle covered by the current manifest, as defined in §05.

A new manifest with a fresh canary MUST declare a `runtime_pubkey` distinct from the `runtime_pubkey` of the immediately preceding manifest for the same `K_publisher.pub` in the client's publisher history. The publisher generates a new `K_runtime` keypair as part of every rotation ceremony.

If a new manifest presents the same `runtime_pubkey` as the immediately preceding verified manifest for the same `K_publisher.pub`, the client MUST reject the manifest with `E_CANARY_RUNTIME_REUSE` (§11). This ensures that canary freshness is evidence of actual key rotation, not merely a timestamp update with the same operational key. Without this rule, a publisher - or an attacker holding a compromised `K_runtime` - can maintain the same runtime key indefinitely while producing apparently fresh canaries, defeating the rotation guarantee described in §05.

The immediate-preceding check above is the universal MUST and applies to every conforming client, including stateless clients that do not retain publisher history across navigations. It does not, however, detect a pattern in which a publisher (or an attacker holding `K_publisher_priv`) alternates between two or more previously announced `runtime_pubkey` values - for example, an `A -> B -> A -> B` rotation sequence - because each step in such a sequence presents a `runtime_pubkey` distinct from the *immediately* preceding manifest while reusing a key that was retired at an earlier rotation. Per the §08 ceremony (steps 5, 7) and per the operator playbook §3.3 "Secure destruction of `K_runtime_priv`", a publisher following the ceremony destroys the prior `K_runtime_priv` at every rotation; a publisher who is able to re-announce a previously retired `runtime_pubkey` has either retained the corresponding private key in violation of the ceremony or is acting under conditions in which the ceremony discipline cannot be presumed (compromise, coercion).

A client that maintains publisher history (the same publisher-history storage used for anti-downgrade, for the `T_verified` reference defined in §10 "Clock reliability and the verified-time reference" - which is the same value as the anti-downgrade floor, not a parallel concept - and for cross-session migration history under §10) SHOULD, in addition to the immediate-preceding MUST above, reject a new manifest whose `runtime_pubkey` matches *any* previously verified `runtime_pubkey` for the same `K_publisher.pub` in that history, with the same `E_CANARY_RUNTIME_REUSE` diagnostic (§11). The structured `details` object distinguishes the immediate-preceding match (`window_position = 1`) from a deeper history match (`window_position >= 2`), allowing clients and operators to distinguish the disciplined-rotation violation from the apparent key resurrection. This SHOULD-level extension is the analogue of the §10 SHOULD on cross-session migration history (publisher-history-based mitigation enforced where the client retains the necessary state). A client that does not maintain runtime-pubkey history is not non-conforming; the limitation is documented in §00.

The history window has no upper bound in v1: a client SHOULD reject a `runtime_pubkey` that matches any entry in the retained history for the publisher, regardless of how long ago the matching entry was first observed. Storage cost is bounded by the number of distinct `runtime_pubkey` values observed for the publisher (32 bytes per entry, in the range of a few KB for a publisher rotating at the §08 cadence floor for several years). Clients with bounded publisher-history storage MAY enforce a smaller window, provided the window is documented and is at least the immediate-preceding entry (so the universal MUST is not weakened); a client with a smaller window enforces a weaker version of the SHOULD but remains conformant against the MUST.

### `issued_at`

`issued_at` is the timestamp at which the canary was signed by the publisher, in RFC 3339 format with the `Z` suffix indicating UTC.

```json
"issued_at": "2026-05-07T00:00:00Z"
```

Only this timestamp form is permitted:

```text
YYYY-MM-DDTHH:MM:SSZ
```

Other RFC 3339 forms are not permitted, including numeric UTC offsets, fractional seconds, and leap-second values.

`issued_at` is the authoritative anti-downgrade and freshness signal for Entangled. Specifically:

* The client uses `issued_at` to determine whether a fetched manifest is newer than a cached manifest for the same `K_publisher.pub`. A manifest with `issued_at` strictly older than the newest verified `issued_at` already observed for the same `K_publisher.pub` MUST NOT be accepted as current. See §06 (publisher history) and §10 (anti-downgrade enforcement).
* The client uses `issued_at` to determine canary age and the corresponding trust state of the canary, as defined in this section.

`issued_at` MUST NOT be more than the allowed clock-skew tolerance in the future relative to the client's clock. A manifest whose canary `issued_at` is implausibly far in the future is rejected. Clock-skew tolerance is defined in §10.

### `next_expected`

`next_expected` is the timestamp by which the publisher commits to issuing a fresh canary, in the same RFC 3339 form as `issued_at`.

```json
"next_expected": "2026-06-07T00:00:00Z"
```

`next_expected` MUST be strictly later than `issued_at`.

The interval between `issued_at` and `next_expected` MUST be:

* at least 7 days (604800 seconds);
* at most 30 days (2592000 seconds).

These bounds prevent two pathological cases:

* intervals shorter than 7 days impose excessive ceremony burden on the publisher and offer diminishing operational returns;
* intervals longer than 30 days defeat the purpose of the warrant canary by allowing prolonged silence to pass without signal.

The publisher chooses the interval based on operational practice. Higher-threat publishers SHOULD choose intervals close to 7 days. Lower-threat publishers MAY choose intervals up to the 30-day ceiling.

A client receiving a manifest with `next_expected - issued_at` outside the permitted bounds rejects the manifest.

### `statement`

`statement` is a human-readable text that the publisher includes in the canary as the substance of the warrant.

It is a UTF-8 string. It MUST NOT exceed 2048 bytes when encoded as UTF-8. It MUST NOT contain control characters in the range U+0000 through U+001F or the value U+007F, except for the line feed character U+000A which is permitted to support multi-line statements. It is subject to the §04 Unicode normalization rule for user-visible strings: `statement` MUST be encoded in Normalization Form C (NFC). A non-NFC `statement` is rejected at schema validation with `E_SCHEMA_FIELD_SYNTAX` per §04 and §11.

Line feed is permitted only as plain text formatting. It has no markup semantics.

The protocol does not prescribe the wording of the statement. Publishers customarily include attestations such as that no warrant has been received, no compelled disclosure has occurred, no third party has obtained operational keys, and similar language adapted to their jurisdiction and threat model.

The statement is rendered by the client as part of the chrome's canary status display, available to users who expand the canary detail view. Display behavior is defined in §10.

The protocol attaches no semantic meaning to the contents of the statement. The cryptographic significance of the canary is the act of signing it on schedule, not the literal text. A publisher who is compelled to issue a misleading canary signs an attestation that may be factually false, but the security property the protocol provides is not the truth of the statement: it is the absence of fresh signatures when the publisher cannot truthfully sign.

### `freshness_proof`

`freshness_proof` is an optional field by which the publisher may anchor the canary to a temporal reference outside the publisher's control.

When present, it is a UTF-8 string not exceeding 200 bytes. It MUST NOT contain control characters. It is subject to the §04 Unicode normalization rule for user-visible strings: `freshness_proof` MUST be encoded in Normalization Form C (NFC), consistent with the §04:144 rule applied to any field a conforming client renders as user-visible text (see §08:127 and §10:709 for the rendering requirement that makes `freshness_proof` subject to NFC). A non-NFC `freshness_proof` is rejected at schema validation with `E_SCHEMA_FIELD_SYNTAX` per §04 and §11.

Common uses include:

* a recent block hash from a public blockchain;
* a short reference to a widely published news item;
* a hash of a public bulletin recently posted by a third party;
* any other short reference to a real-world event whose existence at the time of signing can be independently confirmed.

The protocol does not validate the contents of `freshness_proof`. The client renders it in the chrome's canary detail view when present, allowing users to independently confirm that the canary was signed after the referenced event.

`freshness_proof` is a tool that helps detect certain forms of backdating. A canary signed weeks earlier and held for delayed publication can carry a fabricated `issued_at`, but cannot reference an event that had not yet occurred at signing time. Including such a reference therefore constrains how far back the actual signing time can plausibly be.

`freshness_proof` does not eliminate backdating. A publisher under coercion may still sign a canary using a freshness reference at the time of signing, while the substance of the warrant has already been broken. The field constrains the temporal claim of the signature, not the truth of the statement.

The field is optional in v1 because it is operationally heavier than the other canary fields and not all publishers will use it. Publishers who omit `freshness_proof` rely on `issued_at` alone as the temporal anchor of the canary.

#### Client signaling on absence

Because `freshness_proof` is the only protocol-level signal against canary backdating, its absence is itself relevant to the user's risk assessment.

A client MUST signal in chrome whether the current canary includes a `freshness_proof`. The signal MUST be visible in the canary's summary surface - the surface that exposes the canary state (Fresh, Near-expiration, Expired, Invalid, Unavailable) without requiring the user to expand a detail view, drawer, or other collapsed UI affordance. The "summary surface" in this section is the canary-specific instance of the always-visible compact indicator surface defined in §10 "Always-visible compact indicators"; the contents of `freshness_proof` itself, when present, MAY remain in the corresponding "expandable detail surface" (§10). A client MUST NOT hide the presence-or-absence signal exclusively behind an expandable detail surface that is collapsed by default.

The signal MAY be implicit (the proof is shown when present, and a "no freshness proof" indicator is shown when absent) or explicit (a labelled indicator that is always visible). In either form, the summary surface MUST distinguish present from absent at a glance.

The contents of `freshness_proof` itself, when present, MAY remain in the expandable detail surface; only the presence-or-absence indicator is required in the summary.

A client MUST NOT silently treat a canary with `freshness_proof` and one without as equivalent in chrome.

#### Strict freshness policy

A client MAY operate in a strict freshness policy mode in which `freshness_proof` is treated as required: a manifest whose canary does not include `freshness_proof` is refused for rendering, with the same chrome treatment as Invalid canary state.

Strict freshness policy is a client-side configuration, not a manifest declaration. The protocol does not require strict mode by default. Operators and high-threat users who depend on the temporal anchor MAY enable it; the client MUST document the option in user-accessible form.

A publisher who anticipates being consumed by clients in strict freshness policy mode MUST include `freshness_proof` in every canary issuance. Operator practices for `freshness_proof` are documented in the operator playbook.

## Canary states

The client computes a canary state from the canary's `issued_at` and `next_expected` and the current time. The states are mutually exclusive at any given time:

* **Fresh.** Current time is between `issued_at` and `next_expected`, with substantial margin remaining before `next_expected`.
* **Near-expiration.** Current time is approaching `next_expected`. The publisher has not yet issued a fresh canary, but the deadline has not passed.
* **Expired.** Current time is at or after `next_expected`. The publisher has not issued a fresh canary by the committed deadline.
* **Invalid.** The manifest signature is otherwise valid, but the canary fails structural or semantic validation independently of timing. Examples include: malformed canary fields; invalid timestamp syntax; `issued_at` more than the allowed clock-skew tolerance in the future; `next_expected` not strictly later than `issued_at`; `next_expected - issued_at` outside the 7-to-30-day bounds; a `canary.runtime_pubkey` that fails the §05 public-key strict profile (non-canonical encoding or small-order point), rejected with `details.reason = "public_key_rejected"`; other canary-specific validation failures defined in this section. Manifest signature failure is not a canary Invalid condition: it is reported under the manifest signature failure class defined in §05 and §11.
* **Unavailable.** The client could not fetch a manifest, and therefore could not obtain a canary, for reasons of carrier reachability or transport failure.

The exact thresholds defining "near-expiration" are implementation-defined. The client SHOULD treat the canary as near-expiration when the current time is within the last 10% of the `issued_at` to `next_expected` interval, or within 24 hours of `next_expected`, whichever is longer. The client MUST document the threshold it uses, in user-accessible form.

## Client behavior on canary states

The client MUST display the canary state persistently in client-controlled UI, as part of the chrome elements defined in Pillar C and §10.

The required behavior for each state:

### Fresh

The client renders content normally. The chrome shows the canary state as fresh, including the `next_expected` timestamp.

### Near-expiration

The client renders content normally. The chrome shows the canary state as near-expiration with visual emphasis. The user is informed that the publisher's commitment deadline is approaching.

### Expired

The client MUST refuse to render current content from any site whose canary is in Expired state. The content area MUST be blank or display a client-generated placeholder; publisher-controlled content MUST NOT appear. The chrome MUST display a clear notice that the canary is expired and rendering is blocked, alongside the per-session override control defined below.

The client MUST provide a per-session user-override affordance: a chrome control that explicitly allows the user to proceed with rendering for the current session despite the expired canary. The override MUST require affirmative user action (a button, key combination, or equivalent affordance whose semantics are unambiguously "accept the risk and proceed"); passive events MUST NOT count as acceptance. The override applies for the remainder of the current session for the affected site; it does not persist across sessions, does not modify the canary state, and does not suppress the chrome warning. When the override is active, the client MUST display a persistent, not-easily-dismissible warning in chrome indicating that expired-canary rendering is active by user override.

The per-session override addresses the concern that hard-failing conflates publisher operational pause (vacation, server outage, ceremony delay) with publisher compromise. Users who trust the publisher's operational situation can proceed; the default posture protects users who do not actively assess the situation.

The user is presented with the elapsed time since `next_expected` and the contents of the canary's `statement` and `freshness_proof` (if present).

The client MUST NOT pin a new manifest with a fresh canary to replace the expired one without user awareness. Manifest refresh is normal protocol behavior, but the user MUST be notified when an expired canary is replaced, since the gap itself is the protocol-level warning condition.

If a client has observed an expired canary for a publisher identity, and later observes a fresh canary for the same `K_publisher.pub`, the client MUST notify the user that a canary gap occurred. The fresh canary may restore current freshness, but it MUST NOT erase the historical fact that the publisher missed a committed refresh deadline.

Canary expiration does not cryptographically revoke `K_runtime` in v1. Forgery exposure for a compromised `K_runtime` is bounded by rotation cadence only when the publisher actively rotates `K_runtime` and deploys a fresh manifest. An expired canary is an operational hard-block state with a §08:185 per-session user-override carve-out, not a cryptographic revocation; the rendering block is the §11:79 default behavior for the `error`-severity `E_CANARY_EXPIRED` diagnostic, applied via the §08:183 MUST. Clients MAY offer a permissive-canary mode that reverts to warning-only rendering without requiring the per-session override; see §10. Permissive-canary mode is the §08-sanctioned laxer-policy exception to the default block on `E_CANARY_EXPIRED` mandated by §08:183. It is a spec-defined opt-in, not a §11:87 client-side reclassification of severity.

### Invalid

The client MUST refuse to render any content from the site whose manifest contains an invalid canary. The chrome shows the canary state as invalid with a prominent error.

Unlike expiration, invalidity indicates structural or semantic failure of the canary discipline. The publisher who controls a valid `K_publisher` cannot legitimately produce an invalid canary in a signed manifest; therefore the manifest is rejected even though its signature otherwise verifies.

Manifest signature failure is a distinct condition: it is detected at stage 6 and reported as `E_SIG_VERIFICATION` (§11), not as canary Invalid.

### Unavailable

The client MUST display the unavailable state in the chrome and MUST NOT use cached content if no cached manifest exists for the site.

If a cached manifest exists from a prior session, the client MAY display previously cached content with explicit indication that it is cached and that the current canary state cannot be verified.

The Unavailable state, and the optional cached-content rendering above, apply only while the most recent cached manifest's canary deadline is not shown definitely past. If the client holds a cached manifest for the site whose canary `next_expected` is strictly earlier than the sound verified-time lower bound `T_lower` defined in §10, the client MUST compute Expired (the render-block and per-session override defined above), not Unavailable, even when the live manifest fetch fails. A failed fetch does not relax a canary deadline the client can already see has passed: a missed, client-observable deadline is a publisher commitment failure, not a transport condition. This time-independent lower-bound determination takes precedence over Unavailable so that a coerced or compromised carrier cannot downgrade an Expired render-block to cached-content rendering simply by withholding the manifest fetch.

The unavailable state is distinguished in display from invalid: unavailable indicates network or transport conditions, not a security failure.

## Anti-downgrade enforcement

A client MUST NOT accept a manifest as current when its canary `issued_at` is strictly older than the newest verified `issued_at` previously observed for the same `K_publisher.pub`.

This rule applies across all carrier origins and addresses for the same publisher. If the client has observed a manifest with `issued_at = T_new` for `K_publisher.pub = P`, and later fetches a manifest from any address with `issued_at = T_old < T_new` for the same `P`, the client MUST reject the older manifest as a downgrade attempt.

The client MAY use older manifests to verify historical content, subject to the historical-content rules defined in §10. Anti-downgrade restricts what is considered current; it does not retroactively invalidate cryptographically valid older signatures.

The publisher history records defined in §06 are the storage from which anti-downgrade decisions are made.

### Equal issued_at conflict

A publisher MUST NOT issue two distinct manifests with the same `canary.issued_at` for the same `K_publisher.pub`. Distinct here means any difference in the JCS-canonicalized manifest payload (excluding the `sig` field).

A client that has already accepted a manifest with `canary.issued_at = T` for `K_publisher.pub = P`, and later observes a different manifest from any origin with `canary.issued_at = T` for the same `P`, MUST reject the later manifest and report the conflict. The reported diagnostic is `E_CANARY_CONFLICT` (§11).

A canary conflict is evidence of a publisher protocol violation. Because both conflicting manifests are signed by the same `K_publisher`, an honest publisher operating within the protocol cannot produce them: the conflict is consistent with `K_publisher` compromise or with serious operator error. The client MUST treat `E_CANARY_CONFLICT` as a fault condition for the publisher identity, not as a recoverable transient error.

The client MUST NOT pick a "winner" between the conflicting manifests by lexicographic comparison of the JCS payload, by payload size, by `runtime_pubkey` value, or by any other deterministic tiebreaker over manifest content. A deterministic tiebreaker would be gameable by an attacker holding `K_publisher_priv` - they could grind irrelevant fields until their forged manifest wins the comparison - and would mask the underlying fault behind a false sense of resolution.

The retained manifest accepted before the conflict was observed remains in place for current rendering and anti-downgrade. The later conflicting manifest is rejected. The client MUST surface the conflict as a prominent, not-easily-dismissible chrome warning, analogous to the Changed/mismatch warning defined in §10, and MUST present an explicit user-accessible resolution control as part of that chrome warning. The resolution control MUST offer at least two distinct user actions:

1. **Keep the retained identity.** The user explicitly acknowledges the conflict without abandoning the publisher identity. The chrome warning is cleared from the always-visible position; the conflict is recorded in publisher history and remains visible in the publisher-history detail surface.
2. **Abandon the retained publisher identity.** The user explicitly chooses to stop trusting the publisher identity that produced the conflicting manifests. The effect on the retained trust-state record, on current, pending, and historical origin associations, and on retained `request`-mode state items (which are suspended from transmission, not deleted) is defined in §10 under "Abandoning a retained publisher identity".

A passive event - content rendering, navigation away from the site, dismissal of an unrelated chrome notice, or any other event not bound to the resolution control - MUST NOT clear the canary-conflict warning. A subsequent successful fetch of a non-conflicting newer manifest does not by itself clear the warning, because the conflict is a historical fault on the publisher identity, not a transient state of the current manifest. The warning persists until the user invokes the resolution control.

This rule does not affect refetching the same manifest. A subsequent fetch returning a manifest with the same JCS-canonical signed payload as the previously verified one is not a conflict, regardless of wire-level JSON formatting differences that JCS normalizes away. Ed25519 signing under the same private key over identical signature inputs is deterministic (RFC 8032), so a same-payload refetch necessarily carries an identical `sig`; the protocol-level criterion is the JCS-canonical signed payload, not the wire bytes or the `sig` value.

`E_CANARY_DOWNGRADE` and `E_CANARY_CONFLICT` are mutually exclusive. The former applies when a fetched manifest has a strictly older `canary.issued_at` than the newest verified one for the same `K_publisher.pub`. The latter applies when the `issued_at` is equal but the signed payload differs. The strictly-greater case is acceptance: the fetched manifest becomes the new newest verified record for the publisher.

`E_CANARY_CONFLICT` and `E_CANARY_RUNTIME_REUSE` are not mutually exclusive: two distinct equal-`issued_at` manifests may also declare the same runtime key. Either diagnostic applies to that Stage 8 rejection; implementations that report a single code follow the within-stage precedence rule in §11. This does not create an acceptance alternative.

## Canary lifecycle

The publisher refreshes the canary by performing a publisher ceremony:

1. Generate a new `K_runtime` keypair offline. Set aside `K_runtime_priv` for transfer to the publishing infrastructure.

2. Compose a new canary object with:

   * `runtime_pubkey` set to the new `K_runtime.pub`;
   * `issued_at` set to the current UTC time;
   * `next_expected` set to a future UTC time within the permitted bounds;
   * `statement` set to the publisher's chosen warrant text;
   * `freshness_proof` set to the publisher's chosen proof, if any.

3. Compose a new manifest including this canary, as defined in §06.

4. Sign the manifest with `K_publisher`, as defined in §05.

5. Transfer the new `K_runtime_priv` to the publishing infrastructure according to the operator's key-custody procedure. Configure the infrastructure to sign new content and transaction documents with the new `K_runtime_priv`. Do not deploy the new manifest yet; the old manifest is still served and the previous `K_runtime` remains the announced runtime key. This step is reversible: if the operator decides to abort the ceremony before step 6, the signing configuration can be reverted to the previous `K_runtime_priv` and the previous manifest remains current at the published origin.

6. Deploy the new manifest at `/manifest.json`. Replace, do not amend, the existing manifest. From the instant the new manifest is served, clients verify content and transaction signatures against the new `K_runtime.pub` it announces. A signature-verification window is inherent to single-runtime-key rotation: clients holding a cached prior manifest verify against the previous `K_runtime.pub`, clients fetching the new manifest verify against the new `K_runtime.pub`, and the publisher's signing configuration can only point at one private key at a time. The reordering in this step list does not eliminate the window; it minimizes its duration when steps 5 and 6 are performed in immediate succession (ideally atomically) and ensures that the irreversible step (step 6, which commits the new manifest under anti-downgrade enforcement (§08:71, §06): once the new `canary.issued_at` is observed by any client, that client MUST NOT accept the previous manifest as current) is preceded by the reversible step (step 5), so a failure between steps 4 and 6 can be recovered without an anti-downgrade trap.

7. Destroy the previous `K_runtime_priv` according to the operator's key-custody procedure.

The frequency of this ceremony is determined by the publisher's chosen `next_expected` interval. A publisher who declares a 30-day interval performs this ceremony approximately every 30 days, with a margin to refresh before reaching `next_expected`.

The ceremony is the operational price of the canary mechanism. A publisher unwilling or unable to maintain ceremony cadence cannot maintain a fresh canary, and therefore cannot maintain the warrant property.

## What this section does not cover

This section defines the canary structure, its states, the required client behavior per state, anti-downgrade enforcement, and the canary lifecycle.

It does not define:

* the manifest schema in which the canary is embedded (see §06);
* the keys and signing primitives applied to the manifest (see §05);
* the document schema and envelope rules (see §02);
* canonicalization rules (see §04);
* block types displayed when rendering canary statements (see §03);
* the full client verification pipeline, including pipeline ordering, error precedence, clock-skew tolerance values, and chrome layout (see §10);
* error codes for canary failure conditions (see §11);
* operational practices for protecting `K_publisher_priv` during canary ceremonies (see operator playbook, outside the normative spec).
