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
