# 03 - Block types

This section defines the block types that constitute the rendered content of `content` and `transaction` documents. Each block has a closed schema with declared fields, value ranges, and rendering semantics.

The block grammar is one of the protocol's defenses against the client-side attack surface defined in Pillar A. By restricting authors to a fixed enumeration of block types, each with a strictly bounded schema, Entangled avoids general-purpose markup, scripting, arbitrary styling, and publisher-controlled layout logic.

A block type not enumerated in this section is not part of Entangled v1.0 and causes the document to be rejected.

## Closed enumeration

Entangled v1 defines exactly eleven block types:

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
````

A block whose `kind` is not one of these exact ASCII strings is rejected.

The closed-schema discipline applies to block kinds as it does to all other Entangled fields.

## Common block structure

Every block is a JSON object with a required `kind` field. Additional fields depend on the block kind.

```json
{
  "kind": "<one of the eleven block types>"
}
```

The position of the `kind` field within the JSON object is not significant.

No block has additional fields beyond those defined for its kind. A block containing fields not declared for its kind is rejected.

A block's schema is fully defined per kind in this section. Implementations validate each block against the schema for its declared `kind`.

## Inline model

Several block kinds contain inline content rather than plain strings. Inline content allows limited text formatting and inline links while preserving a closed grammar.

Inline content is used by:

* `paragraph.content`
* `heading.content`
* `quote.content`
* `quote.attribution`
* `list.items`
* `link.label`
* `feedback.content`
* `note.content`

### Inline element schema

Inline content is a JSON array of inline elements.

Each inline element is either a `text` element or a `link` element.

A `text` element:

```json
{
  "kind": "text",
  "value": "string content",
  "marks": ["bold"]
}
```

A `link` element:

```json
{
  "kind": "link",
  "value": "Read more",
  "marks": [],
  "target": {
    "kind": "same_site",
    "path": "/articles/foo"
  }
}
```

Both inline element kinds have:

* `kind`: exactly `"text"` or `"link"`;
* `value`: a UTF-8 string of visible content;
* `marks`: a JSON array of zero or more text marks.

The inline `link` element has an additional `target` field. The target schema is identical for inline links and standalone `link` blocks.

No other fields are permitted.

### Text marks

Text marks are a closed enumeration:

* `"bold"`
* `"italic"`
* `"code"`
* `"strikethrough"`

The `marks` field is a JSON array. It MUST contain only values from this enumeration.

Duplicate marks within the same `marks` array cause the inline element to be rejected with `E_SCHEMA_DUPLICATE_ENTRY` (§11).

Marks combine. An inline text element with `["bold", "italic"]` is rendered as bold italic. Mark order in the array is not significant.

The `code` mark applies monospaced inline rendering and is distinct from the `code_block` block, which is for multi-line code.

### Inline content limits

For a single inline content array:

* the array MUST contain at least one element unless the containing field explicitly permits omission;
* the array MUST NOT exceed 256 elements;
* each `value` string MUST NOT exceed 2048 bytes when encoded as UTF-8;
* the total UTF-8 bytes across all `value` strings MUST NOT exceed the limit declared by the containing block.

A block containing an inline array exceeding these limits is rejected.

### Inline value content

Inline `value` strings:

* MUST be valid UTF-8;
* MUST NOT contain control characters in the range U+0000 through U+001F or U+007F;
* MUST NOT contain line feed characters;
* MUST NOT contain unescaped null characters;
* contain no markup.

Formatting is conveyed only through the `marks` array. Links are conveyed only through inline `link` elements.

## Paragraph block

A `paragraph` block represents a unit of flowing text.

```json
{
  "kind": "paragraph",
  "content": [
    { "kind": "text", "value": "Hello, ", "marks": [] },
    { "kind": "text", "value": "world", "marks": ["bold"] },
    { "kind": "text", "value": ".", "marks": [] }
  ]
}
```

### Schema

`kind` MUST be exactly `"paragraph"`.

`content` is an inline content array. It MUST contain at least one element.

No other fields are permitted.

### Limits

The total UTF-8 bytes of all `value` strings in `content` MUST NOT exceed 8 KiB.

Line feed characters are not permitted. Paragraph breaks are represented by separate `paragraph` blocks.

## Heading block

A `heading` block represents a section heading.

```json
{
  "kind": "heading",
  "level": 2,
  "content": [
    { "kind": "text", "value": "Section title", "marks": [] }
  ]
}
```

### Schema

`kind` MUST be exactly `"heading"`.

`level` is an integer from 1 to 6 inclusive. Level 1 is the most prominent heading level.

`content` is an inline content array. It MUST contain at least one element.

No other fields are permitted.

### Limits

The total UTF-8 bytes of all `value` strings in `content` MUST NOT exceed 200 bytes.

Line feed characters are not permitted.

