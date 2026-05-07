# 03 — Block types

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

Duplicate marks within the same `marks` array cause the inline element to be rejected.

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
  "sha256": "base64url-encoded-32-byte-sha256-digest",
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
* does not exceed 256 ASCII characters.

`sha256` is the SHA-256 digest of the exact response body bytes of the image resource, encoded as base64url without padding.

It MUST be exactly 43 ASCII characters, representing a 32-byte digest.

`media_type` is one of exactly:

* `"image/png"`
* `"image/jpeg"`
* `"image/webp"`

No other media types are permitted in Entangled v1.

`width` is the declared image width in pixels. It MUST be an integer from 1 to 4096 inclusive.

`height` is the declared image height in pixels. It MUST be an integer from 1 to 4096 inclusive.

`alt` is a UTF-8 string providing alternative text for accessibility and for cases where the image cannot be displayed. It MUST NOT contain control characters in the range U+0000 through U+001F or U+007F.

`caption` is optional. When present, it is a UTF-8 string. It MUST NOT contain control characters in the range U+0000 through U+001F or U+007F. When absent, the field is omitted. An empty string is not permitted as a substitute.

No other fields are permitted.

### Image fetching and verification

The client MUST NOT fetch an image resource referenced by an `image` block until the containing `content` or `transaction` document has passed signature verification and closed-schema validation.

The client MUST fetch the image resource from the same origin as the containing document. Cross-origin image fetches are not permitted.

The client MUST verify the SHA-256 digest of the exact image response body bytes before decoding or rendering the image.

The verification order is:

1. verify the containing Entangled document;
2. fetch the image from `src` using the image resource fetch rules in §09;
3. enforce image response size limits;
4. compute SHA-256 over the exact response body bytes;
5. compare the digest to the block's `sha256` field;
6. decode the image only if the digest matches;
7. render the image only if the decoded media type and dimensions satisfy the declared fields and protocol limits.

A hash mismatch causes the image to be rejected and rendered as missing or unavailable. A hash mismatch does not by itself invalidate the containing document.

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

### Limits

A `content` or `transaction` document MUST NOT contain more than 16 `image` blocks.

The image response body MUST NOT exceed 1 MiB.

`alt` MUST NOT exceed 1 KiB when encoded as UTF-8.

`caption`, when present, MUST NOT exceed 500 bytes when encoded as UTF-8.

The decoded image dimensions MUST match the declared `width` and `height`. A mismatch causes the image to be rejected. Dimension-mismatch rejection does not invalidate the containing signed document; the image is rendered as missing or unavailable, and the diagnostic is reported under the image resource diagnostics defined in §11.

The decoded image dimensions MUST NOT exceed 4096 by 4096 pixels.

## Link target schema

Links appear in two places:

* inline `link` elements within inline content;
* standalone `link` blocks.

Both use the same `target` schema.

The link target is a JSON object with a discriminator field `kind`.

`target.kind` is one of:

* `"same_site"`
* `"entangled"`
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

### `target.kind = "citation"`

A `citation` target points to a clearnet URL intended as an external reference.

```json
{
  "kind": "citation",
  "url": "https://example.org/source"
}
```

`url` is a UTF-8 string. It MUST:

* begin with `http://` or `https://`;
* not exceed 1 KiB when encoded as UTF-8;
* contain only valid URL characters per RFC 3986;
* not contain control characters.

The client MUST display citation links distinctly, indicating that the destination is outside Entangled.

The client MUST NOT navigate automatically to a citation URL.

The user may be offered an external handoff: opening the URL in an external browser, copying the URL, or canceling. The handoff mechanism is implementation-defined.

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

Field names MUST be unique within a single form.

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

Option values MUST be unique within a single `select` field.

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
