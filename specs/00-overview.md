# 00 — Overview

## What Entangled is

Entangled is a protocol for publishing signed, structured documents over hostile or anonymity-oriented carrier networks. It is intended for sites where content is the primary concern, where the publisher's identity must remain verifiable across time and address changes, and where the client running on the reader's device must remain safe even when served documents or the hosting server are malicious.

A site built on Entangled looks structurally like a small set of JSON files served over HTTP. Each file conforms to a rigid schema and carries a cryptographic signature. The client fetches these files, verifies them against a publisher identity established outside the document, and renders them as visually plain documents within a strictly bounded grammar.

There is no site-supplied executable code, no JavaScript, no DOM scripting, no implicit cross-request state, and no HTML.

The goal is to occupy the niche where small content sites currently live, while drastically reducing the attack surface of the rendering client and giving readers a verifiable form of publisher identity that survives address rotation, server replacement, and carrier migration.

## What Entangled is not

Entangled deliberately excludes large parts of what general web protocols cover.

It is not a web replacement. There is no model for live updates, no client-side computation directed by the publisher, no rich layouts, and no general document interactivity. Sites that require these features should use other tools.

It is not an anonymity layer. Entangled assumes that Tor, I2P, Yggdrasil, or another carrier handles routing, network-layer anonymity where applicable, transport encryption where applicable, and reachability. Entangled builds on top of carrier properties; it does not provide them.

It is not a distributed storage system. Documents are served from origin hosts authorized by the publisher. There is no content-addressed retrieval, no DHT, and no peer-to-peer redistribution at the protocol level. Independent mirroring of sites is out of scope for v1.

It is not a deniability mechanism. The publisher identity is, by design, a persistent public fingerprint. Operators who require deniability obtain it through how they custody, disclose, and attribute the publisher key, not through the protocol itself.

## Design framing

Entangled is built around two explicitly separated security concerns.

The first concern is the client-side attack surface. An Entangled document is rendered by client software on the reader's device. The document itself may be malicious, either because it was written by an adversary or because the server hosting it has been compromised.

The protocol mitigates this concern by drastically constraining the document grammar: structured blocks with closed enumerated types, no JavaScript, no DOM scripting, no ambient storage, no cookies, and no HTML. The client implements a reduced parser and a deterministic renderer.

The second concern is server compromise. The server hosting an Entangled site may be compromised by an external attacker, by legal compulsion, or by insider action.

The protocol mitigates this concern by separating the publisher identity from the operational signing keys. The publisher identity key is kept offline and outside the publishing infrastructure. Server compromise alone cannot establish a new publisher identity, because authentic documents must trace through a manifest signed by `K_publisher`. A compromised server may still serve stale content or abuse any operational keys it has obtained until those keys are rotated or revoked by a newer manifest.

These two concerns are addressed by distinct mechanisms: the constrained grammar for the first, and the offline publisher identity for the second. The remainder of this overview introduces the trust architecture that supports the second concern, and the client architecture that supports both.

## Pillars

For organizational purposes, the Entangled v1.0 specification groups its design under three pillars. These labels are referenced from later sections of the specification and from the glossary in §01. They are organizing terminology for the specification, not separate normative layers; normative behavior is defined in the numbered sections that follow.

**Pillar A — Threat model.** Pillar A covers the two classes of threat the protocol addresses: the client-side attack surface posed by malicious or attacker-controlled documents, and server compromise of the publishing infrastructure. The protocol mitigates the first through the constrained document grammar described in §02 and §03, and the second through the offline publisher identity established by the keys and signing chain in §05.

**Pillar B — Trust architecture.** Pillar B covers publisher identity and the trust chain. It includes the three keys `K_publisher`, `K_origin`, and `K_runtime` defined in §05; the manifest that authorizes operational keys, defined in §06; the canary and runtime authorization, defined in §08; the Publisher Identity Phrase introduced above and specified in §05; and the four publisher trust states (Externally verified, TOFU pinned, First contact, Changed/mismatch) specified in §10.

**Pillar C — Client architecture.** Pillar C covers what a conforming Entangled client is. It includes the structural separation between client-controlled chrome and publisher-controlled content area introduced under "Client architecture" below, the validation pipeline and trust state machine specified in §10, and the chrome and conformance requirements specified in §10.

References to "Pillar A", "Pillar B", or "Pillar C" elsewhere in the specification point to the corresponding pillar described here. The numbered specification sections govern normative behavior; the pillar labels are not themselves normative.

## Trust architecture

Entangled places trust in the publisher identity, not in the address.

