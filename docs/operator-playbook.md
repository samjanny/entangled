# Operator Playbook

**Status: Draft / non-normative.**

This document is a placeholder for operational guidance that supports running an Entangled publisher deployment. It is not part of the numbered specification (`specs/00-overview.md` through `specs/11-errors-and-versioning.md`) and does not define protocol behavior.

When this document and the numbered specification differ, the numbered specification governs.

## Scope

When written out, the playbook will collect operational guidance for:

- `K_publisher` custody — offline generation, storage, ceremony hardware, secret-sharing, and disaster recovery for the publisher identity key;
- `K_origin` deployment — provisioning the carrier endpoint key on publishing infrastructure, with attention to Tor v3 onion-service requirements;
- `K_runtime` rotation — periodic ceremonies that generate a fresh runtime key, sign a new manifest, deploy the new runtime private key, and destroy the previous one;
- canary ceremonies — composing canary fields, choosing `next_expected` intervals, optionally including a `freshness_proof`, and the cadence at which the publisher must refresh;
- server compromise response — detection signals, immediate steps to revoke compromised operational keys, and how to publish a new manifest when the publishing infrastructure has been replaced;
- backup and recovery practices — preserving signed historical content, retaining old manifests for historical-content verification, and recovering from loss of `K_runtime` or `K_origin` without losing publisher identity.

These topics are operational concerns for the publisher. They sit outside the protocol's normative scope but are required for a viable deployment.

## What this document is not

This document is not:

- a normative part of Entangled v1.0 conformance;
- a substitute for the numbered specification's requirements on key roles (§05), manifest lifecycle (§06), canary lifecycle (§08), or client behavior (§10);
- a guarantee that specific tools, vendors, or hardware are appropriate for any given threat model.

## Status

The detailed operator playbook is not yet drafted. This stub exists so that references from the numbered specification and from `README.md` resolve to a real file.

Detailed operational procedures will be added in subsequent revisions. Until then, operators should treat the numbered specification as the source of truth for protocol-level requirements and consult their own operational practices for matters outside that scope.
