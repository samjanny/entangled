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

## Render dependence on manifest verification

The client MUST NOT render any document, any block, or any image or other resource referenced by a document, from a site, until a manifest signed by `K_publisher` for that site has been fully verified through the pipeline stages applicable to manifests: signature verification (Stage 6), publisher identity and trust-state resolution (Stage 7), canary validation and anti-downgrade (Stage 8), and carrier origin binding (Stage 9).

Rendering publisher-controlled content prior to manifest verification — even transiently, even as a "preview", even in response to explicit user navigation — is not conformant.

This rule is the load-bearing invariant of the Entangled trust model. The publisher trust state, the canary attestation, and the carrier origin binding all anchor on the manifest signature; rendering content without that anchor exposes the user to indistinguishable forged content. The MUST in §05 that "the verifier MUST have a valid manifest for the relevant site before verifying a content document" addresses the verification side of the same invariant; this rule extends it explicitly to the rendering side.

The rule applies symmetrically to content rendering, transaction-response processing for user-visible effect, image fetching, and any other action that turns publisher-controlled bytes into user-perceivable output. Image fetching is further constrained by §03: an image is fetched only after the containing content document has itself been verified.

The rule does not restrict chrome. Chrome elements — origin address, trust-state indicators, "loading" or transport-error reports, the manifest verification progress itself — are client-controlled and may be displayed at any time. The rule covers publisher-controlled content rendering, not chrome.

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
            - cross-field semantic checks declared by the owning
              section, including temporal-relation constraints
              between two fields (for example, the `origin.not_after`
              constraints in §06 against `canary.issued_at`)

Stage 6.  Signature verification (manifest: identity pre-check then
            Ed25519 verify; content/transaction: Ed25519 verify under
            current_manifest.canary.runtime_pubkey)
            - construct signed payload by removing top-level `sig`
            - JCS canonicalization
            - construct signature input with context string and 0x00 separator
            - Ed25519 verification

Stage 7.  Publisher identity and trust state resolution
            - for manifests: apply trust-state transitions for First contact,
              TOFU pinning, and external verification (mismatch detection and
              E_TRUST_MISMATCH already handled in the Stage 6 pre-check)
            - for content/transaction: ensure a relevant verified manifest exists
            - apply trust state transitions

Stage 8.  Canary and anti-downgrade resolution
            - for manifests: compute canary state from `issued_at` and `next_expected`
            - reject invalid canaries
            - apply anti-downgrade against publisher history

Stage 9.  Path and origin binding
            - for manifest: carrier origin binding, such as Tor v3 address derivation
            - for manifest, when `origin.not_after` is present: reject if the
              client's clock (within clock-skew tolerance) is at or after the
              declared instant
            - for manifest, when `migration_pointer` is present and the client
              supports publisher profiles: successor verification and chain-
              depth check
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

For manifests, Stage 9 also evaluates the optional `origin.not_after` field defined in §06. When present, a manifest whose declared `not_after` is at or before the client's clock (subject to the clock-skew tolerance defined under "Clock skew tolerance" below) is rejected as `E_ORIGIN_EXPIRED`. This check runs after carrier origin binding succeeds and uses only fields already validated at Stage 5. A manifest carrying an `origin.not_after` whose value violates the semantic constraints in §06 (`not_after` not strictly later than `canary.issued_at`, or more than 5 years after `canary.issued_at`) is rejected at Stage 5 as `E_ORIGIN_INVALID`; these are cross-field semantic checks per the Stage 5 definition above.

For manifests carrying a present `migration_pointer`, Stage 9 additionally performs the successor-verification and chain-depth checks specified under "Origin migration" below.

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

The client MUST NOT transition from First contact to TOFU pinned without an explicit affirmative response from the user to a pinning prompt presented by the client. Successful manifest verification, content rendering, dismissal of the first-contact notice, navigation away from the site, or any other passive event MUST NOT by itself cause the transition. Silent or render-triggered pinning is not conformant.

The client MAY render the first-contact content before presenting the prompt. Rendering the content does not constitute pinning. The prompt MAY be presented before, alongside, or after content rendering, at the client's discretion.

The pinning prompt MUST convey:

* that the publisher is being seen for the first time and has not been externally verified;
* that retention will cause the client to alert the user on future identity changes for this publisher;
* the action required to affirm retention and the action required to decline.

