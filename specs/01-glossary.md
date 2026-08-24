# 01 - Glossary

This section defines the vocabulary used throughout the Entangled v1.0 specification. Terms are listed alphabetically. Each entry gives a brief definition, a pointer to the section where the term is defined operationally, and a list of related terms.

For external standards referenced by Entangled (Ed25519, JCS, BIP-39, RFC 3339, SHA-256, etc.), this glossary provides brief identification only. The authoritative definition lives in the cited external document.

## Terms

**Anti-downgrade**  
The client rule that prevents a manifest with an older canary `issued_at` from being accepted as current after the client has already observed a newer verified `issued_at` for the same `K_publisher.pub`. Anti-downgrade protects the client from being rolled back to an older publication cycle. Defined in §08 and §10. Related: canary, issued_at, publisher history, manifest.

**BIP-39**  
A standard procedure for encoding bytes as a sequence of words from a fixed wordlist, with checksum. Originally defined for cryptocurrency wallet seeds. In Entangled, BIP-39 is used to encode `K_publisher.pub` as a 24-word public phrase (the PIP). Entangled uses the BIP-39 English wordlist exclusively. The BIP-39 specification is published by the Bitcoin community. Defined in §05. Related: PIP, K_publisher.

**Block**  
A closed-schema content unit inside the `blocks` array of a `content` or `transaction` document. Entangled v1 defines exactly eleven block kinds: `paragraph`, `heading`, `code_block`, `quote`, `list`, `divider`, `image`, `link`, `submit_form`, `feedback`, and `note`. Defined in §03. Related: content document, transaction document, inline element.

**Canary**  
The structure within the manifest by which the publisher attests, on a recurring basis, that the site is operating under publisher control, and authorizes the current `K_runtime`. The canary serves both as a warrant statement and as the runtime authorization mechanism. It is part of the manifest payload and is covered by the manifest signature; it is not signed independently in v1. Defined in §08. Related: warrant canary, manifest, K_runtime, canary gap.

**Canary gap**  
A historical event in which the canary for a publisher was observed in Expired state at some point. The gap is recorded in publisher history and reported to the user even after the publisher resumes issuing fresh canaries. The fresh canary may restore current freshness, but the historical fact of the gap is not erased. Defined in §08 and §10. Related: canary, publisher history.

**Carrier**  
The overlay network over which Entangled documents are transported. The carrier provides reachability and, where applicable, transport-layer confidentiality, integrity, and network-layer anonymity. Entangled v1 fully specifies the Tor v3 carrier profile. I2P and Yggdrasil are reserved as draft carrier profiles. Defined in §05 and §09. Related: carrier endpoint, carrier profile, Tor v3, K_origin.

**Carrier endpoint**  
The address at which an Entangled site is reachable via a specific carrier. For Tor v3, the carrier endpoint is an onion address derived from `K_origin.pub`. Defined in §05 and §06. Related: carrier, K_origin, origin.

**Carrier profile**  
A protocol-defined profile that specifies how a particular carrier (Tor v3, I2P, Yggdrasil, etc.) is used by Entangled, including address syntax, transport expectations, and address-to-key binding rules. Defined in §05 and §09. Related: carrier, carrier endpoint.

**Carrier link**  
A link target kind referencing a non-Entangled service reachable through an Entangled-supported carrier, such as a non-Entangled Tor onion service. The destination is not an Entangled site and does not declare an Entangled publisher identity; the client never navigates automatically and offers an external handoff to a carrier-aware browser. Defined in §03. Related: link, citation link, entangled link, same-site link, carrier.

**Changed/mismatch**  
The trust state entered when the client has a retained publisher identity for a site or publisher profile, but a newly fetched manifest presents a different `K_publisher.pub`. The client must not silently replace the retained identity. Defined in §10. Related: trust state, TOFU pinned, externally verified, publisher history.

**Chrome**  
The client-controlled UI surface that surrounds and accompanies the content area. The chrome displays publisher identity state, PIP, canary state, carrier address, verification warnings, request-state indicators, and other status information that must remain outside publisher control. Structurally separated from the content area. Defined in Pillar C and §10. Related: content area, trust state, canary state.

