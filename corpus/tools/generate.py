#!/usr/bin/env python3
"""
Entangled v1.0 conformance corpus generator.

Produces a deterministic corpus of test vectors for Entangled v1.0 protocol
implementations. Each vector is a complete signed (or deliberately broken)
document with a documented expected verdict (accept / reject + diagnostic).

Run from the repository root:

    python3 corpus/tools/generate.py

Outputs are written to corpus/keys.json, corpus/corpus.json, and
corpus/vectors/<id>/.

Determinism: Ed25519 keys are derived from fixed 32-byte seeds. Signing under
RFC 8032 is deterministic. The output is reproducible byte-for-byte.

Requirements: Python 3.10+, cryptography>=3.4 (for raw Ed25519).
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives import serialization

# Repository root, relative to this script (corpus/tools/generate.py).
ROOT = Path(__file__).resolve().parent.parent
VECTORS_DIR = ROOT / "vectors"

# ---------------------------------------------------------------------------
# Test key seeds. Fixed for reproducibility. NEVER use these for any real
# deployment; they are public test fixtures.
# ---------------------------------------------------------------------------
PUBLISHER_SEED = b"ENTANGLED-v1.0-publisher-test01\x00"
RUNTIME_SEED = b"ENTANGLED-v1.0-runtime-test0001\x00"
ORIGIN_SEED = b"ENTANGLED-v1.0-origin-test00001\x00"
RUNTIME_SEED_2 = b"ENTANGLED-v1.0-runtime-test0002\x00"

assert len(PUBLISHER_SEED) == 32
assert len(RUNTIME_SEED) == 32
assert len(ORIGIN_SEED) == 32
assert len(RUNTIME_SEED_2) == 32


# ---------------------------------------------------------------------------
# Crypto helpers
# ---------------------------------------------------------------------------
def b64u(data: bytes) -> str:
    """RFC 4648 §5 base64url, no padding."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64u_decode(s: str) -> bytes:
    """Decode base64url with strict padding rules; only used in tooling."""
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


# Order of the Ed25519 base point (RFC 8032). Used to construct non-canonical
# S signatures (S' = S + L) for the strict-profile S-canonicalization test.
ED25519_L = 2**252 + 27742317777372353535851937790883648493


def non_canonical_s(sig_bytes: bytes) -> bytes:
    """Given a valid 64-byte Ed25519 signature R||S, return R||(S + L).

    Under cofactored verification, the resulting signature still verifies
    because [L]B is the identity. Under the strict profile, S + L >= L is
    non-canonical and rejected. The vector exercises strict-profile S-range
    enforcement.
    """
    assert len(sig_bytes) == 64
    R = sig_bytes[:32]
    S = int.from_bytes(sig_bytes[32:], "little")
    S_prime = S + ED25519_L
    return R + S_prime.to_bytes(32, "little")


# Small-order Ed25519 public key: the identity point. Compressed encoding is
# the little-endian byte representation of the y-coordinate, with the high bit
# of the last byte carrying the x-sign. For the identity, y = 1 and x = 0, so
# the encoding is 0x01 followed by 31 zero bytes.
SMALL_ORDER_A = bytes([0x01]) + bytes(31)


def keypair(seed: bytes) -> tuple[Ed25519PrivateKey, bytes]:
    """Derive an Ed25519 keypair from a 32-byte seed. Returns (priv, pub_bytes)."""
    priv = Ed25519PrivateKey.from_private_bytes(seed)
    pub = priv.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return priv, pub


def jcs(obj) -> bytes:
    """JCS canonicalization (RFC 8785) for the Entangled JSON subset.

    Entangled uses integer-only numbers, no nulls, no duplicate keys, and
    valid UTF-8 strings, so JCS reduces to: sort object keys lex, no
    whitespace, JSON-standard escaping, UTF-8 output.
    """
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def sign(priv: Ed25519PrivateKey, context: str, payload: dict) -> str:
    """Sign an Entangled payload with the given context string.

    signature_input = context_string || 0x00 || JCS(payload)
    Returns the signature as base64url with no padding.
    """
    sig_input = context.encode("ascii") + b"\x00" + jcs(payload)
    sig = priv.sign(sig_input)
    return b64u(sig)


