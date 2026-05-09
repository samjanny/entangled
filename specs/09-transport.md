# 09 — Transport

This section defines the HTTP subset over which Entangled documents are fetched and submitted. The transport profile is intentionally minimal: it specifies what is permitted, what is required, and what is ignored. Behavior outside this profile is non-conformant.

Entangled v1 fully specifies the Tor v3 transport profile. Other carrier profiles (I2P, Yggdrasil) define their own transport rules; until specified, they are draft profiles and not part of v1 conformance.

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

## Submit request

A submit is a `POST` request to a transaction endpoint declared by the publisher, typically declared in `blocks` of a content document; see §03.

```http
POST /<submit-path> HTTP/1.1
Host: <56-character-onion-address>.onion
Content-Type: application/entangled-submit+json
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

The client MUST generate `request_id` using a cryptographically secure random source. Each submit MUST have a freshly generated `request_id`; the client MUST NOT reuse `request_id` values across submits.

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
* each `value` MUST be a UTF-8 string not exceeding 4096 bytes, the protocol's absolute state-value ceiling (§07). Publishers MAY reject submit bodies carrying a larger `value` as malformed;
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

Image resource responses are not Entangled documents. They are not required to use `Content-Type: application/entangled+json`.

For an image resource response with status `200 OK`, the publisher SHOULD return:

* `Content-Length`: the byte length of the response body;
* `Content-Type`: a media type matching the `media_type` declared in the `image` block (`image/png`, `image/jpeg`, or `image/webp`).

The client MUST reject an image resource response whose `Content-Type` is `application/entangled+json` or `application/entangled-submit+json`. These Content-Types are reserved for Entangled documents and submit bodies only. An image resource is not an Entangled document and MUST NOT use those Content-Types. The image resource is rejected with the appropriate image diagnostic defined in §11.

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

A bad image resource — including transport failure, size-limit violation, hash mismatch, decode failure, media-type mismatch, dimension mismatch, or animation in a WebP file (§03) — invalidates the image rendering only. It does not invalidate the containing signed `content` or `transaction` document. The image is rendered as missing or unavailable, while other blocks of the document continue to render normally.

## Headers

### Request headers

For `GET` requests, the client MUST include:

* `Host`: the carrier address.

The client MUST NOT include a request body in `GET` requests.

The client MUST NOT include any other request headers in `GET` requests.

For `POST` requests, the client MUST include:

* `Host`: the carrier address;
* `Content-Type`: exactly `application/entangled-submit+json`;
* `Content-Length`: the byte length of the submit body.

The client MUST NOT include any other request headers in `POST` requests.

In particular, the client MUST NOT send:

* `User-Agent`;
* `Accept`, `Accept-Language`, `Accept-Encoding`, or any other Accept-family header;
* `Cookie`, `Authorization`, or any other identity-bearing header;
* `Referer`, `Origin`, or any other origin-leakage header;
* `Cache-Control`, `Pragma`, or other cache-directive headers;
* `Connection: keep-alive`;
* any custom `X-` headers.

Identity is anchored in the protocol's signed documents and consented request state, not in HTTP-level headers.

### Response headers

For `200 OK` responses carrying an Entangled document, the publisher MUST include:

* `Content-Type`: exactly `application/entangled+json`;
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

The `Content-Type` header on `200 OK` responses carrying Entangled documents MUST be exactly:

```http
Content-Type: application/entangled+json
```

with no parameters.

The following are rejected:

* `Content-Type: application/entangled+json; charset=utf-8`, because a parameter is present;
* `Content-Type: application/json`, because the type is wrong;
* `Content-Type: text/plain`, because the type is wrong;
* an absent `Content-Type` header.

The encoding is implicit in the protocol: Entangled JSON is always UTF-8, with no BOM. Charset parameters are redundant and rejected as malformed.

A response with a malformed `Content-Type` is treated as a transport-level failure. The body is not parsed as an Entangled document.

### Submit Content-Type strictness

The `Content-Type` header on `POST` submit requests MUST be exactly:

```http
Content-Type: application/entangled-submit+json
```

with no parameters.

The publisher SHOULD reject submit requests with any other `Content-Type` as `400 Bad Request`.

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

Status codes outside the whitelist — including `1xx`, `2xx` other than `200`, all `3xx`, and unlisted `4xx` or `5xx` codes (for example `204`, `304`, `418`) — are treated as transport or protocol errors; the client does not interpret HTTP semantics as Entangled semantics, except for `3xx` redirects which are explicitly rejected as defined under "Redirects" below.

The error reported to the user reflects an unexpected transport response, not the literal HTTP status meaning.

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