**Citation link**  
A link target kind referencing a clearnet (non-Entangled) URL. The client never navigates automatically to a citation link; an external handoff, such as opening in a browser or copying the URL, is offered to the user. Defined in §03. Related: link, same-site link, entangled link, carrier link.

**Client**  
A software component that fetches Entangled documents from a carrier, verifies them, and renders them to the user. A conforming client implements the validation pipeline, the trust state machine, chrome layout, state handling, and operational disciplines defined in §10. Browser extensions are not conforming Entangled v1 clients. Defined in Pillar C and §10. Related: chrome, content area, validation pipeline.

**Client-only state**  
A state mode in which a state item is stored by the client and never attached automatically to network requests. Used for local rendering preferences, display options, and similar non-transmitted information. Defined in §07. Related: state, request state, state policy, consent.

**Closed schema**  
A schema discipline under which all documents and nested objects must contain exactly the declared fields, no more and no fewer. Unknown fields are not silently ignored; they cause document rejection. Entangled v1 uses closed-schema discipline at every document layer. Defined in §02. Related: validation pipeline, schema diagnostics.

**Conformance**  
The set of requirements an implementation must satisfy to claim that it implements Entangled v1.0. Conformance requirements appear throughout the specification; the consolidated set for clients is in §10. Defined in §10. Related: client, validation pipeline.

**Consent**  
Explicit user agreement, granted at the time of an action, before the client commits a state change. Manifest declaration of state policy is not consent. Consent is granted per state item, scoped to publisher, namespace, key, and mode. Defined in §07. Related: state, state policy, request state, client-only state.

**Content area**  
The UI surface in which publisher-signed document content is rendered. The content area is bounded by the document grammar: block types, inline elements, and their schemas. It is distinct from chrome, which is client-controlled. Defined in Pillar C and §10. Related: chrome, block, document.

**Content document**  
A signed Entangled document representing a publication served from a path on a site. Signed by `K_runtime`. Verified against the runtime key authorized by the current manifest for the same site. Defined in §02. Related: document, manifest, transaction document, K_runtime.

**Content index**  
A JSON document served at `/content_index.json`, listing per-path content sequence numbers and SHA-256 hashes. Not an Entangled signed document; its integrity is established by hash binding against the manifest's `content_root` field. The closed structure is defined in §02; the fetch is defined in §09; verification is defined in §10. Related: content root, content sequence number, hash binding.

**Content root**  
An optional manifest field (`content_root`) containing the SHA-256 digest of the content index. When present, the publisher commits to a specific content state via `K_publisher` signature. Content at indexed paths is frozen between ceremonies; a `K_runtime`-only attacker cannot forge or roll back indexed content. Defined in §06. Related: content index, manifest, hash binding.

**Content sequence number**  
An optional field (`seq`) on content documents, a positive integer monotonically increasing per path. Used in conjunction with the content index to detect rollback and forgery of content by a `K_runtime`-only attacker. Indexed paths require exact `seq` match against the content index. Defined in §02; verification in §10. Related: content index, content root.

**Context string**  
An ASCII string prefixed to the JCS-canonicalized payload during signature input construction, providing domain separation between signed object kinds. The context strings reserved for v1 are `ENTANGLED-v1 manifest`, `ENTANGLED-v1 content`, and `ENTANGLED-v1 transaction`. The canary is not signed independently in v1; it is covered by the manifest signature. Defined in §05. Related: signature input, signed payload, JCS, domain separation.

**Diagnostic code**  
A machine-readable code used by clients to classify errors, warnings, and informational events. Diagnostic codes use the prefixes `E_`, `W_`, and `I_`. Defined in §11. Related: validation pipeline, error precedence.

**Document**  
A signed JSON object exchanged in the Entangled protocol. The three document kinds are `manifest`, `content`, and `transaction`. All documents use a flat envelope in which `sig` is the only top-level field outside the signed payload. Defined in §02. Related: manifest, content document, transaction document, envelope.

**Document kind**  
The discriminator field `kind` in every Entangled document. Permitted values are exactly `"manifest"`, `"content"`, and `"transaction"`. Defined in §02. Related: document, manifest, content document, transaction document.

