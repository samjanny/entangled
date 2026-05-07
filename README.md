# Entangled

Entangled is a protocol for publishing signed, structured documents over hostile or anonymity-oriented carrier networks.

It is built around two separate security goals:

1. reducing the client-side attack surface required to read a document;
2. preserving publisher identity across server compromise and address migration.

Entangled does this by separating document rendering, publisher identity, carrier reachability, and routine publication signing.

## Pillar A - Threat model

Entangled addresses two explicitly separated classes of threat.

### Threat 1: client-side attack surface

An Entangled document is rendered by a client in a context where the document itself may be malicious.

The protocol mitigates this threat by drastically constraining the document grammar: structured blocks with closed enumerated types, no JavaScript, no DOM scripting, no ambient storage, no cookies, and no HTML.

The client implements a reduced parser and a deterministic renderer. The attack surface exposed to publisher-controlled input is bounded by protocol design, not by mitigation layers added on top of a general-purpose web runtime.

### Threat 2: server compromise

The server hosting an Entangled site may be compromised by an external attacker, by legal compulsion, or by insider action.

Entangled mitigates this threat by separating three roles:

- `K_publisher`: the offline publisher identity key;
- `K_origin`: the carrier-origin key, such as a Tor onion-service key;
- `K_runtime`: the operational signing key used for current publications.

A correctly operated Entangled deployment assumes that `K_origin` and `K_runtime` may be exposed by server compromise, while `K_publisher` is kept offline and outside the compromised infrastructure.

Server compromise may therefore compromise the current origin address and current runtime signing key, but it does not by itself compromise the publisher identity. The publisher identity survives server compromise as long as `K_publisher` remains uncompromised.

Users verify publisher identity through the Publisher Identity Phrase (PIP), a public human-readable encoding of the publisher identity key. The PIP is independent of the site's current address, so the same publisher can be recognized across origin rotation, server replacement, or carrier migration.

Entangled does not address all threats. In particular, it does not provide network-layer anonymity; that is the responsibility of the selected carrier network. It does not provide payload confidentiality beyond whatever transport encryption the carrier provides. It does not provide cryptographic deniability of the publisher identity: the PIP is a persistent public fingerprint by design. Deniability, where required, is an operational matter involving how `K_publisher` is generated, stored, published, and attributed. Entangled also does not protect users whose own devices are compromised.

## Pillar B - Trust architecture

Entangled places trust in the publisher identity, not in the address.

A site's address is a reachability endpoint. The publisher identity is a cryptographic key that can survive address rotation, server replacement, and carrier migration.

The trust architecture has three keys, each with a distinct role and exposure profile.

### Three keys, three roles

`K_publisher` is the publisher identity key. It is an Ed25519 keypair whose public key is the long-term identity of the publisher. It is generated offline, stored offline, and used only during ceremonies. It does not sign content documents directly. Its role is to authorize the carrier endpoint key (`K_origin`) and the operational publication key (`K_runtime`), and to preserve publisher identity continuity across address changes.

`K_origin` is the carrier endpoint key. It is an Ed25519 keypair whose public key is bound to the address at which the site is reachable. For Tor v3, `K_origin` is the onion-service key, and the `.onion` address is derived from `K_origin.pub`. For other carrier profiles, `K_origin` plays the analogous role within that carrier's identity scheme.

`K_origin` must be available to the carrier infrastructure. In typical Tor v3 deployments, this means it is online or near-online as part of the onion-service infrastructure. Its role is to prove control of the carrier endpoint from which the site is served.

`K_runtime` is the operational signing key. It is an Ed25519 keypair used to sign content and transaction documents within a publication cycle. It is rotated periodically, typically every 30 days, via a fresh canary. `K_runtime` is typically available to the publishing infrastructure. Its role is to sign current content with bounded forgery exposure.

### Authorization without identity transfer

`K_publisher` authorizes `K_origin` and `K_runtime` for specific roles. This authorization does not transfer publisher identity to those keys.

