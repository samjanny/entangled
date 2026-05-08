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
