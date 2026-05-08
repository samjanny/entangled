# 10 — Client behavior

This section defines what a conforming Entangled client does. It specifies the validation pipeline applied to every fetched document, the trust state machine governing publisher identity, the chrome elements that must be present, and the operational details (clock skew tolerance, parser limits, error precedence, refresh policy) referenced by earlier sections.

A conforming Entangled client is the entity that consumes signed documents from carriers, verifies them, and renders them safely. It is structurally distinct from a generic web browser. Its security properties depend on the disciplines defined here.

## Conformance scope

A conforming client MUST:

- implement the verification pipeline defined in this section, in the order defined;
- distinguish all four publisher trust states defined in this section;
- distinguish all five canary states defined in §08;
- provide chrome elements as defined in this section;
- enforce parser, schema, and resource limits defined in this section;
- create publisher identity observation records at first verified manifest, as defined below;
- never silently replace a pinned publisher identity;
- never automatically follow HTTP redirects;
- never implement cookie or ambient identifier semantics;
- never accept publisher-controlled content into chrome;
- maintain structural separation between chrome and content area.

A client that fails any of these requirements is not a conforming Entangled v1 client.

Browser extensions are not conforming Entangled v1 clients. Entangled v1 requires a client-controlled chrome/content separation that browser extensions do not provide as a normative substrate. A future conformance profile may define extension-based clients if a sufficient separation guarantee can be specified; v1 does not.

## Validation pipeline

Every Entangled document passes through a defined validation pipeline before it reaches the rendering stage or before its content is acted upon.

The pipeline applies to manifest documents, content documents, and transaction documents. Stages that depend on an already verified manifest are skipped or adapted for manifest documents themselves, as noted.

## Pipeline order