**Domain separation**  
The cryptographic property that signatures valid for one signed-object kind cannot be valid for another, even if the underlying canonical bytes are identical. Achieved in Entangled through the context-string prefix in the signature input. Defined in §05. Related: signature input, context string.

**Ed25519**  
A public-key signature algorithm specified in RFC 8032. Entangled uses Ed25519 for `K_publisher`, `K_origin` in the Tor v3 carrier profile, and `K_runtime`. All Entangled signatures are Ed25519 signatures over a defined signature input. The authoritative definition is RFC 8032. Defined in §05. Related: signature input, K_publisher, K_origin, K_runtime.

**Entangled**  
The protocol defined by this specification: a system for publishing signed, structured documents over hostile or anonymity-oriented carrier networks, with a publisher identity that survives address rotation, server replacement, and carrier migration. Defined in §00. Related: carrier, document, publisher.

**Entangled link**  
A link target kind referencing another Entangled site. Navigation requires explicit user confirmation in chrome. The target may include `expected_publisher_pubkey` for pre-confirmation. Defined in §03. Related: link, same-site link, citation link, carrier link.

**Envelope**  
The flat JSON object structure of a signed Entangled document: all signed fields at the top level, plus a single `sig` field that is the only unsigned top-level field. The signed payload is the envelope with `sig` removed. Defined in §02. Related: document, signed payload, sig.

**External verification**  
The trust state in which the user has confirmed `K_publisher.pub` by comparing the PIP displayed by the client against an out-of-band reference. The strongest trust state defined by the protocol. Defined in Pillar B and §10. Related: trust state, PIP, TOFU pinned.

**First contact**  
The trust state of a publisher identity for which the client has no prior retained record and no user-confirmed PIP. The manifest signature verifies under the presented `publisher_pubkey`, but the publisher identity is not yet known to the client. Defined in Pillar B and §10. Related: trust state, TOFU pinned, externally verified, changed/mismatch.

**Freshness proof**  
An optional field in the canary structure by which the publisher anchors the canary to a temporal reference outside the publisher's control, such as a recent block hash, a news headline, or another public event. Helps detect certain forms of canary backdating. Defined in §08. Related: canary, issued_at.

**Freshness-unverified mode**  
A presentation qualifier applied by a client that cannot establish a reliable current-time reference and therefore cannot compute the time-dependent canary states (Fresh, Near-expiration, Expired). The client surfaces in chrome an explicit indication that it cannot place the current time within the canary's claimed validity window. Anti-downgrade, structural-validity, and lower-bound expiration determinations remain in force; only the freshness verdict is suppressed. It is an orthogonal qualifier, not a value of the canary state machine. Defined in §10 "Clock reliability and the verified-time reference". Related: canary, verified-time reference, anti-downgrade.

**Hash binding**  
The technique by which a signed document commits to external bytes by including their cryptographic digest in the signed payload. Entangled uses hash binding for image resources: the document contains a same-origin image path and the SHA-256 digest of the exact image response body bytes. Defined in §03. Related: image, SHA-256, signed payload.

**Historical content**  
A content document signed by a `K_runtime` other than the one currently authorized by the publisher's current manifest, but previously authorized for the same `K_publisher`. Renderable by the client only under the historical-content rules, with a clear historical marker in chrome. Defined in §10. Related: K_runtime, manifest, content document, chrome.

**Image**  
A block kind that references a same-origin image resource and binds it to the signed document by SHA-256 digest. Image bytes are not embedded in the document. The client fetches the image only after verifying the containing document, verifies the SHA-256 digest before decoding, and renders only if the digest and format checks pass. Defined in §03. Related: hash binding, SHA-256, block, image resource.

**Image resource**  
The binary image file fetched separately from the same origin as the document referencing it, bound to the document by SHA-256. Distinct from the `image` block, which carries the reference and the expected digest within the signed document. Defined in §03 and §09. Related: image, hash binding, SHA-256.

**Inline element**  
A `text` or `link` element appearing within an inline content array of a block (paragraph, heading, list item, etc.). Carries visible string content plus optional text marks and, for link elements, a target. Defined in §03. Related: block, text mark, link.