A site's address is a reachability endpoint. The publisher identity is a cryptographic key that can survive address rotation, server replacement, and carrier migration. The protocol uses three keys, each with a distinct role and a distinct exposure profile.

`K_publisher` is the publisher identity key. It is generated offline, stored offline, and used only during ceremonies. It does not sign content directly. Its role is to authorize the carrier endpoint key and the operational signing key, and to assert publisher identity continuity across changes of address or carrier.

`K_origin` is the carrier endpoint key. For Tor v3, `K_origin` is the onion service key from which the `.onion` address is derived. For other carrier profiles, `K_origin` plays the analogous role within that carrier's identity scheme. `K_origin` is necessarily available to the carrier infrastructure and is therefore typically online or near-online. Its role is to prove control of the carrier endpoint at which the site is reached.

`K_runtime` is the operational signing key used to sign content and transaction documents. It is rotated periodically, typically every 30 days, via a fresh canary. `K_runtime` is available to the publishing infrastructure. Its role is to sign current content with bounded forgery exposure.

The publisher uses `K_publisher` to sign a manifest that authorizes a specific `K_origin` and a specific `K_runtime` for a publication cycle. Documents signed by `K_runtime` are accepted only if the manifest authorizing them traces back to `K_publisher`.

A correctly operated Entangled deployment assumes that server compromise may expose `K_origin` and `K_runtime`, but not `K_publisher`. The publisher identity survives server compromise as long as `K_publisher` remains offline and uncompromised.

## Publisher Identity Phrase

The Publisher Identity Phrase (PIP) is the user-facing form of the publisher identity. It is a 24-word public phrase derived from the 32-byte Ed25519 public key `K_publisher.pub` using the BIP-39 English wordlist and checksum procedure. The exact derivation is specified in §05.

The PIP is public information. It is not a wallet seed, not a password, not private entropy, and not a recovery secret. It is a human-friendly fingerprint of a public key.

Users verify publisher identity by comparing the PIP displayed by their client against the PIP published by the publisher through out-of-band channels: printed material, social media posts, conference announcements, mailing lists, or other established communication channels.

A user holding a confirmed PIP can recognize the same publisher across address rotation, server replacement, and carrier migration.

The PIP MUST be displayed by the client in client-controlled UI, not as publisher-controlled document content. Display requirements are specified in §10.

## Trust states

The client distinguishes among four trust states for the publisher identity associated with a site. The states are mutually exclusive at any given time:

- **Externally verified.** The user has confirmed `K_publisher.pub` by comparing the PIP against an out-of-band reference.
- **TOFU pinned.** The client has previously pinned `K_publisher.pub` for the current site or origin, and the PIP has not changed.
- **First contact.** The client has no existing pin or external verification for this `K_publisher.pub`.
- **Changed / mismatch.** The current site or origin was previously associated with a different `K_publisher.pub`.

The client MUST display the current trust state persistently in client-controlled UI. Detailed state semantics, including required client behavior for the changed/mismatch state, are specified in §10.

## Client architecture

A conforming Entangled client has two architecturally distinct UI surfaces.

The **content area** is where publisher-signed documents are rendered. Its content is determined by the document being displayed, within the constraints of the document grammar.

The **chrome** is the surrounding UI that the client controls and the publisher does not. It includes the publisher identity state, the PIP display or identity control, the canary status, the carrier address, and any verification warnings.

The chrome MUST be separated from the content area such that publisher-controlled content cannot control, replace, hide, obscure, overlap, or modify the chrome. This separation is structural, not stylistic, and is the foundation on which the security properties of the client rest.

A bare bytes-to-display path that does not enforce this separation is not a conforming Entangled client. Detailed client requirements are specified in §10.

## Operational model

An Entangled deployment involves three components: the publisher, the publishing infrastructure, and the client.

The publisher generates `K_publisher` offline and stores it offline. The PIP is computed once and published through out-of-band channels.

At each publication cycle, the publisher uses `K_publisher` to sign a manifest that authorizes the current `K_origin` and the current `K_runtime` for that cycle. The manifest is the only object signed by `K_publisher` in the core trust chain. Entangled v1 does not define a separate `static_cert` or intermediate certificate.

`K_origin` is deployed to the publishing infrastructure because the carrier requires it. For Tor v3, the onion-service infrastructure must hold `K_origin_priv` in order to operate the endpoint from which the site is reached.

The publishing infrastructure runs the carrier service and serves Entangled documents over HTTP. It holds `K_origin`, because the carrier requires it, and `K_runtime`, the current operational signing key.

At a periodic interval, typically every 30 days, the publisher uses `K_publisher` to sign a fresh manifest with a new `K_runtime` declared in its canary. The new manifest and the new `K_runtime` private key are transferred to the infrastructure. A new `K_origin` is authorized by the same mechanism: a fresh manifest signed by `K_publisher` declares the new `origin`.