```text
Stage 1.  Transport-level checks
            - HTTP status code
            - Content-Type
            - Content-Length within bounds
            - response body retrieval

Stage 2.  Byte-level checks
            - byte size within document-kind cap
            - strict UTF-8 validation
            - no BOM

Stage 3.  JSON parsing
            - parser-enforced limits:
              - nesting depth: max 16
              - string length: max 100 KiB
              - array length: max 10000
              - object keys: max 256 per object
            - duplicate object member names: rejected

Stage 4.  Document kind discrimination
            - presence and primitive type of `spec_version`, `kind`, and `sig`
            - `spec_version` exactly "1.0"
            - `kind` is one of "manifest", "content", "transaction"

Stage 5.  Closed-schema validation
            - top-level field whitelist for the declared kind
            - all required fields present
            - no additional fields
            - per-field type, range, syntax, and length checks
            - nested object and array schema checks

Stage 6.  Signature verification
            - construct signed payload by removing top-level `sig`
            - JCS canonicalization
            - construct signature input with context string and 0x00 separator
            - Ed25519 verification

Stage 7.  Publisher identity and trust state resolution
            - for manifests: compare `publisher_pubkey` against the expected or observed `K_publisher.pub`
            - for content/transaction: ensure a relevant verified manifest exists
            - apply trust state transitions

Stage 8.  Canary and anti-downgrade resolution
            - for manifests: compute canary state from `issued_at` and `next_expected`
            - reject invalid canaries
            - apply anti-downgrade against publisher history

Stage 9.  Path and origin binding
            - for manifest: carrier origin binding, such as Tor v3 address derivation
            - for content: byte-exact comparison of `path` field against fetched path
            - for transaction:
              - byte-exact comparison of `in_response_to` against submit path
              - byte-exact comparison of `request_id` against the request_id sent
              - byte-exact comparison of `request_hash` against the locally
                computed JCS-hash of the submit body sent

Stage 10. Render or report
            - if all required stages pass, the document is rendered or processed
            - if any stage fails, an error is reported per the error precedence rule
````

For a manifest, the acceptance order is: transport, byte validation, JSON parsing, kind discrimination, schema validation, signature verification, publisher identity/trust resolution, canary validation, anti-downgrade, origin binding, then cache/update. A manifest is not accepted as current until all applicable stages have succeeded.

For content and transaction documents, the client must already have a relevant verified manifest before signature verification can succeed.

## Error precedence

Errors are reported in pipeline order. The first stage that fails determines the error reported to the user. Subsequent stages are not executed.

This rule is normative. A client that reports a "signature invalid" error on a document that fails the byte-size cap is non-conformant. The reported error must reflect the actual failure point, not a downstream consequence.

If a stage detects multiple violations within itself, for example schema validation finding two fields out of range, the client MAY report all of them within that stage, but MUST NOT proceed to subsequent stages.

## Stage details

**Stage 1: transport-level checks** are defined in §09. Status codes outside the whitelist, redirect responses, malformed `Content-Type`, missing required headers, or response-body retrieval failure fail at this stage.

**Stage 2: byte-level checks** are defined in §04. Byte caps are document-kind specific: 64 KiB for manifests (§06), 1 MiB for content and transaction documents (§02), and 64 KiB for submit bodies (§09).

**Stage 3: JSON parsing** uses parser-enforced limits to bound resource use before schema validation. The parser MUST refuse documents exceeding any limit and report a parse/input error rather than silently truncating.

**Stage 4: document kind discrimination** obtains the minimum information needed to select a schema for stage 5.

**Stage 5: closed-schema validation** is defined in §02 for content and transaction documents, and §06 for manifests.

**Stage 6: signature verification** uses the cryptographic primitives and signature input construction defined in §05.

For manifest documents, signature verification requires the expected publisher key. After stage 5 closed-schema validation, the client may safely read `publisher_pubkey` from the validated payload. The client then selects the expected verification key according to the trust-state rules below and in §05:

* if a retained publisher identity (TOFU-pinned or Externally verified) exists for the site or publisher profile and `manifest.publisher_pubkey` differs from the retained `K_publisher.pub`, the client reports `E_TRUST_MISMATCH`. The client MUST NOT silently replace the retained identity, MUST NOT treat the new key as authoritative, and MUST NOT continue to ordinary manifest acceptance. Trust-state resolution for the mismatch is governed by the trust state machine below;
* if the retained publisher identity matches `manifest.publisher_pubkey`, that retained `K_publisher.pub` is used as the expected verification key;
* if no retained identity exists for this site or publisher profile, the manifest is in First contact and `manifest.publisher_pubkey` is used as the candidate verification key.

Signature verification proceeds under the expected key selected by the trust-state rules. A signature failure under the correct expected key is reported as `E_SIG_VERIFICATION`. An identity mismatch detected by the rules above is reported as `E_TRUST_MISMATCH` and takes precedence over signature verification, because attempting to verify a manifest under a key that does not match the retained identity is not meaningful.

This manifest-specific sub-step preserves the pipeline model and error precedence: it occurs after stage 5 schema validation and before ordinary stage 6 signature verification, and uses only fields the schema has already validated.

For content and transaction documents, no equivalent pre-check is required: the verification key is `current_manifest.canary.runtime_pubkey` from the already-verified manifest.

**Stage 7: publisher identity and trust state resolution** produces one of the four publisher trust states defined below.

For manifest documents, the manifest-specific identity pre-check above has already detected mismatch with retained identity. Stage 7 resolution covers transitions for First contact, TOFU pinning, and external verification, and any further trust-state bookkeeping not handled by the pre-check.

**Stage 8: canary and anti-downgrade resolution** produces one of the five canary states defined in §08 and applies anti-downgrade rules based on publisher history.

**Stage 9: path and origin binding** prevents path-substitution and origin-substitution attacks.

**Stage 10: render or report** is where the client either commits the document to rendering/processing or surfaces an error to the user.

## Persistence ordering

A client MUST NOT persist any of the following until all applicable manifest validation stages have succeeded, including Stage 9 origin binding:

* publisher identity observations (first-contact records or new pins);
* TOFU pin transitions;
* canary acceptance into history;
* runtime authorization history entries;
* state policy acceptance;
* manifest cache entries.

In particular, a manifest whose signature verifies (Stage 6) but whose origin binding fails (Stage 9) MUST NOT cause any persistent record to be created or updated. The manifest is rejected as if no information had been observed.

This ordering rule applies uniformly to first-contact, TOFU-pinned, externally-verified, and changed/mismatch trust states.

In-flight per-submit state is excluded from this rule. The `request_id` and JCS-canonical submit body bytes that the client retains during an in-flight submit (see "Submit request identifiers") are transient in-memory state, not durable persistence. They are not publisher identity records, TOFU pins, canary history, runtime authorization, state policy acceptance, or manifest cache entries. Their retention before Stage 9 of the corresponding manifest fetch is not a persistence-ordering violation.

## Trust state machine

The client maintains trust state records for publisher identities and the origins from which they have been observed.

The four trust states are:

* **Externally verified**;
* **TOFU pinned**;
* **First contact**;
* **Changed/mismatch**.

These states are mutually exclusive for a given site/origin at a given time.

## Trust state meanings

### Externally verified

The user has confirmed `K_publisher.pub` by comparing the PIP displayed by the client against an out-of-band reference.

This is the strongest trust state. It means the user has anchored publisher identity outside the current carrier address.

### TOFU pinned

The client has previously observed and retained `K_publisher.pub` for the site or publisher profile, but the user has not externally verified it against a PIP.

TOFU pinned is continuity of observation, not external proof of identity.

### First contact

The client has verified a manifest for a publisher identity for which it has no prior retained record and no user-confirmed PIP.

The manifest signature verifies under the `publisher_pubkey` presented by the manifest, but the publisher identity is not yet known to the client.

### Changed/mismatch

The client has a retained publisher identity for the site or publisher profile, but a newly fetched manifest presents a different `K_publisher.pub`.

Even if the new manifest's signature verifies under the newly presented key, it does not verify against the retained identity. The client treats this as a possible identity replacement and enters Changed/mismatch.

## State transitions

```text
                    no retained record
                           |
                           v
                    First contact
                    /           \
                   /             \
          user confirms PIP   observation retained
                 |                 |
                 v                 v
        Externally verified     TOFU pinned
                 |                 |
                 | same            | same
                 | K_publisher     | K_publisher
                 v                 v
              no transition     no transition

        Any retained state, manifest presents different K_publisher.pub
                           |
                           v
                    Changed/mismatch
