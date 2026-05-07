# 05 — Keys and signing

This section defines the keys used in Entangled, their roles, the signature inputs for signed objects, and the cryptographic verification chain anchored at `K_publisher`.

Entangled places publisher identity in `K_publisher`, not in the carrier address. Carrier addresses are reachability endpoints. Runtime keys are operational signing keys. Neither is accepted as a substitute for publisher identity.

## Key roles

Entangled uses three Ed25519 keypairs, each with a distinct role and exposure profile.

### `K_publisher`

`K_publisher` is the publisher identity key.

**Algorithm.** Ed25519, RFC 8032.

**Role.** `K_publisher` establishes publisher identity. It signs manifests that authorize carrier endpoint keys (`K_origin`) and operational signing keys (`K_runtime`). It does not sign content or transaction documents directly.

**Operational profile.** `K_publisher` is generated offline, stored offline, and used only during publisher ceremonies: initial setup, origin migration, and `K_runtime` rotation. In the default v1 model, a fresh manifest is signed whenever the authorized runtime key changes.

**Compromise impact.** Compromise of `K_publisher` is publisher identity compromise. Once `K_publisher_priv` is exposed, the protocol's publisher-identity guarantees no longer hold. Recovery requires generating a new publisher identity, publishing a new PIP through out-of-band channels, and rebuilding the publisher's relationship with users. Entangled v1 provides no in-band recovery mechanism for `K_publisher` compromise.

**Exposure to publishing infrastructure.** `K_publisher_priv` MUST NOT be present on the server, in CI systems, in deployment scripts, or in any infrastructure component outside the isolated environment used for publisher ceremonies.

### `K_origin`

`K_origin` is the carrier endpoint key.

**Algorithm.** Ed25519, RFC 8032, for the Tor v3 carrier profile. Other carrier profiles define their own endpoint-key requirements.

**Role.** `K_origin` proves control of the carrier endpoint at which the site is reached. For Tor v3, `K_origin` is the onion-service key and the `.onion` address is derived from `K_origin.pub`. For other carrier profiles, `K_origin` plays the analogous role within that carrier's identity scheme.

`K_origin` does not sign Entangled documents. It does not establish publisher identity. It is authorized by a manifest signed by `K_publisher`.

**Operational profile.** `K_origin` must be available to the carrier infrastructure. For Tor v3, the onion-service infrastructure requires access to `K_origin_priv`. In typical deployments, this makes `K_origin` online or near-online.

**Compromise impact.** Compromise of `K_origin` allows an attacker to control the carrier endpoint, but does not by itself allow the attacker to sign valid manifests or content for the publisher. An attacker holding `K_origin` but not `K_publisher` cannot establish authentic publisher identity.

The legitimate publisher recovers from `K_origin` compromise by generating a new `K_origin`, deploying it to a new carrier endpoint, and publishing a new manifest signed by `K_publisher` authorizing the new endpoint. For Tor v3, this means a new `.onion` address.

### `K_runtime`

`K_runtime` is the operational signing key.

**Algorithm.** Ed25519, RFC 8032.

**Role.** `K_runtime` signs `content` and `transaction` documents within an authorized publication cycle. It is authorized by the manifest and declared in the canary structure. A `K_runtime` is current only while the current manifest authorizes it.

**Operational profile.** `K_runtime` is available to the publishing infrastructure. It is used to sign content documents at publication time and transaction documents in response to submits. It is online or deployment-adjacent.

**Compromise impact.** Compromise of `K_runtime` allows an attacker to forge `content` and `transaction` documents that verify against any manifest that authorizes that key. Forgery exposure is bounded by the rotation cadence and by how quickly the publisher can issue a newer manifest authorizing a replacement key.

Compromise or rotation of `K_runtime` does not retroactively make old signatures mathematically invalid. A document signed by an older `K_runtime` may remain cryptographically valid as historical content if the client can verify it against the manifest or publication cycle that authorized that key. It MUST NOT be rendered as current publication after the client has observed a newer manifest authorizing a different current `K_runtime`, except with the client behavior defined in §10.