## Code block

A `code_block` block represents a multi-line block of code or other monospaced content.

```json
{
  "kind": "code_block",
  "language": "rust",
  "content": "fn main() {\n    println!(\"hello\");\n}"
}
```

### Schema

`kind` MUST be exactly `"code_block"`.

`language` is a UTF-8 string identifying the programming language or content type for syntax-highlighting hints.

It MUST satisfy the slug syntax:

* ASCII characters in `[a-z0-9_-]`;
* begins with `[a-z0-9]`;
* does not exceed 64 characters.

The empty string is not permitted. For content without a meaningful language hint, use `"text"`.

`content` is a UTF-8 string containing the code. Line feed characters U+000A are permitted as line separators.

Other control characters in the range U+0000 through U+001F, except line feed, and U+007F are not permitted.

The client renders `code_block` content in a monospaced font, preserving whitespace and line breaks.

Syntax highlighting using `language` as a hint is implementation-defined and not normative.

No other fields are permitted.

### Limits

`content` MUST NOT exceed 32 KiB when encoded as UTF-8.

The protocol does not define a closed enumeration of valid `language` values. Implementations may apply syntax highlighting to known languages and fall back to plain monospaced rendering for unknown values.

## Quote block

A `quote` block represents a block-level quotation.

```json
{
  "kind": "quote",
  "content": [
    { "kind": "text", "value": "Lorem ipsum dolor sit amet.", "marks": [] }
  ],
  "attribution": [
    { "kind": "text", "value": "Marcus Aurelius", "marks": [] }
  ]
}
```

### Schema

`kind` MUST be exactly `"quote"`.

`content` is an inline content array. It MUST contain at least one element.

`attribution` is optional. When present, it is an inline content array and MUST contain at least one element. When absent, the field is omitted from the JSON object. An empty array is not permitted as a substitute.

No other fields are permitted.

### Limits

The total UTF-8 bytes of all `value` strings in `content` MUST NOT exceed 4 KiB.

The total UTF-8 bytes of all `value` strings in `attribution`, when present, MUST NOT exceed 200 bytes.

Line feed characters are not permitted.

## List block

A `list` block represents an ordered or unordered list of items.

```json
{
  "kind": "list",
  "ordered": false,
  "items": [
    [
      { "kind": "text", "value": "First item", "marks": [] }
    ],
    [
      { "kind": "text", "value": "Second item", "marks": [] }
    ]
  ]
}
```

### Schema

`kind` MUST be exactly `"list"`.

`ordered` is a boolean. `true` indicates an ordered list. `false` indicates an unordered list.

`items` is a JSON array. Each element of `items` is an inline content array representing one list item.

No other fields are permitted.

### Limits

The `items` array MUST contain at least one element and MUST NOT exceed 64 elements.

Each item inline content array MUST satisfy the inline limits defined above.

The total UTF-8 bytes of all `value` strings across all items in the list MUST NOT exceed 8 KiB.

Line feed characters are not permitted.

Nested lists are not permitted in v1.

## Divider block

A `divider` block represents a visual separator between content sections.

```json
{
  "kind": "divider"
}
```

### Schema

`kind` MUST be exactly `"divider"`.

No other fields are permitted.

The client renders the divider as a horizontal rule or equivalent visual separator. The visual treatment is implementation-defined.

## Image block

An `image` block references a same-site image resource and binds it to the signed document by SHA-256 digest.

The image bytes are not embedded in the document. They are fetched separately from the same origin after the containing document has passed signature verification.

```json
{
  "kind": "image",
  "src": "/assets/diagram.png",
  "sha256": "sha-256:47DEQpj8HBSa-_TImW-5JCeuQeRkm5NMpJWZG3hSuFU",
  "media_type": "image/png",
  "width": 800,
  "height": 600,
  "alt": "Diagram of the system architecture",
  "caption": "System architecture overview."
}
```

### Schema

`kind` MUST be exactly `"image"`.

`src` is a UTF-8 string containing the same-site path of the image resource. It MUST satisfy the same path syntax as content document `path` values defined in §02:

* begins with `/`;
* contains only ASCII characters in the range `[A-Za-z0-9._~/-]`;
* does not contain consecutive `/` characters;
* does not contain `.` or `..` path segments;
* does not contain a query string, fragment, scheme, or host;
* does not equal `/manifest.json`, which is reserved for manifest fetches (§09);
* does not equal `/content_index.json`, which is reserved for content index fetches (§09);
* does not exceed 256 ASCII characters.

`sha256` is the SHA-256 digest of the exact response body bytes of the image resource, encoded as a string of the form:

```text
sha-256:<base64url>
```

The format is byte-for-byte identical to the format used for `request_hash` in §02:

* literal prefix: lowercase ASCII `sha-256:` (eight characters, including the trailing colon);
* digest: base64url encoding (RFC 4648 Section 5) of the 32-byte SHA-256 digest, with no padding, exactly 43 ASCII characters.

The total string length is exactly 51 ASCII characters (8 prefix + 43 digest).

`media_type` is one of exactly:

* `"image/png"`
* `"image/jpeg"`
* `"image/webp"`

No other media types are permitted in Entangled v1.

`width` is the declared image width in pixels. It MUST be an integer from 1 to 4096 inclusive.

`height` is the declared image height in pixels. It MUST be an integer from 1 to 4096 inclusive.

`alt` is a UTF-8 string providing alternative text for accessibility and for cases where the image cannot be displayed. It MUST NOT contain control characters in the range U+0000 through U+001F or U+007F.

`caption` is optional. When present, it is a UTF-8 string. It MUST NOT contain control characters in the range U+0000 through U+001F or U+007F. When absent, the field is omitted. An empty string is not permitted as a substitute.

`alt` MAY be the empty string for purely decorative images, where alternative text would not aid accessibility. This contrasts with `caption`, where the empty string is forbidden - `caption` is omitted entirely when no caption applies.

All seven of `kind`, `src`, `sha256`, `media_type`, `width`, `height`, and `alt` are required. `caption` is optional. No other top-level fields are permitted.

### Image fetching and verification

The client MUST NOT fetch an image resource referenced by an `image` block until the containing `content` or `transaction` document has passed signature verification and closed-schema validation.

The client MUST fetch the image resource from the same origin as the containing document. Cross-origin image fetches are not permitted.

The client MUST verify the SHA-256 digest of the exact image response body bytes before decoding or rendering the image.

The verification order is:

1. verify the containing Entangled document;
2. fetch the image from `src` using the image resource fetch rules in §09. Transport failure is `W_IMAGE_FETCH_FAILED` (§11);
3. compare the response `Content-Type` against the declared `media_type`. Mismatch, including a Content-Type matching one of the reserved Entangled Content-Types defined in §09, is `W_IMAGE_CONTENT_TYPE`;
4. enforce the 2 MiB image response body cap before any decoding. Over-cap is `W_IMAGE_OVERSIZE`;
5. compute SHA-256 over the exact response body bytes and compare to the block's `sha256` field. Mismatch is `W_IMAGE_HASH_MISMATCH`;
6. decode the image bytes using a decoder for the declared `media_type`. The declared `media_type` is authoritative for decoder selection; the response `Content-Type` is checked for header consistency in step 3 but is not itself the format identifier. Decode failure, including a body whose bytes are valid for a different format than the declared `media_type`, is `W_IMAGE_DECODE_FAILED`;
7. determine whether the resource is an animated form of its declared `media_type` and reject an animated resource as `W_IMAGE_DECODE_FAILED` (see "SVG and animated formats are forbidden" below): for `media_type` `image/webp`, inspect the `VP8X` animation flag in the RIFF container; for `media_type` `image/png`, inspect for an APNG animation-control (`acTL`) chunk preceding the first `IDAT`;
8. compare the decoded image dimensions against the declared `width` and `height`. Mismatch is `W_IMAGE_DIMENSIONS`;
9. apply the document's 16-megapixel decoded pixel budget (defined under "Limits" below). Over-budget is `W_IMAGE_BUDGET`;
10. render the image.

Failure at any step from 2 to 9 rejects the image resource; the image is rendered as missing or unavailable, and the corresponding diagnostic is reported. None of these failures invalidate the containing `content` or `transaction` document.

Resource-exhaustion gate (pre-decode). Steps 6 through 9 are written in decode-then-check order for clarity, but a conforming client MUST NOT allocate a full pixel surface before bounding it by the dimension and pixel limits in "Limits" below. Before decoding (step 6), the client MUST read the resource's pixel geometry from its container header - the PNG `IHDR` width and height, the JPEG frame header (`SOFn`), or the WebP `VP8`/`VP8L`/`VP8X` dimensions - and apply the geometry checks against that header value rather than against an already-allocated surface: a header geometry that differs from the block's declared `width` and `height` is rejected as `W_IMAGE_DIMENSIONS` without decoding, and a header geometry that matches the declared dimensions but whose pixel count would exceed the document's remaining 16-megapixel decoded budget is rejected as `W_IMAGE_BUDGET` without decoding. Only a resource whose header geometry both equals the declared `width` and `height` (and is therefore within 4096 by 4096, since those fields are bounded at Stage 5) and fits the remaining budget is decoded. The decoded-geometry checks in steps 8 and 9 remain in force as a post-decode re-confirmation against a decoder that emits geometry differing from its own header. This gate bounds the worst-case allocation so that a body within the 2 MiB cap (step 4) cannot force a multi-gigapixel allocation through a decoder that allocates before validating geometry.

