# 04 — Canonicalization

This section defines how Entangled JSON values are reduced to a deterministic byte sequence for signing and verification.

Entangled does not redefine canonicalization. It uses the JSON Canonicalization Scheme (JCS) defined in RFC 8785, with verified errata EID 6292 and EID 7920 incorporated.

What §04 specifies, beyond the JCS reference, is which JSON values Entangled documents are permitted to contain before canonicalization. Entangled restricts the JCS input space, eliminating value forms whose canonicalization is defined by JCS but not admitted by the Entangled document grammar.

## JCS reference

Entangled implementations MUST canonicalize JSON values according to RFC 8785, JSON Canonicalization Scheme, with the following verified errata incorporated:

- EID 6292;
- EID 7920.

The combined document is published as the inline-errata version of RFC 8785 by the RFC Editor. Implementations SHOULD use the inline-errata version as their primary reference.

The canonicalization output is a UTF-8 byte sequence. Entangled treats this byte sequence as the cryptographic input substrate for signature operations, as defined in §05.

JCS guarantees, given valid input within its scope:

- deterministic property ordering by lexicographic comparison of UTF-16 code units of property names;
- deterministic number serialization following the ECMAScript number-to-string rules for IEEE 754 double-precision values within the I-JSON range;
- deterministic string serialization with minimal escaping;
- elimination of insignificant whitespace.

Entangled relies on these guarantees and adds no canonicalization rules of its own.

## Entangled input restrictions

The protocol restricts what JSON values Entangled documents may contain before they are passed to JCS. The restrictions apply uniformly to manifest documents, content documents, transaction documents, and nested values within them.

These restrictions are properties of the Entangled grammar, not of JCS. JCS canonicalizes some of the forbidden value forms unambiguously; Entangled forbids them at the schema level so that they never reach the canonicalizer in a conforming document.

Schema validation precedes signature verification in the client pipeline; see §02 and §10. A document containing any forbidden value form is rejected before its canonicalized form is computed.

## No `null` values

No field defined by the Entangled grammar accepts the JSON literal `null` as a valid value.

Behaviors that traditional JSON schemas sometimes express through `null` are expressed in Entangled by other means:

- absent values are encoded by omitting the field, where the schema permits omission;
- explicit deletion semantics use distinct operations, such as the `op: "delete"` form in `state_updates` defined in §07;
- empty collections use empty arrays (`[]`) or empty objects (`{}`).

A document containing a `null` literal at any position is rejected by closed-schema validation before canonicalization.

## No floating-point numbers

All numeric fields in Entangled are non-negative integers within ranges declared by the schema of each field.

The protocol does not use:

- floating-point literals, meaning numbers containing a decimal point;
- exponential notation, meaning numbers containing `e` or `E`;
- non-finite values such as `NaN`, `+Infinity`, or `-Infinity`, none of which are valid JSON in any case;
- negative zero;
- numbers outside the range expressible as a 64-bit signed integer.

A document containing a non-integer numeric value at any position is rejected.

JCS specifies deterministic serialization for numbers based on ECMAScript rules. That serialization is well-defined but is not exercised for floating-point values by Entangled, because Entangled documents never contain floating-point values in conforming form.

### Integer grammar

Every numeric token in an Entangled document MUST match the following grammar exactly, in ABNF form:

```text
integer        = "0" / non-zero-digit *digit
non-zero-digit = %x31-39   ; "1" through "9"
digit          = %x30-39   ; "0" through "9"
```

This is the strict subset of RFC 8259 §6 numbers that produces a non-negative integer with no sign, no leading zeros, no decimal point, and no exponent.

The integer's decimal value MUST be in the range `[0, 2^63 − 1]`. Values outside this range are rejected even if a field's own schema would accept a smaller subset; the absolute upper bound is the protocol's, not the field's.

### Parser-level enforcement

Numeric tokens MUST be validated against the integer grammar at the lexical or parse level, before any conversion to a numeric type.

A JSON parser that converts numeric tokens to IEEE 754 binary64 before applying the grammar is non-conforming for Entangled use. Such a parser cannot reliably distinguish:

- `42`, `42.0`, `4.2e1`, and `42E0` — all convert to the same binary64 value;
- integers above `2^53` — they round silently, so `9007199254740993` becomes `9007199254740992`;
- `-0` from `+0`.

Implementations MUST use one of:

- a JSON parser that exposes each numeric token as a string before numeric conversion, allowing lexical inspection;
- a JSON parser that rejects, during parsing, any numeric token whose lexical form does not match the integer grammar above;
- a separate validation pass over the raw document bytes that verifies every numeric token against the integer grammar before parsed values are used.

A document containing a numeric token that fails the integer grammar is rejected with `E_SCHEMA_NON_INTEGER` (§11). The diagnostic's `stage` field reflects the implementation stage at which the violation was detected; the protocol-level meaning is constant.

## No duplicate member names

Every JSON object in an Entangled document, including nested objects, MUST have unique member names. A document containing duplicate member names at any object level MUST be rejected during JSON parsing, before schema validation and before canonicalization.

This rule applies uniformly to manifest, content, and transaction documents, and to submit bodies.

Implementations MUST configure their JSON parser to detect and reject duplicate member names, rather than silently accepting first-wins or last-wins semantics. Different parser defaults (first-wins, last-wins, merge, error) would otherwise produce divergent validation outcomes across implementations.

## Strict UTF-8 input

All Entangled documents on the wire are UTF-8 byte sequences.

The byte sequence MUST be valid UTF-8 in the strict sense:

- no overlong encodings, meaning sequences using more bytes than necessary;
- no encodings of code points outside U+0000 through U+10FFFF;
- no encodings of UTF-16 surrogate code points, U+D800 through U+DFFF, as standalone characters;
- no malformed sequences, including truncated multi-byte sequences, continuation bytes without a leader, or leader bytes without required continuation bytes.

A response whose body is not strict UTF-8 is rejected before JSON parsing. The body is not parsed as an Entangled document and is not canonicalized.

## No BOM

The Entangled byte sequence MUST NOT begin with a UTF-8 byte-order mark (`EF BB BF`).

A BOM at the start of the document is malformed input. The body is rejected.

JCS canonicalization output, by construction, does not produce a BOM. Implementations that apply UTF-8 BOM stripping in their parsers MUST NOT silently accept a BOM-prefixed Entangled document, since the BOM would be present in the original byte sequence but absent from the canonicalized form, causing signature verification to fail with a misleading error.

## No malformed Unicode material in strings

JSON strings within an Entangled document MUST satisfy all of the following:

- escape sequences resolve to valid Unicode code points;
- `\uXXXX` escapes that participate in surrogate pairs form valid pairs;
- a high surrogate escape, `\uD800` through `\uDBFF`, is followed by a low surrogate escape, `\uDC00` through `\uDFFF`;
- isolated surrogate escapes are rejected;
- escape sequences for control characters are permitted only where the field schema explicitly allows control characters.

For example, line feed `U+000A` is permitted in `canary.statement`, as defined in §08. It is not permitted in `state_policy.purpose`, which is single-line plain text as defined in §07.

JCS produces deterministic output for valid Unicode strings. Entangled rejects malformed Unicode material during validation, before canonicalization is performed.

## Unicode normalization for user-visible strings

JCS canonicalizes UTF-8 byte sequences without applying Unicode normalization. Two visually equivalent strings such as `café` (`63 61 66 C3 A9`, U+0063 U+0061 U+0066 U+00E9) and `café` (`63 61 66 65 CC 81`, U+0063 U+0061 U+0066 U+0065 U+0301) produce distinct JCS outputs and therefore distinct signatures. Without a normalization requirement at the input layer, two publishers' tools or two clients' renderers could produce equivalent-looking content that differs at the byte level, frustrating cross-implementation reproducibility and enabling subtle homograph-style attacks where a publisher's signed statement displays as one thing and signs as another.

To eliminate this ambiguity, every JSON string field whose value Entangled requires the client to display to the user as text MUST be encoded in Unicode Normalization Form C (NFC) as defined by Unicode Standard Annex #15.

