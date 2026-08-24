# 09 - Transport

This section defines the HTTP subset over which Entangled documents are fetched and submitted. The transport profile is intentionally minimal: it specifies what is permitted, what is required, and what is ignored. Behavior outside this profile is non-conformant.

Entangled v1 fully specifies the Tor v3 transport profile. Other carrier profiles (I2P, Yggdrasil) define their own transport rules; until specified, they are draft profiles and not part of v1 conformance.

## Media types and registration status

Entangled v1 uses the RFC 6838 vendor-tree media types `application/vnd.entangled+json` for signed Entangled documents and `application/vnd.entangled-submit+json` for submit bodies. These are the only normative v1 wire names; implementations MUST NOT treat the former unregistered standards-tree names `application/entangled+json` and `application/entangled-submit+json`, or any `prs.` or `x-` alias, as equivalent.

As of v1.0-rc.64, IANA registration of both vendor-tree media types is pending Expert Review and is tracked in [issue #40](https://github.com/samjanny/entangled/issues/40). This registration status is informative and does not change the normative wire names. Once assigned, the permanent IANA registry entries will be linked here.

## Transport assumptions

Entangled assumes the carrier provides:

- reachability between the client and the publishing infrastructure;
- transport-layer confidentiality and integrity, where applicable;
- network-layer anonymity, where applicable.

For Tor v3, these properties are provided by the onion service infrastructure. The publishing infrastructure runs an onion service whose `K_origin` private key is held locally; the client connects through the Tor network to that onion service.

Entangled does not require HTTPS over Tor v3. The carrier already provides confidentiality and integrity through onion-service end-to-end encryption. Adding TLS over Tor v3 introduces operational complexity and a dependency on the Web PKI without strengthening the security model. Publisher identity in Entangled is anchored at `K_publisher`, not at a TLS certificate or web-PKI assertion.

Clients MUST NOT use public Web PKI certificate validation as publisher identity for Entangled sites.

Other carrier profiles MAY require transport-layer encryption, such as TLS, when the carrier itself does not provide confidentiality. The carrier profile specifies the requirement.

The transport rules in this section govern requests issued by the Entangled client to Entangled endpoints. They do not constrain how the client hands off non-Entangled URLs (`target.kind = "carrier"` or `"citation"`, see §03) to external components such as Tor Browser or a system browser; those handoffs are external to the Entangled protocol.

## HTTP version and methods

Entangled uses HTTP/1.1 over the carrier connection.

The client MUST issue requests using only the following methods:

- `GET`, used for fetching the manifest and content documents;
- `POST`, used for submit requests.

A client MUST NOT use any other HTTP method.

A publisher MUST reject requests using methods other than `GET` and `POST`.

The publisher MAY respond to non-`GET`, non-`POST` requests with `405 Method Not Allowed`, or it MAY treat such requests as malformed at the transport level and close the connection.

## URLs

Entangled URLs use the carrier-specific scheme and authority for the address, plus an absolute path within the site. Query strings and fragments are not part of the protocol-defined URL space.

For Tor v3:

```text
http://<56-character-onion-address>.onion/<path>
````

The scheme is `http`, not `https`, for the reasons described in transport assumptions.

The path component MUST satisfy the path syntax defined in §02 for content document `path` values: ASCII slug characters, leading `/`, no consecutive `/`, no `.` or `..` segments, no query string, and no fragment.

Query strings and fragments in URLs are forbidden in Entangled v1. A publisher MUST NOT serve content from URLs with query strings. A client MUST NOT generate URLs with query strings or fragments.

This eliminates a class of injection, cache-key confusion, and tracking patterns common to traditional web protocols.

## Manifest fetch

The manifest is fetched at the canonical path `/manifest.json` on every Entangled site:

```http
GET /manifest.json HTTP/1.1
Host: <56-character-onion-address>.onion
```

The manifest fetch is a `GET` request with no request body.

The publisher responds with `200 OK` and the manifest document as the response body. Response headers are defined below.

The client validates the manifest as defined in §06 and §05. A failure rejects the manifest; the client MAY retry after a delay.

## Content fetch

A content document is fetched at the path declared by the document's `path` field:

```http
GET /<content-path> HTTP/1.1
Host: <56-character-onion-address>.onion
```

The content fetch is a `GET` request with no request body.

The publisher responds with `200 OK` and the content document as the response body, or with `404 Not Found` if the path does not exist.

The client validates the content document as defined in §02 and §05, including the byte-exact `path` binding check defined in §02.

State is not transmitted in content fetches. Request-mode state items are excluded from `GET` requests by §07.

## Content index fetch

When the manifest contains a `content_root` field (§06), the client fetches the content index at the reserved path `/content_index.json` on the same carrier origin:

```http
GET /content_index.json HTTP/1.1
Host: <56-character-onion-address>.onion
```

The content index fetch is a `GET` request with no request body. It uses the same restrictive request-header discipline as manifest and content fetches.

The publisher responds with `200 OK` and the content index as the response body.

The response MUST include:

* `Content-Type: application/json`. The content index is not an Entangled signed document; it MUST NOT use `Content-Type: application/vnd.entangled+json`.
* `Content-Length` with the exact byte count of the response body. Responses without `Content-Length` are rejected as `E_CONTENT_INDEX_FETCH_FAILED`.

The response MUST NOT use `Content-Encoding` or `Transfer-Encoding`. The hash binding in `content_root` is over the exact response body bytes; any transfer-layer transformation invalidates the hash. A response carrying `Content-Encoding` or `Transfer-Encoding` is rejected as `E_CONTENT_INDEX_FETCH_FAILED`.

For the `/content_index.json` resource, the content-index-specific code `E_CONTENT_INDEX_FETCH_FAILED` displaces the generic Stage 1 transport codes. Every transport violation listed above for this resource maps to `E_CONTENT_INDEX_FETCH_FAILED`, not to the generic Stage 1 code that would otherwise apply to an Entangled signed document: a missing or inconsistent `Content-Length` maps to `E_CONTENT_INDEX_FETCH_FAILED` and not `E_TRANSPORT_CONTENT_LENGTH`; a present `Content-Encoding` maps to `E_CONTENT_INDEX_FETCH_FAILED` and not `E_TRANSPORT_CONTENT_ENCODING`; a present `Transfer-Encoding` maps to `E_CONTENT_INDEX_FETCH_FAILED` and not `E_TRANSPORT_TRANSFER_ENCODING`. A `Content-Type` other than `application/json` likewise maps to `E_CONTENT_INDEX_FETCH_FAILED` and not `E_TRANSPORT_CONTENT_TYPE`. The content index is not an Entangled signed document, and the Stage 1 transport classification that produces the generic codes is defined for the Entangled-document fetch path; the content-index fetch is its own resource path and carries its own single failure code so that two conforming implementations report the same code on the same wire condition regardless of whether they branch on the resource path before or after Stage 1 classification.

The client enforces the 1 MiB byte cap defined in §02 before parsing. A response body exceeding 1 MiB is rejected as `E_CONTENT_INDEX_INVALID` (§11).

The client verifies the SHA-256 digest of the exact response body bytes against the manifest's `content_root` value. Mismatch is `E_CONTENT_INDEX_HASH_MISMATCH` (§11). The client then validates the content index against the closed structure defined in §02. Structural failure is `E_CONTENT_INDEX_INVALID` (§11).

A non-`200` response is `E_CONTENT_INDEX_FETCH_FAILED` (§11). When the manifest declares `content_root` and the content index cannot be obtained, the client MUST NOT render content documents from the site under that manifest; this is a hard-fail model, because `content_root` is a `K_publisher`-signed commitment and failure to honor it is indistinguishable from server compromise.

Because the index could not be obtained, the per-document content-index checks against that manifest are not evaluated: the client has no verified content index to evaluate `E_CONTENT_SEQ_MISSING`, `E_CONTENT_HASH_MISMATCH`, `E_CONTENT_SEQ_ROLLBACK`, or `E_CONTENT_SEQ_UNCOMMITTED` against. The hard-fail above already blocks all content rendering under the manifest, so a content document that, for example, omits `seq` is not separately rejected as `E_CONTENT_SEQ_MISSING`; the surface diagnostic for the rendering block remains `E_CONTENT_INDEX_FETCH_FAILED`. These per-document checks resume only once a content index for the manifest has been fetched, hash-verified, and structurally validated.

State is not transmitted in content index fetches.

## Submit request

A submit is a `POST` request to a transaction endpoint declared by the publisher, typically declared in `blocks` of a content document; see §03.

```http
POST /<submit-path> HTTP/1.1
Host: <56-character-onion-address>.onion
Content-Type: application/vnd.entangled-submit+json
Content-Length: <bytes>

<submit body>
```

The submit body is a JSON object as defined below.

The publisher responds with `200 OK` and a transaction document as the response body, or with an error status as defined below.

The transaction document's `in_response_to` field MUST equal the submit path, byte-exact, as defined in §02. The transaction document's `request_id` MUST equal the `request_id` of the submit body, and its `request_hash` MUST equal the SHA-256 digest of the JCS-canonical submit body, both as defined in §02. The client rejects a transaction whose `in_response_to`, `request_id`, or `request_hash` does not match.

### Submit body schema

The submit body is a flat JSON object with exactly three top-level fields:

```json
{
  "fields": {
    "message": "hello",
    "name": "alice"
  },
  "request_state": [
    {
      "namespace": "session",
      "key": "auth",
      "value": "..."
    }
  ],
  "request_id": "AAECAwQFBgcICQoLDA0ODw"
}
```

All three fields are required. No additional top-level fields are permitted.

The submit body is unsigned. It is user input transmitted under carrier-provided confidentiality. The client does not sign submit requests in Entangled v1.

Because submit bodies are unsigned user input, publishers MUST treat all submit fields and request-state values as untrusted input.

#### `request_id`

`request_id` is a base64url string encoding 16 random bytes (128 bits) with no padding (22 ASCII characters).

The client MUST generate `request_id` using a cryptographically secure random source. Each submit MUST carry a freshly generated `request_id`; the no-reuse rules are stated under "Collision avoidance" below.

`request_id` is in the unsigned submit body. It is not signed by the client (the client signs nothing in v1). The publisher echoes it in the corresponding transaction document, as defined in §02, where it is signed under `K_runtime` together with the `request_hash` that binds the transaction to the specific submit body bytes.

Collision avoidance.

The 128-bit `request_id` space makes accidental collisions across submits astronomically unlikely. The client MUST NOT reuse a `request_id` across submits, including retries of a previously failed submit. Concurrent in-flight submits to the same publisher MUST NOT carry identical `request_id` values; in practice this is satisfied by drawing each `request_id` from a cryptographically secure random source.

The publisher SHOULD treat a `request_id` seen in an active submit as unique to that submit; concurrent submits with identical `request_id` values are a malformed-client condition and MAY be rejected at the publisher's discretion.

#### `fields`

`fields` is a JSON object representing the user input portion of the submit.

It MUST be a flat object whose keys are ASCII strings and whose values are UTF-8 strings.

Constraints:

* the object MUST contain between 0 and 32 key-value pairs;
* each key MUST satisfy the same slug syntax used for state `namespace` and `key`: one or more ASCII characters in `[a-z0-9_-]`, beginning with `[a-z0-9]`, and not exceeding 64 characters;
* each value MUST be a UTF-8 string not exceeding 8 KiB;
* the object MUST NOT contain nested objects, arrays, numbers, booleans, or null values.

If the submit carries no user input, for example a `logout` submit that only manipulates request state, `fields` is an empty object:

```json
"fields": {}
```

Publishers serializing structured user input must encode it as a string within a single field.

#### `request_state`

`request_state` is a JSON array containing the request-mode state items the client is transmitting with this submit.

Each entry has exactly three fields:

```json
{
  "namespace": "session",
  "key": "auth",
  "value": "..."
}
```

Constraints:

* the array MUST contain between 0 and 32 entries;
* each `namespace` and `key` MUST satisfy the slug syntax defined in §07;
* each `value` MUST be a UTF-8 string whose raw UTF-8 byte length does not exceed 4096 bytes, the protocol's absolute state-value ceiling (§07 `max_size`). This ceiling is measured on the value's own UTF-8 bytes before JSON escaping, consistent with `max_size`; it is distinct from the value's contribution to the submit-body wire budget, which counts JSON-escaped bytes (see "Submit body budget partition" below). Publishers MAY reject submit bodies carrying a larger `value` as malformed;
* entries reflect the state items the client is transmitting at submit time, scoped to the same `K_publisher.pub` that authorized the manifest currently in effect for this site.

The `request_state` array MUST NOT contain duplicate `(namespace, key)` pairs. Each `(namespace, key)` appears at most once in a single submit body. Publishers MUST reject submit bodies containing duplicate `request_state` entries.

If the user has no consented request-state items applicable to this submit, `request_state` is an empty array:

```json
"request_state": []
```

The client constructs `request_state` from its own state store. The user does not directly compose it. The retrieval rules are defined in §07.

### Submit body size limit

The submit body MUST NOT exceed 64 KiB on the wire.

The publisher MAY reject submits exceeding this size with `413 Payload Too Large`.

The client SHOULD validate body size before transmission and refuse to submit oversize bodies.

The client-side preflight check applies to the exact UTF-8 JSON byte sequence the client intends to transmit, not to an abstract submit-body object or to a hypothetical alternative serialization.

For request-mode state, §07 adds a stronger retained-state invariant: the client rejects a request-mode `set` operation before it is committed if the retained request state would no longer fit even in the minimal submit body defined there. This prevents request-state accumulation from making all future submits impossible before any user-entered `fields` are considered.

### Submit body budget partition

The 64 KiB submit body cap is partitioned into three normative reserves so that the declared maximum request-state load and a minimally-submittable form always coexist within the cap:

```text
overhead_reserve + field_min_reserve + state_budget = 65536 bytes
```

with the values:

* `overhead_reserve = 4096 bytes` - the allowance for the submit-body envelope: `request_id` (22 ASCII chars on the wire plus JSON quoting), `in_response_to` and any other top-level non-state non-fields keys defined in this section, the JSON wrapper bytes of the `request_state` and `fields` fields themselves (the `"request_state":` and `"fields":` member names with their colons, and the surrounding `[]` and `{}` brackets), the top-level object braces and the commas separating the top-level members, and a margin for future additive envelope fields under the rc-cycle additive-field rule (§11);
* `field_min_reserve = 8192 bytes` - the allowance reserved for the user-entered `fields` portion of the submit, sized so that a publisher's form whose required fields' minimal lengths fit within this reserve is always submittable alongside a maximally-loaded request_state. This is a *reserve*, not a cap: the `fields` portion of an individual submit MAY exceed `field_min_reserve` provided the total submit body remains within 64 KiB at submit time per the local validation rule above;
* `state_budget = 65536 - overhead_reserve - field_min_reserve = 53248 bytes` - the budget against which a manifest's `state_policy` declared aggregate is evaluated at manifest validation (§07).

The partition is defined in terms of **encoded bytes on the wire**: for request-state entries, this is the JSON-encoded contribution to the `request_state` array (entry object with `namespace`, `key`, and `value` strings, including the per-entry object braces, member names, colons, and quoting, plus one array-delimiter comma per inter-entry boundary), evaluated against the worst-case `value` length equal to the entry's `max_size` per §07. For form fields under `field_min_reserve`, "encoded bytes" similarly counts the wire-form contribution to the `fields` object (key, value, quoting, and one comma per inter-pair boundary). For the actual wire budget enforced at submit time, an implementation MUST account for the JSON escaping a concrete `value` requires (`\"`, `\\`, or `\u00XX` control-character escapes): an implementation that treats a runtime `value`'s raw UTF-8 byte length as its encoded wire length underestimates the wire load. The relationship between this wire accounting and the Stage 5 envelope bound computed from the declared `max_size` is stated below.

The split between the per-array budget and `overhead_reserve` is at the array boundary. The bytes counted against `state_budget` are exactly the per-entry contributions defined above plus the inter-entry commas; the `"request_state":` member name, its colon, and the surrounding `[]` brackets are envelope bytes and count against `overhead_reserve`, not against `state_budget`. The bytes counted against `field_min_reserve` are exactly the per-pair contributions plus the inter-pair commas; the `"fields":` member name, its colon, and the surrounding `{}` braces count against `overhead_reserve`. A publisher tuning a `state_policy` to fill `state_budget` therefore accounts only for the per-entry payload bytes and the inter-entry commas; the array's own wrapper bytes are already provided for in `overhead_reserve`.

Within the per-entry contribution, the `value` is counted at its declared `max_size` measured as a raw UTF-8 byte length (§07 `max_size`), not as a JSON-escaped wire length. The §07:109 aggregate is therefore a Stage 5 envelope-level *necessary* condition on the declared `state_policy`: it bounds the policy under the assumption that retained values do not expand under JSON escaping. It is not a *sufficient* guarantee that every individual submit fits this wire budget, because the wire contribution of a concrete `value` can exceed its raw UTF-8 byte length when the value contains JSON-escaped characters (`\"`, `\\`, or `\u00XX` control-character escapes). The runtime client-side `E_STATE_TRANSMIT_BUDGET` check (§07 "Request-state transmit budget") is the *sufficient* condition: it is evaluated against the actual encoded wire bytes of the retained values at submit time and rejects a `set` operation whose retained state would no longer fit the minimal submit body. A publisher MUST size `max_size` with headroom relative to expected value content so that the worst-case escaped wire form of a maximally-filled value still leaves a satisfiable submit; see the operator playbook.

The specific values of `overhead_reserve` and `field_min_reserve` are normative; an implementation MUST evaluate the §07 `state_policy` invariant against `state_budget = 53248 bytes` exactly. The split is a normative judgment about how much mandatory request-state load is reasonable per submit: smaller `state_budget` favors form-heavy publishers, larger `state_budget` favors session-state-heavy publishers, and the chosen value of 53248 bytes (about 81% of the cap) reflects that mandatory state is the load that triggers the deadlock the partition is designed to prevent. The split MAY be re-tuned in a future protocol version; a v1.0-conforming implementation uses the values above.

Operational note on §09 vs §03 field-count limits: §09 permits a `fields` object containing up to 32 key-value pairs (the transport-level upper bound). The §03 `submit_form` block declaration permits up to 16 fields per form. The wire `fields` object is constructed by the client from the user-entered form data; the per-form limit in §03 is the relevant declarative bound a publisher exercises through the schema, and the per-submit-body limit in §09 is the transport-level upper bound. The two limits are not contradictory: a single `submit_form` cannot declare more than 16 fields, but a wire submit body that originates from a `submit_form` carries at most those 16 declared fields (plus, in principle, any allowed extension a future protocol version might introduce within the §09 transport limit of 32).

### Submit validation timing

A publisher SHOULD NOT early-exit submit validation on the first failing stage. The natural sequential validation path - JSON parse, JCS canonicalization, schema check, `request_state` policy check, `request_hash` computation - exposes the rejecting stage as a server-side timing signal that an attacker probing with crafted submit bodies can sample without authentication. The signal is small per-request but accumulates across probes and can be sufficient to infer publisher-side state (declared `state_policy`, `(namespace, key)` activity, backend availability) that the wire response does not expose.

Conforming publisher implementations SHOULD adopt one of the following disciplines for the submit response path:

* run all validation stages to completion regardless of earlier failures, accumulating any rejection reason for the final response without short-circuiting on the first failure; or
* apply a randomized response-delay floor between 50 ms and 200 ms, drawn from a uniform distribution per request, before returning the submit response (`200 OK` or `400 Bad Request`), independent of the validation outcome.

Either approach removes the rejection-stage signal from the wire timing channel. The choice between them is implementation-defined and may trade computational overhead (complete-validation path) against added latency (randomized-delay path). A publisher MAY combine the two.

This rule is SHOULD-level because the publisher infrastructure is operator-controlled and the protocol cannot enforce timing properties on remote endpoints. Operators of high-threat deployments SHOULD verify their stack against this discipline; the operator playbook documents test procedures. The corresponding client-side side-channel concern (the validation pipeline ordering observable through diagnostic stage emission) is acknowledged separately in §00 "v1.0 limitations" and is not addressed by this rule.

## Image resource fetches

An image resource referenced by an `image` block (§03) is not itself an Entangled document. It is a binary image file fetched separately and bound to the containing signed document by SHA-256 digest.

Image resource fetches use a constrained subset of the rules in this section.

The client MUST NOT fetch an image resource until the containing `content` or `transaction` document has passed signature verification and closed-schema validation, as defined in §03 and §10.

The client uses `GET`:

```http
GET /<image-path> HTTP/1.1
Host: <56-character-onion-address>.onion
```

The request uses the same restrictive request-header discipline as Entangled `GET` requests defined under "Request headers" below: `Host` only, with no request body, no `Cookie`, no `User-Agent`, no `Accept` or other Accept-family header, no `Referer`, no `Origin`, no cache-directive header, no custom `X-` header.

The image path MUST be same-origin, that is, the client connects to the same carrier endpoint as the containing document, and MUST satisfy the image `src` path syntax defined in §03.

Cross-origin image fetches are forbidden, as defined in §03.

### Image response headers

Image resource responses are not Entangled documents. They are not required to use `Content-Type: application/vnd.entangled+json`.

For an image resource response with status `200 OK`, the publisher SHOULD return:

* `Content-Length`: the byte length of the response body;
* `Content-Type`: a media type matching the `media_type` declared in the `image` block (`image/png`, `image/jpeg`, or `image/webp`).

The client MUST reject an image resource response whose parsed media type has a type and subtype that compare case-insensitively equal to `application/vnd.entangled+json` or `application/vnd.entangled-submit+json`. These Content-Types are reserved for Entangled documents and submit bodies only. An image resource is not an Entangled document and MUST NOT use those Content-Types. The image resource is rejected with the appropriate image diagnostic defined in §11.

Rejection of an image resource because of a reserved Content-Type, a `Content-Type` that does not match the declared `media_type`, or any other image-fetch failure does not invalidate the containing signed `content` or `transaction` document. The image is rendered as missing or unavailable; other blocks of the document continue to render normally.

Other response headers, including those listed under "Response headers" below as ignored for Entangled documents, are also ignored for image resource responses.

A non-`200` status code on an image resource fetch is treated as image-resource unavailable. The publisher MAY use `404 Not Found` for missing image resources. Status codes outside the whitelist defined under "Status codes" below are treated as transport errors as for Entangled documents.

### Image response handling

The client MUST enforce the 2 MiB image response body limit (§03) before decoding. A response body exceeding 2 MiB is rejected without decoding.

The client MUST verify the SHA-256 digest of the exact response body bytes against the `image` block's `sha256` field before decoding the image.

The client MUST decode and render the image only if:

* the SHA-256 digest matches;
* the decoded media type matches the declared `media_type`;
* the decoded dimensions match the declared `width` and `height` and satisfy the per-block dimension limits in §03.

A bad image resource - including transport failure, size-limit violation, hash mismatch, decode failure, media-type mismatch, dimension mismatch, or animation in a WebP file (§03) - invalidates the image rendering only. It does not invalidate the containing signed `content` or `transaction` document. The image is rendered as missing or unavailable, while other blocks of the document continue to render normally.

## Headers

### Request headers

For `GET` requests, the client MUST include:

* `Host`: the carrier address.

The client MUST NOT include a request body in `GET` requests.

The client MUST NOT include any other request headers in `GET` requests.

For `POST` requests, the client MUST include:

* `Host`: the carrier address;
* `Content-Type`: exactly `application/vnd.entangled-submit+json`;
* `Content-Length`: the byte length of the submit body.

The client MUST NOT include any other request headers in `POST` requests.

In particular, the client MUST NOT send:

* `User-Agent`;
* `Accept`, `Accept-Language`, `Accept-Encoding`, or any other Accept-family header;
* `Cookie`, `Authorization`, or any other identity-bearing header;
* `Referer`, `Origin`, or any other origin-leakage header;
* `Cache-Control`, `Pragma`, or other cache-directive headers;
* `Connection: keep-alive`;
* `Range`, `If-Range`, or any other range-request header;
* any custom `X-` headers.

Identity is anchored in the protocol's signed documents and consented request state, not in HTTP-level headers.

The `Range` and `If-Range` prohibition is normative: an Entangled document is signed as a whole and is verified, hashed for the byte cap (§02, §06, §10), and digested for image binding (§03) against its complete byte sequence. A partial-content fetch would deliver bytes that do not correspond to any signed object and would defeat the protocol's stage-1 byte cap and stage-3 signature verification. A publisher MUST treat any request carrying a `Range` or `If-Range` header as malformed; the publisher MAY respond `400 Bad Request` or close the connection. The publisher MUST NOT emit `206 Partial Content`; clients reject `206` and any other unlisted `2xx` status as a transport error under "Status codes" below.

### Response headers

For `200 OK` responses carrying an Entangled document, the publisher MUST include:

* `Content-Type`: exactly `application/vnd.entangled+json`;
* `Content-Length`: the byte length of the response body.

The publisher MAY include additional response headers, but the client MUST ignore all headers not in the required list above.

Specifically:

* `Set-Cookie` headers are ignored. The client does not implement cookie semantics in v1. A `Set-Cookie` header in a response has no effect on client state.
* `Cache-Control`, `Expires`, `ETag`, `Last-Modified`, and other cache-control headers are ignored. Caching is governed by manifest `min_refresh_interval` and canary expiration, defined in §06 and §08.
* `Strict-Transport-Security` is ignored. Transport security is governed by the carrier.
* `Content-Security-Policy`, `X-Frame-Options`, and other browser-security headers are ignored. The protocol's security model does not depend on them.
* `Server`, `Date`, `Via`, and other diagnostic headers are ignored.

Headers in error responses, status codes other than `200`, are also ignored except as needed to determine the status code itself.

The client MUST NOT generate behavior based on ignored headers. A publisher who attempts to influence client behavior through ignored headers fails silently.

### Content-Type strictness

Publishers MUST emit the `Content-Type` header on `200 OK` responses carrying Entangled documents in this lowercase, parameter-free form:

```http
Content-Type: application/vnd.entangled+json
```

Recipients MUST parse the header field value as a media type according to RFC 9110 before applying the Entangled profile. A malformed field value is rejected as `E_TRANSPORT_CONTENT_TYPE`. After successful parsing, the recipient MUST compare the parsed type and subtype to `application` and `vnd.entangled+json` case-insensitively, as RFC 9110 requires. Thus, for example, `Content-Type: Application/Vnd.Entangled+JSON` is accepted even though a conforming publisher does not emit that spelling.

The parsed parameter list MUST be empty. The recipient rejects a successfully parsed media type carrying any parameter, including `charset`, as `E_TRANSPORT_CONTENT_TYPE`. This decision is made from the parsed parameter list, not by byte-exact comparison of the header field value: optional whitespace accepted by the RFC 9110 parser, including whether a space follows the semicolon, MUST NOT affect the verdict. Parameters remain forbidden even when their values would be redundant or semantically compatible.

The following are rejected:

* `Content-Type: application/vnd.entangled+json; charset=utf-8`, because the parsed parameter list is non-empty;
* `Content-Type: application/vnd.entangled+json;charset=utf-8`, for the same reason; optional whitespace does not change the parsed media type;
* `Content-Type: application/json`, because the type is wrong;
* `Content-Type: text/plain`, because the type is wrong;
* an absent `Content-Type` header.

The encoding is implicit in the protocol: Entangled JSON is always UTF-8, with no BOM. Charset parameters are redundant and rejected by Entangled's parameter-free media-type profile even when the header field value is syntactically valid.

A response with a malformed `Content-Type` is treated as a transport-level failure. The body is not parsed as an Entangled document.

### Submit Content-Type strictness

Clients MUST emit the `Content-Type` header on `POST` submit requests in this lowercase, parameter-free form:

```http
Content-Type: application/vnd.entangled-submit+json
```

Publishers MUST parse this field value according to RFC 9110 before applying the Entangled profile, compare the parsed type and subtype to `application` and `vnd.entangled-submit+json` case-insensitively, and require an empty parsed parameter list. As for document responses, parameter rejection occurs after parsing and is independent of optional whitespace. The publisher SHOULD reject a malformed field value, a type/subtype mismatch, or any parsed parameter as `400 Bad Request`.

## Content-Encoding and Transfer-Encoding

Entangled responses are transmitted as raw, unencoded body bytes whose length is declared by `Content-Length`. Encoding negotiation and chunked transfer are forbidden in both directions.

### Content-Encoding

Publishers MUST NOT use `Content-Encoding` on responses to manifest fetches, content fetches, transaction responses, or image resource fetches. The `Content-Encoding` header MUST NOT be present on any Entangled response.

Clients MUST disable automatic HTTP-layer decompression in the underlying HTTP stack. A response carrying a `Content-Encoding` header is rejected with `E_TRANSPORT_CONTENT_ENCODING` (§11). The body is not parsed as an Entangled document and is not subject to image-hash verification.

Clients MUST NOT send `Content-Encoding` on submit `POST` requests. The submit body is transmitted unencoded with the byte length declared in `Content-Length`. Publishers MUST reject submit requests carrying a `Content-Encoding` header as `400 Bad Request` and MUST NOT attempt to decode the body.

Since clients are forbidden from sending `Accept-Encoding` (see "Request headers" above), publishers receive no signal indicating client decoding capability and have no protocol-level reason to apply content encoding. The `Content-Encoding` rule eliminates the residual ambiguity created by transport stacks that compress responses by default.

### Transfer-Encoding

Publishers MUST NOT use `Transfer-Encoding` on any Entangled response. In particular, `Transfer-Encoding: chunked` is forbidden. The response body MUST be transmitted in full with a `Content-Length` header declaring the exact byte length.

A response carrying a `Transfer-Encoding` header is rejected with `E_TRANSPORT_TRANSFER_ENCODING` (§11). The body is not parsed.

Clients MUST NOT send `Transfer-Encoding` on submit `POST` requests. Publishers MUST reject submit requests carrying a `Transfer-Encoding` header as `400 Bad Request`.

### Rationale

These restrictions ensure that:

- the byte cap (§02, §06, §10) is applied uniformly to the same byte sequence in every conforming implementation, with no ambiguity about whether the cap precedes or follows decompression;
- the SHA-256 digest of an image resource (§03) is computed over a single, well-defined byte sequence;
- `Content-Length` consistency checks (`E_TRANSPORT_CONTENT_LENGTH`) compare the declared length against the same bytes the application sees;
- HTTP-stack-level differences in default decompression and chunking behavior do not produce divergent validation outcomes between client implementations;
- the overall transport profile remains a fixed-shape exchange suitable for the protocol's strict header discipline.

### Implementation note

Implementations MUST use an HTTP stack that allows automatic decompression and any default `Accept-Encoding`, `Connection`, `User-Agent`, or other headers to be disabled, as required by this section and "Request headers" above. A stack whose defaults cannot be turned off is unsuitable for a conforming Entangled client.

## Status codes

Entangled defines a closed whitelist of HTTP status codes. Each has defined semantics. Status codes outside this whitelist are treated as generic transport or protocol errors.

| Status                    | Meaning                         | When used                                                                               |
| ------------------------- | ------------------------------- | --------------------------------------------------------------------------------------- |
| `200 OK`                  | Success with document body      | Successful manifest fetch, content fetch, or submit response                            |
| `400 Bad Request`         | Submit body malformed           | Submit body fails JSON parsing or schema validation at the publisher                    |
| `404 Not Found`           | Path does not exist             | Content fetch for a path the publisher does not serve, or submit to an unknown endpoint |
| `405 Method Not Allowed`  | Method not supported            | Request using a method other than `GET` or `POST`                                       |
| `413 Payload Too Large`   | Body exceeds size limit         | Submit body exceeds 64 KiB                                                              |
| `429 Too Many Requests`   | Rate limit                      | Publisher rate-limiting the client                                                      |
| `503 Service Unavailable` | Service temporarily unavailable | Publisher unable to serve, expected to recover                                          |

Status codes outside the whitelist - including `1xx`, `2xx` other than `200`, all `3xx`, and unlisted `4xx` or `5xx` codes (for example `204`, `304`, `418`) - are treated as transport or protocol errors; the client does not interpret HTTP semantics as Entangled semantics, except for `3xx` redirects which are explicitly rejected as defined under "Redirects" below.

The error reported to the user reflects an unexpected transport response, not the literal HTTP status meaning.

Two whitelisted codes are scoped to submit responses. `400 Bad Request` and `413 Payload Too Large` are defined for `POST` submit responses only; their semantics describe a publisher judgment about the submit body, which a `GET` does not carry. A client that receives `400` or `413` in response to a `GET` for an Entangled document MUST treat the response as an unexpected transport response, exactly as for a code outside the whitelist: the reported diagnostic is the generic `E_TRANSPORT_STATUS` (§11), not `E_TRANSPORT_BAD_REQUEST` or `E_TRANSPORT_PAYLOAD_TOO_LARGE`. The remaining whitelisted error codes (`404`, `405`, `429`, `503`) have operation-independent semantics and keep their dedicated diagnostics on any request. This rule governs the Entangled-document fetch path; the `/content_index.json` resource and image resources keep their own layer rules ("Content index fetch" and "Image resource fetches" above).

The publisher SHOULD use only whitelisted status codes. A publisher returning non-whitelisted codes fails to communicate intent to the client.

## Redirects

The client MUST NOT automatically follow HTTP redirects.

Status codes in the `3xx` range are treated as redirect-not-supported transport errors. The client MUST NOT interpret the `Location` header and MUST NOT issue follow-up requests based on it.

If a publisher needs to direct users to a different path or address, this is communicated through:

* block types in content documents that explicitly link to other paths within the same site or other addresses subject to client confirmation;
* a fresh manifest declaring a new origin, subject to publisher history and identity-continuity rules in §06.

Publisher-driven navigation by HTTP redirect is not a supported pattern in Entangled v1.

## Connection semantics

The client opens a fresh HTTP exchange to the carrier endpoint for each Entangled request, unless the carrier infrastructure transparently multiplexes connections.

Entangled does not define application-level HTTP keep-alive semantics. The client MUST NOT rely on HTTP keep-alive headers, persistent HTTP connection state, or other application-level connection reuse semantics for protocol behavior. Each Entangled HTTP exchange is request-response and does not assume connection persistence at the HTTP layer.

This rule applies at the application layer only. It does not forbid the carrier or transport implementation from reusing or multiplexing the underlying connections or circuits transparently. For Tor v3, connection and circuit multiplexing is handled by the Tor client implementation. The Entangled client MAY issue multiple requests over the same Tor circuit if the underlying Tor library supports it; the protocol neither requires nor forbids this. Such reuse is a property of the Tor layer, not of the Entangled HTTP exchange.

The client SHOULD apply a transport timeout suitable for the carrier. For Tor v3, timeouts are typically in the tens of seconds range due to circuit establishment latency.

## Concurrent requests

The client MAY issue multiple Entangled requests concurrently to the same site, for example prefetching multiple content documents whose paths are listed in navigation.

Concurrency is bounded by the carrier's capacity. For Tor v3, excessive concurrent requests place load on the publisher's onion service and on the Tor network. The client SHOULD limit concurrency to a small number. Typical implementations cap at 4 to 8 concurrent requests per site.

The client MUST NOT issue concurrent requests that bypass `min_refresh_interval` for manifest fetches. Manifest refresh policy is governed by §06.

## Error response handling

When the publisher returns a non-`200` status code, the client MUST NOT parse the response body as an Entangled document.

The response body of a non-`200` response is ignored. The client reports the status code and corresponding error semantics to the user via chrome.

For status codes within the whitelist, the client MAY display the meaning to the user, for example "Path not found" or "Service unavailable, try again later".

For `3xx` responses, the client reports redirect-not-supported.

For status codes outside the whitelist, the client displays a generic transport error.

In all error cases, the trust state established for the publisher remains unchanged. A failed fetch does not trigger any change in the trust state, the canary state, or the manifest cache.

## What this section does not cover

This section defines the HTTP subset over which Entangled documents are exchanged.

It does not define:

* the carrier itself, including Tor v3 onion-service operation, I2P transport, or Yggdrasil routing;
* the document envelope structure, schema, or signing (see §02, §05, §06);
* the canary structure or anti-downgrade enforcement (see §08);
* state semantics, consent, or storage (see §07);
* block types defining submit endpoint URIs within content (see §03);
* the client verification pipeline, including ordering of fetch, parse, validation, signature verification, and trust state computation (see §10);
* standardized error codes presented to the user (see §11);
* operational practices for running carrier infrastructure (see operator playbook, outside the normative spec).