The default action of the prompt is implementation-defined. A client MAY default to "remember" in environments where TOFU continuity is the user's expected outcome, or default to "do not remember" in conservative or stateless environments. The protocol does not pin a default; the prompt itself is normative.

The transition MUST be visible to the user. After the user affirms retention, the client MUST notify the user that the publisher identity has been retained for future mismatch detection.

The notification is informational, not a request for external trust. TOFU pinning records continuity of observation; it does not elevate the publisher to Externally verified.

A client in stateless mode MAY retain the observation only for the current session. In that case, TOFU pinning is session-scoped, MUST be presented as such, and the explicit pinning prompt MAY be omitted in favor of a chrome indicator that the client did not retain the identity.

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

## Abandoning a retained publisher identity

Several resolution flows in this section and in §08 offer the user an "abandon retained publisher identity" action: the canary-conflict resolution control (§08), the Changed/mismatch "abandon the site, preserving the existing retained identity" action (above), and the high-threat-mode equivalents that may be exposed by a client.

The phrase "abandon the site, preserving the existing retained identity" in the Changed/mismatch resolution above refers to a narrower action that abandons the *current navigation* without altering the retained identity record. "Abandon retained publisher identity" is the broader action that severs the trust relationship itself. The two are distinct user actions and MUST be presented in chrome as distinct choices.

When the user invokes "abandon retained publisher identity" for the publisher keyed by `K_publisher.pub = P`, the client MUST:

1. delete the active trust-state record for `P`, including any TOFU-pinned or Externally verified state, the recorded set of authorized origins for the publisher profile, and any pending migration-history events that name `P` as the publisher key. Cached manifests for those origins become orphaned trust-anchored records and are evicted by the client's normal cache rules; the client MUST NOT use them as current after this step. After this step, the client no longer holds a retained identity for `P`;
2. record the abandonment in publisher history as a terminal event for that identity record. The history entry MUST preserve `P`, the timestamps and origins of the abandoned record, and the reason class (canary conflict, Changed/mismatch resolution, or user-initiated abandonment outside a resolution flow);
3. dissociate from `P` any authorized origins, including successor origins previously adopted under the publisher profile (§10 "Origin migration"). Those origins are no longer authorized origins for the publisher profile of `P`;
4. retain the authorization-history entries for any `K_runtime.pub` that was previously authorized under `P` only insofar as they remain useful for evaluating historical content under publisher-history rules in this section. The client MUST NOT use them to verify any new content fetched after the abandonment as if it were current publication for `P`.

After abandonment, a subsequent navigation to any origin that presents a manifest with `publisher_pubkey == P` is treated as First contact. The pinning prompt defined under "First contact → TOFU pinned" applies; passive transitions are forbidden. The user is responsible for deciding whether to re-establish a retained relationship with `P` and SHOULD be reminded, in the First contact prompt, that the same identity was previously abandoned. The client MUST surface, at the First contact prompt or in an adjacent always-visible chrome element on that navigation, that an abandonment record exists for the presented `K_publisher.pub`.

Abandonment is not retraction of historical content. Documents already rendered and stored locally as historical artefacts are not removed by abandonment. The act of abandonment changes the client's future-facing trust state, not the cryptographic validity of past observations.

A client MUST NOT silently re-establish a retained identity for an abandoned `K_publisher.pub`. Re-establishment requires the explicit affirmative First contact pinning sequence above; an externally verified PIP confirmation also satisfies the affirmative-action requirement and transitions the new record directly to Externally verified.

## Multiple origins per publisher

A client that retains trust state across sessions MUST support publisher profiles: a single publisher identity record keyed by `K_publisher.pub`, recognized across all authorized origins for that publisher. Cross-session retention without publisher-profile support fragments the user's identity model, because the same publisher reached at a new authorized origin appears as First contact and requires re-verification at every migration. A cross-session client that does not maintain publisher-profile records is not conformant.

A stateless client — one that retains no trust state across sessions, by user choice or by design — is exempt from publisher-profile support. A stateless client MUST present its statelessness clearly in chrome and treats each navigation as First contact regardless of carrier address.

When publisher profiles are supported:

* the client maintains a single publisher identity record keyed by `K_publisher.pub`;
* migration to a new origin signed by the same `K_publisher.pub` MUST NOT trigger Changed/mismatch solely because the address differs;
* migration to a new origin with a different `K_publisher.pub` triggers Changed/mismatch.

## Origin migration

A manifest's `migration_pointer` field, defined in §06, is the publisher's signed announcement of a successor carrier endpoint operated under the same `K_publisher`.

A client supporting publisher profiles MUST process a present `migration_pointer` as follows.

### Detection and chrome

When the verified manifest for a site contains a present `migration_pointer`, the client MUST display a migration notice in chrome. The notice MUST identify, at minimum:

* that the publisher has announced a migration;
* the successor address declared by `migration_pointer.successor_origin.address`;
* the announcement timestamp `migration_pointer.announced_at`.

The notice is informational chrome, not publisher-controlled content, and is subject to the chrome separation rules below.

### Successor verification

Before treating the successor origin as authoritative for the publisher, the client MUST:

1. fetch `/manifest.json` from `migration_pointer.successor_origin.address` over the carrier specified by `migration_pointer.successor_origin.carrier`;
2. apply the full validation pipeline (Stages 1 through 9) to the fetched successor manifest;
3. verify that `successor_manifest.publisher_pubkey` byte-equals the announcing manifest's `publisher_pubkey`;
4. verify, for Tor v3, that `successor_manifest.origin.address` byte-equals `migration_pointer.successor_origin.address` and that `successor_manifest.origin.origin_pubkey` byte-equals `migration_pointer.successor_origin.origin_pubkey`.

If any of these checks fails, the client MUST reject the migration announcement. The announcing manifest remains current at the announcing origin, but the successor is not adopted into the publisher profile. The diagnostic is `E_MIGRATION_MISMATCH` (§11). When the failure originates from the Stage 1 through 9 pipeline applied to the successor manifest itself (check 2 above) rather than from the migration-binding fields (checks 3 and 4), `details.mismatch_field` is set to `successor_stage9_failure` and `details.underlying_diagnostic_code` SHOULD carry the diagnostic code identifier (a string such as `"E_ORIGIN_EXPIRED"`) that the successor manifest's pipeline would have reported in isolation, to preserve debuggability for publisher operators (§11).

If all checks pass, the client adopts the successor origin into the publisher profile keyed by `K_publisher.pub`, and the successor manifest is treated as current for the successor origin under the standard caching rules.

### User confirmation

The strength of the user-confirmation requirement before automatically navigating to the successor origin, or before quietly migrating cached state from the announcing origin to the successor origin, depends on the trust state of the publisher identity at the announcing origin:

* if the announcing publisher's trust state is **Externally verified** or **TOFU pinned**, the client MUST obtain the user's affirmative confirmation before navigating to the successor origin and before migrating any cached state to it. "Affirmative confirmation" here means the user explicitly activates a dedicated chrome control (a button, key combination, or equivalent affordance whose semantics are unambiguously "accept the migration"); passive events MUST NOT count as affirmation, including but not limited to focus changes, mouseover, scroll, dismissal of unrelated UI, navigation away and back, and timeout-based auto-acceptance. The MUST is on both verification (defined above) and the user-confirmation step in the navigation flow; neither may be skipped, deferred, or assumed by passive event;
* if the announcing publisher's trust state is **First contact**, the client SHOULD obtain the user's confirmation. A First contact identity has not yet been pinned or externally verified, and the migration-confirmation dialog is informational rather than a continuity-preservation step; a client that omits the dialog for First contact MUST still display the migration notice in chrome.

The confirmation dialog for Externally verified and TOFU-pinned states MUST present both the announcing origin's address and the successor origin's address, the complete 24-word PIP of the publisher identity that signed the announcement, and the announcement timestamp `migration_pointer.announced_at`. The dialog MUST allow the user to accept the migration, decline the migration without changing the existing publisher profile, or open the publisher-history detail surface for context. A client MUST NOT default the dialog to a destructive choice; the user's affirmative action is required.