**JCS**  
JSON Canonicalization Scheme, defined by RFC 8785 with verified errata EID 6292 and EID 7920 incorporated. Entangled uses JCS to produce a deterministic byte sequence from a JSON object for signing. Entangled does not redefine JCS; it restricts the JSON values that may appear before canonicalization. The authoritative definition is RFC 8785, inline-errata version. Defined in §04. Related: signature input, signed payload.

**Issued_at**  
The timestamp at which the canary was signed by the publisher. The authoritative anti-downgrade and freshness signal in Entangled. Used by the client to determine whether a fetched manifest is newer than a cached one for the same `K_publisher.pub`. Defined in §08. Related: canary, anti-downgrade, manifest, publisher history.

**JSON**  
JavaScript Object Notation, the data format in which all Entangled documents are exchanged. Entangled uses a strict subset: UTF-8 encoded, no BOM, no null values, integers only (no floating-point), and no malformed Unicode. Defined in §02 and §04. Related: JCS, closed schema.

**K_origin**  
The carrier endpoint key. For the Tor v3 carrier profile, this is an Ed25519 keypair whose public key is bound to the onion address at which the site is reached. `K_origin` is authorized by the manifest signed by `K_publisher`. It does not sign Entangled documents and does not establish publisher identity. Defined in §05. Related: K_publisher, K_runtime, carrier, manifest.

**K_publisher**  
The publisher identity key. An Ed25519 keypair generated and stored offline, used during publisher ceremonies to sign manifests. Authorizes `K_origin` and `K_runtime` for each publication cycle. The public key `K_publisher.pub` is the trust anchor; the PIP is its user-facing form. Defined in §05. Related: PIP, K_origin, K_runtime, publisher identity, manifest.

**K_runtime**  
The operational signing key. An Ed25519 keypair used to sign content and transaction documents within a publication cycle. Authorized by the manifest, declared in the canary structure, and rotated periodically. Defined in §05. Related: K_publisher, K_origin, canary, content document, transaction document.

**Link**  
A navigational element referring to a destination. Links appear inline within block content as inline `link` elements, or as standalone `link` blocks. Four target kinds are permitted: same-site, entangled, carrier, citation. Defined in §03. Related: same-site link, entangled link, carrier link, citation link, inline element.

**Manifest**  
The signed document by which a publisher declares the current authorization state of an Entangled site. Signed directly by `K_publisher`. Contains `publisher_pubkey`, `origin`, `canary`, `state_policy`, `navigation`, `min_refresh_interval`, `updated`, and optionally `migration_pointer` and `content_root`. Fetched at the canonical path `/manifest.json`. Defined in §06. Related: K_publisher, K_origin, K_runtime, canary, content root, document, migration pointer.

**Migration history**  
A per-publisher log of migration outcomes (adoption, replacement) recorded in publisher history under `K_publisher.pub`. Used by clients to detect cross-session migration cycles where a publisher under the same `K_publisher` alternates between two carrier addresses across sessions, raising user-confirmation friction on second-and-subsequent migrations to a previously-replaced successor within a recall window. MUST-level requirement in v1.0; storage backend is implementation-defined; recall window recommended at 30 days, with a 7-day MUST floor. Defined in §10. Related: migration pointer, publisher history, K_publisher, visited origins.

**Migration pointer**  
The signed announcement, carried in a manifest's optional `migration_pointer` field, that the publisher is migrating to a new carrier endpoint under the same `K_publisher`. Absent in the manifest when no migration is announced; present as an object containing `successor_origin` and `announced_at` when announced. Allows clients with publisher-profile support to migrate trust continuity in-band, without out-of-band PIP exchange, after independently verifying the successor manifest. Clients enforce a chain-depth limit and a per-flow visited-origin cycle check when following successive migration pointers (§10). Defined in §06 and §10. Related: manifest, origin, publisher profile, K_publisher, migration history.

**Onion service**  
A service in the Tor network reachable through a `.onion` address. In Tor v3, an onion service is identified by a 56-character base32-encoded address derived from the onion service public key. In Entangled, the Tor v3 onion service key is `K_origin`. The authoritative definition is the Tor rendezvous specification. Defined in §05 and §09. Related: Tor v3, carrier, K_origin.

