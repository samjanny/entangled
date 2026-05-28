# 11 - Errors and versioning

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

The following catalog defines all diagnostic codes for Entangled v1.0. Codes are organized primarily by pipeline stage and category, with the Trust state diagnostics group spanning Stage 6 (manifest pre-check) and Stage 7 (resolution) as documented below.

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
| `E_TRANSPORT_CONTENT_ENCODING`   | error    | any           | Response carries a `Content-Encoding` header; encoded responses are not permitted (§09) |
| `E_TRANSPORT_TRANSFER_ENCODING`  | error    | any           | Response carries a `Transfer-Encoding` header; transfer encodings, including chunked, are not permitted (§09) |

When a `3xx` status code is received, `E_TRANSPORT_REDIRECT` takes precedence over `E_TRANSPORT_STATUS`. The client MUST NOT interpret the `Location` header and MUST NOT issue follow-up requests based on it.

## Input diagnostics (Stage 2)

| Code               | Severity | Document kind | Meaning                                                                                                            |
| ------------------ | -------- | ------------- | ------------------------------------------------------------------------------------------------------------------ |
| `E_INPUT_BYTE_CAP` | error    | any           | Body exceeds the byte cap for its kind: 64 KiB for manifest, 1 MiB for content/transaction, 64 KiB for submit body |
| `E_INPUT_UTF8`     | error    | any           | Body is not strict UTF-8                                                                                           |
| `E_INPUT_BOM`      | error    | any           | Body begins with a UTF-8 BOM                                                                                       |

## Parsing diagnostics (Stage 3)

| Code                    | Severity | Document kind | Meaning                                                   |
| ----------------------- | -------- | ------------- | --------------------------------------------------------- |
| `E_PARSE_JSON`          | error    | any           | Body is not parseable as JSON                             |
| `E_PARSE_NESTING_DEPTH` | error    | any           | JSON nesting depth exceeds 16                             |
| `E_PARSE_STRING_LENGTH` | error    | any           | A string exceeds 100 KiB                                  |
| `E_PARSE_ARRAY_LENGTH`  | error    | any           | An array exceeds 10000 elements                           |
| `E_PARSE_OBJECT_KEYS`   | error    | any           | An object has more than 256 keys                          |
| `E_PARSE_DUPLICATE_KEY` | error    | any           | An object in the document contains duplicate member names |

The structured diagnostic format for `E_PARSE_DUPLICATE_KEY` SHOULD include in `details`:

* `duplicate_key`: the duplicated member name;
* `object_path`: a JSON pointer or dot-path identifying the object containing the duplicate.

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
| `E_SCHEMA_ENUM_VIOLATION`      | error    | any           | A field whose value is required to be one of an enumerated set carries a syntactically valid value not in that set. For example, a block `kind` slug not in the enumerated block kinds (§03), an unknown state-policy `mode`, or an unknown transaction `feedback` `variant`. |
| `E_SCHEMA_DUPLICATE_ENTRY`     | error    | any           | An array contains duplicate entries where uniqueness is required by the field's schema (e.g. duplicate `(namespace, key)` in `state_policy`, duplicate field `name` in a `submit_form`, duplicate `value` in `select.options`, duplicate marks in inline `marks`). |
| `E_SCHEMA_FIELD_LENGTH`        | error    | any           | A field exceeds its specific length limit                                                                                                                 |
| `E_SCHEMA_NULL_VALUE`          | error    | any           | A `null` literal appears in the document; null values are not permitted                                                                                   |
| `E_SCHEMA_NON_INTEGER`         | error    | any           | A numeric value is not a non-negative integer permitted by the schema                                                                                     |
| `E_SCHEMA_MALFORMED_UNICODE`   | error    | any           | A string contains malformed Unicode escape sequences or isolated surrogates                                                                               |

The structured diagnostic format for `E_SCHEMA_DUPLICATE_ENTRY` SHOULD include in `details`:

* `field_path`: a JSON pointer or dot-path identifying the array containing the duplicate;
* `duplicate_value`: the duplicated entry value, or for composite uniqueness keys (such as `(namespace, key)`), an object identifying the duplicated key components.

## Signature diagnostics (Stage 6)