**Recovery.** The legitimate publisher recovers from `K_runtime` compromise by performing the runtime-rotation ceremony out of cycle: generate a new `K_runtime`, sign a new manifest with `K_publisher` authorizing the new runtime key, deploy the new manifest, and destroy the old runtime private key where possible.

## Publisher Identity Phrase

The Publisher Identity Phrase (PIP) is the user-facing representation of publisher identity. It is derived from `K_publisher.pub`.

### Derivation

The PIP is a 24-word public identity phrase derived from the raw 32-byte Ed25519 public key `K_publisher.pub` using the BIP-39 English wordlist and checksum procedure.

This use of BIP-39 is an encoding of a public key. It is not a wallet seed and does not encode private entropy.

The derivation is:

1. Let `entropy = K_publisher.pub`, the raw 32-byte Ed25519 public key.
2. Compute `checksum = first_8_bits(SHA-256(entropy))`.
3. Concatenate `bits = entropy || checksum`, producing 264 bits.
4. Split `bits` into 24 groups of 11 bits.
5. Interpret each 11-bit group as an index into the BIP-39 English wordlist.
6. Join the 24 words with single ASCII spaces.

Implementations MUST use the BIP-39 English wordlist. Localized wordlists are not part of Entangled v1.

### Properties

The PIP is public information. It is not a password, not a wallet seed, not private entropy, and not a recovery secret. Anyone with `K_publisher.pub` can compute the PIP.

The PIP MUST be displayed by the client in client-controlled UI. Display requirements are specified in §10.

A user holding a confirmed PIP can verify publisher identity at first contact and across address changes, server replacements, and carrier migrations.

## Authorization model

`K_publisher` authorizes `K_origin` and `K_runtime` for specific roles during a publication cycle. Authorization is carried by the manifest.

Authorization is role-specific and does not transfer publisher identity:

- `K_origin` proves control of a carrier endpoint. It does not sign Entangled documents and is not accepted as publisher identity.
- `K_runtime` signs documents within an authorized publication cycle. It does not authorize other keys, does not authorize origins, and is not accepted as publisher identity.

A document signed by `K_runtime` is accepted as current only if the current manifest signed by `K_publisher` authorizes that exact `K_runtime.pub`.

A document signed by an older `K_runtime` may be accepted as historical content only under the historical-content rules defined by the client verification pipeline in §10.

A publisher may authorize a sequence of distinct `K_origin` and `K_runtime` keys over time. Each manifest declares the keys authorized for the publication cycle covered by that manifest.

## Manifest signing

The manifest is the signed object by which `K_publisher` declares the current site-level authorization state.

The manifest is signed directly by `K_publisher`. Entangled v1 does not define an intermediate manifest-signing key and does not use a separate `static_cert` in the core trust chain.

The exact manifest schema is defined in §06. From the perspective of this section, the manifest is a flat JSON object whose fields include, at minimum:

- `spec_version`;
- `kind`, set to `"manifest"`;
- `publisher_pubkey`, equal to `K_publisher.pub`;
- an `origin` declaration, including carrier type, address, and `origin_pubkey`;
- a `canary` structure containing the current `runtime_pubkey`;
- validity and freshness metadata defined by the manifest and canary sections;
- additional site-level fields defined elsewhere in the specification;
- `sig`, the Ed25519 signature defined below.

The manifest's `sig` field is outside the signed payload. The signed payload is the manifest object with the `sig` field removed. The exact signature input is defined below.

A manifest's `publisher_pubkey` is not by itself a trust anchor. It must match the publisher identity established by the user's confirmed PIP, a previous TOFU pin, or the candidate first-contact identity being presented to the user. Trust-state behavior is defined in §10.

## Carrier origin binding

The manifest declares the carrier endpoint at which the site is reachable. The client verifies that the origin from which the manifest was fetched matches the origin authorized by the manifest.

For Tor v3, the binding is structural:

1. The client fetches the manifest from a `.onion` address.
2. The client decodes the Tor v3 address and obtains the service public key encoded in that address, following the Tor v3 address format.
3. The client verifies that the decoded service public key equals `manifest.origin.origin_pubkey`.
4. The client verifies that the fetched address equals `manifest.origin.address` after applying the canonical address form required by the Tor profile.