A client that has obtained the user's confirmation for a specific `(announcing_origin, successor_origin)` pair MAY proceed without re-prompting on subsequent navigations involving the same pair during the same trust-state lifetime. A trust-state lifetime for a publisher identity `P` begins when the client transitions `P` into a retained trust state (TOFU pinning at First contact, or Externally verified) and ends on any of: (a) the user invoking "abandon retained publisher identity" for `P` per the abandonment procedure above; (b) `P` reverting to First contact through Changed/mismatch resolution; (c) a user-initiated identity reset that clears the trust-state record for `P`. Trust-state lifetime has no implicit expiration timer; a retained identity persists across sessions until one of (a), (b), or (c) occurs. A new migration-confirmation prompt is required if the announcing manifest is replaced by a newer manifest with a different `migration_pointer.successor_origin` (see "Anti-downgrade and anti-forgery interaction" below), if the publisher's trust state transitions in a way that revisits identity continuity, or if the recall check defined under "Cross-session migration history" below names the successor as a previously-replaced address.

A client MAY auto-fetch the successor manifest in the background to perform verification before prompting the user, provided that fetching does not occur before the announcing manifest has itself been verified through Stage 9, and provided that no publisher-controlled content from the successor origin is rendered before the user has confirmed the migration. The user-confirmation requirement above is on the navigation and cached-state migration; it does not forbid the background verification fetch.

### Anti-downgrade and anti-forgery interaction

A migration announcement is signed under `K_publisher`. An attacker holding `K_origin_priv` for the announcing origin but not `K_publisher_priv` cannot forge a `migration_pointer` because they cannot produce a manifest signature.

An attacker who controls the network path to the announced successor address but does not hold `K_publisher_priv` cannot serve a manifest with a matching `publisher_pubkey`; the client's successor verification will fail at step 3 above.

If the announcing manifest is replaced by a newer manifest (later canary `issued_at`) that omits `migration_pointer`, the client MUST treat the migration as withdrawn. The successor origin previously adopted into the publisher profile remains adopted unless the user explicitly removes it through publisher-history controls; the announcement's withdrawal does not retroactively unbind a successfully verified successor.

If the announcing manifest is replaced by a newer manifest with a different `migration_pointer` (different `successor_origin`), the client MUST treat the new announcement independently: re-run successor verification for the new successor, prompt the user, and adopt only on success. Multiple successive migrations are allowed.

### Chain depth and cycle prevention

A `migration_pointer` chain is the sequence of origins reached by following the `migration_pointer` field across successive manifests within a single navigation. Without limits, a publisher could chain announcements `A → B → C → …`, and a client following them automatically would incur the full validation pipeline at every hop while obscuring from the user how many origins were traversed.

A client supporting publisher profiles MUST enforce both of the following rules per navigation:

1. **Automatic chain-depth limit.** A client MAY automatically adopt at most one `migration_pointer` hop without re-prompting the user when the announcing publisher's trust state requires user confirmation under "User confirmation" above. After one automatic adoption from announcer `A` to successor `B`, a further `migration_pointer` present on `B`'s manifest pointing to `C` MUST NOT be adopted in the same navigation flow without a new user-confirmation step, evaluated under the trust state of the publisher identity at `B` (which, since `B` adopted under the same `K_publisher.pub`, is the same publisher profile as `A`).
2. **Visited-origin cycle rejection.** The client MUST maintain, for the duration of a single migration-resolution flow, a set `visited_origins` containing the address of every origin visited in that flow, beginning with the announcing origin. Before adopting a successor announced by `migration_pointer.successor_origin.address`, the client MUST check that the address is not already present in `visited_origins`. A successor address already in `visited_origins` is a chain cycle and MUST be rejected as `E_MIGRATION_INVALID` with `details.reason = "chain_cycle"`.

The `visited_origins` set is per-navigation and per-publisher-profile. It is reset when the migration-resolution flow ends (whether by successful adoption, user decline, or rejection at any pipeline stage). It is not persisted across sessions and does not interact with publisher history.

The chain-depth limit applies to *automatic* hops only. A user who, after the chain-depth limit is reached, explicitly confirms the next hop under the user-confirmation rules above resets the automatic chain-depth counter to zero for that confirmed hop's flow. A client MAY expose a high-threat mode in which the automatic chain-depth limit is zero, requiring user confirmation for every hop regardless of trust state.

When the chain-depth limit is reached without user confirmation, the client treats the deeper successor as "pending user action": the announcement is displayed in chrome (per "Detection and chrome" above), but the client MUST NOT automatically navigate, MUST NOT fetch publisher-controlled content from the deeper successor, and MUST NOT migrate cached state to it. The migration remains pending until the user invokes the confirmation control or the announcing manifest's chain changes (replacement, withdrawal, or replacement of the deeper announcement).