| Code                 | Severity | Document kind | Meaning                                                                       |
| -------------------- | -------- | ------------- | ----------------------------------------------------------------------------- |
| `E_SIG_VERIFICATION` | error    | any           | Ed25519 signature verification failed                                         |
| `E_SIG_INVALID_KEY`  | error    | any           | The expected verification key for this document is not available              |
| `E_SIG_MALFORMED`    | error    | any           | The signature cannot be decoded to a 64-byte Ed25519 signature in a context where stage-5 wire-side field-syntax validation does not apply. When the `sig` field is received on the wire, length and base64url-alphabet violations are reported as `E_SCHEMA_FIELD_SYNTAX` at stage 5 per §04 and §10 first-failing-stage precedence. |

For content and transaction documents, `E_SIG_INVALID_KEY` includes the case where no relevant verified manifest is available from which to obtain the authorized `runtime_pubkey`.

## Trust state diagnostics (Stage 6 manifest pre-check and Stage 7 resolution)

`E_TRUST_MISMATCH` and `E_TRUST_USER_REJECTED` are detected during the Stage 6 manifest identity pre-check defined in §10. The structured diagnostic `stage` field for these codes is therefore `6`, and `E_TRUST_MISMATCH` takes precedence over `E_SIG_VERIFICATION` per §10. The remaining codes in this group are emitted as part of Stage 7 trust-state resolution (transitions for First contact, TOFU pinning, and external verification), and carry `stage: 7`.

| Code                    | Severity | Document kind | Meaning                                                                                                           |
| ----------------------- | -------- | ------------- | ----------------------------------------------------------------------------------------------------------------- |
| `E_TRUST_MISMATCH`      | error    | manifest      | The presented `K_publisher.pub` does not match the retained publisher identity for this site or publisher profile |
| `E_TRUST_USER_REJECTED` | error    | manifest      | The user explicitly rejected the presented publisher identity during mismatch resolution                          |
| `I_TRUST_FIRST_CONTACT` | info     | manifest      | First-contact observation recorded for a previously unknown publisher identity                                    |
| `I_TRUST_TOFU_PINNED`   | info     | manifest      | First-contact observation transitioned to TOFU-pinned state                                                       |
| `I_TRUST_VERIFIED`      | info     | manifest      | User externally verified the publisher identity by PIP comparison                                                 |

## Canary diagnostics (Stage 8)

| Code                       | Severity | Document kind | Meaning                                                                                                                                                |
| -------------------------- | -------- | ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `E_CANARY_INVALID`         | error    | manifest      | The canary structure fails validation: malformed fields, interval bounds violated, `issued_at` implausibly in the future, or similar                   |
| `E_CANARY_DOWNGRADE`       | error    | manifest      | Anti-downgrade failure: canary `issued_at` is older than the newest verified `issued_at` for the same `K_publisher.pub`                                |
| `E_CANARY_CONFLICT`        | error    | manifest      | A manifest with the same canary `issued_at` as a previously verified manifest for the same `K_publisher.pub` presents a different signed payload       |
| `W_CANARY_NEAR_EXPIRATION` | warning  | manifest      | The canary is approaching `next_expected`                                                                                                              |
| `W_CANARY_EXPIRED`         | warning  | manifest      | The canary has passed `next_expected`                                                                                                                  |
| `W_CANARY_GAP`             | warning  | manifest      | A canary gap was previously observed and has not been dismissed by the user                                                                            |
| `W_CANARY_UNAVAILABLE`     | warning  | manifest      | The current canary state could not be determined; cached content may be available                                                                      |
| `E_CANARY_RUNTIME_REUSE`   | error    | manifest      | The canary declares the same `runtime_pubkey` as the immediately preceding verified manifest for the same `K_publisher.pub`; key rotation did not occur |

The structured diagnostic format for `E_CANARY_RUNTIME_REUSE` SHOULD include in `details`:

* `runtime_pubkey`: the reused key;
* `previous_issued_at`: the `issued_at` of the preceding manifest that also declared this key;
* `current_issued_at`: the `issued_at` of the current manifest.

The structured diagnostic format for `E_CANARY_CONFLICT` SHOULD include in `details`:

* `issued_at`: the conflicting timestamp;
* `retained_runtime_pubkey`: the `runtime_pubkey` from the previously verified manifest;
* `presented_runtime_pubkey`: the `runtime_pubkey` from the current manifest.

## Binding diagnostics (Stage 9)