**Origin**  
In the manifest, the JSON object declaring the carrier endpoint at which the site is reachable: `carrier`, `address`, `origin_pubkey`, and the optional `not_after`. Distinct from the HTTP-style "origin" concept; this term refers to the carrier-level reachability declaration. Defined in §06. Related: manifest, carrier endpoint, K_origin, origin binding, origin not-after.

**Origin binding**  
The verification rule that the carrier endpoint from which a manifest was fetched matches the `origin` declared in the manifest, with carrier-specific key derivation (for Tor v3, the `.onion` address derived from `origin_pubkey`). Origin binding is enforced at Stage 9 of the validation pipeline; failure is reported as `E_BIND_ORIGIN`. Defined in §05 and §06. Related: origin, K_origin, manifest, validation pipeline.

**Origin not-after**  
The optional `origin.not_after` field on a manifest, declaring the UTC instant after which the publisher commits that this carrier endpoint is no longer authoritative for the site under `K_publisher`. When present and reached, the manifest is rejected as `E_ORIGIN_EXPIRED` at Stage 9. Bounds the time window during which an attacker holding a compromised `K_origin_priv` can continue to serve cached clients of an abandoned origin. Defined in §06 and §10. Related: origin, K_origin, manifest, migration pointer.

**Path binding**  
The verification rule that a content document's `path` field, or a transaction document's `in_response_to` field, must match byte-exactly the path from which the document was fetched or to which the submit was sent. Prevents path-substitution attacks. Defined in §02 and §10. Related: content document, transaction document, validation pipeline.

**Pillar A**  
The threat model pillar. Identifies and frames the two threats Entangled addresses: client-side attack surface and server compromise. Defined in §00. Related: Pillar B, Pillar C, threat model.

**Pillar B**  
The trust architecture pillar. Defines publisher identity, the three keys (`K_publisher`, `K_origin`, `K_runtime`), authorization without identity transfer, and the four trust states. Defined in §00. Related: Pillar A, Pillar C, trust state, publisher identity.

**Pillar C**  
The client architecture pillar. Defines the structural separation between chrome and content area, the requirements for a conforming client, and the limits on what publisher-controlled content may control. Defined in §00. Related: Pillar A, Pillar B, chrome, content area, client.

**PIP (Publisher Identity Phrase)**  
The 24-word public phrase derived from `K_publisher.pub` using BIP-39 English wordlist encoding. The user-facing form of publisher identity. Public information; not a wallet seed, password, or recovery secret. Displayed by the client in chrome, used for out-of-band verification of publisher identity. Defined in §05. Related: K_publisher, BIP-39, external verification, chrome.

**Publisher**  
The entity that operates an Entangled site. Holds `K_publisher` offline, performs publisher ceremonies to sign manifests, deploys content and transaction documents to the publishing infrastructure, and publishes the PIP through out-of-band channels. Defined in §00 and §05. Related: K_publisher, publisher identity, manifest.

**Publisher history**  
Client-side storage of observed publisher identities, keyed by `K_publisher.pub`. Records the newest verified canary `issued_at`, runtime keys, origins, trust state changes, and canary gap notifications for each publisher the client has encountered. Used for anti-downgrade enforcement and identity continuity across origin migrations. Defined in §10 and referenced in §06 and §08. Related: K_publisher, anti-downgrade, canary gap, trust state.

**Publisher identity**  
The cryptographic identity of a publisher, anchored at `K_publisher.pub` and represented to users as the PIP. Distinct from the carrier address, which is a reachability endpoint and may change. Survives `K_origin` rotation, server replacement, and carrier migration, assuming `K_publisher` remains uncompromised. Defined in Pillar B and §05. Related: K_publisher, PIP, publisher.

**Publisher profile**  
A client capability that recognizes the same `K_publisher.pub` across verified origin replacements while maintaining exactly one current origin. When supported, migration to a new origin signed by the same `K_publisher` does not trigger Changed/mismatch solely because the address differs. Required for clients that retain trust state across sessions; stateless clients are exempt. Defined in §10. Related: K_publisher, trust state, changed/mismatch.

