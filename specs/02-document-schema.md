# 02 — Document schema

This section defines the general schema of Entangled documents: their shared envelope structure, the three document kinds (`manifest`, `content`, `transaction`), and the per-kind schemas for `content` and `transaction`. The `manifest` schema is defined in detail in §06.

## The envelope rule

Every signed Entangled document is a flat JSON object with exactly one top-level `sig` field. The signed payload is the object with that top-level `sig` field removed. All other permitted top-level fields are signed. No other unsigned fields exist in Entangled v1.

This rule applies uniformly to `manifest`, `content`, and `transaction` documents. It is the cryptographic invariant on which all signature verification depends.

```text
signed_payload = document object with top-level `sig` field removed
signature_input = context_string || 0x00 || JCS(signed_payload)
sig = Ed25519.sign(signing_key_priv, signature_input)
````

Context strings, signing keys, and verification rules are defined in §05.

## Closed schema discipline

All Entangled v1 documents follow closed-schema discipline:

* All required fields MUST be present.
* No additional top-level fields are permitted.
* Each field MUST satisfy the type and value constraints declared in this section or in the section that owns the field.
* Nested objects MUST contain exactly the fields defined for them.
* Arrays MUST satisfy declared length and element-schema constraints.

A document that fails any of these checks is rejected. Error codes are defined in §11. Validation order is defined in §10.

The closed-schema discipline applies to all document kinds. Lenient acceptance of unknown fields is non-conformant.

## Document kinds

Entangled v1 defines three document kinds:

* `manifest`: the site-level authorization document, defined in §06;
* `content`: a publication served from a path on the site;
* `transaction`: a response to a submit on the site.

The document kind is declared in the top-level `kind` field. Clients use `kind` to select the schema for validation before applying full per-field checks.

A document whose `kind` is not one of the three values defined above is rejected.

## Common top-level fields

All three document kinds share three top-level fields:

### `spec_version`

`spec_version` is the Entangled protocol version targeted by the document.

Entangled v1 documents declare:

```json
"spec_version": "1.0"
```

A client implementing Entangled v1.0 MUST reject any document whose `spec_version` is not exactly `"1.0"`.

Specification document patch releases do not change this field. For example, a corrective specification release such as `v1.0.1` does not cause documents to declare `"1.0.1"`.

### `kind`

`kind` is the document kind discriminator. Permitted values are exactly:

* `"manifest"`
* `"content"`
* `"transaction"`

A document whose `kind` is not one of these exact ASCII strings is rejected.

### `sig`

`sig` is the Ed25519 signature over the document's signature input as defined in §05.

It is encoded as 86 ASCII characters of base64url representing 64 bytes, with no padding.

`sig` is the only top-level field that is not part of the signed payload. The signed payload is the document object with the `sig` field removed.

## Content document

A `content` document is a publication served from a path on a site. It is signed by `K_runtime` and verified against the runtime key authorized by the current manifest for the same site.

### Schema

```json
{
  "spec_version": "1.0",
  "kind": "content",
  "path": "/articles/first-post",
  "meta": {
    "title": "First post",
    "published_at": "2026-05-07T00:00:00Z"
  },
  "blocks": [ ],
  "sig": "..."
}
```

All six fields are required. No other top-level fields are permitted.

### `path`

`path` is the absolute path within the site at which this document is served.

The value MUST:

* begin with `/`;
* contain only ASCII characters in the range `[A-Za-z0-9._~/-]`;
* not contain consecutive `/` characters;
* not contain `.` or `..` path segments;
* not contain a query string, fragment, scheme, or host.

The value MUST NOT exceed 256 ASCII characters.

The `path` field is part of the signed payload. The client MUST compare it against the path from which the document was fetched. A document fetched from a path that does not equal the document's `path` field is rejected.

Path comparison is byte-exact. Trailing slashes, case differences, and every byte of the path are significant. The client MUST NOT normalize the path, case-fold it, percent-decode it, resolve dot segments, or collapse slashes in order to obtain a match.

This binding prevents an attacker controlling the server from serving a document signed for one path under a different path.

### `meta`

`meta` is a JSON object containing per-document editorial metadata.

In Entangled v1, `meta` has exactly two required fields and no other fields:

* `title`, a string;
* `published_at`, a timestamp.

```json
"meta": {
  "title": "First post",
  "published_at": "2026-05-07T00:00:00Z"
}
```

Author, tags, summary, and categorization fields are not part of `meta` in v1.0. They may be represented in `blocks` if the publisher chooses, and may be added to `meta` in a future version.

#### `meta.title`

`meta.title` is a UTF-8 string. It MUST NOT exceed 200 bytes when encoded as UTF-8. It MUST NOT contain control characters in the range U+0000 through U+001F or the value U+007F.

The title is rendered by the client in the content area or in chrome elements that reference the document, depending on context.

#### `meta.published_at`

`meta.published_at` is the timestamp at which the publisher considers the document published, in RFC 3339 format with the `Z` suffix indicating UTC.

```json
"published_at": "2026-05-07T00:00:00Z"
```

Only this timestamp form is permitted:

```text
YYYY-MM-DDTHH:MM:SSZ
```

Other RFC 3339 forms are not permitted, including:

* numeric UTC offsets;
* fractional seconds;
* leap-second values.

`published_at` is editorial metadata. It is not a freshness signal and not a security signal. The authoritative freshness signal for the publication cycle is the canary's `issued_at`, defined in §08 and applied in §10.

The client MAY use `published_at` for ordering, display, or diagnostic purposes. The client MUST NOT reject a document solely because `published_at` is in the past or in the future relative to the client's clock.

The client MAY display `published_at` distinctly when it is significantly in the future relative to the client's clock, for example by indicating that the document is post-dated by the publisher. Display behavior is defined in §10.

### `blocks`

`blocks` is a JSON array of block objects representing the rendered content of the document.

The block types and their schemas are defined in §03.

The `blocks` array MUST contain at least one block and MUST NOT contain more than 1024 blocks.

## Transaction document

A `transaction` document is a response to a submit. It is signed by `K_runtime` and verified against the runtime key authorized by the current manifest for the same site.

A transaction document is not addressable by a path. It is generated in response to a submit and returned in the same HTTP response cycle. The client does not cache transaction documents and does not navigate back to them.

### Schema

```json
{
  "spec_version": "1.0",
  "kind": "transaction",
  "in_response_to": "/contact",
  "state_updates": [],
  "blocks": [ ],
  "sig": "..."
}
```

All six fields are required. No other top-level fields are permitted.

### `in_response_to`

`in_response_to` is the path of the submit endpoint that produced this response.

The value MUST satisfy the same path syntax as `path` in content documents:

* begin with `/`;
* contain only ASCII characters in the range `[A-Za-z0-9._~/-]`;
* not contain consecutive `/` characters;
* not contain `.` or `..` path segments;
* not contain a query string, fragment, scheme, or host;
* not exceed 256 ASCII characters.

The `in_response_to` field is part of the signed payload. The client MUST compare it against the path to which the submit was sent. A transaction document whose `in_response_to` does not equal the path of the originating submit is rejected.

The comparison is byte-exact, with the same disciplines as `path` comparison: no normalization, case-folding, percent-decoding, dot-segment resolution, or slash collapsing.

This binding prevents an attacker controlling the server from substituting a transaction signed for one submit endpoint as the response to a different submit endpoint.

### `state_updates`

`state_updates` is a JSON array of state update operations requested by the transaction response.

The field is required. If the transaction does not request state changes, it is an empty array:

```json
"state_updates": []
```

The array MUST contain between 0 and 32 entries.

The schema and semantics of state update operations are defined in §07.

### `blocks`

`blocks` is a JSON array of block objects representing the response content.

The block types and their schemas are defined in §03. Some block types are intended primarily for transaction responses (such as `feedback` blocks); others may appear in both content and transaction documents.

The `blocks` array MUST contain at least one block and MUST NOT contain more than 256 blocks.

The 256-block limit on transaction documents is tighter than the 1024-block limit on content documents because transaction responses are intended for short feedback rather than full publications.

## Document size limits

The following limits apply to all Entangled documents on the wire:

* the total document MUST NOT exceed 1 MiB;
* individual string fields MUST NOT exceed 100 KiB unless a stricter or more specific limit is defined for that field;
* arrays MUST NOT exceed 10000 elements unless a stricter limit is defined;
* JSON nesting depth MUST NOT exceed 16.

The 1 MiB byte cap is enforced before JSON parsing. A response that exceeds 1 MiB is rejected without parsing.

Per-document-kind limits override the general limits when stricter:

* manifests have a 64 KiB envelope limit (see §06);
* content documents have a 1024-block array limit (above);
* transaction documents have a 256-block array limit and a 32-state-update limit (above).

Parser resource-limit enforcement is defined in §10.

## Field validation order

Within a document, validation proceeds in the order defined by the master verification pipeline in §10. From the perspective of this section, the per-document checks include:

1. Byte size cap before JSON parsing.
2. JSON parsing with parser-enforced nesting and string-length limits.
3. Validate the presence and primitive type of `spec_version`, `kind`, and `sig`.
4. Select the schema and top-level field whitelist for the declared `kind`.
5. Validate all fields against the selected closed schema.
6. Verify the signature using the object-specific signature input defined in §05.
7. Apply fetch-path or submit-path binding checks where required.

Failure at any step rejects the document. Specific error codes are in §11.

## What this section does not cover

This section defines the document envelope shape, the closed-schema discipline, and the schemas of `content` and `transaction` documents.

It does not define:

* the schema of `manifest` documents (see §06);
* the block types and field kinds used inside `blocks` arrays (see §03);
* canonicalization of JSON values for signing (see §04);
* key roles, signature inputs, or verification chain (see §05);
* state policy, consent model, or state update semantics (see §07);
* canary structure and lifecycle (see §08);
* transport protocol details (see §09);
* client behavior, validation order, error precedence, and chrome (see §10);
* error codes and versioning (see §11).