Old `K_runtime` private keys are destroyed. Previously signed content remains cryptographically valid as historical content, but only the `K_runtime` authorized by the current manifest is accepted for current publication.

The client fetches the manifest, verifies it against `K_publisher`, and uses the manifest to verify subsequent content and transaction documents.

The publisher identity may be anchored by the user's confirmed PIP, by a previous TOFU pin, or by first contact. The client maintains the trust state for each site, displays the current state and the PIP in chrome, and warns visibly if the publisher identity changes. Detailed client behavior is specified in §10.

## Goals and non-goals

Entangled provides:

- a constrained document grammar that bounds the client-side attack surface;
- a publisher identity that survives server compromise, address rotation, and carrier migration, provided `K_publisher` remains uncompromised;
- a user-verifiable identity anchor, the PIP, independent of any single address;
- bounded operational forgery exposure through periodic key rotation;
- a warrant-canary mechanism that makes failure to refresh visible to clients, including cases where refresh stops because of operator inactivity, loss of control, or coercion.

Entangled does not provide:

- network-layer anonymity, which is the carrier's responsibility;
- payload confidentiality beyond what the carrier provides;
- protection of users whose own devices are compromised;
- cryptographic deniability of the publisher identity;
- automatic protection of `K_publisher` against operational mistakes by the publisher.

The latter point is worth stating explicitly. Entangled's security properties depend on the publisher correctly custodying `K_publisher`. If `K_publisher` is exposed, lost, or coerced, the protocol's identity guarantees do not hold.

The operator playbook describes recommended practices for `K_publisher` custody. Those practices are operational and outside the protocol's normative scope.

## v1.0 limitations

Beyond the high-level non-goals above, Entangled v1.0 has specific limitations that affect what guarantees the protocol can offer in particular threat scenarios. They are listed here so that integrators do not overclaim protection in user-facing material. Each limitation references the section that specifies the underlying rule.

- **No in-band revocation.** Entangled v1 has no protocol-level revocation list for compromised `K_runtime` keys. Forgery exposure for a compromised `K_runtime` is bounded by the publisher's rotation cadence only after the publisher deploys a fresh manifest authorizing a new runtime key (§05, §08).

- **No in-band revocation of `K_origin`.** Entangled v1 has no protocol-level revocation list for compromised `K_origin` keys. The optional `origin.not_after` field in the manifest (§06) lets the publisher declare a maximum lifetime for an origin binding; when present, it bounds the time window during which an attacker holding the compromised `K_origin_priv` can serve cached clients of the abandoned origin. When `origin.not_after` is absent, the recovery window is unbounded at the protocol level: a cached client that never observes the new manifest or its `migration_pointer` continues to treat the compromised origin as authoritative until publisher history is rebuilt out of band (§05, §06).

- **Cross-session migration cycle mitigation depends on implementation-defined storage.** Entangled v1 requires (MUST) migration-history recording with cross-session persistence (§10): clients MUST record Adoption and Replacement events, MUST persist them across sessions, and MUST consult the recall window when processing new migration announcements. The storage backend (serialization format, database technology) is implementation-defined; persistence across sessions is not. Per-flow cycle prevention (visited-origin set) remains MUST and is unaffected (§10).

- **Publisher history portability across client implementations is not specified.** Entangled v1 does not specify a serialization format or migration mechanism for publisher history (trust-state pinning records, migration history, abandonment records). A user who switches client implementations resets these records and must re-establish them through PIP-confirmed out-of-band channels (§05). The protocol's identity guarantees still hold across the switch — the new client treats the publisher as First contact — but cross-session continuity benefits (TOFU pinning persistence, migration-history recall) are lost until the user re-pins or externally verifies the publisher under the new client (§10).

- **No retroactive revocation of historical content.** Entangled v1 does not distinguish documents signed before a `K_runtime` compromise from documents signed after it within the same authorization window. If a runtime key compromise is discovered ex post — after the publisher has already rotated to a new key — historical content signed under the compromised `K_runtime` remains cryptographically valid in the authorization history retained by every client that observed it, even though some of that content may have been produced by an attacker. The protocol has no mechanism to retroactively invalidate a subset of documents signed by an authorized key. This concerns `K_runtime`; `K_publisher` compromise is addressed under "No in-band revocation" above (§05, §08, §10).