### No retry on image verification failure

After a failure at any of steps 2-9 above, the client MUST NOT re-fetch the same `src` for the same `image` block within the same document rendering session. The verification failure is a property of the bound triple `(src, sha256, media_type)` declared by the signed document: refetching the same `src` cannot change the signed expectation, and a retry loop adds no information while wasting traffic and exposing the user's browsing pattern to additional observation on the carrier.

A separate user-initiated reload of the containing document, including any document fetched anew under a refreshed manifest, MAY re-issue the image fetch under the verification pipeline above; that is a new rendering session, not a retry within the failed one. A different `image` block referencing a different `src` is not affected by the no-retry rule.

This rule applies uniformly to transport failures (`W_IMAGE_FETCH_FAILED`), Content-Type or media-type mismatches (`W_IMAGE_CONTENT_TYPE`), oversize responses (`W_IMAGE_OVERSIZE`), hash mismatches (`W_IMAGE_HASH_MISMATCH`), decode failures (`W_IMAGE_DECODE_FAILED`), dimension mismatches (`W_IMAGE_DIMENSIONS`), and pixel-budget violations (`W_IMAGE_BUDGET`).

### Inline image data is forbidden

Image content MUST NOT be inlined as a data URI, base64 blob, or any other in-document byte encoding.

The image is fetched separately as a same-site resource and verified by hash. Inlining image data into the document is non-conformant.

### Cross-origin image fetch is forbidden

The `src` MUST refer to a path on the same site and same origin as the document containing the block.

Cross-origin image fetch is not permitted in Entangled v1.

### SVG and animated formats are forbidden

SVG is not permitted in Entangled v1. SVG is markup and can include references, scripting surfaces in some environments, and rendering behaviors inconsistent with the bounded grammar discipline.

Animated image formats are not permitted in Entangled v1.

The only permitted image media types are:

* `image/png`
* `image/jpeg`
* `image/webp`

If a WebP file contains animation, the client MUST reject it.

A client MUST determine whether a WebP resource contains animation before rendering, by inspecting the RIFF container's chunk structure or by querying its decoding library for an animation flag. An implementation whose WebP library cannot expose this property reliably MUST reject all WebP resources, or MUST disable WebP support in the client. A WebP file determined to be animated is reported as `W_IMAGE_DECODE_FAILED` (§11). Silently rendering only the first frame of an animated WebP is non-conformant.

A client MUST likewise determine whether an `image/png` resource is an animated PNG (APNG) before rendering, by inspecting the PNG chunk stream for an animation-control (`acTL`) chunk appearing before the first `IDAT` chunk, or by querying its decoding library for an animation flag. A PNG resource carrying an `acTL` chunk is an animated PNG and MUST be rejected, reported as `W_IMAGE_DECODE_FAILED` (§11). An implementation whose PNG decoder cannot reliably expose this property MUST reject all `image/png` resources, or MUST disable PNG support in the client. Silently rendering only the default image of an APNG is non-conformant: the animated-format prohibition above is blanket, and `image/png` is not exempt from it.

### Decoder safety

SHA-256 hash verification authenticates the bytes of an image resource against the signed document; it does not make image decoding safe. A document signed by an authorized `K_runtime` may reference an image whose bytes are intentionally crafted to exploit bugs in the decoder. The publisher may be malicious or compromised even when its operational keys are not.

Implementations SHOULD use memory-safe image decoders, hardened parsers, sandboxed decoder processes, or other isolation mechanisms appropriate to the deployment environment. The choice among these mitigations is implementation-defined; the protocol does not mandate any specific decoder or sandboxing technology.

The protocol-level rejections in this section - the media-type allowlist, the SVG and animated-format prohibitions, hash verification, dimension limits, and the document-wide pixel budget - are necessary but not sufficient to make decoding fully safe. They reduce the attack surface; they do not eliminate it.

The residual surface includes resource exhaustion as well as memory-safety bugs. An image whose container header declares an enormous geometry, or whose compressed body expands to far more than its wire size (a decompression bomb), can exhaust client memory if it is decoded naively, even though its wire body is within the 2 MiB cap. The pre-decode resource-exhaustion gate under "Image fetching and verification" above bounds the worst-case allocation to the per-image and per-document pixel limits in this section; implementations SHOULD additionally cap total decoder memory and per-image decode time, and SHOULD prefer decoders that stream and enforce geometry limits before allocation.

### Limits

A `content` or `transaction` document MUST NOT contain more than 16 `image` blocks.

The image response body MUST NOT exceed 2 MiB.

`alt` MUST NOT exceed 1 KiB when encoded as UTF-8.

`caption`, when present, MUST NOT exceed 500 bytes when encoded as UTF-8.