**Rendering session**  
The lifetime of a single client commitment to render a specific document instance. A rendering session begins when the client commits to rendering a document after Stages 6 through 9 have succeeded, and ends on user-initiated reload, navigation away from the document, or replacement of the underlying manifest by a newer manifest whose content supersedes the rendered document. In-flight retry attempts during the same render share the same rendering session. Defined operationally in §03 (no-retry rule for image verification failure) and §10. Related: image, rendering, validation pipeline.

**Request state**  
A state mode in which a state item is stored by the client and may be attached automatically to submit requests after explicit user consent. Used for session tokens, authenticated form tokens, and similar user-action context. Never attached to manifest fetches or content fetches. Defined in §07. Related: state, client-only state, state policy, consent, submit.

**RFC 3339**  
The standard for date and time format used in Entangled. All timestamps are in the form `YYYY-MM-DDTHH:MM:SSZ` (UTC, integer seconds, no fractional seconds, no numeric offset). Defined where used, primarily §06 and §08. Related: issued_at, updated.

**Same-site link**  
A link target kind referencing a path within the current Entangled site and current carrier origin. Direct navigation without cross-site confirmation. Defined in §03. Related: link, entangled link, citation link, carrier link.

**SHA-256**  
The cryptographic hash function specified in FIPS PUB 180-4. Used in Entangled for the BIP-39 PIP checksum (§05) and for image hash binding (§03). The authoritative definition is FIPS PUB 180-4. Related: BIP-39, image, hash binding.

**Sig**  
The top-level field in every signed Entangled document containing the Ed25519 signature. The only unsigned top-level field. The signed payload is the document with the `sig` field removed. Defined in §02. Related: envelope, signed payload, signature input.

**Signature input**  
The byte sequence over which a signature is computed: `context_string || 0x00 || JCS(signed_payload)`. Different context strings provide domain separation between document kinds. Defined in §05. Related: context string, signed payload, JCS, domain separation.

**Signed payload**  
The portion of a document that is covered by the signature: the document object with the top-level `sig` field removed. JCS-canonicalized to produce the bytes input to signing. Defined in §02 and §05. Related: envelope, sig, signature input, JCS.

**Site**  
An Entangled deployment associated with a `K_publisher.pub` and reachable through one or more carrier endpoints. A specific fetched instance of a site is reached through one current origin declared by a manifest. Defined in §00 and §06. Related: publisher, K_publisher, origin, carrier endpoint.

**Spec release**  
A revision of the specification document. Identifies a particular text version (for example `1.0`, `1.0.1`). Carried in spec metadata, not in any Entangled document. Spec releases correct or clarify text without changing protocol behavior. Distinct from protocol version (`spec_version`) and implementation version. Defined in §11. Related: spec_version, implementation version.

**Spec_version**  
The protocol version identifier carried in every Entangled document. In v1, exactly `"1.0"`. Reflects the wire-format version of the protocol. Documents declaring other values are rejected. Defined in §02 and §11. Related: spec release, breaking change.

**State**  
Per-user information that a publisher may persist on the client's device, declared in the manifest's `state_policy`. Each state item has a mode (client-only or request) and is bound to `(K_publisher.pub, namespace, key)`. Stored on the client; never sent to the server automatically except as request state in submits. Defined in §07. Related: state policy, client-only state, request state, consent.

**State policy**  
The manifest's declaration of every state item the site is authorized to use, with mode, maximum size, maximum lifetime, and purpose for each. Required field of the manifest, even when empty. Defined in §06 and §07. Related: state, manifest.

**Submit**  
A user-initiated request from the client to a transaction endpoint, carrying user input (`fields`) and consented request-state items. Always uses HTTP POST with Content-Type `application/vnd.entangled-submit+json`. Defined in §07 and §09. Related: transaction document, request state, fields, submit body.

**Submit body**  
The unsigned JSON object transmitted as the body of a POST submit request, containing `fields`, `request_state`, and `request_id`. Defined in §09. Related: submit, transaction document, request state, fields.

**Submit form**  
A block kind that declares a form whose user input the client packages into a submit request. Defines the transaction endpoint path, the form fields, and the submit button label. Defined in §03. Related: submit, transaction document, fields.