When a successor address is rejected as a chain cycle under the `visited_origins` rule, the publisher profile retains the most recently verified successor adopted earlier in the same migration-resolution flow as the current origin; the flow's root origin remains accessible through publisher-history controls. Future fetches addressed at any origin in `visited_origins` MAY use that origin's cached manifest if one is held and is still within its refresh policy; the cycle rejection invalidates the new migration adoption, not the prior verifications.

A `migration_pointer` whose `successor_origin.address` equals `origin.address` is already ill-formed at the manifest layer (§06) and is rejected at Stage 5 as part of `migration_pointer` validation; it does not reach the chain check.

### Cross-session migration history

The `visited_origins` set defined under "Chain depth and cycle prevention" is per-flow and per-navigation, not persisted across sessions. A publisher under the same `K_publisher` who alternately announces address `A → B` in one session and `B → A` in a later session can therefore force a client to re-traverse the migration on every fresh navigation, since each new flow begins with an empty `visited_origins`. For First-contact identities, where one automatic migration hop is permitted without a user-confirmation prompt under "User confirmation" above, this re-traversal can be silent.

The vector is most concerning when an attacker has temporarily compromised `K_publisher_priv` and used the window to publish a self-cancelling migration loop: even after the publisher recovers control of the keys, every cached client continues to ping-pong between the two announced addresses on each session until a user explicitly intervenes.

To raise friction on this vector, a client SHOULD record migration outcomes in publisher history, keyed by `K_publisher.pub`. The recorded events are:

* **Adoption.** A successor address that the client adopted into the publisher profile under "Successor verification" above. The record SHOULD preserve the announcing origin address, the successor origin address, the announcement timestamp `migration_pointer.announced_at`, and the local timestamp at adoption.
* **Replacement.** Recorded in two situations: (a) when an Adoption is recorded for a successor `S`, the address that was the publisher profile's current origin immediately before that Adoption (the announcing origin) is recorded as Replacement at that time; (b) when a previously adopted successor address is itself superseded by a newer migration announcement (per "Anti-downgrade and anti-forgery interaction" above), that address is recorded as Replacement at that time. The dual recording is required so that the cross-session ping-pong vector `A → B → A → B` is detectable in both directions: case (a) ensures the starting origin `A` appears as "previously replaced" the first time the publisher migrates from it, even though `A` was never itself a successor in any earlier event. The Replacement record SHOULD preserve the replaced address, the replacing address (when known — for case (a) this is the new successor; for case (b) this is the new replacing successor), and the local timestamp at replacement.

When processing a new migration announcement that names successor address `S` for the publisher profile keyed by `P = K_publisher.pub`, a client that maintains migration history SHOULD consult publisher history for `P` and check whether `S` appears as a previously-replaced successor within a recall window. The recommended recall window is 30 days. A client MAY make the window configurable; the minimum SHOULD be 7 days. A window of zero (no recall) is permitted but discouraged because it disables the mitigation entirely. The recall window SHOULD NOT exceed 365 days; clients with bounded storage MAY enforce a smaller cap, whether by time or by event count (for example, the most recent 100 migration events per publisher profile, evicting the oldest first), provided the cap remains at or above the 7-day floor.

If `S` is in the recall window as a previously-replaced successor for `P`, the client SHOULD treat the migration with elevated friction:

* For trust states **Externally verified** and **TOFU pinned**, the user-confirmation requirement under "User confirmation" above already applies; no additional behavior is required, but the confirmation dialog SHOULD surface the recall information, including the prior replacement timestamp and the address pair involved.
* For trust state **First contact**, where automatic adoption of one hop is otherwise permitted under "Chain depth and cycle prevention" above, the client SHOULD instead require explicit user confirmation before adopting `S`, presenting the recall information.

The mitigation is SHOULD-level rather than MUST because v1 does not specify the storage backend for publisher history beyond what is already required for trust-state continuity, and this subsection introduces a new event class within publisher history. Implementations that do not maintain migration history are not non-conformant; they leave the cross-session ping-pong vector open as documented in §00 "v1.0 limitations".