The fields subject to this rule are, non-exhaustively:

* `canary.statement` (§08);
* `meta.title` of content documents (§02);
* `navigation` entry `label` fields in the manifest (§06);
* `state_policy` entry `purpose` fields (§07);
* every block text content span and every block string field that the client renders to the user, including in particular `paragraph` runs, `heading` runs, `quote` content, `list` item runs, `link.label`, `image.alt`, `code_block.content`, `feedback.statement`, `note.statement`, `submit_form` form-level labels, and `submit_form.fields[*].label` and `submit_form.fields[*].options[*].label` (§03).

The rule applies to any future field whose semantics include "displayed to the user as text" by a conforming client. A field is subject to NFC if the client is required to render its value as user-visible text; whether a particular field meets this test is determined by the schema section that owns the field.

Fields whose grammar is ASCII-only or whose semantics are non-textual are not subject to NFC. This includes `path` (ASCII), `spec_version`, `kind`, `sig`, all base64url-encoded keys and digests, RFC 3339 timestamp fields, and any field whose value is a structured identifier rather than displayable text.

NFC, not NFD or NFKC or NFKD, is the required form. NFKC and NFKD apply compatibility decomposition that folds characters whose meanings differ (such as `²` and `2`, or `ﬁ` and `fi`), changing the publisher's authored content. NFD requires more bytes than NFC for the same logical content. NFC composes precomposed characters where possible, without case folding, diacritic removal, or compatibility folding; it preserves the publisher's authorial intent while eliminating combining-mark ambiguity.

A document containing a field subject to NFC whose value is not in NFC is rejected with `E_SCHEMA_FIELD_SYNTAX` (§11). The check is performed at schema validation, before signature verification, consistent with the pipeline ordering in §10.

Implementations MUST validate NFC at parse time. They MUST NOT silently re-normalize a non-NFC value to NFC during parsing or canonicalization, because re-normalization would alter the JCS canonical bytes and invalidate the publisher's signature on the unmodified original. Re-normalization at composition time, before the publisher signs, is permitted and is the recommended way for publisher tooling to ensure NFC.

## Strict base64url decoding

Several Entangled fields are base64url-encoded byte strings: signatures (`sig`), public keys (`publisher_pubkey`, `origin_pubkey`, `runtime_pubkey`, `expected_publisher_pubkey`), submit request identifiers (`request_id`), and SHA-256 digest payloads in `image.sha256` and `transaction.request_hash`. Each such field declares its expected decoded length and the corresponding exact ASCII length on the wire (32 bytes / 43 chars, 64 bytes / 86 chars, 16 bytes / 22 chars).

All base64url-encoded fields MUST be decoded using strict RFC 4648 §5 ("Base 64 Encoding with URL and Filename Safe Alphabet") rules. The decoder MUST:

- accept only the URL-safe alphabet: `A-Z`, `a-z`, `0-9`, `-`, `_`;
- reject every character outside this alphabet, including `+`, `/`, whitespace, line breaks, control characters, and any Unicode character above U+007F;
- reject the padding character `=`. Entangled base64url fields are unpadded;
- reject inputs whose length is not the field-declared exact ASCII length;
- reject non-canonical encodings: the unused bits in the final group's encoded character MUST be zero, ensuring a unique decoded byte string for each input.

A field whose value violates any of these rules is rejected with `E_SCHEMA_FIELD_SYNTAX` (§11).

Permissive base64 decoders that accept padded input, silently ignore whitespace, accept the standard `+`/`/` alphabet, or accept non-canonical trailing-group encodings are non-conforming for Entangled use. Implementations MUST configure or replace such decoders.

## Closed-schema validation precedes signature verification

A document is canonicalized and signature-verified only after closed-schema validation has succeeded for all of its top-level fields and nested values.

This ordering ensures that:

- malformed documents are rejected before cryptographic verification;
- the canonicalizer operates only on values within Entangled's restricted input space;
- JCS behavior remains predictable and uniform for all conforming documents;
- signature failures indicate cryptographic mismatch, not schema violation.

