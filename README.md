# Entangled

[![Spec](https://img.shields.io/badge/spec-v1.0--rc.53-blue)](#versioning)
[![Code license: MIT OR Apache-2.0](https://img.shields.io/badge/code-MIT%20OR%20Apache--2.0-blue.svg)](#license)
[![Spec license: CC-BY-4.0](https://img.shields.io/badge/spec-CC--BY--4.0-blue.svg)](#license)

Entangled is a protocol for publishing signed, structured documents over hostile or anonymity-oriented carrier networks.

It is built around two separate security goals:

1. reducing the client-side attack surface required to read a document;
2. preserving publisher identity across server compromise, address rotation, and carrier migration.

Entangled does this by separating document rendering, publisher identity, carrier reachability, and routine publication signing.

A site built with Entangled is not a general web application. It is a small set of signed JSON documents, served over a carrier such as Tor v3, rendered by a dedicated client whose grammar is intentionally constrained.

There is no JavaScript, no DOM scripting, no HTML, no ambient storage, no cookies, no arbitrary styling, and no publisher-controlled client chrome.

## What Entangled is for

Entangled is for publishing small, verifiable, mostly-static documents over carriers such as Tor onion services, without exposing readers to a browser-like active content surface.

It is not a website framework, not a social network protocol, and not a general application runtime.

Entangled deliberately gives up general web interactivity in exchange for a smaller, more auditable reader surface and a publisher identity that is independent of the current host or address.

Example use cases:

- a journalist publishing signed updates over rotating onion addresses;
- a whistleblowing organization publishing tamper-evident notices;
- a small collective distributing verified documents without trusting the server;
- an archive that wants stable publisher identity independent of hosting.

## How Entangled compares

Entangled is easy to mistake for a static-site generator or a signed-page scheme. The real difference is what a reader's client is allowed to execute, and what the publisher's identity is anchored to.

| Approach | Active content for readers | Identity anchored to | Content tied to a stable publisher identity | Reader must trust the server |
|---|---|---|---|---|
| **Entangled** | None; closed document grammar, no script | An offline key, shown as a PIP and verified out of band | Yes; every document is signed, and identity survives address or host changes | No; you confirm the PIP out of band once, then the client verifies every document against that pinned identity, so a hostile server cannot impersonate the publisher |
| Plain web site | Full (HTML + JavaScript) | A domain and its CA (TLS) | No | Yes |
| Static site over HTTPS | Full (still HTML + JS in a browser) | A domain and its CA (TLS) | No | Yes; the server or deploy controls the current content served under the domain |
| Signed HTML (e.g. Signed Exchanges) | Full (still HTML + JS in a browser) | A certificate bound to a domain | To a certificate and domain, not to a stable publisher key | Partly; signing limits tampering, but the active-content surface remains |
| IPFS | Depends on the gateway or browser, usually full | A content address (CID); a stable publisher identity is not part of plain CID semantics and is added through layers such as IPNS, DNSLink, or app-level signatures | Integrity is content-addressed by CID; binding to a stable publisher identity needs an added naming or signing layer | No for integrity once the client verifies the CID; a public gateway, if used to fetch, is still a trust point |

This is a difference in goals, not a ranking: the other approaches target general, interactive web applications, which Entangled deliberately does not.

## Pillar A - Threat model

Entangled addresses two explicitly separated classes of threat.

### Threat 1: client-side attack surface

An Entangled document is rendered by a client in a context where the document itself may be malicious.

The protocol mitigates this threat by drastically constraining the document grammar:

- closed enumerated block types;
- closed schemas;
- deterministic rendering;
- no JavaScript;
- no DOM scripting;
- no HTML;
- no cookies;
- no ambient browser storage;
- no arbitrary publisher-controlled styling;
- no generic embed or iframe-like mechanism.

The client implements a reduced parser and a deterministic renderer. The attack surface exposed to publisher-controlled input is bounded by protocol design, not by mitigation layers added on top of a general-purpose web runtime.

Images are not embedded as executable or markup-bearing resources. In Entangled v1, image blocks reference same-origin image resources by path and bind them to the signed document with a SHA-256 digest. The client fetches and decodes an image only after the containing document has been verified, and only if the image bytes match the signed hash.

### Threat 2: server compromise

The server hosting an Entangled site may be compromised by an external attacker, by legal compulsion, or by insider action.

Entangled mitigates this threat by separating three roles:

- `K_publisher`: the offline publisher identity key;
- `K_origin`: the carrier-origin key, such as a Tor onion-service key;
- `K_runtime`: the operational signing key used for current publications.

A correctly operated Entangled deployment assumes that `K_origin` and `K_runtime` may be exposed by server compromise, while `K_publisher` is kept offline and outside the compromised infrastructure.

Server compromise may therefore compromise the current origin address and the current runtime signing key, but it does not by itself compromise publisher identity. The publisher identity survives server compromise as long as `K_publisher` remains uncompromised.

Users verify publisher identity through the Publisher Identity Phrase (PIP), a public human-readable encoding of the publisher identity key. The PIP is independent of the site's current address, so the same publisher can be recognized across origin rotation, server replacement, or carrier migration.

### Non-goals

Entangled does not address all threats.

In particular, Entangled does not provide:

- network-layer anonymity, which is the responsibility of the selected carrier network;
- payload confidentiality beyond whatever transport encryption the carrier provides;
- cryptographic deniability of publisher identity;
- protection for users whose own devices are compromised;
- automatic protection against poor operational custody of `K_publisher`.

The PIP is a persistent public fingerprint by design. Deniability, where required, is an operational matter involving how `K_publisher` is generated, stored, published, and attributed.

## Pillar B - Trust architecture

Entangled places trust in the publisher identity, not in the address.

A site's address is a reachability endpoint. The publisher identity is a cryptographic key that can survive address rotation, server replacement, and carrier migration.

The trust architecture has three keys, each with a distinct role and exposure profile.

### Three keys, three roles

`K_publisher` is the publisher identity key.

It is an Ed25519 keypair whose public key is the long-term identity of the publisher. It is generated offline, stored offline, and used only during publisher ceremonies. It does not sign content documents directly.

Its role is to authorize the carrier endpoint key (`K_origin`) and the operational publication key (`K_runtime`), and to preserve publisher identity continuity across address changes.

`K_origin` is the carrier endpoint key.

It is the key whose public part is bound to the address at which the site is reachable. For Tor v3, `K_origin` is the onion-service key, and the `.onion` address is derived from `K_origin.pub`. For other carrier profiles, `K_origin` plays the analogous role within that carrier's identity scheme.

`K_origin` must be available to the carrier infrastructure. In typical Tor v3 deployments, this means it is online or near-online as part of the onion-service infrastructure. Its role is to prove control of the carrier endpoint from which the site is served.

`K_runtime` is the operational signing key.

It is an Ed25519 keypair used to sign content and transaction documents within a publication cycle. It is rotated periodically, typically every 30 days, via a fresh canary. `K_runtime` is typically available to the publishing infrastructure. Its role is to sign current content with bounded forgery exposure.

### Authorization without identity transfer

`K_publisher` authorizes `K_origin` and `K_runtime` for specific roles. This authorization does not transfer publisher identity to those keys.

`K_origin` proves control of a carrier endpoint.

`K_runtime` signs current content within an authorized publication cycle.

Neither key is accepted as a substitute for `K_publisher`, and neither key can establish publisher identity on its own.

The manifest carries this authorization. It is signed by `K_publisher` and declares:

- the carrier endpoint, including carrier type, address, and `K_origin.pub`;
- the current `K_runtime.pub`, within the canary structure;
- site-level parameters such as navigation, state policy, refresh interval, and update time.

A document is externally verified when the client can verify a chain from the user-confirmed publisher identity to the manifest, and from the manifest to the document's signing key.

A document may be locally trusted under first-contact trust (TOFU) if the client has retained the same `K_publisher.pub` from a previous visit. TOFU provides continuity of observation; it does not provide external publisher authentication.

### Publisher Identity Phrase (PIP)

The Publisher Identity Phrase (PIP) is the user-facing form of publisher identity.

It is a 24-word public identity phrase derived from the raw 32-byte Ed25519 public key `K_publisher.pub` using the BIP-39 English wordlist and checksum procedure.

The PIP is public information.

It is not:

- a wallet seed;
- a password;
- private entropy;
- a recovery secret.

It is a human-friendly fingerprint of the publisher public key.

Users verify publisher identity by comparing the PIP displayed by their client against the PIP published by the publisher through out-of-band channels, such as printed material, social media posts, conference announcements, mailing lists, or other established communication channels.

The PIP must be displayed by the client in client-controlled UI, not as publisher-controlled document content.

### Identity continuity

Because the trust chain terminates at `K_publisher` and not at the address, a publisher can:

- rotate `K_origin`, and therefore the address, without losing publisher identity;
- rotate `K_runtime` periodically, with the rotation authorized by the manifest and announced through the canary;
- migrate across carrier networks by issuing a new manifest authorizing a new `K_origin` for the new carrier.

Origin rotation can be announced in-band through the manifest's optional `migration_pointer` field, which signs a successor carrier endpoint under the same `K_publisher`. Clients with publisher-profile support migrate trust continuity across origins after independently verifying the successor manifest, with chain-depth limits and per-flow cycle prevention enforced by the client.

Users with the publisher's PIP can recognize the same publisher across these changes.

Users without an out-of-band PIP can only use first-contact trust. The client may remember the first `K_publisher.pub` it sees for a site, but the first contact is not externally authenticated.

### Out of scope at this layer

This layer does not define how `K_publisher` is physically or operationally protected.

Hardware tokens, secret sharing, encrypted-at-rest storage, geographic separation, and similar measures are operational concerns for the publisher and are documented separately in the operator playbook.

The protocol defines the cryptographic relationships among the keys. Physical custody of the keys remains the publisher's responsibility.

## Trust state visualization

Publisher identity has four mutually exclusive states. A conforming client must distinguish among them in client-controlled UI. Collapsing them into a binary "OK / not OK" state is non-conformant.

| State | Meaning | Trust level |
|---|---|---|
| Externally verified | The user has confirmed this `K_publisher.pub` by comparing its PIP with an out-of-band reference | Highest |
| TOFU pinned | The client has previously retained this `K_publisher.pub` for the current site, origin, or publisher profile, and the PIP is unchanged | Intermediate |
| First contact | The client has no existing retained identity or external verification for this `K_publisher.pub` in the current context | Low |
| Changed / mismatch | The current site, origin, or publisher profile was previously associated with a different `K_publisher.pub` | Asserted breach |

The client must display the current state persistently in client-controlled UI, not as publisher-controlled document content.

The client must display the PIP alongside the state, or make it available through a persistent identity control, so the user can compare it against any out-of-band reference they hold.

For state `Changed / mismatch`:

- the client must display a prominent warning that is not easily dismissible;
- the client must not automatically replace the existing retained identity;
- the client may refuse to render content until the user explicitly resolves the mismatch;
- resolution must require explicit user action, such as confirming that the new `K_publisher.pub` is legitimate and replacing the retained identity, or abandoning the site.

A client may support publisher profiles that allow a user-confirmed `K_publisher.pub` to be recognized across multiple authorized origins. In that case, migration to a new origin signed by the same externally verified publisher key must not be treated as a mismatch solely because the address changed.

## Pillar C - Client architecture

A conforming Entangled client has two architecturally distinct UI surfaces.

### Content area and chrome

The content area is where publisher-signed documents are rendered.

Its content is determined by the document being displayed, within the constraints of the Entangled document grammar: block types, field kinds, text, images, links, forms, and other protocol-defined document elements. The publisher controls what appears in the content area, subject to those structural rules.

The chrome is the client-controlled UI surrounding or accompanying the content area.

The publisher does not control the chrome. It includes:

- publisher identity state;
- the PIP display or identity control;
- canary status;
- carrier address;
- navigation indicators;
- request-state indicators;
- warnings or errors raised by the verification pipeline.

The chrome must be separated from the content area. Publisher-controlled content must not be able to control, replace, hide, obscure, overlap, or modify the chrome.

The client must present chrome status in a persistent client-controlled region that remains distinguishable from document content during navigation within the same site.

A document cannot be prevented from containing misleading prose. However, misleading prose remains publisher-controlled content: it must not affect the actual client-controlled identity state, canary state, address display, or verification warnings.

Document block types must not include browser-chrome, address-bar, trust-badge, canary-status, identity-status, or similar reserved UI components whose semantics are defined as client-controlled.

This separation is the structural foundation of the client's security guarantees. Without it, a compromised server could render fake "verified" badges or fake canary status inside the document and make them difficult for the user to distinguish from the actual client state.

### Client as required component

A bare bytes-to-display path is not a conforming Entangled client.

A conforming client must verify the document, determine the publisher identity state, determine the canary state, and present the required chrome before or while rendering the content area according to the protocol's rendering rules.

An implementation that streams Entangled JSON directly to a generic JSON renderer is not a conforming client.

An implementation that delegates the entire user interface to publisher-controlled content is not a conforming client.

This distinguishes Entangled clients from generic web browsers. A web browser provides chrome around HTML pages, but accepts publisher-supplied scripts, fonts, layouts, styles, embedded resources, and other programmable or semi-programmable inputs within the page.

An Entangled client provides chrome around documents whose grammar is strictly constrained. The publisher cannot supply executable code, arbitrary styling, or client-status UI.

### Required chrome information

A conforming client must display, persistently and in client-controlled UI:

- the publisher identity state: externally verified, TOFU pinned, first contact, or changed/mismatch;
- the PIP, either always visible in compact form or available through a persistent identity control;
- the current carrier address from which the document was fetched;
- the canary state: fresh, near-expiration, expired, invalid, or unavailable;
- request-state indicators when request state is active;
- any verification warnings produced by the verification pipeline.

The visual treatment of these elements is implementation-defined. Their presence, persistence, and client-controlled nature are normative.

### Chrome restrictions

The chrome must not include publisher-controlled content.

The chrome must not display third-party content, advertising, analytics, remote badges, remote images, or externally fetched status indicators unless the user has explicitly enabled such behavior outside the document context.

Chrome semantics must not depend on unauthenticated document fields. If a protocol-defined document field is displayed in chrome, the client must display it only after the field has passed the required verification pipeline, and must visually distinguish publisher-provided labels from client-generated status.

### Out of scope at this layer

The choice of widget toolkit, rendering engine, font, color scheme, layout, and overall visual style is implementation-defined.

A conforming Entangled client is expected to be a standalone software component. Desktop applications, mobile applications, TUIs, and dedicated embedded viewers are in scope.

Generic web pages are not conforming Entangled clients.

Browser-extension implementations are out of scope for v1 because the protocol requires enforceable separation between client-controlled chrome and publisher-controlled content. A future conformance profile may define requirements for extension-based clients if that separation can be enforced.

The protocol defines the architectural separation and the semantic content of the chrome. It does not define a mandatory visual design.

## Document model

Entangled v1 defines three signed document kinds:

- `manifest`;
- `content`;
- `transaction`.

All signed documents are flat JSON objects with a single top-level `sig` field. The signed payload is the document object with `sig` removed.

The signature input is:

```text
context_string || 0x00 || JCS(signed_payload)
````

The context string provides domain separation between document kinds.

The manifest is signed by `K_publisher`.

Content and transaction documents are signed by the currently authorized `K_runtime`.

The canary is not signed independently in v1. It is part of the manifest and is covered by the manifest signature.

## Content grammar

Entangled v1 defines a closed set of block types:

```text
paragraph
heading
code_block
quote
list
divider
image
link
submit_form
feedback
note
```

Unknown block types are rejected.

Blocks have closed schemas. Unknown fields are rejected. Inline content supports only constrained text elements and inline links, with a small set of text marks:

```text
bold
italic
code
strikethrough
```

There is no generic HTML escape hatch.

There is no script block, embed block, iframe block, style block, table model, or arbitrary layout mechanism in v1.

Links are explicitly typed:

* `same_site` links navigate within the current site;
* `entangled` links point to another Entangled site and require user confirmation;
* `carrier` links point to a non-Entangled service reachable through the same carrier (such as a non-Entangled Tor onion service) and are not auto-navigated; the client offers an external handoff to a carrier-aware browser;
* `citation` links point to clearnet `https://` URLs and are handled as external references, not automatic Entangled navigation.

Images are same-origin resources bound by SHA-256. A document may reference an image path, but the signed document contains the expected digest. The client verifies the digest before decoding or rendering the image.

## State model

Entangled state is client-stored and publisher-scoped.

The manifest declares a `state_policy`, listing the state items the site is authorized to use.

State is bound to:

```text
K_publisher.pub + namespace + key
```

Entangled v1 defines two state modes:

* `client_only`: stored locally and never attached automatically to network requests;
* `request`: stored locally and attached to submit requests after explicit user consent.

State is not sent with manifest fetches or content fetches.

Request state is sent only with submits, and only after the user has consented to that state item.

State exists to support limited per-user functionality without recreating the traditional web cookie model.

## Canary model

The canary is part of the manifest.

It serves two roles:

1. a warrant canary: a periodic signed statement of publisher control;
2. runtime authorization: declaration of the current `K_runtime.pub`.

The canary includes:

* `runtime_pubkey`;
* `issued_at`;
* `next_expected`;
* `statement`;
* optional `freshness_proof`.

The client computes canary state as:

* fresh;
* near-expiration;
* expired;
* invalid;
* unavailable.

An expired canary is a warning, not an automatic hard failure. The client may render content but must prominently warn the user.

An invalid canary is a hard failure for current content.

Canary gaps are recorded in publisher history. If a canary expires and the publisher later resumes issuing fresh canaries, the client must still be able to inform the user that a gap occurred.

## Transport model

Entangled v1 uses a minimal HTTP subset over the selected carrier.

For Tor v3, Entangled uses HTTP over the onion service. HTTPS is not required for the Tor v3 profile because the carrier already provides onion-service transport security, and publisher identity is anchored in `K_publisher`, not in the Web PKI.

The client uses:

* `GET` for manifest, content, and same-origin image resources;
* `POST` for submit requests.

Redirects are not followed.

Cookies are not implemented.

Ambient identifiers are not implemented.

Request and response headers are tightly constrained.

The manifest is fetched from:

```text
/manifest.json
```

Content documents are fetched from their signed path.

Transaction documents are returned in response to submit requests.

Image resources are fetched from same-origin paths only, after the containing document has been verified, and are accepted only if their SHA-256 digest matches the signed image block.

## Versioning

Entangled uses three independent version axes:

1. protocol version;
2. specification release;
3. implementation version.

The protocol version is carried in every document as:

```json
"spec_version": "1.0"
```

Entangled v1 defines exactly one document protocol version: `"1.0"`.

There is no `"1.0.1"` or `"1.1"` document version.

During the pre-release rc cycle (`1.0-rc.<N>`), the closed schema MAY be extended additively with optional fields without bumping `spec_version`; documents valid under an earlier rc remain valid under a later rc. Examples include `migration_pointer` (added at rc.13) and `origin.not_after` (added at rc.14): both are optional top-level or nested fields, and both leave `spec_version` at `"1.0"`. Once v1.0 is tagged final, the closed schema is frozen: any subsequent change to the accepted wire format, including additive optional fields, is a breaking protocol change and requires a new protocol version.

Specification releases such as `1.0.1` may clarify or correct the text of the specification post-final, but they do not change wire-format behavior.

Implementation versions are independent.

## Current status

Entangled is a pre-v1 security protocol.

It has a complete specification, a normative conformance corpus, and two reference implementations ([Rust](https://github.com/samjanny/entangled-api), [Java](https://github.com/samjanny/entangled-api-java)) kept in lockstep with the spec through that corpus. Both are verifier libraries: they implement the per-document validation pipeline (Stages 2 through 9) and deliberately leave the Stage 7 trust-state machine (TOFU pinning, externally-verified PIP, retained-identity mismatch detection) and its history persistence to an embedding client layer, so the trust-state and image-layer corpus vectors are reported as out of scope rather than as failures; those vector families are driven by the client-side conformance harnesses in entangled-client. A conforming client, as defined in section 10, is the full component built on top of such a verifier. Across the release-candidate cycle the wire format is stable: a document valid under one `1.0-rc.N` stays valid under later ones.

"Pre-v1" here means two specific things: the v1.0 specification is not yet frozen, and it has not had an independent security audit. Until both are done, Entangled is suitable for review, implementation, and experimentation, but you should not yet stake high-risk operational safety on it.

## Repository structure

The specification is organized into numbered sections:

```text
specs/
  00-overview.md
  01-glossary.md
  02-document-schema.md
  03-block-types.md
  04-canonicalization.md
  05-keys-and-signing.md
  06-manifest.md
  07-state.md
  08-canary.md
  09-transport.md
  10-client-behavior.md
  11-errors-and-versioning.md
```

Additional design rationale, operational notes, and release engineering live in:

```text
docs/
  design-decisions.md
  operator-playbook.md
  RELEASES.md
```

The numbered specification sections define protocol behavior. Design notes explain why decisions were made. If design notes and the numbered specification conflict, the numbered specification governs.

A normative conformance corpus accompanies the specification:

```text
corpus/
  README.md         corpus layout, harness contract, and clock-mocking rules
  corpus.json       machine-readable index of vectors with expected verdicts
  keys.json         test-only Ed25519 keys and the publisher PIP
  vectors/<id>/     one directory per vector, with input.json (and optional extras)
  tools/
    generate.py        deterministic generator for the corpus
    bip39_english.txt  canonical BIP-39 English wordlist used for PIP derivation
```

Each rejection vector carries the normative §11 diagnostic the implementation must produce. See [`corpus/README.md`](corpus/README.md) for the harness contract.

## License

This repository uses separate licenses for code and specification text.

### Code

All source code, examples, test utilities, fixtures, and implementation artifacts are licensed under either of:

- MIT License
- Apache License, Version 2.0

at your option.

This follows the common dual-license model used by many Rust and protocol projects.

### Specification and documentation

The Entangled specification text and documentation are licensed under:

- Creative Commons Attribution 4.0 International (CC BY 4.0)

You may share, copy, redistribute, remix, transform, translate, and build upon the specification text, including for commercial purposes, provided appropriate attribution is given.

### Summary

- Code: `MIT OR Apache-2.0`
- Specification and documentation: `CC-BY-4.0`