def sha256_b64u(data: bytes) -> str:
    """SHA-256 of `data`, formatted as 'sha-256:<base64url>'."""
    digest = hashlib.sha256(data).digest()
    return f"sha-256:{b64u(digest)}"


def onion_address(origin_pub: bytes) -> str:
    """Tor v3 onion address from a 32-byte Ed25519 public key (rend-spec-v3)."""
    version = bytes([0x03])
    checksum = hashlib.sha3_256(b".onion checksum" + origin_pub + version).digest()[:2]
    body = origin_pub + checksum + version
    return base64.b32encode(body).decode("ascii").lower() + ".onion"


# ---------------------------------------------------------------------------
# Domain separation context strings (§05)
# ---------------------------------------------------------------------------
CTX_MANIFEST = "ENTANGLED-v1 manifest"
CTX_CONTENT = "ENTANGLED-v1 content"
CTX_TRANSACTION = "ENTANGLED-v1 transaction"


# ---------------------------------------------------------------------------
# Document factories
# ---------------------------------------------------------------------------
def make_manifest(*, publisher_priv, publisher_pub, origin_pub, runtime_pub,
                  issued_at="2026-05-07T00:00:00Z",
                  next_expected="2026-06-06T00:00:00Z",
                  updated="2026-05-07T00:00:00Z",
                  state_policy=None) -> dict:
    """Build and sign a minimal valid manifest."""
    if state_policy is None:
        state_policy = []
    payload = {
        "spec_version": "1.0",
        "kind": "manifest",
        "publisher_pubkey": b64u(publisher_pub),
        "origin": {
            "carrier": "tor-v3",
            "address": onion_address(origin_pub),
            "origin_pubkey": b64u(origin_pub),
        },
        "canary": {
            "runtime_pubkey": b64u(runtime_pub),
            "issued_at": issued_at,
            "next_expected": next_expected,
            "statement": "No warrants received.",
        },
        "state_policy": state_policy,
        "navigation": [],
        "min_refresh_interval": 3600,
        "updated": updated,
    }
    payload["sig"] = sign(publisher_priv, CTX_MANIFEST, payload)
    return payload


def make_content(*, runtime_priv, path="/articles/first-post",
                 title="First post", published_at="2026-05-07T00:00:00Z",
                 blocks=None) -> dict:
    """Build and sign a minimal valid content document."""
    if blocks is None:
        blocks = [
            {
                "kind": "paragraph",
                "content": [
                    {"kind": "text", "value": "Hello, world.", "marks": []},
                ],
            }
        ]
    payload = {
        "spec_version": "1.0",
        "kind": "content",
        "path": path,
        "meta": {"title": title, "published_at": published_at},
        "blocks": blocks,
    }
    payload["sig"] = sign(runtime_priv, CTX_CONTENT, payload)
    return payload


def make_transaction(*, runtime_priv, in_response_to="/contact",
                     submit_body=None, blocks=None,
                     state_updates=None) -> tuple[dict, dict]:
    """Build and sign a transaction document.

    Returns (transaction_doc, submit_body_used). The submit body is needed by
    the client to verify request_hash; vectors carrying transactions also
    carry the corresponding submit body.
    """
    if submit_body is None:
        submit_body = {
            "fields": {"message": "hello", "name": "alice"},
            "request_state": [],
            "request_id": "AAECAwQFBgcICQoLDA0ODw",
        }
    if blocks is None:
        blocks = [
            {
                "kind": "feedback",
                "variant": "success",
                "content": [
                    {"kind": "text", "value": "Received.", "marks": []},
                ],
            }
        ]
    if state_updates is None:
        state_updates = []
    submit_canonical = jcs(submit_body)
    request_hash = sha256_b64u(submit_canonical)
    payload = {
        "spec_version": "1.0",
        "kind": "transaction",
        "in_response_to": in_response_to,
        "request_id": submit_body["request_id"],
        "request_hash": request_hash,
        "state_updates": state_updates,
        "blocks": blocks,
    }
    payload["sig"] = sign(runtime_priv, CTX_TRANSACTION, payload)
    return payload, submit_body


# ---------------------------------------------------------------------------
# Vector emission
# ---------------------------------------------------------------------------
def write_vector(vid: str, body: bytes, *, filename: str = "input.json") -> str:
    """Write a vector's raw bytes to corpus/vectors/<vid>/<filename>.

    Returns the relative path stored in the corpus index.
    """
    vdir = VECTORS_DIR / vid
    vdir.mkdir(parents=True, exist_ok=True)
    path = vdir / filename
    path.write_bytes(body)
    return f"vectors/{vid}/{filename}"


