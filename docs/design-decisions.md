# Design decisions log

Decisions made during the rebuild of Entangled. This file tracks the
agreed terminology, model choices, and rationale, before they propagate
into normative spec text.

## Vocabulary

| Term | Definition |
|---|---|
| `K_publisher` | Publisher root identity key. Offline. Ed25519. Authorizes all server-side keys. |
| `K_origin` | Carrier endpoint key. Online on the server. Ed25519. For Tor v3, this is the onion service key. |
| `K_runtime` | Content and transaction signing key. Online on the server. Ed25519. Rotated periodically via canary. |
| PIP (publisher identity phrase) | BIP39 encoding of `K_publisher.pub` (32 bytes → 24 English words). The user-facing identity anchor. |

## Trust model (high level, pre-spec)

- `K_publisher` is the root of trust for a publisher's identity.
- `K_publisher` authorizes one or more `K_origin` keys (one per carrier endpoint).
- `K_publisher` authorizes `K_runtime` via the canary mechanism (see §08 when written).
- The user-held anchor of trust is the PIP (24-word phrase derived from `K_publisher.pub`).

## Open decisions

(To be filled as we make further choices.)