`visited_origins` (per-flow) and migration history (per-publisher, persistent) are independent mitigations: the former rejects intra-flow cycles outright as `E_MIGRATION_INVALID`; the latter raises friction on cross-session cycles without rejecting them, since a publisher rotating between addresses for legitimate operational reasons must remain reachable. Migration history never causes outright rejection; the diagnostic outcome of a cross-session cycle, when the user declines, is simply that the migration is not adopted in the current navigation, identical to any other declined migration.

### Refusal scope

A client that does not support publisher profiles MAY ignore `migration_pointer`. In that case, navigation to the successor origin presents as First contact, with all attendant re-verification requirements.

A client that supports publisher profiles but is operating in a mode that disables in-band migration (for example, a high-threat mode) MAY ignore `migration_pointer` and require the user to navigate to the successor origin out of band. The client MUST display, in chrome, that an announcement was present and that automatic migration is disabled.

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

If signature verification succeeds under more than one distinct retained `K_runtime.pub` for the same document — an outcome whose probability under Ed25519 is approximately `2^-256` and which therefore indicates a cryptographic anomaly, an implementation bug, or corruption in the authorization-history store — the client MUST reject the document and surface `W_HISTORICAL_RUNTIME_AMBIGUOUS` (§11). The document is not rendered. Clients SHOULD log the condition for offline analysis.

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

## PIP display requirements

When the client displays the PIP for user verification — at First contact, during Changed/mismatch resolution, in expandable detail surfaces, or anywhere a user is being asked to compare publisher identity against an out-of-band reference — the client MUST display the complete 24-word phrase.

The client MUST NOT display only a prefix, only a suffix, only selected words, or any "first-N + last-M" pattern as a substitute for the full PIP. Truncated or partial PIP displays are not conformant. A 24-word BIP-39 PIP encodes the full 256-bit `K_publisher.pub` plus an 8-bit checksum; any display short of the full phrase reduces the work an attacker must do to grind a `K_publisher` whose PIP collides with the displayed prefix or suffix.

The client MAY format the 24 words across multiple lines, in a numbered grid, with grouping separators, or with other layout treatments that aid legibility. The MUST is on completeness and legibility, not on a specific layout.

The client MAY collapse the PIP behind a user-action affordance (such as an "expand" control) in surfaces where space is limited, but the user-action expansion MUST reveal the full 24 words without further truncation. A collapsed PIP MUST NOT be the only representation shown when the user is being asked to perform identity verification or mismatch resolution.

## Conditional always-visible warnings

The client MUST display, prominently and not easily dismissibly, when present:

* Changed/mismatch trust state warning;
* canary conflict warning, after `E_CANARY_CONFLICT` (§08) has been observed for the publisher and not yet resolved by the user;
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

The same 300-second tolerance applies symmetrically to past-bound checks, where the timestamp is a publisher-declared expiration and the protocol concern is whether the present moment has passed it.

A timestamp is rejected as past the declared instant when:

```text
current_time > timestamp + 300 seconds
```

This applies to:

* `origin.not_after` (§06).

The symmetric tolerance gives the publisher a margin to publish a successor manifest near the declared instant without producing a brief window during which clients with slightly fast clocks reject the still-current manifest. Beyond the tolerance window, the rejection is hard: the manifest is treated as origin-expired per §06 and §10 Stage 9.

When rejecting a timestamp because it exceeds the clock-skew tolerance (in either direction), the client SHOULD indicate to the user that the local clock may be incorrect, since clock-skew failures are a likely cause of false positives on devices with unsynchronized clocks. The protocol-level diagnostic remains the one specified for the failing field (`E_CANARY_INVALID` for canary `issued_at`, `E_SCHEMA_FIELD_SYNTAX` for `manifest.updated`, `E_ORIGIN_EXPIRED` for `origin.not_after`); the local-clock advisory is a user-presentation hint, not a separate diagnostic code.

For `manifest.updated` future-skew rejection specifically, the `details` field of the structured `E_SCHEMA_FIELD_SYNTAX` diagnostic SHOULD include `reason: "future_beyond_skew_tolerance"` and the offending timestamp, to distinguish this temporal-domain failure from lexical RFC 3339 violations.

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

When Expired-canary-block mode is active, the rendered content area is replaced by a clear notice that the canary is expired and rendering is blocked by client policy.

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