`K_origin` proves control of a carrier endpoint. `K_runtime` signs current content within an authorized publication cycle. Neither key is accepted as a substitute for `K_publisher`, and neither key can establish publisher identity on its own.

The manifest carries this authorization. It is signed by `K_publisher` and declares:

- the carrier endpoint, including carrier type, address, and `K_origin.pub`;
- the current `K_runtime.pub`, within the canary structure;
- additional site-level parameters defined by the protocol.

A document is externally verified when the client can verify a chain from the user-supplied or user-confirmed publisher identity to the manifest and from the manifest to the document's signing key.

A document may be locally trusted under first-contact trust (TOFU) if the client has pinned the same `K_publisher.pub` from a previous visit. TOFU does not provide external publisher authentication.

### Publisher Identity Phrase (PIP)

The Publisher Identity Phrase (PIP) is the user-facing form of the publisher identity.

It is a 24-word public identity phrase derived from the raw 32-byte Ed25519 public key `K_publisher.pub` using the BIP-39 English wordlist and checksum procedure.

The PIP is public information. It is not a wallet seed, not a password, not private entropy, and not a recovery secret. It is a human-friendly fingerprint of the publisher public key.

Users verify publisher identity by comparing the PIP displayed by their client against the PIP published by the publisher through out-of-band channels, such as printed material, social media posts, conference announcements, mailing lists, or other established communication channels.

The PIP MUST be displayed by the client in client-controlled UI, not as publisher-controlled document content.

### Identity continuity

Because the trust chain terminates at `K_publisher` and not at the address, a publisher can:

- rotate `K_origin`, and therefore the address, without losing publisher identity;
- rotate `K_runtime` periodically, with the rotation authorized by the manifest and announced through the canary;
- migrate across carrier networks by issuing a new manifest authorizing a new `K_origin` for the new carrier.

Users with the publisher's PIP can recognize the same publisher across these changes.

Users without an out-of-band PIP can only use first-contact trust. The client may remember the first `K_publisher.pub` it sees for a site, but the first contact is not externally authenticated.

### Out of scope at this layer

This layer does not define how `K_publisher` is physically or operationally protected.

Hardware tokens, secret sharing, encrypted-at-rest storage, geographic separation, and similar measures are operational concerns for the publisher and are documented separately in the operator playbook.

The protocol defines the cryptographic relationships among the keys. Physical custody of the keys remains the publisher's responsibility.

## Trust state visualization

Publisher identity has four mutually exclusive states. The client MUST distinguish among them in client-controlled UI; collapsing them into a binary "OK / not OK" state is non-conformant.

| State | Meaning | Trust level |
|---|---|---|
| Externally verified | The user has confirmed this `K_publisher.pub` by comparing its PIP with an out-of-band reference | Highest |
| TOFU pinned | The client has previously pinned this `K_publisher.pub` for the current site entry or origin, and the PIP is unchanged | Intermediate |
| First contact | The client has no existing pin or external verification for this `K_publisher.pub` in the current context | Low |
| Changed / mismatch | The current site entry or origin was previously associated with a different `K_publisher.pub` | Asserted breach |

The client MUST display the current state persistently in client-controlled UI, not as publisher-controlled document content.

The client MUST display the PIP alongside the state, or make it available through a persistent identity control, so the user can compare it against any out-of-band reference they hold.

For state `Changed / mismatch`:

- The client MUST display a prominent warning that is not easily dismissible.
- The client MUST NOT automatically replace the existing pin.
- The client MAY refuse to render content until the user explicitly resolves the mismatch.
- Resolution MUST require explicit user action, such as confirming that the new `K_publisher.pub` is legitimate and replacing the pin, or abandoning the site.

A client MAY support publisher profiles that allow a user-confirmed `K_publisher.pub` to be recognized across multiple authorized origins. In that case, migration to a new origin signed by the same externally verified publisher key MUST NOT be treated as a mismatch solely because the address changed.