Failure of any of these checks rejects the manifest with the origin-mismatch error defined in §11.

For other carrier profiles, the binding rule is profile-specific. Entangled v1 fully specifies only the Tor v3 binding. I2P and Yggdrasil remain draft carrier profiles until their address-to-key binding rules are specified byte-for-byte.

## Signature inputs

Every independently signed object in Entangled has a precise signature input.

All signed Entangled v1 objects share the same envelope shape: a flat JSON object whose fields are the signed payload, plus a top-level `sig` field that carries the Ed25519 signature. The `sig` field is outside the signed payload because a value cannot sign itself. The context string and the signing key vary by object kind; the envelope shape and the signed payload extraction do not.

The signed payload is the JSON object with the `sig` field removed. The signed payload is then JCS-canonicalized (RFC 8785) before signing or verification.

The signature input consists of:

1. an object-kind context string for domain separation;
2. a single null byte (`0x00`) separator;
3. the JCS canonicalization of the signed payload.

The general form is:

```text
signed_payload = envelope object with `sig` field removed
signature_input = context_string || 0x00 || JCS(signed_payload)
signature       = Ed25519.sign(signing_key_priv, signature_input)
```

Verification reconstructs the same input and verifies it with the corresponding public key:

```text
signed_payload   = envelope object with `sig` field removed
signature_input  = context_string || 0x00 || JCS(signed_payload)
verified         = Ed25519.verify(signing_key_pub, signature_input, envelope.sig)
```

Context strings are exact ASCII byte sequences.

The `0x00` separator prevents ambiguity between context and payload. JCS canonical JSON is UTF-8 JSON text and does not emit literal null bytes as structural separators.

### Signed object contexts

| Signed object        | Context string             | Signing key   | Signed payload         | Failure class              |
| -------------------- | -------------------------- | ------------- | ---------------------- | -------------------------- |
| Manifest             | `ENTANGLED-v1 manifest`    | `K_publisher` | envelope minus `sig`   | Manifest signature failure |
| Content document     | `ENTANGLED-v1 content`     | `K_runtime`   | envelope minus `sig`   | Document signature failure |
| Transaction document | `ENTANGLED-v1 transaction` | `K_runtime`   | envelope minus `sig`   | Document signature failure |

The canary is not signed as an independent object in Entangled v1. It is part of the manifest, and the manifest signature covers it. Future versions may define an independently signed canary context, but v1 does not.

### Manifest signature input

The signed payload is the manifest object with the `sig` field removed.

```text
context        = "ENTANGLED-v1 manifest"
signed_payload = manifest object with `sig` field removed
input          = context || 0x00 || JCS(signed_payload)
sig            = Ed25519.sign(K_publisher_priv, input)
```

Verification:

```text
input    = "ENTANGLED-v1 manifest" || 0x00 || JCS(manifest minus sig)
verified = Ed25519.verify(expected_K_publisher_pub, input, manifest.sig)
```

`expected_K_publisher_pub` is determined by the client's trust state:

* from a user-confirmed PIP in externally verified state;
* from a previous pin in TOFU-pinned state;
* from `manifest.publisher_pubkey` as a first-contact candidate in first-contact state.

In all cases, the verifier MUST confirm that `manifest.publisher_pubkey == expected_K_publisher_pub` before accepting the manifest.

### Content document signature input

The signed payload is the content document object with the `sig` field removed.

```text
context        = "ENTANGLED-v1 content"
signed_payload = content document with `sig` field removed
input          = context || 0x00 || JCS(signed_payload)
sig            = Ed25519.sign(K_runtime_priv, input)
```

Verification for current content:

```text
input    = "ENTANGLED-v1 content" || 0x00 || JCS(content minus sig)
verified = Ed25519.verify(current_manifest.canary.runtime_pubkey, input, content.sig)
```

The verifier MUST have a valid manifest for the relevant site before verifying a content document.

For current publication, the runtime key used for verification is `current_manifest.canary.runtime_pubkey`.

