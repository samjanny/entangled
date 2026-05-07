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

## Future-version TODOs

These are non-normative notes for future protocol versions. They are not part of Entangled v1.0 and do not affect v1.0 conformance. Each item that affects the wire format or validation will require a new `spec_version` and a new family of signing context strings, per §11.

- **`table` block type.** A table block would broaden the renderable content grammar. It is intentionally absent from v1.0 to keep the reference renderer narrow. Adding a table block is a wire-format change and a v2 candidate; an early stake should choose between a strict cell-grid model and a header/row schema with closed cell content.

- **Machine-readable content index / sitemap.** v1.0 deliberately omits a machine-readable site index; `navigation` is top-level navigation only (see §06). A future version could define an index document kind or an `index` field on the manifest. Either is a wire-format change.

- **Historical manifest archive for new clients.** v1.0 does not define server-provided historical manifest discovery (see §10, "Historical content"). A future version could define a bounded archive endpoint or an in-manifest pointer to historical manifests, with rules that prevent server-pushed historical authorization without prior client observation.

- **Optional `K_publisher` recovery or revocation model.** v1.0 has no in-band recovery from `K_publisher` compromise (§05). A future revocation commitment in the manifest is non-trivial because a compromised key can sign over any in-band field; any design must rely on prior client-observed commitments and out-of-band republication of a new identity. Note for future work, not for v1.

- **Compression tradeoffs.** v1.0 does not negotiate transport compression. A future version could permit content-encoding negotiation or pre-compressed bodies, but any such mechanism must not weaken byte-cap enforcement before parse, must not introduce new request headers in the v1 sense, and must remain compatible with the carrier's confidentiality assumptions.

- **Image count and image size limits.** v1.0 caps a document at 16 image blocks and image responses at 2 MiB (see §03). The 16-block cap reflects "not a web replacement"; the 2 MiB per-image cap is a compromise between usability for editorial images and bounded decoder/transport exposure. Revisit when a reference renderer is in place.

- **Non-empty `code_block.language` and the `"text"` fallback.** v1.0 requires `code_block.language` to be a non-empty slug, with `"text"` as the fallback for unhighlightable content (§03). Document the rationale: avoiding an "absent vs empty" ambiguity in closed-schema parsers, and giving renderers a single sentinel for plain monospaced fallback.

- **Content `revision` or `content_hash`.** v1.0 has no in-band signal that a known path's content has changed: clients compare bytes or rely on operator practices. A future version could define a `revision` counter or a `content_hash` field on content documents, letting clients detect that `/articles/foo` has been republished without using `meta.published_at` as a freshness or security signal. `meta.published_at` would remain editorial. Adding such a field is a wire-format change.

- **Submit replay protection for non-Tor carriers.** Tor v3 provides confidentiality and integrity at the carrier layer, so v1.0 submit bodies are unsigned and have no nonce or timestamp (see §09). Future carrier profiles without those properties may need replay protection: a per-submit nonce, a server-issued challenge, or a timestamp window. Any such mechanism is part of the carrier profile that introduces it, not of v1.0 conformance, and is a wire-format addition.

- **Image display-density metadata.** v1.0 image blocks carry only declared pixel `width` and `height` (§03). A future version could add optional display-density metadata such as a logical display width or a pixel-density hint for high-DPI clients, to keep editorial images consistent across devices. Decoded-dimension verification would still bind to `width`/`height`. Any such addition is a wire-format change.

- **Freshness proof structure review.** v1.0 keeps `freshness_proof` as a free-form opaque string up to 200 bytes (§08). A future version could introduce a more expressive structure, for example a tagged pair `(kind, value)` covering blockchain block hashes, news bulletins, or third-party signed timestamps, with per-kind validation rules. Any such change is a wire-format change and must keep the property that the protocol does not validate truthfulness.
