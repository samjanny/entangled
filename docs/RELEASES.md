# Release engineering

This document describes the release engineering conventions for the Entangled specification repository. It is not part of the protocol specification.

## Tag naming

Tags follow these patterns:

| Type | Format | Example |
|---|---|---|
| Release candidate | v\<MAJOR\>.\<MINOR\>-rc.\<N\> | v1.0-rc.1, v1.0-rc.2 |
| Final release | v\<MAJOR\>.\<MINOR\> | v1.0, v1.1 |
| Patch release (spec text only) | v\<MAJOR\>.\<MINOR\>.\<PATCH\> | v1.0.1, v1.0.2 |

All tags use a leading "v". The release-candidate suffix uses a dot before the number ("rc.1", not "rc1") for consistency with the semver-style pre-release format.

Tag uniqueness is normative: a tag once published is immutable. To correct a mistaken tag, create a new tag with a new name; do not rewrite or move existing tags.

## Release types

### Release candidate

A release candidate marks a state in which the specification is considered substantially complete and ready for community review, but is not yet final. Multiple rc tags are expected during stabilization.

Each rc must have a corresponding entry in the repository describing what changed since the previous tag.

### Final release

A final release marks a stable specification version. After a final release, the specification text for that version is frozen except for patch releases that correct errors without changing protocol behavior (see §11 for the spec release rules).

### Patch release

A patch release corrects errors in the specification text without changing wire-format behavior, validation rules, error codes, or cryptographic primitives. Patch releases follow the rules in §11 "Spec release".

## Release process

1. Apply substantive changes via pull request review or direct commits to the main branch.
2. Verify cross-references and run any available automated checks.
3. Update this file's release notes section if applicable.
4. Tag the commit with the appropriate name from the table above.
5. Push the tag to the origin remote.
6. Verify the tag appears in the repository tag list.

Tag deletion is reserved for accidental or malformed tags only and requires explicit communication if the tag has been published or referenced externally.

## Release notes

Release notes for each tag are added below as releases are made. Newest entries first.

### v1.0-rc.13

Date: 2026-05-10

Changes since v1.0-rc.12:

This rc lands the audit-driven hardening tranche split into two batches: tightening of `MAY`/`SHOULD` to `MUST` in §10 and §08 (Lotto 1, patch-level, no schema change), and additive features in §06, §08, §04, and the corpus (Lotto 2, additive, schema and diagnostic-catalog changes).

**Lotto 1 — patch-level tightening (§10, §08, §01)**

- §10 First contact → TOFU pinned (W18) — Strengthened to `MUST` an explicit affirmative pinning prompt. Successful manifest verification, content rendering, dismissal of the first-contact notice, navigation away, or any other passive event MUST NOT cause the transition. The client MAY render the first-contact content before presenting the prompt; rendering does not constitute pinning. The prior `SHOULD` form, which permitted "first successful render" to trigger the transition, is removed: a client that pins on first render is now non-conformant.
- §10 PIP display requirements (W11/W12) — New normative subsection. The client MUST display the complete 24-word PIP at First contact, during Changed/mismatch resolution, in expandable detail surfaces, and anywhere the user is being asked to compare publisher identity against an out-of-band reference. Truncated, prefix-only, suffix-only, or "first-N + last-M" displays are not conformant. A 24-word BIP-39 PIP encodes the full 256-bit `K_publisher.pub` plus an 8-bit checksum; partial display reduces attacker grinding cost.
- §10 Multiple origins per publisher (W23) — `publisher_profile` strengthened to `MUST` for clients that retain trust state across sessions. A cross-session client without publisher-profile records is not conformant. Stateless clients are exempt and MUST present their statelessness in chrome.
- §10 Render dependence on manifest verification — New consolidated `MUST` (formerly distributed across §05, §06, §10): no document, block, or referenced resource is rendered until manifest signature, trust-state, canary, and origin-binding stages have completed. Chrome elements (origin, loading indicator, transport errors, verification progress) are exempt; the rule covers publisher-controlled content.
- §10 Conditional always-visible warnings — Added canary conflict warning entry to the chrome warnings list; persists until the user resolves it.
- §08 Equal `issued_at` conflict (W7) — Reframed `E_CANARY_CONFLICT` as a fault condition on the publisher identity, not a recoverable transient error. The client MUST NOT pick a deterministic "winner" between conflicting manifests by lexicographic comparison, payload size, `runtime_pubkey` value, or any other tiebreaker over manifest content; a deterministic tiebreaker is gameable by an attacker holding `K_publisher_priv` and would mask the underlying fault. The retained pre-conflict manifest stays in place for current rendering and anti-downgrade; the conflict is surfaced as a prominent chrome warning analogous to Changed/mismatch, with an option to abandon the retained publisher identity. The warning persists until the user explicitly resolves it.
- §01 — Publisher profile glossary entry now notes the conditional `MUST` for stateful clients.