```

## Transition rules

### No record → First contact

When the client completes all applicable validation pipeline stages for a manifest from a site for which it has no previous retained publisher identity, the trust state is First contact. The client creates an observation record for the presented `K_publisher.pub` only after Stage 9 origin binding has succeeded.

Failed manifests do not create observation records. See "Persistence ordering" above.

The observation record is not yet an external verification. It is a retained observation used to detect later changes.

The client MUST display the First contact state in chrome and MUST display the PIP so the user can compare it against an out-of-band reference.

### First contact → TOFU pinned

The client SHOULD transition from First contact to TOFU pinned after the user explicitly chooses to continue to the site or after the first successful render of content from the site. The transition MAY also occur in response to other events such as dismissal of the first-contact notice. A client SHOULD document, in user-accessible form, the trigger it uses.

The transition MUST be visible to the user. The client MUST notify the user that the publisher identity has been retained for future mismatch detection.

The notification is informational, not a request for external trust. TOFU pinning records continuity of observation; it does not elevate the publisher to Externally verified.

A client in stateless mode MAY retain the observation only for the current session. In that case, TOFU pinning is session-scoped and MUST be presented as such.

### First contact or TOFU pinned → Externally verified

The user explicitly confirms `K_publisher.pub` against an out-of-band PIP reference.

The client provides a UI affordance for entering, scanning, or comparing a PIP. If the PIP resolves to the same `K_publisher.pub` presented by the manifest or retained record, the trust state becomes Externally verified.

The client records the verification timestamp.

### Retained identity → Changed/mismatch

A manifest fetched for a site with an existing retained identity presents a different `K_publisher.pub`.

The client MUST NOT silently replace the retained identity. The client MUST enter Changed/mismatch and display a prominent warning in chrome.

This rule applies whether the previous state was TOFU pinned or Externally verified. A changed externally verified identity is especially severe and MUST be presented as a high-risk identity mismatch.

### Changed/mismatch → resolved

The user resolves Changed/mismatch by one of two actions:

* abandon the site, preserving the existing retained identity;
* explicitly confirm the new `K_publisher.pub` as legitimate, replacing the retained identity.

If the user confirms the new identity, the client:

* replaces the retained identity for the affected site or publisher profile with the newly confirmed `K_publisher.pub`;
* treats the new identity as a new First contact, unless the user also externally verifies the new PIP, in which case the new identity enters the Externally verified state;
* on subsequent manifest fetches for the same site, signature verification proceeds with the new `K_publisher.pub` as the expected key under the trust-state rules in §05 and the manifest pre-check in stage 6 above. The `E_TRUST_MISMATCH` check then operates against the new retained identity;
* preserves the prior identity in publisher history as a replaced-identity event, retrievable through the publisher history detail surface defined under "Expandable detail surfaces" below.

The client MUST NOT offer an option that would automatically resolve future Changed/mismatch events.

## Multiple origins per publisher

A client MAY support publisher profiles that recognize the same `K_publisher.pub` across multiple authorized origins.

When supported:

* the client maintains a single publisher identity record keyed by `K_publisher.pub`;
* migration to a new origin signed by the same `K_publisher.pub` MUST NOT trigger Changed/mismatch solely because the address differs;
* migration to a new origin with a different `K_publisher.pub` triggers Changed/mismatch.

If publisher profiles are not supported, the client treats each origin as an independent site for trust-state purposes. Cross-origin migration by the same publisher is then treated as First contact at the new origin, unless the user externally verifies the PIP.

## Canary integration

The canary state, as defined in §08, governs additional client behavior beyond the publisher trust state.

## Canary state behavior

| Canary state    | Render content                                | Display in chrome                         |
| --------------- | --------------------------------------------- | ----------------------------------------- |
| Fresh           | Yes                                           | Compact: state + `next_expected`          |
| Near-expiration | Yes                                           | Compact, with visual emphasis             |
| Expired         | Yes                                           | Prominent warning, not easily dismissible |
| Invalid         | No                                            | Prominent error                           |
| Unavailable     | Cached content only, with explicit indication | Compact, with explanation                 |

Invalid canary state is a hard failure for current content. Expired canary state is not a hard failure by itself, but MUST be displayed prominently.

## Canary gap memory

If the client has observed an Expired canary for a publisher, and later observes a Fresh canary for the same `K_publisher.pub`, the client MUST notify the user that a canary gap occurred (§08).

The notification MUST persist until the user explicitly dismisses it. Dismissal does not erase the recorded gap from publisher history. Subsequent inspection of publisher history MUST show that a gap occurred and when.

## Anti-downgrade enforcement

A client MUST NOT accept a manifest as current when its canary `issued_at` is strictly older than the newest verified `issued_at` previously observed for the same `K_publisher.pub`.

This rule applies across origins, as defined in §08.

Anti-downgrade applies to current-publication acceptance. It does not invalidate cryptographically valid older manifests for historical content verification.

## Historical content

A content document signed by a `K_runtime` other than the one currently authorized by the current manifest is historical content.

## Verification requirement

Historical content MAY be rendered only if all of the following hold:

* the document signature verifies against a `K_runtime` that the client has previously verified as authorized for the same `K_publisher.pub` under a previous manifest or publication cycle;
* the relevant previous manifest or publication cycle is present in the client's publisher history;
* the current publisher identity is not in Changed/mismatch state;
* the path binding (§02) succeeds against the path from which the historical content was fetched.

A client MUST NOT treat a runtime key as historically authorized merely because a server presents an old manifest during the current fetch. Historical authorization is based on publisher history already verified by the client, or on historical-verification rules explicitly defined by a future version. Entangled v1 does not define server-provided historical manifest discovery.

A historical content document signed by a `K_runtime` the client has never observed as authorized for the same `K_publisher.pub` is rejected.

## Storage of authorization history

To support historical content, the client maintains, per `K_publisher.pub`, a list of previously authorized `K_runtime.pub` values and their authorization windows.

Each entry records:

* `K_runtime.pub`;
* the `issued_at` of the manifest in which it was first observed as the authorized runtime key;
* the `issued_at` of the manifest in which it was superseded, if known;
* the origin from which the manifest was fetched.

The client MAY bound this list to a reasonable cap. When the cap is reached, the client SHOULD evict the oldest entries first.

Evicting old authorization history may make some historical content unverifiable by that client.

## Verification key trial order

A historical content document is signed by a `K_runtime.pub` other than the one currently authorized by the manifest in effect for the publisher. The client verifies the document signature against retained runtime keys in its authorization history for the same `K_publisher.pub`.

The order in which retained `K_runtime.pub` entries are tried is implementation-defined. The recommended order is reverse chronological by the entry's first-observed `issued_at`, since most historical-content reads are for recently superseded runtimes.

The first retained `K_runtime.pub` under which the document signature verifies is the authorizing runtime key for the document. The corresponding authorization-history entry determines the `issued_at` displayed in the historical-content chrome marker.

If no retained runtime key verifies the document, the document is rejected with `E_HISTORICAL_NO_AUTHORIZATION` (§11).

If signature verification succeeds under more than one distinct retained `K_runtime.pub` for the same document — an outcome whose probability under Ed25519 is approximately `2^-256` and which therefore indicates a cryptographic anomaly, an implementation bug, or corruption in the authorization-history store — the client MUST reject the document and surface a client-implementation diagnostic. The document is not rendered. Entangled v1 does not assign a normative error code to this case; clients SHOULD log the condition for offline analysis.

## Historical content marker

When historical content is rendered, the client MUST display a clear marker in chrome indicating that the content is historical.

The marker:

* MUST be visually distinguishable from chrome elements applied to current content;
* MUST include the canary `issued_at` of the manifest under which the content was originally authorized;
* MAY include the elapsed time since that authorization;
* MUST NOT be hidable, replaceable, or modifiable by document content.

The user MUST be able to identify, at a glance, that they are viewing historical rather than current publication.

## Historical content does not affect canary state

Rendering historical content does not change the canary state of the site. The canary state reflects the current manifest, regardless of whether the user is viewing historical or current content.

## Chrome layout requirements

The chrome is the client-controlled UI surface defined in Pillar C. This section specifies its mandatory contents and structure.

## Always-visible compact indicators

The client MUST display, in a persistent and always-visible region of the chrome, at minimum:

* the publisher identity state: Externally verified, TOFU pinned, First contact, or Changed/mismatch;
* a compact representation of the current carrier address;
* the canary state: Fresh, Near-expiration, Expired, Invalid, or Unavailable.

The abbreviated carrier address form is implementation-defined, but MUST allow the user to distinguish the current address from other observed addresses.

The compact form MAY use icons, color coding, or short text labels. The visual treatment is implementation-defined; presence and persistence are normative.

## Expandable detail surfaces

The client MUST provide, accessible from the compact indicators by user action, expandable detail surfaces containing:

* the full Publisher Identity Phrase (PIP), as a 24-word phrase formatted for legibility;
* the full carrier address;
* the full canary structure: `issued_at`, `next_expected`, `statement`, and `freshness_proof` if present;
* publisher history: observed manifests, `issued_at` values, runtime keys, origins, canary gap notifications, and trust state change events;
* state items currently stored for the publisher: namespace, key, mode, value or safe representation, `expires_at`, and purpose;
* controls to delete individual state items;
* a control to delete all state for the publisher;
* a control to revoke remembered consent.

The expansion mechanism is implementation-defined.

PIP labeling.

The client MUST label the PIP as "publisher identity phrase", "publisher phrase", or an equivalent term that conveys public identity.

The client MUST NOT label the PIP using any of the following terms or their close synonyms: "seed phrase", "recovery phrase", "wallet phrase", "secret phrase", "private phrase", or any term suggesting private cryptographic material.

This rule prevents users from confusing the PIP with cryptocurrency wallet seeds (which use the same BIP-39 encoding for very different purposes) and from treating the PIP as secret material that must be hidden.

Localized translations of the label are permitted and encouraged. The labeling rule applies in spirit to translations: the chosen translation MUST convey "public identity" semantics, not "secret" or "recovery" semantics.

## Conditional always-visible warnings

The client MUST display, prominently and not easily dismissibly, when present:

* Changed/mismatch trust state warning;
* Expired canary warning;
* Invalid canary warning;
* canary gap notification, after a gap has been observed and not yet dismissed by the user;
* historical content marker, whenever historical content is rendered;
* stale cached content marker, when cached content is rendered while current canary state is unavailable.

These warnings are conditional: present only when the corresponding state holds. When present, they MUST be highly visible. They MUST NOT be replaceable, hidable, or modifiable from publisher-controlled content.

## Request state indicator

The client MUST display, in chrome, when a publisher has at least one stored request-state item that will be transmitted with future submit requests.

This indicator is conditional and present only when applicable.

The indicator MUST be visually distinguishable from the indicator for client-only state. The user MUST be able to identify, at a glance, whether the publisher has request state active for the current session.

## Chrome separation

The chrome MUST be structurally separated from the content area such that publisher-controlled content cannot:

* replace, hide, obscure, overlap, or modify chrome elements;
* use protocol-defined chrome labels, icons, placement, borders, colors, or visual treatments in a way likely to impersonate client-controlled status;
* cause user interaction with content to be interpreted as interaction with chrome;
* suppress, delay, or alter chrome warnings.

A document may contain ordinary text that includes words such as "verified", "warning", or "expired"; this is not by itself a violation. The violation is visual or interactional impersonation of client-controlled status.

A client implementation that fails to enforce chrome separation is non-conformant.

## Navigation and fetch flow

This subsection describes the high-level flow the client follows when the user navigates to a path on an Entangled site.

```text
on user navigation to URL <carrier_address>/<path>:

  if no manifest in cache for <carrier_address>:
    fetch /manifest.json
    pass through applicable stages of the validation pipeline
    if any stage fails:
      report error per error precedence
      abort
    create first-contact observation if no prior identity record exists
    apply trust state transitions
    cache manifest

  else if cached manifest is stale (min_refresh_interval elapsed,
                                     or canary next_expected passed,
                                     or user explicit refresh):
    fetch /manifest.json
    pass through applicable stages of the validation pipeline
    if any stage fails:
      report error per error precedence
      continue with cached state only where permitted
    apply anti-downgrade against publisher history
    update cache or transition to Changed/mismatch as appropriate

  fetch /<path>
    pass through applicable stages of the validation pipeline
    if any stage fails:
      report error per error precedence
      abort

  if document is current:
    render in content area
    update chrome with current trust and canary state

  if document is historical:
    if historical-content verification succeeds:
      render with historical content marker
    else:
      reject

  display chrome warnings as required by trust state, canary state,
  state indicators, and historical-content state