The decoded image dimensions MUST match the declared `width` and `height`. A mismatch causes the image to be rejected. Dimension-mismatch rejection does not invalidate the containing signed document; the image is rendered as missing or unavailable, and the diagnostic is reported under the image resource diagnostics defined in §11.

The decoded image dimensions MUST NOT exceed 4096 by 4096 pixels.

Decoded pixel budget.

The total decoded pixel count across all rendered image blocks in a single content or transaction document MUST NOT exceed 16 megapixels (16,777,216 pixels).

When the budget would be exceeded by an additional image, the client MUST refuse to decode that image and any subsequent images in the document, rendering them as missing or as a placeholder. Already-decoded images in the same document remain rendered.

The budget applies after hash verification: a client MUST NOT count an image whose hash failed against the budget. A client MAY count an image whose hash matched but which it chose to skip rendering for other reasons.

16 megapixels is approximately one full 4096x4096 image, four 2048x2048 images, or sixteen 1024x1024 images.

## Link target schema

Links appear in two places:

* inline `link` elements within inline content;
* standalone `link` blocks.

Both use the same `target` schema.

The link target is a JSON object with a discriminator field `kind`.

`target.kind` is one of:

* `"same_site"`
* `"entangled"`
* `"carrier"`
* `"citation"`

No other link target kinds are permitted.

### `target.kind = "same_site"`

A `same_site` target points to a path within the current Entangled site.

```json
{
  "kind": "same_site",
  "path": "/articles/foo"
}
```

`path` MUST satisfy the same path syntax as content document `path` values defined in §02.

The client MAY navigate directly without confirmation. The trust state and chrome identity indicators do not change because the destination is within the same publisher identity and origin.

### `target.kind = "entangled"`

An `entangled` target points to another Entangled site.

```json
{
  "kind": "entangled",
  "carrier": "tor-v3",
  "address": "<56-character-onion-address>.onion",
  "path": "/articles/foo",
  "expected_publisher_pubkey": "<base64url, 32 bytes>"
}
```

`carrier` is the carrier profile identifier. A conforming Entangled v1.0 client MUST reject an `entangled` link target whose `carrier` is not exactly `"tor-v3"`, in the same way it rejects manifests with non-`tor-v3` carriers (§06).

`address` is the carrier address of the destination site.

For Tor v3, `address` is the 56-character onion address followed by `.onion`.

`path` is the path within the destination site and MUST satisfy the same path syntax as content document `path` values.

`expected_publisher_pubkey` is optional. When present, it is the base64url-encoded 32-byte public key the client expects the destination manifest to present as `publisher_pubkey`.

When absent, navigation to the destination is treated as first contact at the destination.

The client MUST NOT navigate to an `entangled` cross-site link without explicit user confirmation in chrome.

The confirmation UI MUST present:

* the destination carrier;
* the destination address;
* the destination path;
* the expected publisher key or PIP information, if declared;
* the fact that navigation leaves the current publisher identity.

If `expected_publisher_pubkey` is declared and the destination manifest presents a different `publisher_pubkey`, the client MUST treat the destination as Changed/mismatch and apply §10.

### URL profile for external targets

The following URL profile applies to both `carrier` and `citation` targets, in addition to the kind-specific scheme and host rules below:

* the value MUST be an absolute RFC 3986 URI with an authority and a non-empty host;
* the authority MUST NOT contain a userinfo component, including an empty userinfo followed by `@`; clients MUST reject userinfo rather than strip it before validating or displaying the host;
* a port is optional. Default and non-default ports are permitted; when present, the port MUST be a non-empty decimal integer in the range 1 through 65535;
* the path may be empty. A query component and a fragment component are each permitted, including an empty query or fragment;
* every unencoded byte MUST be in the RFC 3986 unreserved or reserved ASCII sets. A percent sign MUST begin a complete `%HH` triplet, where each `H` is a hexadecimal digit; uppercase and lowercase hexadecimal digits are both permitted;
* percent-encoded octets are permitted wherever RFC 3986 permits them, including encodings of unreserved or reserved octets. Validation, signing, display, copying, and external handoff MUST preserve the encoded spelling byte-for-byte: clients MUST NOT decode or normalize percent-encoded octets. A percent-encoded delimiter therefore does not acquire delimiter semantics during validation.

These rules intentionally permit queries, fragments, non-default ports, and well-formed percent-encoding. The userinfo prohibition prevents a publisher from presenting an apparent trusted destination before `@` while handing off to a different host, and prevents the validator, chrome, and external URL consumer from disagreeing about which substring is the authority's host.

### `target.kind = "carrier"`

A `carrier` target points to a service reachable through an Entangled-supported carrier but **not** governed by the Entangled protocol. Typical uses are linking to non-Entangled wikis, repositories, or mirrors that exist only as carrier-native services (for example, a non-Entangled Tor onion service).