The full client validation pipeline order, including the relative position of size limits, JSON parsing, schema validation, canonicalization, and signature verification, is defined in §10.

## Use in signature inputs

The signature input for every signed Entangled object combines a context string, a null-byte separator, and the JCS canonicalization of the signed payload.

The general form, as defined in §05, is:

```text
signed_payload  = document object with top-level `sig` field removed
canonical_bytes = JCS(signed_payload)
signature_input = context_string || 0x00 || canonical_bytes
signature       = Ed25519.sign(signing_key_priv, signature_input)
````

The context strings are exact ASCII byte sequences listed in §05.

The null byte (`0x00`) separates the context from the canonical payload bytes unambiguously. JCS-canonicalized JSON is UTF-8 text and contains no `0x00` byte as a structural separator.

A verifier reconstructs `signature_input` by:

1. extracting the document object received over the wire;
2. removing the top-level `sig` field;
3. canonicalizing the remaining object using JCS;
4. concatenating the appropriate context string, a `0x00` byte, and the canonical bytes;
5. invoking Ed25519 verification with the appropriate public key.

The signature input is never transmitted on the wire. It is constructed locally by the signer and verifier from the document and the protocol-defined context string.

The wire format is the original, non-canonicalized JSON object. JCS guarantees that any conforming canonicalizer produces identical bytes from any equivalent JSON representation of the same value.

## Test vector

The following vector is not a complete Entangled document. It is a minimal JSON value used only to sanity-check JCS behavior under Entangled-compatible value restrictions.

It exercises:

* property ordering by UTF-16 code-unit comparison;
* canonical integer serialization;
* canonical string serialization;
* elimination of insignificant whitespace.

### Input

A JSON object as it might appear on the wire, with insignificant whitespace and arbitrary key order:

```json
{
  "kind": "content",
  "spec_version": "1.0",
  "value": "hello world",
  "count": 42
}
```

### Canonical form

After JCS canonicalization, the byte sequence is exactly:

```text
{"count":42,"kind":"content","spec_version":"1.0","value":"hello world"}
```

Notes on the canonical form:

* properties are reordered by lexicographic comparison of UTF-16 code units of property names: `count` < `kind` < `spec_version` < `value`;
* the integer `42` is serialized without leading zeros, decimal point, or exponent;
* all insignificant whitespace is removed;
* the string `hello world` requires no escaping beyond the surrounding JSON string quotes.

### Bytes

The canonical form, byte by byte, is:

```text
7B 22 63 6F 75 6E 74 22 3A 34 32 2C 22 6B 69 6E
64 22 3A 22 63 6F 6E 74 65 6E 74 22 2C 22 73 70
65 63 5F 76 65 72 73 69 6F 6E 22 3A 22 31 2E 30
22 2C 22 76 61 6C 75 65 22 3A 22 68 65 6C 6C 6F
20 77 6F 72 6C 64 22 7D
```

The byte sequence length is 72 bytes.

Implementations are expected to reproduce this byte sequence exactly when canonicalizing the input above. Disagreement with this byte sequence indicates a non-conforming JCS implementation or a misapplication of these rules.

This test vector is illustrative. The full conformance corpus, including manifest, content, and transaction documents with known canonical forms and signatures, plus negative vectors covering input checks, parsing, schema, numeric grammar, signature strictness, base64url decoding, binding, and canary rules, is distributed in the `corpus/` directory of the specification repository. The corpus is normative: a v1.0-conforming implementation MUST agree with the verdict recorded for each vector.

## What this section does not cover

This section defines the canonicalization scheme and the input restrictions Entangled places on JSON values before canonicalization.

It does not define:

* the document envelope structure or schema (see §02);
* block types and field-level grammar (see §03);
* key roles, signature input construction beyond canonical bytes, or the verification chain (see §05);
* the manifest schema (see §06);
* state policy or state update operations (see §07);
* the canary structure (see §08);
* the HTTP transport (see §09);
* the client validation pipeline order (see §10);
* error codes for canonicalization or schema failures (see §11);
* the conformance corpus, which is distributed separately.
