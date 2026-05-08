# Entangled v1.0 conformance corpus

Test vectors for Entangled v1.0 protocol implementations.

## Status

This corpus is normative: a v1.0-conforming implementation MUST agree with the verdicts recorded here for each vector. Implementations are encouraged to drive their own conformance test suite from `corpus.json`.

The corpus is generated deterministically from a fixed set of test seeds. Anyone can reproduce it byte-for-byte by running the generator.

## Layout

```
corpus/
├── README.md          this file
├── keys.json          public key material derived from fixed test seeds
├── corpus.json        machine-readable index: vector id, expected verdict, etc.
├── vectors/
│   └── <id>/
│       ├── input.json      (or input.bin for non-JSON inputs)
│       └── ... extra files such as submit_body.json, image bytes
└── tools/
    └── generate.py    deterministic generator
```

`corpus.json` is the entry point. Every vector is described by:

- `id` — stable identifier, prefixed with a numeric category (000-049 reserved, 050-099 positive, 100-199 negative);
- `kind` — `manifest`, `content`, or `transaction`;
- `description` — what the vector exercises;
- `spec_refs` — the spec sections the vector tests;
- `input` — relative path to the input bytes;
- `expected.verdict` — `accept` or `reject`;
- `expected.diagnostic` — for rejections, the normative §11 diagnostic code;
- `context` — optional fields needed to apply the vector (fetched path, fetched origin address, prerequisites such as a previously verified manifest, the corresponding submit body for transactions, etc.);
- `extra_files` — additional files in the vector directory.

The corpus index also carries a top-level `clock_now` field, in RFC 3339 form. Harnesses MUST mock the implementation's wall clock to this value for the duration of the test run. This is required because canary diagnostics depend on `now` and the corpus uses fixed `issued_at` timestamps; without clock mocking, time-dependent vectors are not reproducible.

## Test keys

`keys.json` records the test-only Ed25519 keypairs derived from fixed 32-byte seeds. The seeds are public ASCII strings (e.g., `b"ENTANGLED-v1.0-publisher-test01\x00"`); the corresponding private keys are NOT secret. They MUST NOT be used for any deployment.

Three roles are pre-derived: `publisher` (`K_publisher`), `runtime` (`K_runtime`), `origin` (`K_origin`). A second runtime keypair (`runtime_2`) is provided for tests that need a distinct `K_runtime.pub` (e.g., the equal-`issued_at` conflict vector).

For the `origin` keypair, the corresponding Tor v3 onion address is also recorded; it is derived from the public key by the rend-spec-v3 procedure and used for origin-binding in manifest vectors.

## Diagnostics

Negative vectors carry the normative diagnostic code from §11 of the specification. Where multiple stages could in principle detect the violation, the diagnostic listed is the one the spec assigns (or, for parser-detectable cases, the one whose protocol-level meaning matches the violation regardless of detection stage).

## Running the corpus against an implementation

The general test harness pattern:

1. Load `corpus.json`.
2. Set the implementation's wall clock to `corpus.json["clock_now"]` (mock or inject) for the duration of the test run.
3. For each vector:
   - read the raw input bytes from `input` (no normalization, no transcoding);
   - apply implementation-specific context: e.g., set the "fetched path" to `context.fetched_path` for content documents, set the "previously verified manifest" for canary-conflict vectors, etc.;
   - run the input through the implementation's validation pipeline;
   - compare the implementation's outcome against `expected`.

Implementations SHOULD report any vector whose actual outcome diverges from the expected one as a conformance failure.

## Regenerating

```
python3 corpus/tools/generate.py
```

Requires Python 3.10+ and the `cryptography` package (for raw Ed25519 RFC 8032 signing). The generator is fully deterministic; output bytes match across runs and across machines.

## Categories of vectors in this initial release

| Range | Category |
|---|---|
| 001–099 | Positive (must be accepted) |
| 100–109 | Stage 2 input checks (BOM, UTF-8) |
| 110–119 | Stage 3 JSON parsing (duplicate keys) |
| 120–129 | Stage 4 kind / spec_version |
| 130–139 | Stage 5 schema (unknown field, missing required, null, block-kind) |
| 140–149 | Numeric grammar (float, exponent, overflow) |
| 150–159 | Stage 6 signature (modified payload, malformed length, non-canonical S, small-order A) |
| 160–169 | Strict base64url (padding, alphabet, whitespace) |
| 170–179 | Stage 9 binding (path mismatch, reserved path, request_hash) |
| 180–189 | Canary (equal `issued_at` conflict) |

Future tranches will extend the corpus with additional cases: image hash mismatch, image content-type mismatch, oversized images, state-policy violations, anti-downgrade across origins, transaction state_updates rejection, chrome-separation requirements (out of pipeline scope), and JCS edge cases (Unicode property ordering, large but valid integer strings, etc.).

Coverage relative to the §11 diagnostic code catalog is intentionally partial in this initial corpus. The categories above exercise representative codes per pipeline stage; future tranches will fill out the remaining codes.