```json
{
  "kind": "carrier",
  "carrier": "tor-v3",
  "url": "http://<56-character-onion-address>.onion/<path>"
}
```

`carrier` is the carrier profile identifier. A conforming Entangled v1.0 client MUST reject a `carrier` link target whose `carrier` is not exactly `"tor-v3"`, in the same way it rejects manifests with non-`tor-v3` carriers (§06).

`url` is a UTF-8 string. It MUST:

* begin with `http://`;
* have a host that is a valid carrier address for the declared `carrier` - for `tor-v3`, a 56-character onion address followed by `.onion`;
* not exceed 1 KiB when encoded as UTF-8;
* conform to the external-target URL profile above;
* not contain control characters.

`https://` URLs are not permitted as `carrier` targets in v1. The carrier already provides confidentiality and integrity at the rendezvous layer, and the destination identity is anchored at the carrier address itself rather than at a Web PKI certificate, for the same reasons Entangled transport runs over plain HTTP on Tor v3 (§09).

The `carrier` kind does not assert any Entangled publisher identity. The destination is not an Entangled site, so `expected_publisher_pubkey`, `K_publisher`, manifest-level state, and Entangled trust transitions do not apply to it.

The client MUST display `carrier` links distinctly, indicating that the destination is outside Entangled but still reachable via the carrier.

The client MUST NOT navigate automatically to a `carrier` URL.

The user may be offered an external handoff: opening the URL in a carrier-aware external browser (such as Tor Browser for `tor-v3`), copying the URL, or canceling. The handoff mechanism is implementation-defined. However, the client MUST NOT hand a `carrier` URL to a component that would resolve the host through public DNS or route the request over the clearnet, since this would leak the request and defeat the carrier's confidentiality.

`carrier` links MUST NOT carry Entangled request state.

### `target.kind = "citation"`

A `citation` target points to a clearnet URL intended as an external reference.

```json
{
  "kind": "citation",
  "url": "https://example.org/source"
}
```

`url` is a UTF-8 string. It MUST:

* begin with `https://`;
* not exceed 1 KiB when encoded as UTF-8;
* conform to the external-target URL profile above;
* not contain control characters.

`http://` URLs are not permitted as citation targets in v1. Citation targets are by definition clearnet references; over the clearnet, plaintext HTTP is exposed to in-path tampering, injection, and tracking, and the destination must present a Web PKI certificate to be safely opened in a system browser. To link to a non-Entangled service reachable through an Entangled carrier (for example, a non-Entangled onion service), use `target.kind = "carrier"` instead of `citation`.

The client MUST display citation links distinctly, indicating that the destination is outside Entangled.

The client MUST NOT navigate automatically to a citation URL.

The user may be offered an external handoff: opening the URL in an external browser, copying the URL, or canceling. The handoff mechanism is implementation-defined.

Opening a citation URL transmits it to a browser and a network outside Entangled's carrier. The destination's operators, any in-path observer on the clearnet route, and the chosen browser may learn that the URL was reached from the user's local environment, along with whatever identifying metadata each layer collects. This is outside the privacy and integrity properties Entangled provides for in-protocol fetches over a carrier such as Tor v3. The handoff mechanism SHOULD make this trust boundary visible to the user before navigation proceeds, so that the act of opening a citation is an informed step out of Entangled rather than a transparent one.

Citation links MUST NOT carry Entangled request state.

## Link block

A `link` block represents a standalone navigational element. It uses the same target schema as inline links.

```json
{
  "kind": "link",
  "label": [
    { "kind": "text", "value": "Read the technical report", "marks": [] }
  ],
  "target": {
    "kind": "same_site",
    "path": "/reports/2026-q1"
  }
}
```

### Schema

`kind` MUST be exactly `"link"`.

`label` is an inline content array describing the link. It MUST contain at least one element.

`label` MUST NOT contain inline `link` elements. Nested links are not permitted.

`target` is a JSON object conforming to the link target schema.

No other fields are permitted.

### Limits

The total UTF-8 bytes of all `value` strings in `label` MUST NOT exceed 200 bytes.

The serialized `target` object MUST NOT exceed 1 KiB.

## Submit form block

A `submit_form` block declares a form whose user input the client packages into a submit request and sends to a transaction endpoint.

```json
{
  "kind": "submit_form",
  "label": [
    { "kind": "text", "value": "Send a message", "marks": [] }
  ],
  "submit_to": "/contact",
  "fields": [
    {
      "kind": "text",
      "name": "name",
      "label": "Your name",
      "required": true,
      "max_length": 100
    },
    {
      "kind": "textarea",
      "name": "message",
      "label": "Your message",
      "required": true,
      "max_length": 4096
    }
  ],
  "submit_label": "Send"
}
```

### Schema

`kind` MUST be exactly `"submit_form"`.