For historical content, the runtime key used for verification is the `runtime_pubkey` declared by the manifest or publication cycle under which that content was signed. Historical-content retrieval and rendering behavior is defined in §10.

### Transaction document signature input

Transaction documents use the same envelope shape as content documents, with context string `ENTANGLED-v1 transaction`.

They are signed by `K_runtime` and verified against the runtime key authorized for the relevant publication cycle.

```text
context        = "ENTANGLED-v1 transaction"
signed_payload = transaction document with `sig` field removed
input          = context || 0x00 || JCS(signed_payload)
sig            = Ed25519.sign(K_runtime_priv, input)
```

Verification uses:

```text
input    = "ENTANGLED-v1 transaction" || 0x00 || JCS(transaction minus sig)
verified = Ed25519.verify(authorized_runtime_pubkey, input, transaction.sig)
```

## Domain separation rationale

A signature valid for one signed-object kind MUST NOT be valid for another kind, even if the underlying JCS payload bytes are identical.

Domain separation via the context string ensures this property. A content-document signature cannot be replayed as a transaction-document signature, and a document signature cannot be replayed as a manifest signature.

Without domain separation, an attacker could potentially craft a JSON object whose canonical form is byte-identical across two object types and re-use a signature from one context in another. The context-string prefix prevents this at the cryptographic layer.

## Verification chain overview

The full client-side verification pipeline is specified in §10. From the perspective of this section, the cryptographic checks for verifying an Entangled document are:

1. Establish the expected publisher identity:

   * by user-confirmed PIP;
   * by previous TOFU pin;
   * or, in first-contact state, by treating `manifest.publisher_pubkey` as an unauthenticated candidate identity.

2. Verify the manifest signature using `expected_K_publisher_pub`.

3. Confirm `manifest.publisher_pubkey == expected_K_publisher_pub`.

4. Confirm that the fetched carrier origin matches the carrier endpoint authorized by the manifest.

5. Confirm that the carrier-specific origin binding is valid, such as Tor v3 address decoding matching `manifest.origin.origin_pubkey`.

6. For a current content or transaction document, verify `document.sig` using `current_manifest.canary.runtime_pubkey`.

7. For historical content, verify `document.sig` using the runtime key authorized for the publication cycle under which the document is being treated as historical.

Failure at any check rejects the relevant object or triggers the warning/degraded behavior defined in §10. Error codes and pipeline ordering are defined in §10 and §11.

Anti-downgrade, time-based validity, historical-content behavior, trust-state visualization, and chrome requirements are defined in §10.

## Compromise summary

Entangled separates publisher identity from server-held operational keys.

Server compromise may expose `K_origin` and `K_runtime`. It does not compromise publisher identity unless `K_publisher` is also exposed.

### `K_publisher` compromise

Compromise of `K_publisher` is publisher identity compromise. An attacker with `K_publisher_priv` can sign manifests authorizing arbitrary origins and runtime keys. Entangled v1 provides no in-band recovery from this condition.

### `K_origin` compromise

Compromise of `K_origin` is carrier endpoint compromise. The attacker may control the address, but cannot sign valid manifests unless they also compromise `K_publisher`.

The publisher recovers by authorizing a new `K_origin` in a new manifest signed by `K_publisher`.

### `K_runtime` compromise

Compromise of `K_runtime` is current publication compromise. The attacker can sign content and transaction documents that verify under the manifest that authorizes that runtime key.

The publisher recovers by authorizing a new `K_runtime` in a new manifest signed by `K_publisher`.

Previously valid signatures do not become mathematically invalid solely because a key is later rotated or found compromised. Client behavior for old signatures, stale manifests, and currentness warnings is defined in §10.

## What this section does not cover

This section defines the cryptographic machinery: keys, signing, domain separation, and verification primitives.

It does not define:

* the manifest schema in detail (see §06);
* the canary lifecycle, freshness rules, or rotation cadence (see §08);
* the client verification pipeline order, error precedence, or trust state behavior (see §10);
* operational practices for protecting `K_publisher_priv` (see the operator playbook, outside the normative spec);
* network-layer anonymity, payload confidentiality, or deniability guarantees.