**Lotto 2 — additive (§06, §10, §11, §04, §08, §02, §00, §01, corpus)**

- §06 `migration_pointer` (W22) — New optional top-level manifest field. The publisher's signed announcement of a successor carrier endpoint operated under the same `K_publisher`. When present, contains exactly `successor_origin` (mirrors `origin` schema, with `successor_origin.address` MUST differ from `origin.address` and `successor_origin.carrier` MUST equal `origin.carrier`) and `announced_at` (RFC 3339 UTC, MUST NOT be later than `updated`). Absent when no migration is announced; per §04 no-`null` discipline, encoded by omitting the field rather than by a `null` value.
- §10 Origin migration handling — New subsection. A client supporting publisher profiles MUST detect a present `migration_pointer`, display a chrome migration notice, fetch the successor manifest from `successor_origin.address`, apply Stages 1–9, and verify that `successor_manifest.publisher_pubkey` byte-equals the announcing manifest's `publisher_pubkey`. On match, the successor origin is adopted into the publisher profile. On mismatch, the announcement is rejected as `E_MIGRATION_MISMATCH`. The client SHOULD obtain user confirmation before automatic migration; a strict-mode client MAY refuse in-band migration and require out-of-band navigation, but MUST display in chrome that an announcement was present.
- §11 — Added `E_MIGRATION_MISMATCH` and `E_MIGRATION_INVALID` to the Binding diagnostics (Stage 9) catalog. `E_MIGRATION_MISMATCH` SHOULD include in `details` the announced successor address, the successor and announcing publisher keys, and the specific mismatch field. `E_MIGRATION_INVALID` covers structural well-formed but semantically invalid announcements (successor equals announcing, `announced_at` after `updated`, carrier mismatch).
- §04 Unicode normalization for user-visible strings (W6) — New normative subsection. JSON string fields whose values the client renders to the user as text MUST be encoded in NFC (Unicode Standard Annex #15). Non-exhaustive list: `canary.statement`, `meta.title`, manifest `navigation` `label`, `state_policy` `purpose`, and every block text content span and string field rendered to the user including `link.label`, `image.alt`, `code_block.content`, `feedback.statement`, `note.statement`, `submit_form` labels and option labels. NFD, NFKC, NFKD are not permitted forms. Non-NFC values rejected with `E_SCHEMA_FIELD_SYNTAX` at schema validation, before signature verification. Implementations MUST NOT silently re-normalize: re-normalization would alter the JCS canonical bytes and break the publisher's signature.
- §02 Closed-schema discipline — Made the optional-fields semantics explicit: a field is optional only if its owning section designates it optional; only fields explicitly listed (required or optional) may appear at the top level; absent values are encoded by omitting the field, never by `null`. Required for `migration_pointer` to land cleanly in the closed schema.
- §08 `freshness_proof` signaling and strict policy (W4) — Added "Client signaling on absence": the chrome MUST signal whether the current canary includes a `freshness_proof`; absence MUST NOT be silently treated as equivalent to presence. Added "Strict freshness policy": a client MAY operate in a mode that rejects manifests whose canary omits `freshness_proof`, with chrome treatment analogous to Invalid canary state. Strict policy is client-side configuration, not a manifest declaration.
- §00 — Replaced "No in-band origin migration discovery" entry with "In-band origin migration is publisher-initiated only", reflecting `migration_pointer`. Pre-existing publisher cache without a prior announcement still requires out-of-band recovery.
- §01 — Added "Migration pointer" glossary entry; updated "Manifest" entry to list `migration_pointer` among manifest fields.
- corpus — Added 4 new vectors:
  - `154-sig-non-canonical-r`: signature whose R has a non-canonical compressed encoding (y portion 2^255 − 1, exceeds the field prime). Strict profile rejects with `E_SIG_VERIFICATION` independently of the verification equation.
  - `155-sig-non-canonical-a`: `publisher_pubkey` with the same non-canonical encoding. Strict profile rejects with `E_SIG_VERIFICATION` before signature check.
  - `181-canary-issued-at-downgrade`: manifest with `canary.issued_at` strictly older than a previously verified manifest (001) for the same `K_publisher.pub`. Anti-downgrade rejects with `E_CANARY_DOWNGRADE`.
  - `190-unicode-nfd-statement`: manifest whose `canary.statement` contains a decomposed combining mark (NFD: `Cafe` + U+0301) instead of the precomposed NFC form. Schema validation rejects with `E_SCHEMA_FIELD_SYNTAX` before signature verification.
- `corpus/corpus.json` — `rc_target` bumped from `"1.0-rc.12"` to `"1.0-rc.13"`. Total vectors: 32 (was 28). The original 28 vectors are unchanged byte-for-byte: rc.13 schema and §10 changes are additive (the optional `migration_pointer` field is omitted in all existing vectors) or behavioral additions that do not affect their verdicts.

**Diagnostic catalog summary.** Two new error codes: `E_MIGRATION_MISMATCH`, `E_MIGRATION_INVALID`. No existing code is renamed or has its semantics changed. Implementations consuming the rc.12 catalog need to add the two new codes; existing codes are otherwise unchanged.

**Wire format summary.** The wire-level `spec_version` remains `"1.0"`. The closed-schema top-level field set for manifests gains one optional field (`migration_pointer`); content and transaction documents are unchanged. JCS canonicalization is unchanged. NFC validation is an input restriction at schema time, not a canonicalization rule. Manifests omitting `migration_pointer` validate identically under rc.12 and rc.13. A manifest carrying a present `migration_pointer` is rejected by rc.12 clients (which see it as an unknown top-level field and fail closed-schema discipline) and accepted by rc.13 clients.

### v1.0-rc.12

Date: 2026-05-09

Changes since v1.0-rc.11:

- §00 — Added a new v1.0 limitation entry, "No retroactive revocation of historical content," disclosing that the protocol does not distinguish documents signed before from documents signed after a `K_runtime` compromise within the same authorization window. Historical content signed by an attacker who held the compromised key during its authorization window is indistinguishable from legitimate publisher content at the protocol level.
- §05 — Extended the `K_publisher` compromise subsection in "Compromise summary" with an explicit paragraph on identity retirement: Entangled has no in-band way to retire a publisher identity key while keeping the corresponding PIP attributable. Operators who wish to permanently decommission an identity SHOULD destroy `K_publisher_priv`; the protocol cannot distinguish "publisher stopped publishing" from "publisher resumed under attacker control after a long pause."
- Repo — Added `.gitattributes` enforcing LF on `*.json`, `*.md`, and `*.py` to keep the corpus byte-for-byte reproducible across platforms. The corpus generator's `keys.json` and `corpus.json` writes were converted from `write_text` to `write_bytes` with an explicit UTF-8/LF terminator as a defensive layer in case `.gitattributes` is bypassed (e.g., editing on Windows without Git filters active). Existing `corpus/keys.json` and `corpus/corpus.json` regenerated to match.
- docs/RELEASES.md rc.11 entry — Retroactively added three bullets for changes that landed in rc.11 but were omitted from the rc.11 release notes: the §03 citation external-handoff paragraph, the README missing carrier-link bullet, and the README repo-layout and corpus documentation. No spec text was modified by this release-note correction; it is a tracking fix only.
- `corpus/corpus.json` — `rc_target` bumped from `"1.0-rc.11"` to `"1.0-rc.12"`. The 28 input vectors and their expected verdicts are unchanged byte-for-byte; the rc.12 spec changes since rc.11 are additive disclosures and do not affect any existing vector's outcome.

This rc adds no new diagnostic codes, changes no existing diagnostic semantics, and makes no wire-format or signature-input changes. Two new spec-text entries are added — one §00 limitation and one §05 compromise-summary clarification — both purely additive disclosures that codify behavior already implicit in the protocol. Repo housekeeping fixes the corpus reproducibility regression on mixed-platform clones and corrects the rc.11 release-note coverage. The wire-level `spec_version` remains `"1.0"`. The deferred rc.10 corpus follow-up — vectors exercising `E_SCHEMA_DUPLICATE_ENTRY` and `W_HISTORICAL_RUNTIME_AMBIGUOUS` — is still pending and is tracked separately from this rc.

### v1.0-rc.11

Date: 2026-05-09

Changes since v1.0-rc.10:

- §00 — Added a new v1.0 limitation entry, "Diagnostic stage selection is not constant-time." The validation pipeline in §10 emits diagnostics keyed to the first failing stage, and the structured diagnostic itself names that stage (§11). A natural sequential implementation therefore exhibits observable timing differences across rejection causes, and the diagnostic is itself an explicit channel. A passive observer with timing access, or any consumer of the structured diagnostic, may infer information about a document's failure mode. Entangled v1 does not require constant-time diagnostic emission and does not place this in the protocol's threat model. Whether a future protocol version should constrain this side channel is acknowledged as open and may be revisited.
- §03 — Added a citation handoff trust-boundary callout. After the existing external-handoff sentence, a paragraph notes that opening a citation transmits the URL to a browser and a network outside Entangled's carrier; the destination operators, any in-path clearnet observer, and the chosen browser may learn that the URL was reached from the user's local environment, along with whatever metadata each layer collects. SHOULD-level UX guidance: the handoff mechanism should make this trust boundary visible before navigation proceeds. The wire schema, the existing MUSTs around citation handling (no auto-navigation, distinct display, no request state), and the HTTPS-only / no-`http://`-permitted rule are unchanged.
- README — Added the `carrier` link kind to the "Links are explicitly typed" list, alongside `same_site`, `entangled`, and `citation`. The README description matches §03's no-auto-navigate + external-handoff treatment for `carrier`. The kind has been defined in §03 since the carrier-link work; the omission predated rc.11.
- README — Repository structure listing now names `corpus/` (with a sub-tree pointer to `corpus/README.md`) and `docs/RELEASES.md`. The omission predated rc.11 and was carried over from the pre-corpus README.
- Corpus — Added `publisher.pip` to `corpus/keys.json`: the 24-word Publisher Identity Phrase derived from `publisher.pub_b64u` per §05 (BIP-39 English wordlist over the raw 32-byte public key with an 8-bit SHA-256 checksum). An implementation deriving PIPs MUST produce the same string for this public key. The canonical BIP-39 English wordlist is bundled at `corpus/tools/bip39_english.txt` (sourced from `bitcoin/bips: bip-0039/english.txt`, SHA-256 `2f5eed53a4727b4bf8880d8f3f199efc90e58503646d9ff8eff3a2ed3b24dbda`); `compute_pip()` and `load_bip39_wordlist()` helpers are added to the generator. The expected PIP value was cross-verified byte-for-byte against an independent BIP-39 reference implementation.
- Corpus — Added a normative paragraph to `corpus/README.md` describing how negative vectors are constructed: after all earlier stages pass cleanly, exactly one diagnostic-relevant violation is intended to be live at the first failing stage. This is the principle that drove the rc.9 fixes for vectors 132 and 142 and the rc.9 reclassification of 151; it is now stated explicitly as a corpus design rule so that future tranches preserve diagnostic determinism.
- Corpus — Strengthened the docstring on `corpus/tools/generate.py`'s `jcs()` helper, which is currently a thin wrapper over Python's `json.dumps(sort_keys=True, separators=(",", ":"), ensure_ascii=False)`. The new note enumerates the specific edge cases — non-ASCII member names (UTF-16 vs codepoint sort order divergence), non-integer numerics (RFC 8785 §3.2.2.3 ECMA-262 number serialization), and Python-specific escaping divergences — that require replacing the helper with a verified RFC 8785 implementation before the corpus can grow to cover them. No current vector exercises any of those cases, so the bundled `jcs()` is sufficient for the rc.11 corpus.
- `corpus/corpus.json` — `rc_target` bumped from `"1.0-rc.9"` to `"1.0-rc.11"` to reflect that the corpus is now consistent with both the rc.10 spec-text fixes and the rc.11 §00 limitation and PIP additions. The 28 input vectors and their expected verdicts are unchanged byte-for-byte from rc.9; the rc.11 spec changes since rc.9 are additive and do not affect any existing vector's outcome.

This rc adds no new diagnostic codes, changes no existing diagnostic semantics, and makes no wire-format or signature-input changes. The wire-level `spec_version` remains `"1.0"`. The deferred rc.10 corpus follow-up — vectors exercising `E_SCHEMA_DUPLICATE_ENTRY` and `W_HISTORICAL_RUNTIME_AMBIGUOUS` — is still pending and is tracked separately from this rc.

### v1.0-rc.10

Date: 2026-05-09

Changes since v1.0-rc.9:

- §11 — Moved `E_TRUST_MISMATCH` and `E_TRUST_USER_REJECTED` from "Trust state diagnostics (Stage 7)" to a new heading "Trust state diagnostics (Stage 6 manifest pre-check and Stage 7 resolution)". The diagnostic codes themselves are unchanged in spelling and semantics; only the catalog grouping and the `stage` field of structured diagnostics for these two codes change (from `7` to `6`). `I_TRUST_FIRST_CONTACT`, `I_TRUST_TOFU_PINNED`, and `I_TRUST_VERIFIED` remain Stage 7 transitions. This resolves the prior contradiction between §10's pre-check description and §11's Stage 7 grouping. The catalog framing sentence at the top of §11 is updated to note the Trust state group's Stage 6/7 span.
- §10 — Added an inline note to the Stage 6 line of the pipeline summary clarifying that manifest signature verification has two sub-steps (identity pre-check then Ed25519 verify), while content/transaction signature verification uses `current_manifest.canary.runtime_pubkey`. Aligned the Stage 7 summary line to describe only First contact / TOFU pinning / external-verification transitions (mismatch detection is handled in the Stage 6 pre-check). The detailed Stage 6 and Stage 7 prose is unchanged.
- §06 — Replaced the redundant restatement of path-syntax bullets in the navigation `path` constraint with a pure reference to §02, including the reservation of `/manifest.json` (which the prior restatement omitted). The local cross-host/cross-origin/absolute-URL prohibition sentence is preserved.
- §09, §10 — Aligned `request_id` no-reuse language. §09 now uses MUST for both cross-temporal no-reuse (including retries) and concurrent-in-flight no-reuse, matching the existing §10 MUST. The two requirements are split into explicit sentences under "Collision avoidance"; the schema-side `request_id` paragraph defers to that subsection rather than restating the MUST, removing a now-redundant phrasing. Verbal strength is consistent across §09 and §10.
- §11 — Added `E_SCHEMA_DUPLICATE_ENTRY` to the Stage 5 schema diagnostics catalog, severity `error`, document_kind `any`. Covers within-array uniqueness violations: duplicate `(namespace, key)` in `state_policy` (§07), duplicate field `name` in a `submit_form` (§03), duplicate `value` in `select.options` (§03), and duplicate marks in inline `marks` (§03). The structured diagnostic SHOULD include `field_path` and the duplicated value in `details`. Previously these were forced into `E_SCHEMA_FIELD_SYNTAX` or `E_SCHEMA_ENUM_VIOLATION`, neither of which fit. §07 and §03 now reference the new code by name at each uniqueness rule.
- §09 — Added an explicit 4096-byte cap on `request_state[].value` in the submit body schema, restating the protocol's absolute state-value ceiling (§07). Publishers MAY reject larger values as malformed submits.
- §11, §10 — Added `W_HISTORICAL_RUNTIME_AMBIGUOUS` to the Historical content diagnostics catalog, severity `warning`, document_kind `content`. Covers the case in which historical content signature verifies under more than one distinct retained `K_runtime.pub` for the same `K_publisher.pub` — an outcome with probability ~2^-256 indicating cryptographic anomaly, implementation bug, or authorization-history corruption. Severity is `warning` because the document is rejected per §10 but the condition does not invalidate other content. §10 now references this code where it previously said "client-implementation diagnostic".
- README, §06 — Replaced the term "site entry" with "site" everywhere it appeared (README trust-state table, §06 `publisher_pubkey` prose). The term was not defined in §01 and the distinction between "site entry" and "site" was unintentional.
- §10 — For `manifest.updated` future-skew rejection, added a note that the structured `E_SCHEMA_FIELD_SYNTAX` diagnostic SHOULD include `reason: "future_beyond_skew_tolerance"` and the offending timestamp in `details`, distinguishing temporal-domain failures from lexical RFC 3339 violations. No new diagnostic code is added; `E_CANARY_INVALID` remains the dedicated code for canary `issued_at` future skew.
- §03 — Added a canonical "All seven of `kind`, `src`, `sha256`, `media_type`, `width`, `height`, and `alt` are required. `caption` is optional. No other top-level fields are permitted." sentence to the image block schema. Clarified that `alt` MAY be the empty string for purely decorative images, in contrast to `caption` where the empty string is forbidden.
- §01 — Added glossary entries for "Submit body" (referenced from §09), "Origin binding" (the verification rule defined in §05 and §06), and "Image resource" (distinct from the `image` block; defined in §03 and §09). Cross-references updated on related entries.
- §10 — Removed a redundant chrome-display sentence under Expired-canary-block mode that duplicated the general "When a reduced mode is active, the client MUST display the mode in chrome." rule. The mode-specific notice about the replaced content area is preserved; only the duplicated chrome-display MUST is removed.
- §09 — Added an explicit clarifying sentence after the status-code whitelist table noting that codes outside the whitelist (including `204`, `304`, `418`) are treated as transport or protocol errors rather than as Entangled semantics, except for `3xx` redirects which are explicitly rejected.
- docs/design-decisions.md — Added a banner near the top noting that the file's vocabulary and trust-model summary are pre-spec snapshots; authoritative definitions live in §01 and §05; when the document and the numbered specification differ, the numbered specification governs.

This rc adds two new diagnostic codes (`E_SCHEMA_DUPLICATE_ENTRY`, `W_HISTORICAL_RUNTIME_AMBIGUOUS`); the rest of the catalog is unchanged in spelling and semantics. `E_TRUST_MISMATCH` and `E_TRUST_USER_REJECTED` move from Stage 7 to Stage 6 in the catalog grouping (the codes themselves are unchanged; only the `stage` field of structured diagnostics for these two codes changes from `7` to `6`). Implementations consuming the rc.9 diagnostic catalog need to add the two new codes and update their Stage attribution for the two trust codes; existing codes are otherwise unchanged in semantics. Corpus vectors exercising the affected within-array uniqueness rules and the multi-key historical trial anomaly should be updated to assert the new codes; that corpus update is out of scope for this rc and will be tracked in a follow-up tranche.

The wire format, signature inputs, and signature input construction are unchanged. The wire-level `spec_version` remains `"1.0"`.

### v1.0-rc.9

Date: 2026-05-08

Changes since v1.0-rc.8:

- §11 — Added `E_SCHEMA_ENUM_VIOLATION` to the stage 5 schema diagnostics catalog. The code applies when a field whose value is required to be one of an enumerated set carries a syntactically valid value not in that set: for example a block `kind` slug not in the enumerated block kinds (§03), an unknown state-policy `mode`, or an unknown transaction `feedback` `variant`. Previously such cases were forced into `E_SCHEMA_FIELD_SYNTAX`, which conflated lexical-form violations (slug grammar, base64url alphabet, RFC 3339 form) with set-membership violations.
- §11 — Reformulated the `E_SIG_MALFORMED` row to make the §04 / §05 precedence boundary explicit. When the `sig` field is received on the wire, length and base64url-alphabet violations are reported as `E_SCHEMA_FIELD_SYNTAX` at stage 5 per §04 and §10's first-failing-stage rule; `E_SIG_MALFORMED` covers signature decoding contexts where stage-5 wire-side field-syntax validation does not apply. No semantic change.
- corpus — Added a top-level `clock_now` field (`"2026-05-07T00:01:00Z"`) to `corpus.json`. Harnesses MUST mock the implementation's wall clock to this value for the duration of the test run. Canary diagnostics depend on `now` against fixed `issued_at` timestamps; without clock mocking, time-dependent vectors drift into `W_CANARY_EXPIRED` or `E_CANARY_INVALID` as real time advances. `corpus/README.md` documents the requirement and adds it as a step to the harness pattern.
- corpus — Vectors 132 (`schema-null-value`) and 142 (`numeric-overflow`) now carry all required manifest fields. Previously six required fields were omitted, allowing `E_SCHEMA_REQUIRED_FIELD` to compete with the targeted diagnostic at stage 5; with the fix, the `null` literal (132) and the 2^63 overflow (142) are unambiguously the only stage-5 violations. Diagnostic codes are unchanged.
- corpus — Vector 133 (`schema-block-kind-unknown`) diagnostic changes from `E_SCHEMA_FIELD_SYNTAX` to `E_SCHEMA_ENUM_VIOLATION`, reflecting the new §11 code.
- corpus — Vector 151 renamed from `sig-malformed-length` to `sig-syntax-length`, diagnostic changes from `E_SIG_MALFORMED` to `E_SCHEMA_FIELD_SYNTAX`. The `sig` field is 43 ASCII characters instead of the canonical 86; the §04 declared-length check at stage 5 fires before §05 stage-6 signature decoding under §10's first-failing-stage rule, so the prior `E_SIG_MALFORMED` diagnostic was unreachable.
- corpus/README.md — Added a coverage note: this initial corpus exercises representative diagnostic codes per pipeline stage and does not cover every code in the §11 catalog. Future tranches will fill out the remaining codes.

This rc adds one new diagnostic code (`E_SCHEMA_ENUM_VIOLATION`) and corrects two corpus-vector diagnostic mappings (133 → `E_SCHEMA_ENUM_VIOLATION`; 151 → `E_SCHEMA_FIELD_SYNTAX`). Vectors 132 and 142 keep their codes but are now unambiguously isolated to the targeted violation. Implementations that consumed the rc.8 corpus need to update their diagnostic mapping for vectors 133 and 151 and must mock the wall clock to `corpus.json["clock_now"]`. The wire format, signature inputs, signature input construction, and the rest of the diagnostic code catalog are unchanged.

The wire-level `spec_version` remains `"1.0"`.

### v1.0-rc.8

Date: 2026-05-08

Changes since v1.0-rc.7:

- Added a normative conformance corpus under `corpus/`. A v1.0-conforming implementation MUST agree with the verdict (accept or reject + diagnostic) recorded for each vector. The corpus is generated deterministically from fixed test seeds by `corpus/tools/generate.py` (Python 3.10+ with `cryptography`).
- Initial corpus: 28 vectors covering manifest, content, and transaction documents. 5 positive (must accept) and 23 negative (must reject), spanning input checks (BOM, bad UTF-8), JSON parsing (duplicate keys), kind / spec_version, schema (unknown field, missing required, null, unknown block kind), numeric grammar (float, exponent, overflow), signatures (modified payload, malformed length, non-canonical S, small-order A), strict base64url (padding, alphabet, whitespace), binding (path mismatch, reserved `/manifest.json`, request_hash), and canary (equal-`issued_at` conflict). Each vector carries a description, spec references, and a normative diagnostic code from §11.
- §04 — Replaced the "distributed separately" disclaimer for the conformance corpus with a normative reference to `corpus/`. The illustrative single-object JCS test vector remains.

The wire-level `spec_version` remains `"1.0"`. The corpus does not change protocol behavior; it makes the existing rules testable across implementations.

### v1.0-rc.7

Date: 2026-05-08

Changes since v1.0-rc.6:

- §00 — Added a "v1.0 limitations" subsection that consolidates protocol-level limitations a v1.0 implementation should disclose to users: no in-band runtime-key revocation, canary expiration is not cryptographic revocation, no general anti-replay against malicious backends, no historical-content bootstrap for new clients, no in-band origin-migration discovery, no protection from a malicious publisher, image decoding is a residual attack surface. Each bullet references the section that defines the underlying rule.
- §03 — Added a "Decoder safety" subsection. Hash verification authenticates image bytes against the signed document but does not make decoding safe; a publisher with a valid `K_runtime` may sign a document referencing an intentionally crafted image. Implementations SHOULD use memory-safe decoders, hardened parsers, sandboxed processes, or other isolation appropriate to the deployment environment. Protocol-level rejections (media-type allowlist, no SVG, no animation, hash verification, dimension limits, pixel budget) are necessary but not sufficient.
- §07 — Strengthened the request-state consent prompt: the client MUST explain that the item is included in future submit requests across every submit endpoint under the publisher's identity, not only the current form or endpoint. Made explicit that request-state scope in v1 is publisher-wide and endpoint-scoped request state is not part of v1.
- §10 — Strengthened the First contact → TOFU pinned transition from MAY to SHOULD. The recommended trigger is the user explicitly choosing to continue to the site or the first successful render of content. The client SHOULD document, in user-accessible form, the trigger it uses. Other triggers (e.g. dismissal of the first-contact notice) remain permitted.
- §10 — Added a clock-skew UX hint. When rejecting a timestamp because it exceeds the 300-second tolerance, the client SHOULD indicate to the user that the local clock may be incorrect, since clock skew is a likely cause of false positives. The protocol-level diagnostic remains the one specified for the failing field; the advisory is a presentation hint, not a separate diagnostic code.

This rc is editorial. It does not change the wire format, signature inputs, signature input construction, or the diagnostic code catalog.

The wire-level `spec_version` remains `"1.0"`.

### v1.0-rc.6

Date: 2026-05-08

Changes since v1.0-rc.5:

- §02 — Reserved `/manifest.json` at the protocol level. The path is now explicitly forbidden as a content document `path`, transaction `in_response_to`, image `src` (§03), submit endpoint, and inline-link target. Added a bullet to each path-syntax restatement.
- §02 — Clarified the scope of the `request_id` / `request_hash` binding: they bind the signed transaction response to the submit body the client sent, but are not a general anti-replay mechanism against a malicious or compromised publisher backend, which may still receive, store, or reuse submit bodies and sign transaction responses for any submit body it accepts.
- §03 — Replaced the abstract image-resource verification list with a precise, ten-step ordered sequence that names the specific diagnostic for each step (`W_IMAGE_FETCH_FAILED`, `W_IMAGE_CONTENT_TYPE`, `W_IMAGE_OVERSIZE`, `W_IMAGE_HASH_MISMATCH`, `W_IMAGE_DECODE_FAILED`, `W_IMAGE_DIMENSIONS`, `W_IMAGE_BUDGET`). Made explicit that the declared `media_type` is authoritative for decoder selection while the response `Content-Type` is checked separately for header consistency.
- §03 — Added a normative WebP animation detection requirement. A client MUST determine animation status before rendering, by inspecting the RIFF chunk structure or by querying its decoding library. An implementation whose WebP library cannot expose this property reliably MUST reject all WebP resources or disable WebP support. Silently rendering only the first frame of an animated WebP is non-conformant.
- §08 — Refined the equal-`issued_at`-not-a-conflict criterion to depend solely on the JCS-canonical signed payload rather than on byte-for-byte wire equivalence and signature equality. Under deterministic Ed25519 (RFC 8032) signing the same payload under the same key produces an identical `sig`, so the canonical-payload criterion subsumes the signature criterion; framing it as canonical payload makes the protocol-level invariant clear.
- §10 — Added a "Verification key trial order" section for historical content. The order in which retained `K_runtime.pub` entries are tried is implementation-defined (reverse chronological by first-observed `issued_at` recommended). Verification under more than one distinct retained key for the same document is treated as a cryptographic anomaly, an implementation bug, or authorization-history corruption; the client MUST reject the document. No new normative error code; clients SHOULD log the condition.

This rc clarifies path reservation, image verification ordering, and historical-content trial order, and scopes the submit-binding guarantees against backend replay. None of these changes alter the wire format, signature inputs, signature input construction, or the diagnostic code catalog.

The wire-level `spec_version` remains `"1.0"`.

### v1.0-rc.5

Date: 2026-05-08

Changes since v1.0-rc.4:

- §04 — Added an explicit ABNF integer grammar (`integer = "0" / non-zero-digit *digit`) and a parser-level enforcement rule. Numeric tokens MUST be validated lexically before any conversion to a numeric type. JSON parsers that convert numeric tokens to IEEE 754 binary64 first are non-conforming for Entangled use because they cannot reliably distinguish `42` from `42.0` or `1e0`, lose precision above `2^53` (so `9007199254740993` becomes `9007199254740992`), and conflate `-0` with `+0`. Implementations MUST use a parser that either exposes raw numeric tokens for lexical inspection, or rejects non-integer tokens at parse time, or perform a separate raw-bytes validation pass. The integer's decimal value MUST be in `[0, 2^63 − 1]`.
- §04 — Added a "Strict base64url decoding" section that pins decoder behavior for every base64url-encoded field in the protocol (`sig`, `publisher_pubkey`, `origin_pubkey`, `runtime_pubkey`, `expected_publisher_pubkey`, `request_id`, `image.sha256`, `transaction.request_hash`). The decoder MUST use only the URL-safe alphabet (`A-Z`, `a-z`, `0-9`, `-`, `_`), reject every character outside it including `+`, `/`, whitespace, line breaks, and non-ASCII characters, reject the padding character `=`, enforce the field-declared exact ASCII length, and reject non-canonical trailing-group encodings (the unused bits in the final encoded character MUST be zero). Permissive decoders that accept padded input, ignore whitespace, accept the standard `+`/`/` alphabet, or accept non-canonical trailing-group encodings are non-conforming.

This rc tightens parsing strictness without changing the wire format, signature inputs, signature input construction, or the diagnostic code catalog. Documents that an rc.4 client accepted by virtue of a permissive JSON parser or base64 decoder may be rejected by an rc.5 client; conforming current parsers and decoders are unaffected.

The wire-level `spec_version` remains `"1.0"`.

### v1.0-rc.4

Date: 2026-05-08

Changes since v1.0-rc.3:

- §02 — Clarified that `request_hash` is computed over the JCS-canonical bytes of the parsed submit body, not over the wire bytes received. The formula already pinned this; the prose previously read "the exact submit body bytes received, after JCS-canonicalization", which was ambiguous. Insignificant whitespace and member ordering in the wire submit body are now stated explicitly to not affect the hash.
- §05 — Added an "Ed25519 verification profile" section that pins the strict, cofactorless validation rules. Public keys MUST be in canonical encoding and MUST NOT be small-order; signatures MUST use canonical `R` and canonical `S` (`0 ≤ S < L`); verification uses the cofactorless equation `[S]B = R + [k]A`. The profile aligns with `verify_strict` in `ed25519-dalek`. Implementations MUST NOT use cofactored verification or accept non-canonical encodings. This eliminates cross-implementation divergence in signature acceptance, in particular between libraries that historically split between RFC 8032 permissive and ZIP-215-style strict modes.
- §07 — Replaced the "opaque byte strings" terminology for state values with "opaque UTF-8 strings", aligning the safe-display subsection with the value field schema (`value` is a UTF-8 string). Editorial only; no wire-format change.
- §09 — Added a "Content-Encoding and Transfer-Encoding" section that forbids both headers in both directions. Publishers MUST NOT use `Content-Encoding` on any Entangled response or `Transfer-Encoding` (including `chunked`) on any response; clients MUST disable automatic HTTP-layer decompression and reject responses carrying either header. The same rules apply to submit `POST` request bodies. Closes the interop ambiguity that arose when transport stacks decompressed responses by default, which would change the byte sequence used for the byte cap (§02, §06, §10), for `Content-Length` consistency checks, and for the SHA-256 digest of image resources (§03). Adds a normative implementation note that conforming clients must use an HTTP stack whose default header injection and decompression can be disabled.
- §11 — Added `E_TRANSPORT_CONTENT_ENCODING` and `E_TRANSPORT_TRANSFER_ENCODING` to the Stage 1 transport diagnostics catalog.

This rc tightens transport and signature-verification behavior. Responses or signatures that an rc.3 client might have accepted under HTTP-stack default decompression or under cofactored Ed25519 verification can now be rejected; conforming current signers and HTTP stacks are unaffected. The wire-level `spec_version` remains `"1.0"`; the rc number tracks pre-release stabilization, not protocol identity (§11).

### v1.0-rc.3

Date: 2026-05-08

Changes since v1.0-rc.2:

- §03 — Added a fourth link target kind, `target.kind = "carrier"`, for linking to non-Entangled services reachable through an Entangled-supported carrier (for example, non-Entangled Tor onion services). The `carrier` kind takes `carrier` and `url` fields, accepts only `http://` URLs (the carrier provides confidentiality and integrity at the rendezvous layer, and the destination identity is anchored at the carrier address itself), and shares the no-auto-navigate and no-request-state disciplines of `citation` while additionally requiring a carrier-aware browser handoff.
- §03 — Replaced the placeholder note on `citation`'s `http://` ban ("a future protocol version may revisit this...") with an explicit redirect: non-clearnet destinations belong under `kind: "carrier"`, not under `kind: "citation"`.
- §01 — Added the **Carrier link** glossary entry; updated the **Citation link**, **Entangled link**, **Link**, and **Same-site link** entries to reference the new kind. The **Link** entry now describes four target kinds, not three.
- §09 — Clarified that the transport rules govern requests issued by the Entangled client to Entangled endpoints. They do not constrain how the client hands off non-Entangled URLs (`target.kind = "carrier"` or `"citation"`) to external components such as Tor Browser or a system browser.

This rc adds a value to a closed-schema enum (`target.kind`). A document using `kind:"carrier"` is rejected by rc.1 and rc.2 clients during schema validation. The wire-level `spec_version` remains `"1.0"`; the rc number tracks pre-release stabilization, not protocol identity (§11).

## Relationship to the specification

This document describes engineering process. It does not define protocol behavior. The authoritative protocol specification lives in the `specs/` directory; this file does not override or modify it.