| Code                   | Severity | Document kind | Meaning                                                                                                                                                  |
| ---------------------- | -------- | ------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `E_BIND_PATH`          | error    | content       | The `path` field of the content document does not match the path from which it was fetched                                                               |
| `E_BIND_RESPONSE_PATH` | error    | transaction   | The `in_response_to` field of the transaction document does not match the submit path                                                                    |
| `E_BIND_REQUEST_ID`    | error    | transaction   | The `request_id` field of the transaction document does not match the `request_id` the client included in the submit body                                |
| `E_BIND_REQUEST_HASH`  | error    | transaction   | The `request_hash` field of the transaction document does not match the locally computed JCS-hash of the submit body the client sent                     |
| `E_BIND_ORIGIN`        | error    | manifest      | The carrier origin from which the manifest was fetched does not match `origin`, including Tor v3 address-to-key derivation failure                       |
| `E_ORIGIN_EXPIRED`     | error    | manifest      | `origin.not_after` is present and the client's clock is strictly later than the declared instant, applying the past-bound clock-skew tolerance (`current_time > not_after + 300 seconds`); the manifest is not accepted as current |
| `E_ORIGIN_INVALID`     | error    | manifest      | `origin.not_after` is present but violates a semantic constraint (`not_after` not strictly later than `canary.issued_at`, or more than 5 years after `canary.issued_at`)            |
| `E_MIGRATION_MISMATCH` | error    | manifest      | A `migration_pointer` announcement was present, but the successor manifest fetched from the announced address fails a binding check (publisher key, origin address, or origin pubkey) |
| `E_MIGRATION_INVALID`  | error    | manifest      | The `migration_pointer` value is structurally valid JSON but fails semantic checks: successor address equals announcing address, `announced_at` later than manifest `updated`, carrier mismatch, or the successor address is already present in the per-flow `visited_origins` set (a chain cycle; `details.reason = "chain_cycle"`, §10). Reaching the client's automatic chain-depth limit is not a semantic failure and does not produce this diagnostic; per §10 it is a recoverable "pending user action" state resolved by user confirmation. |
| `E_CONTENT_INDEX_FETCH_FAILED` | error | manifest | The manifest declares `content_root` but the `/content_index.json` fetch failed at the transport level; the client MUST NOT render content under this manifest |
| `E_CONTENT_INDEX_HASH_MISMATCH` | error | manifest | The SHA-256 digest of the fetched `/content_index.json` response body bytes does not match the manifest's `content_root` value |
| `E_CONTENT_INDEX_INVALID` | error | manifest | The content index was fetched and hash-verified but fails structural validation: not valid JSON, closed-structure violation, path syntax violation, entry field violation, or exceeds the 1 MiB size cap (§02) |
| `E_CONTENT_SEQ_MISSING` | error | content | The content index has an entry for the document's path, but the content document omits the `seq` field; `seq` is conditionally required when the path is indexed |
| `E_CONTENT_SEQ_ROLLBACK` | error | content | The content document's `seq` is strictly less than the `seq` in the verified content index for the same path |
| `E_CONTENT_SEQ_UNCOMMITTED` | error | content | The content document's `seq` is strictly greater than the `seq` in the verified content index for the same path; the content is not covered by the publisher's `content_root` commitment |
| `E_CONTENT_HASH_MISMATCH` | error | content | The content document's `seq` equals the content index entry's `seq` for the same path, but the SHA-256 digest of the response body bytes does not match the entry's `hash` |

The structured diagnostic format for `E_BIND_REQUEST_ID` and `E_BIND_REQUEST_HASH` SHOULD include in `details`:

* `expected`: the value the client computed (the `request_id` generated for the submit, or the SHA-256 hash of the JCS-canonical submit body);
* `received`: the value the publisher returned in the corresponding transaction field.

The structured diagnostic format for `E_MIGRATION_MISMATCH` SHOULD include in `details`:

* `announced_successor_address`: the address declared by `migration_pointer.successor_origin.address`;
* `successor_publisher_pubkey`: the `publisher_pubkey` observed in the fetched successor manifest, when the successor's own Stage 5 schema validation succeeded; otherwise omitted;
* `announcing_publisher_pubkey`: the `publisher_pubkey` of the announcing manifest;
* `mismatch_field`: which check failed (`publisher_pubkey`, `address`, `origin_pubkey`, or `successor_stage9_failure` when the successor manifest fails any Stage 1 through 9 check independently of the migration-binding fields);
* `underlying_diagnostic_code` (only when `mismatch_field` is `successor_stage9_failure`): the diagnostic code identifier the successor manifest's pipeline would have reported in isolation, encoded as a string (for example, `"E_ORIGIN_EXPIRED"`, `"E_SIG_VERIFICATION"`, or `"E_TRUST_MISMATCH"`). This is the code identifier only, not the full structured diagnostic record: the successor's own `details` object is not nested inside `underlying_diagnostic_code`. An operator wishing to inspect the successor's full diagnostic record fetches the successor manifest in isolation and observes the diagnostic produced by the standard pipeline. The field is informational; the migration is rejected under `E_MIGRATION_MISMATCH` regardless of the underlying cause.

