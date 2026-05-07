# 11 — Errors and versioning

This section defines the diagnostic codes Entangled uses to communicate failure conditions, warning conditions, and informational events; the structured diagnostic format implementations are encouraged to follow; and the versioning model that governs protocol evolution.

It does not define implementation-specific user-facing messages, localization, telemetry, metrics, or usage reporting. Those concerns are out of scope.

## Diagnostic model

Entangled clients encounter failures and notable conditions throughout the validation pipeline (§10) and during operational interactions such as state operations, transport handling, and rendering.

Each distinct diagnostic category has a normative diagnostic code.

Diagnostic codes are machine-readable identifiers. They are normative: a client reporting condition X uses the code defined for X. Suggested human-readable labels accompany each code; those labels are not normative and may be localized.

The 10-stage pipeline in §10 defines the order in which validation failures are detected. Error precedence follows pipeline order: the first stage that fails determines the reported error.

Warnings and informational diagnostics do not necessarily abort the operation. Their handling is governed by the severity assigned in this section and by the client behavior requirements in §10.

## Diagnostic code namespace

Entangled diagnostic codes use one of three prefixes:

- `E_` for error conditions;
- `W_` for warning conditions;
- `I_` for informational conditions.

The form is:

```text
<SEVERITY_PREFIX>_<CATEGORY>[_<DETAIL>]
````

`<CATEGORY>` identifies the broad diagnostic type. `<DETAIL>` distinguishes between specific conditions within a category, where the specificity is operationally meaningful.

Codes are uppercase ASCII. They contain only letters and underscores. They do not change once defined; codes are stable for the lifetime of the protocol version.

## Structured diagnostic format

Implementations SHOULD produce diagnostics in the following structured form, suitable for local logging, debugging, and cross-implementation interoperability:

```json
{
  "code": "E_SIG_VERIFICATION",
  "stage": 6,
  "severity": "error",
  "document_kind": "manifest",
  "message": "Manifest signature verification failed.",
  "details": {
    "publisher_pubkey": "...",
    "fetched_origin": "..."
  }
}
```

### Fields

`code` is the normative diagnostic code, as defined in this section. Required.

`stage` is the pipeline stage, 1 through 10, at which the condition was detected, as defined in §10. Required when the condition maps to a pipeline stage. For diagnostics that do not map to a pipeline stage, such as user consent events, implementations SHOULD use `0`.

`severity` is one of `"error"`, `"warning"`, or `"info"`. Required.

* `error`: a hard failure that prevents rendering or operation completion;
* `warning`: a condition the user must be informed of but that does not block rendering by default;
* `info`: an informational notification.

`document_kind` is one of `"manifest"`, `"content"`, `"transaction"`, or `"none"` if the diagnostic is not specific to a document kind. Required.

`message` is a suggested human-readable label for the diagnostic, in English. Implementations MAY substitute a localized message. The `message` field is not normative.

`details` is an object containing additional context relevant to the diagnostic, for debugging or interoperability. The structure of `details` varies by diagnostic code. Optional.

The structured diagnostic format is SHOULD, not MUST. Implementations may use other formats internally as long as the normative `code` is preserved when the diagnostic is exposed cross-implementation.

## Severity assignment

Diagnostic severity is normative for the codes defined below.

A code marked `error` MUST be presented as a hard failure that prevents the affected operation. The client does not render the affected document or commit the affected operation.

A code marked `warning` MUST be presented in chrome with the prominence required by §10. Warnings do not block rendering by default unless a user-selected client policy says otherwise.

A code marked `info` MAY be presented passively. It does not block rendering or operation completion, and persistent display is not required unless another section explicitly requires it.

Implementations MUST NOT change the normative severity assigned to a diagnostic code when reporting that code. A warning remains a warning, and an error remains an error.

A client MAY apply stricter user-selected policies that block rendering or operations in the presence of warning conditions, provided the diagnostic code and its normative severity are still reported accurately. Such policy decisions MUST be presented as client policy, not as a reclassification of the underlying protocol condition.

## Diagnostic code catalog

The following catalog defines all diagnostic codes for Entangled v1.0. Codes are organized by pipeline stage and category.

## Transport diagnostics (Stage 1)

| Code                             | Severity | Document kind | Meaning                                                                            |
| -------------------------------- | -------- | ------------- | ---------------------------------------------------------------------------------- |
| `E_TRANSPORT_STATUS`             | error    | any           | HTTP status code outside the whitelist defined in §09                              |
| `E_TRANSPORT_REDIRECT`           | error    | any           | HTTP 3xx response received; redirects are not supported                            |
| `E_TRANSPORT_CONTENT_TYPE`       | error    | any           | `Content-Type` header missing or does not match the required value                 |
| `E_TRANSPORT_CONTENT_LENGTH`     | error    | any           | `Content-Length` header missing, malformed, or inconsistent with the response body |
| `E_TRANSPORT_BODY_FAILURE`       | error    | any           | Response body could not be retrieved or was truncated by the transport             |
| `E_TRANSPORT_RATE_LIMITED`       | error    | any           | HTTP 429 received; the client backs off before retry                               |
| `E_TRANSPORT_NOT_FOUND`          | error    | any           | HTTP 404 received                                                                  |
| `E_TRANSPORT_METHOD_NOT_ALLOWED` | error    | any           | HTTP 405 received                                                                  |
| `E_TRANSPORT_PAYLOAD_TOO_LARGE`  | error    | transaction   | HTTP 413 received in response to a submit                                          |
| `E_TRANSPORT_UNAVAILABLE`        | error    | any           | HTTP 503 received or transport-level unreachability                                |
| `E_TRANSPORT_BAD_REQUEST`        | error    | transaction   | HTTP 400 received in response to a submit                                          |

When a `3xx` status code is received, `E_TRANSPORT_REDIRECT` takes precedence over `E_TRANSPORT_STATUS`. The client MUST NOT interpret the `Location` header and MUST NOT issue follow-up requests based on it.

## Input diagnostics (Stage 2)

| Code               | Severity | Document kind | Meaning                                                                                                            |
| ------------------ | -------- | ------------- | ------------------------------------------------------------------------------------------------------------------ |
| `E_INPUT_BYTE_CAP` | error    | any           | Body exceeds the byte cap for its kind: 64 KiB for manifest, 1 MiB for content/transaction, 64 KiB for submit body |
| `E_INPUT_UTF8`     | error    | any           | Body is not strict UTF-8                                                                                           |
| `E_INPUT_BOM`      | error    | any           | Body begins with a UTF-8 BOM                                                                                       |

## Parsing diagnostics (Stage 3)

| Code                    | Severity | Document kind | Meaning                          |
| ----------------------- | -------- | ------------- | -------------------------------- |
| `E_PARSE_JSON`          | error    | any           | Body is not parseable as JSON    |
| `E_PARSE_NESTING_DEPTH` | error    | any           | JSON nesting depth exceeds 16    |
| `E_PARSE_STRING_LENGTH` | error    | any           | A string exceeds 100 KiB         |
| `E_PARSE_ARRAY_LENGTH`  | error    | any           | An array exceeds 10000 elements  |
| `E_PARSE_OBJECT_KEYS`   | error    | any           | An object has more than 256 keys |

## Document kind diagnostics (Stage 4)

| Code                    | Severity | Document kind | Meaning                                                                                   |
| ----------------------- | -------- | ------------- | ----------------------------------------------------------------------------------------- |
| `E_KIND_MISSING_FIELDS` | error    | any           | One or more of `spec_version`, `kind`, or `sig` is absent or has the wrong primitive type |
| `E_KIND_SPEC_VERSION`   | error    | any           | `spec_version` is not exactly `"1.0"`                                                     |
| `E_KIND_UNKNOWN`        | error    | any           | `kind` is not one of `"manifest"`, `"content"`, `"transaction"`                           |

## Schema diagnostics (Stage 5)

| Code                           | Severity | Document kind | Meaning                                                                                                                                                   |
| ------------------------------ | -------- | ------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `E_SCHEMA_REQUIRED_FIELD`      | error    | any           | A required field is absent                                                                                                                                |
| `E_SCHEMA_UNKNOWN_FIELD`       | error    | any           | A field not permitted by the schema is present                                                                                                            |
| `E_SCHEMA_BLOCK_NOT_PERMITTED` | error    | any           | A block of an enumerated kind appears in a document kind that does not permit that block. For example, a `submit_form` block in a `transaction` document. |
| `E_SCHEMA_FIELD_TYPE`          | error    | any           | A field has the wrong type                                                                                                                                |
| `E_SCHEMA_FIELD_RANGE`         | error    | any           | A numeric field is outside its permitted range                                                                                                            |
| `E_SCHEMA_FIELD_SYNTAX`        | error    | any           | A string field violates its declared syntax: slug rules, base64url format, RFC 3339 form, path syntax, or similar                                         |
| `E_SCHEMA_FIELD_LENGTH`        | error    | any           | A field exceeds its specific length limit                                                                                                                 |
| `E_SCHEMA_NULL_VALUE`          | error    | any           | A `null` literal appears in the document; null values are not permitted                                                                                   |
| `E_SCHEMA_NON_INTEGER`         | error    | any           | A numeric value is not a non-negative integer permitted by the schema                                                                                     |
| `E_SCHEMA_MALFORMED_UNICODE`   | error    | any           | A string contains malformed Unicode escape sequences or isolated surrogates                                                                               |

## Signature diagnostics (Stage 6)

| Code                 | Severity | Document kind | Meaning                                                                       |
| -------------------- | -------- | ------------- | ----------------------------------------------------------------------------- |
| `E_SIG_VERIFICATION` | error    | any           | Ed25519 signature verification failed                                         |
| `E_SIG_INVALID_KEY`  | error    | any           | The expected verification key for this document is not available              |
| `E_SIG_MALFORMED`    | error    | any           | The `sig` field is not a valid 64-byte Ed25519 signature encoded as base64url |

For content and transaction documents, `E_SIG_INVALID_KEY` includes the case where no relevant verified manifest is available from which to obtain the authorized `runtime_pubkey`.

## Trust state diagnostics (Stage 7)

| Code                    | Severity | Document kind | Meaning                                                                                                           |
| ----------------------- | -------- | ------------- | ----------------------------------------------------------------------------------------------------------------- |
| `E_TRUST_MISMATCH`      | error    | manifest      | The presented `K_publisher.pub` does not match the retained publisher identity for this site or publisher profile |
| `E_TRUST_USER_REJECTED` | error    | manifest      | The user explicitly rejected the presented publisher identity during mismatch resolution                          |
| `I_TRUST_FIRST_CONTACT` | info     | manifest      | First-contact observation recorded for a previously unknown publisher identity                                    |
| `I_TRUST_TOFU_PINNED`   | info     | manifest      | First-contact observation transitioned to TOFU-pinned state                                                       |
| `I_TRUST_VERIFIED`      | info     | manifest      | User externally verified the publisher identity by PIP comparison                                                 |

## Canary diagnostics (Stage 8)

| Code                       | Severity | Document kind | Meaning                                                                                                                              |
| -------------------------- | -------- | ------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| `E_CANARY_INVALID`         | error    | manifest      | The canary structure fails validation: malformed fields, interval bounds violated, `issued_at` implausibly in the future, or similar |
| `E_CANARY_DOWNGRADE`       | error    | manifest      | Anti-downgrade failure: canary `issued_at` is older than the newest verified `issued_at` for the same `K_publisher.pub`              |
| `W_CANARY_NEAR_EXPIRATION` | warning  | manifest      | The canary is approaching `next_expected`                                                                                            |
| `W_CANARY_EXPIRED`         | warning  | manifest      | The canary has passed `next_expected`                                                                                                |
| `W_CANARY_GAP`             | warning  | manifest      | A canary gap was previously observed and has not been dismissed by the user                                                          |
| `W_CANARY_UNAVAILABLE`     | warning  | manifest      | The current canary state could not be determined; cached content may be available                                                    |

## Binding diagnostics (Stage 9)

| Code                   | Severity | Document kind | Meaning                                                                                                                            |
| ---------------------- | -------- | ------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| `E_BIND_PATH`          | error    | content       | The `path` field of the content document does not match the path from which it was fetched                                         |
| `E_BIND_RESPONSE_PATH` | error    | transaction   | The `in_response_to` field of the transaction document does not match the submit path                                              |
| `E_BIND_ORIGIN`        | error    | manifest      | The carrier origin from which the manifest was fetched does not match `origin`, including Tor v3 address-to-key derivation failure |

## State diagnostics

State diagnostics arise during state operation processing. They are related to transaction documents but are not part of the main document validation pipeline stages unless the transaction document itself is being validated.

| Code                         | Severity | Document kind | Meaning                                                                                                   |
| ---------------------------- | -------- | ------------- | --------------------------------------------------------------------------------------------------------- |
| `E_STATE_UNDECLARED`         | error    | transaction   | A state update operation references a `(namespace, key)` not declared in the current `state_policy`       |
| `E_STATE_VALUE_SIZE`         | error    | transaction   | A state set operation `value` exceeds the declared `max_size` for the `(namespace, key)`                  |
| `E_STATE_TTL`                | error    | transaction   | A state set operation `ttl` is outside permitted bounds: 300 to 7776000 seconds and within `max_lifetime` |
| `E_STATE_OP`                 | error    | transaction   | A state update operation has an unknown `op` value or is missing required fields for its operation form   |
| `E_STATE_STORAGE_CAP`        | error    | transaction   | The client's per-publisher storage cap would be exceeded by the operation                                 |
| `I_STATE_CONSENT_REJECTED`   | info     | transaction   | The user rejected a state set operation                                                                   |
| `I_STATE_CONSENT_REMEMBERED` | info     | transaction   | The user remembered consent for a state item                                                              |

A rejected state set operation does not necessarily invalidate the transaction document. It means the requested state change was not committed. The transaction response may still render as defined in §07 and §10.

## Historical content diagnostics

| Code                            | Severity | Document kind | Meaning                                                                                                                |
| ------------------------------- | -------- | ------------- | ---------------------------------------------------------------------------------------------------------------------- |
| `E_HISTORICAL_NO_AUTHORIZATION` | error    | content       | The runtime key signing the historical content is not in the client's authorization history for this `K_publisher.pub` |
| `E_HISTORICAL_TRUST_BLOCKED`    | error    | content       | Historical content cannot be rendered while the publisher identity is in Changed/mismatch state                        |
| `W_HISTORICAL_RENDERED`         | warning  | content       | Historical content is being rendered with the historical-content marker                                                |

## Image resource diagnostics

Image resource diagnostics are warnings. A bad image resource is rendered as missing or as a placeholder. It does not invalidate the containing `content` or `transaction` document.

For image resource diagnostics, `document_kind` is the kind of the containing document: `"content"` when the `image` block appears in a content document, and `"transaction"` when it appears in a transaction document. The structured diagnostic schema enum defined above is unchanged: each diagnostic instance carries exactly one of `"manifest"`, `"content"`, `"transaction"`, or `"none"`. The `containing document` notation in the table column below indicates that these diagnostics select between `"content"` and `"transaction"` per instance.

| Code                    | Severity | Document kind       | Meaning                                                                                                                                                 |
| ----------------------- | -------- | ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `W_IMAGE_HASH_MISMATCH` | warning  | containing document | The SHA-256 digest of the fetched image bytes does not match the hash declared in the `image` block                                                     |
| `W_IMAGE_OVERSIZE`      | warning  | containing document | The image response exceeds the 1 MiB image resource limit before hash verification                                                                      |
| `W_IMAGE_CONTENT_TYPE`  | warning  | containing document | The image response `Content-Type` does not match the declared `media_type`, or is one of the reserved Entangled Content-Types defined in §09            |
| `W_IMAGE_DIMENSIONS`    | warning  | containing document | The decoded image dimensions do not match the declared `width` and `height`                                                                             |
| `W_IMAGE_DECODE_FAILED` | warning  | containing document | The image bytes failed to decode in the declared media format                                                                                           |
| `W_IMAGE_FETCH_FAILED`  | warning  | containing document | The image fetch failed at the transport level, for example timeout, network error, or status code other than `200`                                      |

## Error reporting requirements

The client MUST report errors at their actual point of failure, in pipeline order (§10).

The client MUST display `error` severity codes in chrome and MUST NOT render the affected document or commit the affected operation.

The client MUST display `warning` severity codes in chrome with the prominence required by §10. Warnings do not block rendering by default unless user-selected client policy says otherwise.

The client MAY display `info` severity codes passively or omit them, unless another section requires a visible notification.

The diagnostic code, when displayed to the user, SHOULD be accompanied by a human-readable description appropriate to the user's locale. The description is not normative.

In all cases, the client's chrome MUST continue to display the actual current trust state, canary state, and other status indicators. A failed operation does not transiently change trust or canary state.

## Versioning

Entangled uses a three-axis versioning model. The three axes are independent.

## Protocol version

The protocol version identifies which version of the Entangled protocol a document conforms to. It is carried in the `spec_version` field of every Entangled document.

Entangled v1 defines exactly one protocol version:

```json
"spec_version": "1.0"
```

There is no `"1.0.1"` and no `"1.1"` at the document protocol-version level.

The reason is structural. Entangled v1 uses closed schemas at every document layer. Adding a new field to a closed schema causes parsers conforming to the previous schema to reject the document with `E_SCHEMA_UNKNOWN_FIELD`. Therefore any change to the accepted wire format, including additive fields, is a breaking change at the protocol level. There is no middle ground for additive minor revisions within v1.

A future protocol version will use a different `spec_version` value, for example `"2.0"`, and a different family of signing context strings, for example `ENTANGLED-v2 manifest`. Documents from different protocol versions are not interchangeable.

## Spec release

The spec release identifies which revision of the specification document a reader is consulting. It is carried in the specification's own metadata, such as release notes, version control tags, or document headers, and not in any Entangled document.

Spec releases follow the pattern chosen by the project, for example `1.0-draft-3`, `1.0-rc-1`, `1.0`, or `1.0.1`.

Releases beyond the initial `1.0` correct or clarify specification text without changing what conforming documents look like on the wire or how they are validated.

A spec release MUST NOT change normative protocol behavior. If a clarification reveals that the current spec text is ambiguous or incorrect, and resolving the ambiguity would change wire-level behavior or validation outcomes, the resolution requires a new protocol version, not a new spec release.

A spec release MAY:

* correct typographical errors;
* clarify ambiguous wording without changing meaning;
* add or improve examples and test vectors;
* improve organization, cross-references, or non-normative discussion;
* adjust style, terminology presentation, or formatting.

A spec release MUST NOT:

* change wire-format requirements;
* change diagnostic codes or their semantics;
* change validation behavior;
* change cryptographic primitives or signature input construction;
* change conformance requirements.

The spec release is for human readers of the specification. It does not affect Entangled clients or publishers at runtime.

## Implementation version

The implementation version identifies a specific build of an Entangled client, server, or library. It follows whatever versioning scheme the implementation chooses, typically semantic versioning.

The implementation version is independent of the protocol version and the spec release. An implementation MAY release multiple versions targeting the same protocol version, with bug fixes, performance improvements, or feature additions internal to the implementation.

The implementation version is implementation metadata. It does not affect protocol behavior.

## Breaking changes

A breaking change is any modification that prevents a conformant v1.0 implementation from correctly validating a document, processing a manifest, or operating with a v1.0 publisher or client.

Breaking changes require a new protocol version. The protocol version is reflected in:

* the `spec_version` field of all documents, for example `"2.0"`;
* the family of signing context strings, for example `ENTANGLED-v2 manifest`, `ENTANGLED-v2 content`, `ENTANGLED-v2 transaction`;
* any changed schema, semantics, or cryptographic primitive.

A v1.0 client MUST reject documents declaring a `spec_version` other than `"1.0"`. The rejection uses diagnostic code `E_KIND_SPEC_VERSION`.

A v2.0 client MAY support v1.0 documents in compatibility mode. Compatibility mode is a v2.0 client decision, not a v1.0 protocol guarantee. No v1 client is expected to handle v2 documents.

The signing context string family, `ENTANGLED-v1 ...`, provides cryptographic separation between protocol versions. A v1.0 signature is not valid for v2.0 verification, and vice versa, even when the underlying JCS bytes are identical. This is intentional: domain separation between protocol versions is part of the cryptographic security model.

## Deprecation

Deprecation of a feature, carrier profile, or syntactic form is communicated through specification text only. There is no in-protocol deprecation flag.

If a future version of the protocol removes a feature, that removal is a breaking change and triggers a new protocol version.

Within a given protocol version, all features defined in that version remain available and conformant.

Deprecation notices in the specification text serve to inform implementers and publishers of upcoming changes that may affect them in a future protocol version. They do not change the behavior of the current protocol version.

## Forward compatibility

Entangled v1 does not define forward-compatibility mechanisms.

A v1.0 client encountering a document whose `spec_version` is not exactly `"1.0"` rejects it with `E_KIND_SPEC_VERSION`.

There is no partial parsing, no field skipping, and no graceful degradation for unknown protocol versions.

This rigidity is consistent with the closed-schema discipline. The protocol treats unknown content as a structural failure, not as an opportunity for best-effort interpretation.

Future protocol versions MAY define migration paths or compatibility profiles. Such paths, when defined, belong to the specification of the future version.

## What this section does not cover

This section defines the diagnostic code catalog, the structured diagnostic format, and the three-axis versioning model.

It does not define:

* implementation-specific user-facing messages or localization;
* diagnostic logging formats beyond the SHOULD-level structured diagnostic object;
* telemetry, metrics, or usage reporting;
* the spec release process, branching strategy, or document publication workflow;
* migration strategies between protocol versions, which are the responsibility of each protocol version's specification when defined;
* specific behaviors of any particular implementation.