def vec(vid: str, kind: str, description: str, spec_refs: list[str],
        verdict: str, *, body: bytes | None = None,
        body_obj: dict | None = None, diagnostic: str | None = None,
        context: dict | None = None,
        extra_files: dict[str, bytes] | None = None) -> dict:
    """Build a corpus vector entry and write its files."""
    if body is None:
        if body_obj is None:
            raise ValueError("either body or body_obj required")
        # Serialize without sort_keys so the wire form preserves authoring order.
        body = json.dumps(body_obj, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    input_path = write_vector(vid, body)
    expected: dict = {"verdict": verdict}
    if diagnostic is not None:
        expected["diagnostic"] = diagnostic
    entry = {
        "id": vid,
        "kind": kind,
        "description": description,
        "spec_refs": spec_refs,
        "input": input_path,
        "expected": expected,
    }
    if context is not None:
        entry["context"] = context
    if extra_files:
        for fname, fdata in extra_files.items():
            write_vector(vid, fdata, filename=fname)
        entry["extra_files"] = sorted(extra_files.keys())
    return entry


# ---------------------------------------------------------------------------
# Vector definitions
# ---------------------------------------------------------------------------
def positive_vectors(keys) -> list[dict]:
    """Documents that a conforming v1.0 implementation MUST accept."""
    out: list[dict] = []
    pp, pp_pub = keys["publisher_priv"], keys["publisher_pub"]
    rp, rp_pub = keys["runtime_priv"], keys["runtime_pub"]
    op, op_pub = keys["origin_priv"], keys["origin_pub"]

    # 001: minimal valid manifest
    m = make_manifest(
        publisher_priv=pp, publisher_pub=pp_pub,
        origin_pub=op_pub, runtime_pub=rp_pub,
    )
    out.append(vec(
        "001-manifest-valid-minimal",
        kind="manifest",
        description="Minimal valid manifest signed by K_publisher. Empty state_policy and navigation. Tor v3 origin with derived address.",
        spec_refs=["§02", "§05", "§06"],
        verdict="accept",
        body_obj=m,
        context={"fetched_origin_address": m["origin"]["address"]},
    ))

    # 002: valid manifest with state_policy
    m2 = make_manifest(
        publisher_priv=pp, publisher_pub=pp_pub,
        origin_pub=op_pub, runtime_pub=rp_pub,
        state_policy=[
            {
                "namespace": "session",
                "key": "auth",
                "mode": "request",
                "max_size": 512,
                "max_lifetime": 86400,
                "purpose": "Authenticate submit requests after login.",
            },
            {
                "namespace": "ui",
                "key": "lang",
                "mode": "client_only",
                "max_size": 32,
                "max_lifetime": 7776000,
                "purpose": "Remember the chosen language for the user interface.",
            },
        ],
    )
    out.append(vec(
        "002-manifest-valid-state-policy",
        kind="manifest",
        description="Valid manifest declaring two state_policy entries: one request-mode session token, one client-only language preference.",
        spec_refs=["§06", "§07"],
        verdict="accept",
        body_obj=m2,
        context={"fetched_origin_address": m2["origin"]["address"]},
    ))

    # 003: valid content document
    c = make_content(runtime_priv=rp)
    out.append(vec(
        "003-content-valid-minimal",
        kind="content",
        description="Minimal valid content document with a single paragraph block. Signed by K_runtime authorized by manifest 001.",
        spec_refs=["§02", "§03", "§05"],
        verdict="accept",
        body_obj=c,
        context={
            "fetched_path": c["path"],
            "expected_runtime_pubkey": b64u(rp_pub),
        },
    ))

    # 004: valid content with multiple block kinds
    c2 = make_content(
        runtime_priv=rp,
        path="/articles/blocks-showcase",
        title="Block showcase",
        blocks=[
            {"kind": "heading", "level": 1, "content": [
                {"kind": "text", "value": "Showcase", "marks": []},
            ]},
            {"kind": "paragraph", "content": [
                {"kind": "text", "value": "An example of ", "marks": []},
                {"kind": "text", "value": "bold", "marks": ["bold"]},
                {"kind": "text", "value": " and ", "marks": []},
                {"kind": "text", "value": "italic", "marks": ["italic"]},
                {"kind": "text", "value": " text.", "marks": []},
            ]},
            {"kind": "list", "ordered": False, "items": [
                [{"kind": "text", "value": "First", "marks": []}],
                [{"kind": "text", "value": "Second", "marks": []}],
            ]},
            {"kind": "code_block", "language": "rust",
             "content": "fn main() {\n    println!(\"hi\");\n}"},
            {"kind": "divider"},
            {"kind": "quote", "content": [
                {"kind": "text", "value": "Lorem ipsum.", "marks": []},
            ]},
        ],
    )
    out.append(vec(
        "004-content-valid-blocks-showcase",
        kind="content",
        description="Valid content document exercising heading, marked paragraph, unordered list, code_block, divider, and quote. No image; image is exercised separately.",
        spec_refs=["§03"],
        verdict="accept",
        body_obj=c2,
        context={
            "fetched_path": c2["path"],
            "expected_runtime_pubkey": b64u(rp_pub),
        },
    ))

    # 005: valid transaction document
    t, sb = make_transaction(runtime_priv=rp)
    out.append(vec(
        "005-transaction-valid-minimal",
        kind="transaction",
        description="Minimal valid transaction document with a single feedback block. Carries a request_hash bound to the submit body in extra_files/submit_body.json.",
        spec_refs=["§02", "§09"],
        verdict="accept",
        body_obj=t,
        context={
            "submit_path": t["in_response_to"],
            "expected_runtime_pubkey": b64u(rp_pub),
            "submit_body_path": "vectors/005-transaction-valid-minimal/submit_body.json",
        },
        extra_files={
            "submit_body.json": json.dumps(
                sb, separators=(",", ":"), ensure_ascii=False
            ).encode("utf-8"),
        },
    ))

    return out


def negative_vectors(keys) -> list[dict]:
    """Documents that a conforming v1.0 implementation MUST reject, with the
    specific diagnostic listed."""
    out: list[dict] = []
    pp, pp_pub = keys["publisher_priv"], keys["publisher_pub"]
    rp, rp_pub = keys["runtime_priv"], keys["runtime_pub"]
    op, op_pub = keys["origin_priv"], keys["origin_pub"]

    # ---- input: BOM, bad UTF-8 ----
    m = make_manifest(
        publisher_priv=pp, publisher_pub=pp_pub,
        origin_pub=op_pub, runtime_pub=rp_pub,
    )
    m_bytes = json.dumps(m, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    out.append(vec(
        "100-input-bom",
        kind="manifest",
        description="Otherwise-valid manifest preceded by a UTF-8 BOM (EF BB BF). Must be rejected at stage 2 input checks.",
        spec_refs=["§04"],
        verdict="reject",
        diagnostic="E_INPUT_BOM",
        body=b"\xEF\xBB\xBF" + m_bytes,
    ))
    out.append(vec(
        "101-input-bad-utf8",
        kind="manifest",
        description="Body is not valid UTF-8: contains a lone 0xFE byte that is not part of any UTF-8 sequence. Must be rejected at stage 2.",
        spec_refs=["§04"],
        verdict="reject",
        diagnostic="E_INPUT_UTF8",
        body=b'{"spec_version":"1.0","kind":"manifest","x":"\xFE"}',
    ))

    # ---- parse: duplicate keys ----
    out.append(vec(
        "110-parse-duplicate-keys",
        kind="content",
        description="Content document with a duplicate top-level member name (\"path\" appears twice). Must be rejected at stage 3 with E_PARSE_DUPLICATE_KEY before schema validation.",
        spec_refs=["§04"],
        verdict="reject",
        diagnostic="E_PARSE_DUPLICATE_KEY",
        body=b'{"spec_version":"1.0","kind":"content","path":"/x","path":"/y","meta":{"title":"t","published_at":"2026-05-07T00:00:00Z"},"blocks":[{"kind":"divider"}],"sig":"' + (b"A" * 86) + b'"}',
    ))

    # ---- kind / spec_version ----
    out.append(vec(
        "120-spec-version-wrong",
        kind="manifest",
        description="Document declaring spec_version \"1.1\". A v1.0 client must reject with E_KIND_SPEC_VERSION before schema validation.",
        spec_refs=["§02", "§11"],
        verdict="reject",
        diagnostic="E_KIND_SPEC_VERSION",
        body=b'{"spec_version":"1.1","kind":"manifest","sig":"' + (b"A" * 86) + b'"}',
    ))
    out.append(vec(
        "121-kind-unknown",
        kind="manifest",
        description="Document whose kind is \"unknown\" (not one of manifest/content/transaction). Rejected at stage 4 with E_KIND_UNKNOWN.",
        spec_refs=["§02", "§11"],
        verdict="reject",
        diagnostic="E_KIND_UNKNOWN",
        body=b'{"spec_version":"1.0","kind":"unknown","sig":"' + (b"A" * 86) + b'"}',
    ))

    # ---- schema: unknown field, missing required, null value ----
    bad = dict(m)
    bad["unexpected_field"] = "x"
    # need to re-sign would be wrong (signature wouldn't match this payload anyway,
    # because we can't sign a document our schema rejects from inside the
    # generator). Use the original signature; the test exercises stage 5 schema
    # rejection ahead of stage 6 signature verification.
    out.append(vec(
        "130-schema-unknown-field",
        kind="manifest",
        description="Manifest with an extra top-level field \"unexpected_field\". Closed-schema discipline rejects at stage 5 with E_SCHEMA_UNKNOWN_FIELD before signature verification.",
        spec_refs=["§02", "§06"],
        verdict="reject",
        diagnostic="E_SCHEMA_UNKNOWN_FIELD",
        body_obj=bad,
    ))

    bad2 = {k: v for k, v in m.items() if k != "min_refresh_interval"}
    out.append(vec(
        "131-schema-missing-required",
        kind="manifest",
        description="Manifest with required field min_refresh_interval omitted. Rejected at stage 5 with E_SCHEMA_REQUIRED_FIELD.",
        spec_refs=["§06"],
        verdict="reject",
        diagnostic="E_SCHEMA_REQUIRED_FIELD",
        body_obj=bad2,
    ))

    m_null_nav = dict(m)
    m_null_nav["navigation"] = None
    m_null_nav["sig"] = "A" * 86  # placeholder; stage 5 fails before stage 6
    out.append(vec(
        "132-schema-null-value",
        kind="manifest",
        description=(
            "Manifest where navigation is null. All other required fields "
            "are present and well-formed; only the null literal triggers "
            "stage 5 rejection. E_SCHEMA_NULL_VALUE."
        ),
        spec_refs=["§04", "§06"],
        verdict="reject",
        diagnostic="E_SCHEMA_NULL_VALUE",
        body_obj=m_null_nav,
        context={"fetched_origin_address": m_null_nav["origin"]["address"]},
    ))

    # Invalid block kind in content document
    c_bad_block = make_content(
        runtime_priv=rp,
        path="/articles/bad-block",
        title="Bad block",
        blocks=[{"kind": "marquee", "content": "scrolling text"}],
    )
    out.append(vec(
        "133-schema-block-kind-unknown",
        kind="content",
        description=(
            "Content document with a block whose kind is \"marquee\", a "
            "syntactically valid slug not in the enumerated block kinds "
            "(§03). Stage 5 schema rejection. E_SCHEMA_ENUM_VIOLATION."
        ),
        spec_refs=["§03", "§11"],
        verdict="reject",
        diagnostic="E_SCHEMA_ENUM_VIOLATION",
        body_obj=c_bad_block,
        context={
            "fetched_path": c_bad_block["path"],
            "expected_runtime_pubkey": b64u(rp_pub),
        },
    ))

    # ---- numeric grammar: float, big int ----
    out.append(vec(
        "140-numeric-float",
        kind="manifest",
        description="Manifest where min_refresh_interval has a float-shape token (3600.0). The strict integer grammar rejects floats lexically. E_SCHEMA_NON_INTEGER.",
        spec_refs=["§04"],
        verdict="reject",
        diagnostic="E_SCHEMA_NON_INTEGER",
        body=b'{"spec_version":"1.0","kind":"manifest","min_refresh_interval":3600.0,"sig":"' + (b"A" * 86) + b'"}',
    ))
    out.append(vec(
        "141-numeric-exponent",
        kind="manifest",
        description="Manifest where min_refresh_interval is written in exponent form (3.6e3). Integer grammar rejects exponents. E_SCHEMA_NON_INTEGER.",
        spec_refs=["§04"],
        verdict="reject",
        diagnostic="E_SCHEMA_NON_INTEGER",
        body=b'{"spec_version":"1.0","kind":"manifest","min_refresh_interval":3.6e3,"sig":"' + (b"A" * 86) + b'"}',
    ))
    m_overflow = dict(m)
    m_overflow["min_refresh_interval"] = 9223372036854775808  # 2**63
    m_overflow["sig"] = "A" * 86
    out.append(vec(
        "142-numeric-overflow",
        kind="manifest",
        description=(
            "Manifest where min_refresh_interval is 9223372036854775808 "
            "(= 2^63), one above the protocol's 64-bit signed integer "
            "cap. All other required fields are present and well-formed. "
            "E_SCHEMA_NON_INTEGER."
        ),
        spec_refs=["§04", "§06"],
        verdict="reject",
        diagnostic="E_SCHEMA_NON_INTEGER",
        body_obj=m_overflow,
        context={"fetched_origin_address": m_overflow["origin"]["address"]},
    ))

    # ---- signature: modified payload, wrong length ----
    m_tamper = dict(m)
    # Modify a non-sig field after signing. The signature no longer matches.
    m_tamper["min_refresh_interval"] = m["min_refresh_interval"] + 1
    out.append(vec(
        "150-sig-modified-payload",
        kind="manifest",
        description="Otherwise-valid manifest whose min_refresh_interval was changed after signing. The wire signature no longer verifies. E_SIG_VERIFICATION.",
        spec_refs=["§05"],
        verdict="reject",
        diagnostic="E_SIG_VERIFICATION",
        body_obj=m_tamper,
        context={"fetched_origin_address": m_tamper["origin"]["address"]},
    ))

    # Sig field length: 43 chars instead of the canonical 86. Stage 5 §04
    # declared-length check fires before stage 6 signature decoding (§10
    # first-failing-stage rule), so the diagnostic is E_SCHEMA_FIELD_SYNTAX,
    # not E_SIG_MALFORMED.
    short_sig = b64u(b"\x00" * 32)  # 43 chars
    m_short = dict(m)
    m_short["sig"] = short_sig
    out.append(vec(
        "151-sig-syntax-length",
        kind="manifest",
        description=(
            "Manifest whose sig field is 43 ASCII characters instead of the "
            "canonical 86. §04 declared-length check at stage 5 rejects with "
            "E_SCHEMA_FIELD_SYNTAX before stage 6 signature decoding fires "
            "(§10 first-failing-stage precedence)."
        ),
        spec_refs=["§04", "§02"],
        verdict="reject",
        diagnostic="E_SCHEMA_FIELD_SYNTAX",
        body_obj=m_short,
        context={"fetched_origin_address": m_short["origin"]["address"]},
    ))

    # Non-canonical S: take the valid signature from manifest m, replace S
    # with S + L. The resulting signature verifies under cofactored rules but
    # is rejected under the strict profile (§05).
    real_sig = b64u_decode(m["sig"])
    nc_sig = non_canonical_s(real_sig)
    m_nc = dict(m)
    m_nc["sig"] = b64u(nc_sig)
    out.append(vec(
        "152-sig-non-canonical-s",
        kind="manifest",
        description="Manifest with a signature whose S component is non-canonical (S' = S + L >= L). The signature would verify under cofactored Ed25519, but the strict profile (§05) rejects non-canonical S. E_SIG_VERIFICATION.",
        spec_refs=["§05"],
        verdict="reject",
        diagnostic="E_SIG_VERIFICATION",
        body_obj=m_nc,
        context={"fetched_origin_address": m_nc["origin"]["address"]},
    ))

    # Small-order public key (identity). The strict profile rejects the
    # public key before signature verification; the vector replaces both
    # publisher_pubkey and the sig with a placeholder. Even with a forged
    # signature, the public-key rejection takes precedence.
    m_smallorder = dict(m)
    m_smallorder["publisher_pubkey"] = b64u(SMALL_ORDER_A)
    m_smallorder["sig"] = b64u(b"\x00" * 64)
    out.append(vec(
        "153-sig-small-order-pubkey",
        kind="manifest",
        description="Manifest where publisher_pubkey is the encoded identity point (small-order, order 1). The strict profile (§05) rejects small-order public keys before signature verification; E_SIG_VERIFICATION.",
        spec_refs=["§05"],
        verdict="reject",
        diagnostic="E_SIG_VERIFICATION",
        body_obj=m_smallorder,
        context={"fetched_origin_address": m_smallorder["origin"]["address"]},
    ))

    # ---- base64url strictness ----
    # padded sig
    m_padded = dict(m)
    real_sig_b = b64u_decode(m["sig"])
    m_padded["sig"] = base64.urlsafe_b64encode(real_sig_b).decode("ascii")  # keeps "=" padding — no rstrip
    out.append(vec(
        "160-base64url-padded",
        kind="manifest",
        description="Manifest whose sig field carries '=' padding. Strict base64url decoding rejects with E_SCHEMA_FIELD_SYNTAX before signature verification.",
        spec_refs=["§04", "§02"],
        verdict="reject",
        diagnostic="E_SCHEMA_FIELD_SYNTAX",
        body_obj=m_padded,
        context={"fetched_origin_address": m_padded["origin"]["address"]},
    ))

    # standard alphabet (+/) instead of url-safe (-_)
    m_stdalpha = dict(m)
    std_b64 = base64.b64encode(real_sig_b).rstrip(b"=").decode("ascii")
    if "+" not in std_b64 and "/" not in std_b64:
        # extremely unlikely with random 64-byte sig but handle gracefully
        std_b64 = std_b64[:-1] + "+"
    m_stdalpha["sig"] = std_b64
    out.append(vec(
        "161-base64url-standard-alphabet",
        kind="manifest",
        description="Manifest whose sig field uses the standard base64 alphabet (+ and /) instead of the URL-safe alphabet (- and _). Rejected with E_SCHEMA_FIELD_SYNTAX.",
        spec_refs=["§04"],
        verdict="reject",
        diagnostic="E_SCHEMA_FIELD_SYNTAX",
        body_obj=m_stdalpha,
        context={"fetched_origin_address": m_stdalpha["origin"]["address"]},
    ))

    # whitespace in sig
    m_ws = dict(m)
    m_ws["sig"] = m["sig"][:43] + " " + m["sig"][43:]
    out.append(vec(
        "162-base64url-whitespace",
        kind="manifest",
        description="Manifest whose sig field contains an embedded space character. Strict base64url rejects whitespace; E_SCHEMA_FIELD_SYNTAX.",
        spec_refs=["§04"],
        verdict="reject",
        diagnostic="E_SCHEMA_FIELD_SYNTAX",
        body_obj=m_ws,
        context={"fetched_origin_address": m_ws["origin"]["address"]},
    ))

    # ---- binding: path mismatch, /manifest.json reservation, request_hash ----
    c = make_content(runtime_priv=rp, path="/articles/foo")
    out.append(vec(
        "170-bind-path-mismatch",
        kind="content",
        description="Otherwise-valid content document whose path field is /articles/foo, fetched from /articles/bar. Stage 9 path binding rejects with E_BIND_PATH.",
        spec_refs=["§02", "§10"],
        verdict="reject",
        diagnostic="E_BIND_PATH",
        body_obj=c,
        context={
            "fetched_path": "/articles/bar",
            "expected_runtime_pubkey": b64u(rp_pub),
        },
    ))

    # /manifest.json as content path — schema-level rejection (rc.6 reservation)
    c_manifest_path = make_content(runtime_priv=rp, path="/manifest.json")
    out.append(vec(
        "171-bind-reserved-manifest-path",
        kind="content",
        description="Content document declaring path /manifest.json. The path is reserved for manifest fetches and the schema rejects it with E_SCHEMA_FIELD_SYNTAX.",
        spec_refs=["§02", "§09"],
        verdict="reject",
        diagnostic="E_SCHEMA_FIELD_SYNTAX",
        body_obj=c_manifest_path,
        context={
            "fetched_path": "/manifest.json",
            "expected_runtime_pubkey": b64u(rp_pub),
        },
    ))

    # transaction with mismatched request_hash
    t, sb = make_transaction(runtime_priv=rp)
    # Tamper the recorded submit body so the locally-computed request_hash
    # differs from the one in the (still valid) transaction.
    sb_tampered = dict(sb)
    sb_tampered["fields"] = {"message": "TAMPERED", "name": "alice"}
    out.append(vec(
        "172-bind-request-hash-mismatch",
        kind="transaction",
        description="Transaction document whose request_hash matches the original submit body, but the client's recorded submit body has been tampered (fields.message changed). Stage 9 rejects with E_BIND_REQUEST_HASH.",
        spec_refs=["§02", "§09"],
        verdict="reject",
        diagnostic="E_BIND_REQUEST_HASH",
        body_obj=t,
        context={
            "submit_path": t["in_response_to"],
            "expected_runtime_pubkey": b64u(rp_pub),
            "submit_body_path": "vectors/172-bind-request-hash-mismatch/submit_body.json",
        },
        extra_files={
            "submit_body.json": json.dumps(
                sb_tampered, separators=(",", ":"), ensure_ascii=False
            ).encode("utf-8"),
        },
    ))

    # ---- canary: equal issued_at conflict ----
    m_alt = make_manifest(
        publisher_priv=pp, publisher_pub=pp_pub,
        origin_pub=op_pub, runtime_pub=keys["runtime_pub_2"],
        # same issued_at as 001
    )
    out.append(vec(
        "180-canary-equal-issued-at-conflict",
        kind="manifest",
        description="Two manifests with the same canary.issued_at and the same K_publisher.pub but different runtime_pubkey. Once 001 is verified and retained, observing this manifest at the same issued_at must produce E_CANARY_CONFLICT.",
        spec_refs=["§08"],
        verdict="reject",
        diagnostic="E_CANARY_CONFLICT",
        body_obj=m_alt,
        context={
            "fetched_origin_address": m_alt["origin"]["address"]
        ,
            "previously_verified": "vectors/001-manifest-valid-minimal/input.json",
        },
    ))

    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    # Reset the vectors directory so generation is fresh and reproducible.
    if VECTORS_DIR.exists():
        shutil.rmtree(VECTORS_DIR)
    VECTORS_DIR.mkdir(parents=True)

    publisher_priv, publisher_pub = keypair(PUBLISHER_SEED)
    runtime_priv, runtime_pub = keypair(RUNTIME_SEED)
    origin_priv, origin_pub = keypair(ORIGIN_SEED)
    runtime_priv_2, runtime_pub_2 = keypair(RUNTIME_SEED_2)

    keys = {
        "publisher_priv": publisher_priv,
        "publisher_pub": publisher_pub,
        "runtime_priv": runtime_priv,
        "runtime_pub": runtime_pub,
        "origin_priv": origin_priv,
        "origin_pub": origin_pub,
        "runtime_priv_2": runtime_priv_2,
        "runtime_pub_2": runtime_pub_2,
    }

    keys_doc = {
        "_comment": "Test fixtures only. NEVER use these for any real deployment.",
        "publisher": {
            "seed_hex": PUBLISHER_SEED.hex(),
            "pub_b64u": b64u(publisher_pub),
        },
        "runtime": {
            "seed_hex": RUNTIME_SEED.hex(),
            "pub_b64u": b64u(runtime_pub),
        },
        "origin": {
            "seed_hex": ORIGIN_SEED.hex(),
            "pub_b64u": b64u(origin_pub),
            "tor_v3_address": onion_address(origin_pub),
        },
        "runtime_2": {
            "seed_hex": RUNTIME_SEED_2.hex(),
            "pub_b64u": b64u(runtime_pub_2),
        },
    }
    (ROOT / "keys.json").write_text(
        json.dumps(keys_doc, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    vectors: list[dict] = []
    vectors.extend(positive_vectors(keys))
    vectors.extend(negative_vectors(keys))

    corpus = {
        "_comment": "Generated by corpus/tools/generate.py. Do not hand-edit.",
        "spec_version_target": "1.0",
        "rc_target": "1.0-rc.9",
        "keys": "keys.json",
        "clock_now": "2026-05-07T00:01:00Z",
        "vectors": vectors,
    }
    (ROOT / "corpus.json").write_text(
        json.dumps(corpus, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"Generated {len(vectors)} vectors -> {VECTORS_DIR}")
    print(f"  positive: {sum(1 for v in vectors if v['expected']['verdict'] == 'accept')}")
    print(f"  negative: {sum(1 for v in vectors if v['expected']['verdict'] == 'reject')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