The structured diagnostic format for `E_MIGRATION_INVALID` SHOULD include in `details`:

* `reason`: a short identifier of which semantic check failed, drawn from `self_pointer` (successor address equals announcing address), `announced_at_after_updated` (`migration_pointer.announced_at` is later than the manifest's `updated`), `carrier_mismatch` (the successor's declared carrier does not match the announcing carrier), and `chain_cycle` (the successor address is already present in the per-flow `visited_origins` set, per §10);
* `announcing_origin_address`: the address of the announcing origin;
* `successor_origin_address`: the address declared by `migration_pointer.successor_origin.address`.

The structured diagnostic format for `E_ORIGIN_EXPIRED` SHOULD include in `details`:

* `not_after`: the declared `origin.not_after` value;
* `now`: the client's clock value used for the comparison, rounded down to minute precision (UTC, RFC 3339 form `YYYY-MM-DDTHH:MM:00Z`). The minute-precision rounding limits the precision of any clock-skew leak when the diagnostic is logged or transmitted to third parties (crash reports, support channels) without compromising the diagnostic's usefulness for clock-skew troubleshooting, where minute-level resolution is sufficient.

The structured diagnostic format for `E_ORIGIN_INVALID` SHOULD include in `details`:

* `reason`: a short identifier of which constraint was violated, drawn from `not_after_not_later_than_issued_at` (the declared `not_after` is not strictly later than `canary.issued_at`) and `not_after_beyond_5y` (the declared `not_after` is more than 5 years after `canary.issued_at`);
* `not_after`: the declared `origin.not_after` value;
* `issued_at`: the declared `canary.issued_at` value.

## State diagnostics

State diagnostics arise during state operation processing. They are related to transaction documents but are not part of the main document validation pipeline stages unless the transaction document itself is being validated.

| Code                         | Severity | Document kind | Meaning                                                                                                   |
| ---------------------------- | -------- | ------------- | --------------------------------------------------------------------------------------------------------- |
| `E_STATE_UNDECLARED`         | error    | transaction   | A state update operation references a `(namespace, key)` not declared in the current `state_policy`       |
| `E_STATE_VALUE_SIZE`         | error    | transaction   | A state set operation `value` exceeds the declared `max_size` for the `(namespace, key)`                  |
| `E_STATE_TTL`                | error    | transaction   | A state set operation `ttl` is outside permitted bounds: 300 to 7776000 seconds and within `max_lifetime` |
| `E_STATE_OP`                 | error    | transaction   | A state update operation has an unknown `op` value or is missing required fields for its operation form   |
| `E_STATE_STORAGE_CAP`        | error    | transaction   | The client's per-publisher storage cap would be exceeded by the operation                                 |
| `E_STATE_DUPLICATE`          | error    | transaction   | The `request_state` array of a submit body contains duplicate `(namespace, key)` pairs                    |
| `I_STATE_CONSENT_REJECTED`   | info     | transaction   | The user rejected a state set operation                                                                   |
| `I_STATE_CONSENT_REMEMBERED` | info     | transaction   | The user remembered consent for a state item                                                              |

The structured diagnostic format for `E_STATE_DUPLICATE` SHOULD include in `details`:

* `duplicate_namespace`: the namespace of the duplicated entry;
* `duplicate_key`: the key of the duplicated entry.

`E_STATE_DUPLICATE` is a publisher-side diagnostic in practice: the publisher detects it when parsing the submit body. A conformant client never generates it.

A rejected state set operation does not necessarily invalidate the transaction document. It means the requested state change was not committed. The transaction response may still render as defined in §07 and §10.

## Historical content diagnostics