`label` is an inline content array describing the form. It MUST contain at least one element.

`label` MUST NOT contain inline `link` elements.

`submit_to` is a UTF-8 string containing the path of the transaction endpoint. It MUST satisfy the path syntax defined in §02.

`fields` is a JSON array of form field declarations.

`submit_label` is a UTF-8 string containing the text for the submit button. It MUST NOT contain control characters.

No other fields are permitted.

### Form field schema

Each field in `fields` is a JSON object with a `kind` discriminator and additional fields per kind.

The `kind` of a field is one of:

* `"text"`
* `"textarea"`
* `"select"`
* `"checkbox"`

All field kinds share three required fields:

* `name`
* `label`
* `required`

`name` is an ASCII slug identifying the field in the submitted body. It MUST satisfy the slug syntax:

* characters in `[a-z0-9_-]`;
* begins with `[a-z0-9]`;
* does not exceed 64 characters.

Field names MUST be unique within a single form. A form containing duplicate field `name` values is rejected with `E_SCHEMA_DUPLICATE_ENTRY` (§11).

`label` is a UTF-8 string of up to 200 bytes. It MUST NOT contain control characters.

`required` is a boolean indicating whether the field is required for submission.

Additional fields per kind are defined below.

### Field kind: `text`

A `text` field is a single-line text input.

```json
{
  "kind": "text",
  "name": "subject",
  "label": "Subject",
  "required": true,
  "max_length": 100
}
```

`max_length` is a positive integer specifying the maximum number of UTF-8 bytes accepted.

It MUST be between 1 and 8192 inclusive.

The client renders a single-line input. The user's input MUST NOT contain line feed characters.

The submitted value in §09's `fields` map is a UTF-8 string.

### Field kind: `textarea`

A `textarea` field is a multi-line text input.

```json
{
  "kind": "textarea",
  "name": "message",
  "label": "Your message",
  "required": true,
  "max_length": 4096
}
```

`max_length` is a positive integer specifying the maximum number of UTF-8 bytes accepted.

It MUST be between 1 and 8192 inclusive.

The client renders a multi-line input. The user's input may contain line feed characters U+000A, which are preserved in the submitted value.

The submitted value in §09's `fields` map is a UTF-8 string.

### Field kind: `select`

A `select` field is a single-selection field.

```json
{
  "kind": "select",
  "name": "category",
  "label": "Category",
  "required": true,
  "options": [
    { "value": "support", "label": "Customer support" },
    { "value": "feedback", "label": "Feedback" },
    { "value": "other", "label": "Other" }
  ]
}
```

`options` is a JSON array of option objects.

Each option object has exactly two fields:

* `value`
* `label`

`value` is an ASCII slug satisfying the same slug syntax as field `name`. It MUST NOT exceed 64 characters.

Option values MUST be unique within a single `select` field. A `select` field containing duplicate option `value` entries is rejected with `E_SCHEMA_DUPLICATE_ENTRY` (§11).

`label` is a UTF-8 string of up to 200 bytes. It MUST NOT contain control characters.

The `options` array MUST contain at least one option and MUST NOT exceed 32 options.

The client renders a single-selection control.

If `required` is `true`, the user must select one option before submission.

If `required` is `false`, the client MAY allow no selection. If no option is selected, the submitted value is the empty string.

If an option is selected, the submitted value in §09's `fields` map is the chosen option's `value`.

### Field kind: `checkbox`

A `checkbox` field is a single boolean checkbox.

```json
{
  "kind": "checkbox",
  "name": "subscribe",
  "label": "Subscribe to updates",
  "required": false
}
```

The client renders a checkbox.

The submitted value in §09's `fields` map is exactly:

* `"true"` if checked;
* `"false"` if unchecked.

A checkbox field MUST always be included in the submit body's `fields` map.

A `required` checkbox MUST be checked before the form can be submitted. An unchecked required checkbox prevents submission.

### Form behavior

When the user submits the form, the client packages the field values into a submit body conforming to §09:

* the `fields` map is populated from the user's inputs;
* the `request_state` array is populated by the client according to §07.

The client validates locally before transmission:

* all `required: true` fields have valid values;
* all `text` and `textarea` field values are within their `max_length`;
* all `select` field values are either one of the declared options or the empty string if `required: false`;
* all `checkbox` field values are exactly `"true"` or `"false"`;
* the total submit body does not exceed the §09 submit body limit.

A form failing local validation is not transmitted. The client surfaces validation errors in chrome or in the form area.

Local form validation errors are user-input feedback. They are not document validation errors.

### Limits

The `fields` array MUST contain at least one element and MUST NOT exceed 16 elements.

`submit_label` MUST NOT exceed 100 bytes when encoded as UTF-8.

The total submit body resulting from form submission is bounded by §09.

## Feedback block