- **Canary expiration is not cryptographic revocation.** An expired canary triggers a rendering block by default (§08) and requires a per-session user override to proceed. It does not invalidate `K_runtime` mathematically; documents signed by the runtime key the manifest still authorizes continue to verify cryptographically. Users or environments where operational pauses are frequent can enable permissive-canary mode (§10), which reverts to warning-only rendering.

- **No general anti-replay against malicious backends.** The `request_id` and `request_hash` fields bind the signed transaction response to the submit body the client sent. They do not prevent a compromised or malicious publisher backend from receiving, storing, or reusing submit bodies it has accepted (§02).

- **No historical content bootstrap for new clients.** A client that has never observed a runtime key cannot verify content signed under that key. Entangled v1 does not provide server-supplied historical manifest discovery; historical authorization is based on publisher history the client has previously verified (§10).

- **In-band origin migration is publisher-initiated only.** Entangled v1 provides a signed `migration_pointer` field in the manifest by which a publisher can announce a successor carrier endpoint operated under the same `K_publisher`. Clients with publisher-profile support verify the announcement by independently fetching the successor manifest and confirming `publisher_pubkey` continuity, but the protocol does not provide discovery for migrations the publisher has not announced. If a publisher loses the announcing origin without having previously published a `migration_pointer`, recovery for cached clients is out-of-band (§06, §10).

- **No protection from a malicious publisher.** Entangled protects readers from server compromise and from the client-side attack surface. It does not protect them from a publisher who legitimately controls `K_publisher` and uses that control to publish deceptive content, request misleading state, or link to harmful resources.

- **Image decoding is a residual attack surface.** SHA-256 verification authenticates the bytes of an image resource against the signed document; it does not make image decoding safe. A publisher with a valid `K_runtime` can sign a document referencing an image whose bytes are intentionally crafted to exploit decoder bugs (§03).

- **Diagnostic stage selection is not constant-time.** The validation pipeline in §10 is staged so that the first failing stage produces the rejection diagnostic, and the structured diagnostic itself names that stage (§11). A natural sequential implementation therefore exhibits observable timing differences across rejection causes, and the diagnostic is itself an explicit channel. A passive observer with timing access, or any consumer of the structured diagnostic, may infer information about a document's failure mode. Entangled v1 does not require constant-time diagnostic emission and does not place this in the protocol's threat model. Whether a future protocol version should constrain this side channel is acknowledged as open and may be revisited (§10, §11).

- **Partial detection of content rollback by an authorized runtime key.** When the publisher uses `content_root` (§06) and the content index mechanism (§02, §09, §10), rollback of indexed content is detected and rejected via `E_CONTENT_SEQ_ROLLBACK` (§11), and forgery of indexed content is detected and rejected via `E_CONTENT_HASH_MISMATCH` and `E_CONTENT_SEQ_UNCOMMITTED` (§11). Content at paths not in the content index, and content from publishers that do not use `content_root`, remains unprotected: a server in possession of a previously-issued signed document for an unindexed path can serve that older instance, and the client has no protocol-level basis to distinguish stale from current within the same `K_runtime` authorization window. Operator mitigations for unindexed paths are the same as before: rotate `K_runtime`, publish a new manifest, out-of-band republication (§02, §08, §10).

- **Remembered consent does not reprompt on policy widening within the same `(namespace, key, mode)` scope.** Remembered consent under §07 is keyed on `(K_publisher.pub, namespace, key, mode)`. If a publisher changes the `state_policy` for an existing `(namespace, key, mode)` combination to widen `max_size`, widen `max_lifetime`, or change `purpose`, the client MAY commit subsequent set operations under the remembered consent without reprompting the user, provided each new operation stays within the new policy bounds. The protocol does not require fresh consent on policy widening within the same scope. Existing stored entries retain their commit-time bounds and mode per §07 (§07 "Client behavior on policy changes"); the relaxation applies only to new set operations after the policy change. Tighter binding of remembered consent to policy terms is a v1.0 simplification of the consent model and a candidate for tightening in a future protocol version (§07).

These limitations are implementation-relevant: a v1.0 client and publisher SHOULD align user-facing security claims with what the protocol actually enforces.

## Structure of this specification

The remaining sections cover, in order:

- the vocabulary used (§01);
- the schema of documents and the envelope structure (§02);
- the block types and field kinds (§03);
- the canonicalization rules used for signing (§04);
- the keys and signing chain anchored at `K_publisher` (§05);
- the structure and lifecycle of the manifest (§06);
- the state declaration and consent mechanism (§07);
- the canary structure and lifecycle (§08);
- the HTTP transport subset (§09);
- the required client behavior, including chrome and trust states (§10);
- the standardized error codes and versioning policy (§11).

A complete implementation of Entangled v1.0 satisfies the requirements in all of these sections.