**Text mark**  
An optional formatting annotation on inline `text` or `link` elements. The four marks defined in v1 are `bold`, `italic`, `code`, and `strikethrough`. Defined in §03. Related: inline element.

**TOFU pinned**  
The trust state in which the client has previously observed and retained `K_publisher.pub` for the site or publisher profile, without external verification by the user. Continuity of observation, not external proof of identity. Defined in Pillar B and §10. Related: trust state, first contact, externally verified, publisher history.

**Tor v3**  
Version 3 of Tor onion services, specifying 56-character base32-encoded onion addresses derived from Ed25519 service keys. The fully specified carrier profile in Entangled v1. The authoritative definition is the Tor rendezvous specification (rend-spec-v3). Defined in §05 and §09. Related: carrier, onion service, K_origin.

**Transaction document**  
A signed Entangled document representing the response to a submit. Signed by `K_runtime`. Carries response blocks and zero or more state update operations. Includes the `in_response_to` field, byte-exactly matching the submit path. Defined in §02. Related: document, content document, submit, K_runtime.

**Trust state**  
One of four mutually exclusive states the client maintains for each publisher identity it has observed: Externally verified, TOFU pinned, First contact, or Changed/mismatch. Displayed persistently in chrome. Defined in Pillar B and §10. Related: chrome, externally verified, TOFU pinned, first contact, changed/mismatch.

**UTF-8**  
The character encoding used for all Entangled byte sequences. Strict UTF-8 is required: no overlong encodings, no malformed sequences, no isolated surrogates, no BOM. Defined in §04. Related: JCS, closed schema.

**Validation pipeline**  
The 10-stage sequence by which a fetched document is validated, from transport-level checks to render-or-report. Errors are reported in pipeline order: the first failed stage determines the reported error. Defined in §10. Related: error precedence, conformance.

**Verification chain**  
The cryptographic sequence by which a document is verified, anchored at `K_publisher.pub`: PIP or TOFU pin establishes expected `K_publisher.pub`, manifest signature verifies under it, manifest authorizes `K_origin` and `K_runtime`, content and transaction documents verify under the authorized `K_runtime`. Defined in §05. Related: K_publisher, K_origin, K_runtime, manifest, signature input.

**Verified-time reference (`T_verified`)**  
The greatest `canary.issued_at` among all manifests verified for a `K_publisher.pub`; it is the anti-downgrade floor. It is authenticated publisher history but is not itself a sound lower bound on real time, because a time-checked `issued_at` may be up to 300 seconds ahead and a clock-less verification cannot enforce even that bound. A separate `T_lower` is advanced only by time-checked manifests, using `issued_at - 300 seconds`, and supplies the sound but incomplete lower-bound expiry check. Neither reference advances offline or supplies the upper bound needed for future-skew validation. Defined in §10 "Clock reliability and the verified-time reference". Related: anti-downgrade, freshness-unverified mode, issued_at.

**Warrant canary**  
A traditional security pattern: a periodic signed statement attesting that the publisher has not been compromised, coerced, or compelled to act against users. The signal is the absence of fresh signatures when the publisher cannot, or will not, sign on schedule. In Entangled, the warrant function is unified with runtime authorization in the canary structure. The protocol does not verify the truth of the statement; it provides a structural failure condition. Defined in §08. Related: canary, canary gap.

## Notation conventions

`Identifier_in_code`: a code-style identifier used in JSON, RFCs, or implementation artifacts.

**Term**: a defined term in this glossary. Bold marks the term being defined.

§NN: a reference to section NN of this specification.

`docs/design-decisions.md`: a reference to the design-decisions log distributed with the specification. It provides design rationale and background, not normative protocol behavior.

External standards (RFC NNNN, FIPS PUB NNN, BIP-39, etc.): references to external specifications, authoritative for terms cited from them.

## What this section does not cover

This section is a glossary. It does not define normative behavior.

Normative requirements are in the numbered specification sections that define operational behavior. `docs/design-decisions.md` provides design rationale and background. When it conflicts with the numbered specification, the numbered specification governs.

When a glossary entry summarizes a concept defined operationally in another section, the section reference is authoritative. The glossary entry is for orientation; the operational definition is what governs implementation.