| Code                              | Severity | Document kind | Meaning                                                                                                                                                                                                                            |
| --------------------------------- | -------- | ------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `E_HISTORICAL_NO_AUTHORIZATION`      | error    | content       | The runtime key signing the historical content is not in the client's authorization history for this `K_publisher.pub`                                                                                                             |
| `E_HISTORICAL_NO_PUBLICATION_PROOF`  | error    | content       | The historical content document cannot be verified as having been published during the authorization window: no content-index entry and no client rendering record exist for the document under the authorizing manifest             |
| `E_HISTORICAL_TRUST_BLOCKED`        | error    | content       | Historical content cannot be rendered while the publisher identity is in Changed/mismatch state                                                                                                                                    |
| `W_HISTORICAL_RENDERED`             | warning  | content       | Historical content is being rendered with the historical-content marker                                                                                                                                                            |
| `W_HISTORICAL_RUNTIME_AMBIGUOUS`    | warning  | content       | Historical content signature verifies under more than one distinct retained `K_runtime.pub` for the same `K_publisher.pub`; the document is rejected as a cryptographic anomaly indicating implementation bug or authorization-history corruption. |

Severity for `W_HISTORICAL_RUNTIME_AMBIGUOUS` is `warning` rather than `error` because the affected document is rejected (per §10) but the condition does not invalidate other content for the same publisher. Clients SHOULD log the condition for offline analysis.

`E_HISTORICAL_NO_PUBLICATION_PROOF` is an error because an attacker who has exfiltrated a former `K_runtime_priv` can fabricate arbitrary documents that verify under the old key but were never published. Without a publication-existence check, historical content mode becomes an avenue for injecting forged content with apparent authenticity. The structured diagnostic format for `E_HISTORICAL_NO_PUBLICATION_PROOF` SHOULD include in `details`: the `path`, the authorizing `K_runtime.pub`, and whether the authorizing manifest carried `content_root`.

## Image resource diagnostics

Image resource diagnostics are warnings. A bad image resource is rendered as missing or as a placeholder. It does not invalidate the containing `content` or `transaction` document.

For image resource diagnostics, `document_kind` is the kind of the containing document: `"content"` when the `image` block appears in a content document, and `"transaction"` when it appears in a transaction document. The structured diagnostic schema enum defined above is unchanged: each diagnostic instance carries exactly one of `"manifest"`, `"content"`, `"transaction"`, or `"none"`. The `containing document` notation in the table column below indicates that these diagnostics select between `"content"` and `"transaction"` per instance.

| Code                    | Severity | Document kind       | Meaning                                                                                                                                                 |
| ----------------------- | -------- | ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `W_IMAGE_HASH_MISMATCH` | warning  | containing document | The SHA-256 digest of the fetched image bytes does not match the hash declared in the `image` block                                                     |
| `W_IMAGE_OVERSIZE`      | warning  | containing document | The image response exceeds the 2 MiB image resource limit before hash verification                                                                      |
| `W_IMAGE_CONTENT_TYPE`  | warning  | containing document | The image response `Content-Type` does not match the declared `media_type`, or is one of the reserved Entangled Content-Types defined in §09            |
| `W_IMAGE_DIMENSIONS`    | warning  | containing document | The decoded image dimensions do not match the declared `width` and `height`                                                                             |
| `W_IMAGE_DECODE_FAILED` | warning  | containing document | The image bytes failed to decode in the declared media format                                                                                           |
| `W_IMAGE_FETCH_FAILED`  | warning  | containing document | The image fetch failed at the transport level, for example timeout, network error, or status code other than `200`                                      |
| `W_IMAGE_BUDGET`        | warning  | containing document | Decoding this image would exceed the document's 16-megapixel decoded pixel budget; the image is rendered as missing                                     |

The structured diagnostic format for `W_IMAGE_BUDGET` SHOULD include in `details`:

* `budget_pixels`: the document budget (16777216 in v1);
* `consumed_pixels`: pixels already consumed by previously decoded images;
* `skipped_image_dimensions`: width and height of the skipped image.

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

This rule defines the wire-format stability guarantee that holds from v1.0 final onward. During the pre-release rc cycle (tags of the form `v1.0-rc.<N>`), the closed schema MAY be extended additively with optional fields without bumping `spec_version`; documents valid under an earlier rc remain valid under a later rc. Examples include `migration_pointer` (added at rc.13) and `origin.not_after` (added at rc.14): both are optional fields, and both leave `spec_version` at `"1.0"`. This pre-freeze relaxation is the release engineering convention documented in `docs/RELEASES.md` and is not part of the v1.0 conformance profile: a conforming v1.0 implementation is one that conforms to the spec at v1.0 final, not to an intermediate rc. Once `v1.0` is tagged final, the closed schema is frozen and the rule above applies without exception.

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
