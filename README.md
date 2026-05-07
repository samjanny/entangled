# Entangled

Entangled is a protocol for publishing signed, structured documents over hostile or anonymity-oriented carrier networks.

It is built around two separate security goals:

1. reducing the client-side attack surface required to read a document;
2. preserving publisher identity across server compromise and address migration.

Entangled does this by separating document rendering, publisher identity, carrier reachability, and routine publication signing.

## Pillar A — Threat model

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