A `feedback` block represents a publisher-controlled status or response message.

It is intended primarily for transaction documents, where it conveys success, failure, or informational results of a submit operation.

```json
{
  "kind": "feedback",
  "variant": "success",
  "content": [
    { "kind": "text", "value": "Your message has been received.", "marks": [] }
  ]
}
```

### Schema

`kind` MUST be exactly `"feedback"`.

`variant` is one of the following exact ASCII strings:

* `"success"`
* `"info"`
* `"warning"`
* `"error"`

`content` is an inline content array. It MUST contain at least one element.

No other fields are permitted.

### Usage

The `feedback` block is permitted in `transaction` documents and in `content` documents.

Its primary use is in transaction documents. In content documents, it may be used as a publisher-styled notice.

A `feedback` block is publisher-controlled content. Even when `variant` is `"error"` or `"warning"`, it MUST NOT be rendered as, or visually confused with, a client chrome error or warning.

The visual treatment per `variant` is implementation-defined, subject to the chrome separation requirements in §10.

### Limits

The total UTF-8 bytes of all `value` strings in `content` MUST NOT exceed 2 KiB.

## Note block

A `note` block represents a publisher-controlled callout in content. It is distinct from:

* `quote`, which represents quoted material;
* `feedback`, which represents status or response information.

```json
{
  "kind": "note",
  "variant": "info",
  "title": "Background",
  "content": [
    { "kind": "text", "value": "This section assumes familiarity with...", "marks": [] }
  ]
}
```

### Schema

`kind` MUST be exactly `"note"`.

`variant` is one of the following exact ASCII strings:

* `"info"`
* `"warning"`
* `"danger"`
* `"success"`

`title` is optional. When present, it is a UTF-8 string containing the callout heading. It MUST NOT contain control characters. When absent, the field is omitted. An empty string is not permitted as a substitute.

`content` is an inline content array. It MUST contain at least one element.

No other fields are permitted.

### Usage

The `note` block is for publisher-styled callouts within content.

It is not a security warning. Chrome warnings are client-controlled per §10 and remain distinct.

The visual treatment per `variant` is implementation-defined, subject to the chrome separation requirements in §10.

### Limits

`title` MUST NOT exceed 200 bytes when encoded as UTF-8.

The total UTF-8 bytes of all `value` strings in `content` MUST NOT exceed 4 KiB.

## Block usage by document kind

| Block kind    | Permitted in `content` | Permitted in `transaction` |
| ------------- | ---------------------: | -------------------------: |
| `paragraph`   |                    Yes |                        Yes |
| `heading`     |                    Yes |                        Yes |
| `code_block`  |                    Yes |                        Yes |
| `quote`       |                    Yes |                        Yes |
| `list`        |                    Yes |                        Yes |
| `divider`     |                    Yes |                        Yes |
| `image`       |                    Yes |                        Yes |
| `link`        |                    Yes |                        Yes |
| `submit_form` |                    Yes |                         No |
| `feedback`    |                    Yes |                        Yes |
| `note`        |                    Yes |                        Yes |

A `submit_form` block is not permitted in transaction documents. Transaction documents are responses to submits, not solicitations of further submits.

Including a `submit_form` block in a transaction document causes the document to be rejected with `E_SCHEMA_BLOCK_NOT_PERMITTED`, defined in §11.

All other blocks are permitted in both document kinds, with semantic differences as noted.

## Block validation order

Block validation is part of stage 5, closed-schema validation, of the validation pipeline defined in §10.

For each block in the `blocks` array:

1. The block is a JSON object.
2. The `kind` field is present and is one of the eleven enumerated kinds.
3. The block contains exactly the fields declared for its kind, no more and no fewer.
4. Each field satisfies the type, range, syntax, and length constraints for its position in the block schema.
5. Inline content arrays satisfy inline limits and contain only valid `text` and `link` elements.
6. Link targets satisfy the link target schema.
7. The block does not exceed its own size limits.
8. The block is permitted in the document kind in which it appears.

A block failing any of these checks causes the document to be rejected. Specific diagnostic codes are in §11.

Image resource fetching and decoding are not part of stage 5 block validation. Stage 5 validates the image block schema. Image resource fetching, hash verification, decoding, and rendering occur only after the containing document has been verified.

## What this section does not cover

This section defines the eleven block types and their schemas.

It does not define:

* the document envelope structure or validation pipeline (see §02 and §10);
* canonicalization rules (see §04);
* key roles or signing (see §05);
* the manifest schema (see §06);
* state policy or state update operations (see §07);
* the canary structure (see §08);
* HTTP transport, including image resource fetching (see §09);
* the full client validation pipeline, including the image-fetch, hash-verification, and image-decode pipeline (see §10);
* diagnostic codes for block validation (see §11);
* implementation-specific visual styling.