```

This flow is high-level. Implementations may vary in concurrency, prefetching, and caching specifics, subject to the constraints in §06, §08, and §09.

## Operational parameters

## Clock skew tolerance

The client uses a clock skew tolerance of 300 seconds, 5 minutes, for timestamp future-bound checks.

A timestamp is rejected as implausibly in the future when:

```text
timestamp > current_time + 300 seconds
```

This applies to:

* `manifest.updated`;
* `canary.issued_at`.

It does not apply to:

* `meta.published_at`, which is editorial metadata and not a freshness signal (§02);
* `canary.next_expected`, which is a future commitment by definition.

The 300-second tolerance is normative. A client using a different value is non-conformant.

When rejecting a timestamp because it exceeds the clock-skew tolerance, the client SHOULD indicate to the user that the local clock may be incorrect, since clock-skew failures are a likely cause of false positives on devices with unsynchronized clocks. The protocol-level diagnostic remains the one specified for the failing field (`E_CANARY_INVALID` for canary `issued_at`, `E_SCHEMA_FIELD_SYNTAX` for `manifest.updated`); the local-clock advisory is a user-presentation hint, not a separate diagnostic code.

## Editorial published_at display

`meta.published_at` (§02) is editorial metadata, not a freshness or security signal. The client MUST NOT reject a content document solely because `meta.published_at` is in the past or in the future relative to the client's clock.

If `meta.published_at` is significantly in the future relative to the client clock, the client MAY display a non-security editorial notice indicating that the document is post-dated by the publisher. The threshold and presentation of this notice are implementation-defined.

This editorial notice MUST NOT be confused with canary, trust-state, signature, or transport warnings. It is not a chrome warning of the kinds defined in this section. Its visual treatment MUST be distinct from the warnings listed under "Conditional always-visible warnings" above.

## Refresh policy

The client refreshes the manifest when at least one of the following holds:

* no manifest is cached for the carrier origin;
* `min_refresh_interval` (§06) has elapsed since the last successful manifest fetch;
* the cached manifest's canary `next_expected` has passed;
* the user has requested a refresh explicitly;
* a previous manifest verification failed and the client wishes to retry once;
* the trust state has changed, for example after Changed/mismatch resolution;
* the client suspects its cached manifest is stale, for example after observing a content document signed by a runtime key not in the cached manifest's canary or publisher history.

The client MUST NOT refresh more frequently than `min_refresh_interval` except in the conditions above.

Submit-time freshness.

Before sending a submit request, the client MUST ensure that the manifest used to authorize the submit endpoint, the `K_runtime` under which the eventual transaction will be verified, and the `state_policy` governing `request_state` is not stale. The manifest is considered fresh for submit purposes when:

* the cached manifest's canary state is Fresh or Near-expiration; and
* `min_refresh_interval` has not elapsed since the last successful manifest fetch.

If either condition fails, the client MUST refresh the manifest before transmitting the submit. If the refresh fails, the client MUST NOT transmit the submit and MUST surface the failure to the user.

This rule applies to every submit, regardless of whether the submit carries `request_state`.

## Submit request identifiers

For every submit, the client MUST generate a fresh `request_id` (§09) using a cryptographically secure random source. The client MUST NOT reuse `request_id` values across submits, including retries of a previously failed submit.

The client retains, for the duration of an in-flight submit, both the generated `request_id` and the JCS-canonical bytes of the submit body it sent, so that the Stage 9 transaction binding checks (`request_id` and `request_hash`, §02) can be performed against the originating submit. After the submit completes (success or failure), this retained material may be discarded.

## Parser limits

The client enforces, during JSON parsing in stage 3:

| Limit                  | Value   |
| ---------------------- | ------- |
| Nesting depth          | 16      |
| String length          | 100 KiB |
| Array length           | 10000   |
| Object keys per object | 256     |

A document exceeding any of these limits is rejected at parse time. The client does not partially parse.

These limits are normative unless a stricter field-specific or document-kind-specific limit applies, in which case the stricter limit wins.

A client allowing larger values for these parser limits is non-conformant.

The client also rejects, at parse time, any object containing duplicate member names, as defined in §04. The reported diagnostic is `E_PARSE_DUPLICATE_KEY` (§11).

Implementations SHOULD apply implementation-appropriate parser timeouts or cancellation limits.

## Rate-limit handling

When the publisher returns `429 Too Many Requests` (§09), the client MUST back off before retrying.

The back-off duration is implementation-defined; the protocol does not require a specific value.

The client MUST NOT retry aggressively in a tight loop. A client SHOULD apply exponential back-off with a reasonable initial value, typically 1 to 30 seconds.

The client MAY display a notice to the user when rate-limited, indicating that the publisher is throttling requests.

## Error reporting to the user

When a stage of the validation pipeline fails, the client surfaces an error to the user via chrome.

## Error categories

The client distinguishes among at least:

* transport errors: status code, network failure, carrier unreachable, redirect-not-supported;
* input errors: byte cap exceeded, invalid UTF-8, BOM present;
* parsing errors: malformed JSON;
* schema errors: closed-schema violation, kind mismatch, field range violation;
* signature errors: signature does not verify;
* trust state errors: Changed/mismatch;
* canary errors: Invalid canary, Expired canary warning, anti-downgrade rejection;
* binding errors: path mismatch, submit-path mismatch, origin mismatch;
* state errors: consent rejected, storage cap reached, state policy violation.

## Error display

For errors detectable before signature verification, including transport, input, parsing, schema, and kind mismatch errors, the client displays the error in chrome and does not render any content area for the failed document.

For errors detectable after signature verification but before rendering, including trust state, canary, and binding errors, the client displays the error in chrome with the additional context of which check failed.

For errors arising during rendering or user operation, including state consent rejection or storage cap reached, the client displays the error in chrome adjacent to the affected operation.

In all cases, the chrome's identity, address, and canary indicators reflect the actual current state. A failed fetch does not transiently change the trust state or canary state; the chrome shows the cached state plus the error.

## Specific error codes

The specific error codes assigned to each failure category are defined in §11.

## Stateless and reduced modes

A client MAY support modes with reduced functionality:

* **Stateless mode** (§07): state items are not persisted across sessions. Other state semantics apply normally during the session.
* **Read-only mode**: the client refuses all submit operations regardless of user input. Useful for archival viewers.
* **Externally-verified-only mode**: the client refuses to render content from sites in First contact or TOFU pinned trust states; only Externally verified publishers are accepted. Useful for high-threat users.
* **Expired-canary-block mode**: the client refuses to render current content from sites whose canary is in Expired state. Historical content rules are unaffected. Useful for users who want canary expiration to act as a hard block, not a warning.

When this mode is active, the client MUST display the mode in chrome, and the rendered content area is replaced by a clear notice that the canary is expired and rendering is blocked by client policy.

When a reduced mode is active, the client MUST display the mode in chrome.

A client MAY combine modes, for example read-only plus stateless. Interactions between modes are implementation-defined, but the active restrictions MUST be visible in chrome.

## What this section does not cover

This section defines client behavior: validation pipeline, trust state machine, canary integration, historical content, chrome layout, navigation flow, operational parameters, and error reporting framework.

It does not define:

* the document envelope structure (see §02);
* block types and rendering rules within blocks (see §03);
* canonicalization (see §04);
* key roles, signing, and verification primitives (see §05);
* the manifest schema (see §06);
* state policy and storage semantics (see §07);
* canary structure (see §08);
* HTTP transport (see §09);
* specific error codes (see §11);
* implementation-specific UX, layout, color, or interaction details, which are the implementation's responsibility within the constraints above.
