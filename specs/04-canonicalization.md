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

The byte sequence length is 74 bytes.

Implementations are expected to reproduce this byte sequence exactly when canonicalizing the input above. Disagreement with this byte sequence indicates a non-conforming JCS implementation or a misapplication of these rules.

This test vector is illustrative. A full conformance corpus, including manifest, content, and transaction documents with known canonical forms and signatures, is distributed separately from the specification text.

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
