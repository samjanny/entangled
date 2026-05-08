# Operator Playbook

**Status: Draft / non-normative operational guidance.**

This playbook describes recommended operational practices for running an Entangled publisher deployment.

It supports the numbered Entangled v1.0 specification, but it is not itself part of the normative wire protocol. When this document and the numbered specification differ, the numbered specification governs.

The purpose of this playbook is to reduce the gap between the protocol's cryptographic model and real-world operation. Entangled's publisher-identity guarantees depend on correct custody of `K_publisher`, disciplined rotation of `K_runtime`, safe deployment of `K_origin`, and careful response to compromise.

## 1. Operational security goals

An Entangled deployment has three practical security goals:

1. keep `K_publisher_priv` offline and outside the publishing infrastructure;
2. limit the damage caused by compromise of `K_origin_priv` or `K_runtime_priv`;
3. preserve publisher identity continuity across server replacement, origin rotation, and carrier migration.

The protocol helps with these goals by separating three keys:

* `K_publisher`: long-term publisher identity key;
* `K_origin`: carrier endpoint key, such as the Tor v3 onion-service key;
* `K_runtime`: operational signing key for content and transaction documents.

The operator's job is to keep these roles separate in practice.

## 2. Threat assumptions

This playbook assumes that the publishing infrastructure may eventually be compromised.

A compromise may expose:

* the onion-service key or other carrier endpoint key;
* the current runtime signing key;
* unsigned source content before publication;
* deployment scripts;
* server logs;
* transaction-handling code;
* stored request data received through submit endpoints.

A routine server compromise must not expose `K_publisher_priv`.

If `K_publisher_priv` is exposed, publisher identity is compromised. Entangled v1 has no in-band recovery mechanism for a compromised publisher identity key. Recovery then requires generating a new publisher identity, publishing the new PIP through out-of-band channels, and rebuilding user trust.

## 3. Key roles and custody requirements

## 3.1 `K_publisher`

`K_publisher` is the publisher identity key.

It signs manifests. It does not sign content or transaction documents directly.

### Requirements

`K_publisher_priv` MUST NOT be present on:

* the web server;
* the onion-service host;
* CI/CD systems;
* build runners;
* deployment scripts;
* developer laptops used for routine publishing;
* shared cloud storage;
* unattended remote machines;
* source repositories, even private ones.

`K_publisher_priv` SHOULD be generated and used only on an offline ceremony machine.

The public key `K_publisher.pub` and the Publisher Identity Phrase (PIP) are public information. They may be published widely.

### Recommended custody model

Use one of the following models:

1. **Offline laptop model.** A dedicated laptop kept offline except when physically maintained. It generates `K_publisher`, signs manifests, and exports signed manifests plus runtime private keys through removable media.

2. **Air-gapped removable OS model.** A bootable read-only or reproducible environment used only for publisher ceremonies. Secrets are stored on encrypted removable media.

3. **Hardware-backed model.** A hardware token or signing device holds `K_publisher_priv` and signs manifest payloads without exposing the private key. This model is acceptable only if the signing flow can produce the exact Ed25519 signature input required by the Entangled specification.

The operator should choose the simplest model they can perform reliably.

### Backup

The publisher should maintain at least two encrypted backups of `K_publisher_priv`.

Backups should be stored in separate physical locations.

A backup should include:

* `K_publisher_priv`;
* `K_publisher.pub`;
* the PIP;
* creation date;
* the tool version or procedure used to generate it;
* recovery instructions sufficient for a trusted operator to reconstruct the signing environment.

Backups must not be stored on the publishing infrastructure.

## 3.2 `K_origin`

`K_origin` is the carrier endpoint key.

For Tor v3, this is the onion-service key whose public key is encoded in the `.onion` address.

### Requirements

`K_origin_priv` must be present wherever the carrier service requires it.

For Tor v3, this normally means the onion-service host stores the onion-service private key.

Compromise of `K_origin_priv` compromises the carrier endpoint, but does not compromise publisher identity unless `K_publisher_priv` is also compromised.

### Operational notes

Treat `K_origin_priv` as sensitive online infrastructure material.

Restrict file permissions.

Back it up only if preserving the same address is operationally important.

If `K_origin_priv` is suspected compromised, rotate to a new origin and publish a fresh manifest signed by `K_publisher` authorizing the new `origin`.

## 3.3 `K_runtime`

`K_runtime` signs content and transaction documents for the current publication cycle.

It is intentionally more exposed than `K_publisher`.

### Requirements

`K_runtime_priv` may be present on the publishing infrastructure.

It should be rotated whenever the canary is refreshed.

Old `K_runtime_priv` values should be destroyed after successful deployment of the new manifest and runtime key.

### Compromise impact

An attacker with the current `K_runtime_priv` can sign valid current content and transaction documents as long as clients accept the manifest that authorizes that runtime key.

Canary expiration does not cryptographically revoke `K_runtime`. It changes the client presentation state to a warning. Operators who suspect `K_runtime_priv` compromise must perform an out-of-cycle runtime rotation.

## 4. Publisher identity setup ceremony

This ceremony creates the long-term publisher identity.

Perform it offline.

### Inputs

* offline ceremony machine;
* trusted Entangled key-generation tool;
* encrypted backup media;
* paper or other durable medium for recording the PIP;
* optional hardware signing device.

### Steps

1. Boot or prepare the offline ceremony environment.
2. Generate a new Ed25519 keypair for `K_publisher`.
3. Compute `K_publisher.pub`.
4. Compute the Publisher Identity Phrase from `K_publisher.pub`.
5. Verify that the PIP is labeled as public publisher identity, not as a seed phrase or recovery secret.
6. Store `K_publisher_priv` in encrypted form.
7. Create at least two encrypted backups.
8. Record the PIP separately in a human-readable form.
9. Confirm that no copy of `K_publisher_priv` was written to unencrypted storage.
10. Shut down the ceremony environment.

### Output

* `K_publisher_priv`, offline only;
* `K_publisher.pub`, public;
* PIP, public;
* encrypted backups;
* ceremony log.

### Ceremony log

The ceremony log should contain:

* date and time;
* operator names or roles;
* tool versions;
* key fingerprint or public key;
* generated PIP;
* backup locations;
* any deviations from the procedure.

The ceremony log must not contain `K_publisher_priv`.

## 5. Initial deployment ceremony

This ceremony creates the first origin, runtime key, canary, and manifest.

### Inputs

* `K_publisher_priv` in the offline ceremony environment;
* carrier endpoint key or carrier endpoint public key;
* current site navigation;
* current state policy;
* canary statement;
* optional freshness proof;
* desired `next_expected` interval;
* current content set.

### Steps

1. Generate or obtain the carrier endpoint key `K_origin`.
2. For Tor v3, derive the `.onion` address from `K_origin.pub` and verify the address-to-key binding.
3. Generate a fresh `K_runtime` keypair.
4. Compose the canary object:

   * `runtime_pubkey` = `K_runtime.pub`;
   * `issued_at` = current UTC time;
   * `next_expected` = chosen future UTC time within the protocol bounds;
   * `statement` = chosen canary statement;
   * `freshness_proof` = optional external freshness reference.
5. Compose the manifest with:

   * `spec_version`;
   * `kind`;
   * `publisher_pubkey`;
   * `origin`;
   * `canary`;
   * `state_policy`;
   * `navigation`;
   * `min_refresh_interval`;
   * `updated`.
6. Validate the unsigned manifest against the manifest schema.
7. Canonicalize the signed payload using JCS.
8. Sign the manifest with `K_publisher_priv`.
9. Add the `sig` field.
10. Verify the completed manifest using an independent verification step.
11. Transfer the signed manifest and `K_runtime_priv` to the publishing infrastructure.
12. Deploy `/manifest.json`.
13. Configure the server to sign content and transaction documents with `K_runtime_priv`.
14. Verify the site from a clean Entangled client.
15. Publish the PIP through out-of-band channels.

### Output

* signed `/manifest.json`;
* active `K_runtime_priv` on publishing infrastructure;
* active carrier endpoint;
* public PIP;
* deployment log.

## 6. Routine content publication

Routine content publication should not require `K_publisher_priv`.

The publishing infrastructure signs content documents with the currently authorized `K_runtime_priv`.

### Steps

1. Prepare the content document.
2. Ensure the document uses only allowed block types and fields.
3. Ensure the `path` field equals the intended serving path byte-for-byte.
4. Hash any referenced image resources and include their SHA-256 digests.
5. Validate the content document schema before signing.
6. Sign the content document with the current `K_runtime_priv` using the content context string.
7. Deploy the signed content document at its signed path.
8. Fetch the document through the carrier using a client or conformance tool.
9. Confirm that path binding, signature verification, and image verification pass.

### Notes

Changing a content document at the same path creates a new signed object, but Entangled v1 has no explicit `revision` or `content_hash` field. Operators who republish content at an existing path should keep their own publication log.

## 7. Canary and runtime rotation ceremony

The canary ceremony refreshes publisher-control attestation and authorizes a new runtime key.

It requires `K_publisher_priv`, so it must occur in the offline ceremony environment.

### When to rotate

Rotate before `next_expected`.

Recommended margin:

* high-risk deployment: at least 24 hours before `next_expected`;
* normal deployment: at least 3 days before `next_expected`;
* low-risk deployment: at least 7 days before `next_expected` if using long canary intervals.

Rotate immediately if `K_runtime_priv` may have been exposed.

### Inputs

* current manifest;
* current publisher history record;
* current `K_publisher_priv`;
* new canary statement;
* optional freshness proof;
* current origin information;
* current state policy and navigation;
* chosen `next_expected`.

### Steps

1. Enter the offline ceremony environment.
2. Review the current manifest and canary `issued_at`.
3. Generate a fresh `K_runtime` keypair.
4. Compose a new canary with:

   * new `runtime_pubkey`;
   * new `issued_at` greater than the previously published canary `issued_at`;
   * new `next_expected` within the allowed interval;
   * statement;
   * optional freshness proof.
5. Compose a new manifest preserving the current origin unless intentionally rotating origin.
6. Preserve or update `state_policy`, `navigation`, and `min_refresh_interval` as intended.
7. Set `updated` to the current UTC time.
8. Validate the unsigned manifest.
9. Sign the manifest with `K_publisher_priv`.
10. Verify the signed manifest independently.
11. Transfer the new manifest and new `K_runtime_priv` to the publishing infrastructure.
12. Deploy the new manifest atomically or near-atomically.
13. Configure the publisher infrastructure to use the new `K_runtime_priv`.
14. Stop using the previous `K_runtime_priv`.
15. Destroy the previous `K_runtime_priv` where practical.
16. Verify from a clean client that the new canary is fresh and the new runtime key signs content correctly.
17. Record the rotation in the operator log.

### Atomicity guidance

The manifest and runtime key must be deployed together.

A server that publishes the new manifest but still signs content with the old runtime key will produce document signature failures.

A server that signs content with the new runtime key before publishing the new manifest will also produce document signature failures.

## 8. Origin rotation ceremony

Origin rotation replaces the carrier endpoint key and, for Tor v3, usually changes the onion address.

Origin rotation requires a fresh manifest signed by `K_publisher`.

### When to rotate origin

Rotate origin when:

* `K_origin_priv` is suspected compromised;
* the server is replaced after compromise;
* the publisher intentionally migrates to a new carrier endpoint;
* operational security requires address rotation.

### Steps

1. Generate a new `K_origin` keypair in the carrier environment or an appropriate secure environment.
2. For Tor v3, derive and record the new `.onion` address.
3. Verify that the derived address encodes the new `K_origin.pub`.
4. Enter the offline publisher ceremony environment.
5. Generate a fresh `K_runtime` keypair unless intentionally preserving the current runtime key.
6. Compose a fresh canary with a strictly newer `issued_at`.
7. Compose a new manifest declaring the new origin.
8. Sign the manifest with `K_publisher_priv`.
9. Deploy the new carrier endpoint.
10. Deploy the new manifest at `/manifest.json` on the new origin.
11. Deploy content and runtime signing infrastructure.
12. Verify the new origin from a clean client.
13. Publish the new address through out-of-band channels together with the same PIP.

### Important limitation

Entangled v1 preserves publisher identity across origin changes, but it does not provide automatic discovery of a new origin when the old origin is unreachable.

Users learn about the new origin through out-of-band channels, through publisher profiles, or through signed links from an old origin while that old origin remains available and trustworthy.

## 9. Multi-origin operation

Entangled v1 manifests are single-origin.

A publisher operating multiple origins under the same `K_publisher.pub` publishes one manifest per origin.

### Requirement

Canary `issued_at` values must remain monotonically non-decreasing across all origins for the same publisher identity.

If one origin publishes a newer canary and another origin still serves an older manifest, clients that have seen the newer canary may reject the older origin as a downgrade.

### Recommended practice

Treat multi-origin manifest deployment as atomic or near-atomic:

1. prepare all per-origin manifests in one ceremony;
2. use the same `canary.issued_at` only if the signed payloads are otherwise identical where the protocol permits;
3. avoid same-`issued_at` divergent manifests unless the specification explicitly permits the exact form;
4. deploy all origins before announcing the refresh;
5. verify each origin from a clean client.

If exact atomicity is impossible, deploy in a maintenance window and expect some clients to warn or reject stale origins until all origins are updated.

## 10. State policy operation

State is client-stored and publisher-scoped.

Operators should treat `state_policy` as a privacy-sensitive public contract.

### Principles

* Declare only state items the site actually needs.
* Use `client_only` unless the value must be sent with submit requests.
* Use the shortest practical lifetime.
* Use the smallest practical size limit.
* Write clear, non-misleading purpose strings.
* Do not store secrets as request state unless they must be transmitted to submit endpoints.

### Request-state warning

In Entangled v1, request state is publisher-wide. Once consented, a request-state item may be attached to every future submit request for the same publisher until it expires, is deleted, or consent is revoked.

Do not use request state for values that should be confined to one endpoint.

### Policy changes

Before changing `state_policy`, review whether the change:

* removes a state item;
* changes mode from `client_only` to `request`;
* changes `max_size`;
* changes `max_lifetime`;
* changes the purpose string.

A mode change from `client_only` to `request` is privacy-sensitive and should be treated as a new consent surface.

## 11. Submit endpoint operation

Submit bodies are unsigned user input.

Publishers must treat all submit fields and request-state values as untrusted.

### Server-side requirements

A submit endpoint should:

1. enforce the Entangled submit body schema;
2. reject duplicate `request_state` entries;
3. validate all user fields against application-level rules;
4. treat request-state values as untrusted bearer data;
5. produce a signed transaction document using the current `K_runtime_priv`;
6. copy `request_id` exactly from the submit body;
7. compute `request_hash` exactly as required by the protocol;
8. include state updates only for items declared in the current manifest `state_policy`.

### Replay note

`request_id` and `request_hash` bind a transaction response to the submit body observed by the client. They are not a general server-side anti-replay mechanism.

If an application needs replay protection, it must implement it at the application layer, for example by using request-state tokens, one-time form tokens, or server-side nonce tracking.

## 12. Image operation

Images are signed indirectly by hash binding.

The signed document contains the expected SHA-256 digest. The image bytes are fetched separately and decoded only after the hash matches.

### Operator checklist

For every image block:

1. store the image on the same origin as the document;
2. ensure the image path satisfies Entangled path syntax;
3. ensure the image format is permitted in v1;
4. ensure the image is not animated;
5. compute SHA-256 over the exact response body bytes;
6. include the digest in the `image.sha256` field;
7. declare correct `media_type`, `width`, and `height`;
8. keep the image below the response size limit;
9. test with a conforming client.

### Security note

Hash verification authenticates image bytes. It does not make image decoding safe.

Client implementations should use hardened image decoders, memory-safe libraries, process isolation, or sandboxing where practical.

Operators should avoid unnecessary image formats and should prefer simple, static images.

## 13. Transport operation

For Tor v3, Entangled uses HTTP over the onion service.

HTTPS is not required by the v1 Tor profile.

### Server behavior

The server should:

* serve `/manifest.json` with `Content-Type: application/entangled+json`;
* serve content and transaction documents with `Content-Type: application/entangled+json`;
* require submit requests to use `Content-Type: application/entangled-submit+json`;
* include accurate `Content-Length`;
* avoid redirects;
* avoid cookies;
* avoid cache-control semantics as protocol signals;
* avoid compression unless a future protocol version specifies it;
* return only whitelisted status codes.

### Recommended hardening

Disable:

* access logs containing sensitive submit data;
* default server banners where practical;
* automatic redirects;
* HTTP compression;
* cookie injection by frameworks;
* analytics middleware;
* generic web application features not used by Entangled.

## 14. Monitoring and audit logs

Operational logs should help detect compromise without leaking user data.

### Recommended logs

Keep logs for:

* manifest signing ceremonies;
* canary refreshes;
* runtime rotations;
* origin rotations;
* deployment timestamps;
* published manifest hashes;
* public runtime keys used per cycle;
* unexpected signature verification failures during deployment tests;
* unexpected transport status codes;
* server compromise indicators.

### Avoid logging

Avoid logging:

* raw submit bodies;
* request-state values;
* state update values;
* user-entered form data;
* IP addresses or carrier-level metadata beyond what is operationally necessary;
* private keys;
* decrypted backups.

If logs must contain sensitive operational material, protect them separately from the publishing infrastructure.

## 15. Server compromise response

Use this procedure if the publishing infrastructure may be compromised but `K_publisher_priv` is believed safe.

### Immediate actions

1. Stop the compromised service if doing so does not create greater risk.
2. Preserve forensic evidence if needed.
3. Assume `K_origin_priv` and `K_runtime_priv` are exposed.
4. Do not use the compromised host for signing or deployment.
5. Prepare replacement infrastructure.
6. Generate a new `K_origin` if endpoint compromise is suspected.
7. Generate a new `K_runtime`.
8. Use the offline `K_publisher` ceremony to sign a fresh manifest.
9. Deploy the fresh manifest to clean infrastructure.
10. Publish an incident notice as signed Entangled content if appropriate.
11. Publish out-of-band notice if the origin changed.

### Client-visible result

Clients that fetch the new manifest see a fresh canary and new runtime authorization.

If clients observed a canary gap or downgrade attempt, they may continue to show history warnings.

Do not attempt to hide a canary gap. The protocol treats the gap as a user-visible event.

## 16. Runtime key compromise response

Use this procedure if `K_runtime_priv` may be compromised but `K_origin_priv` and `K_publisher_priv` are believed safe.

### Steps

1. Stop using the compromised runtime key.
2. Generate a new `K_runtime` keypair offline or in a trusted environment.
3. Compose a fresh canary with a newer `issued_at`.
4. Sign a new manifest with `K_publisher_priv`.
5. Deploy the new manifest and new runtime key together.
6. Re-sign current content with the new runtime key if necessary.
7. Review content signed during the suspected compromise window.
8. Publish an incident note if users may have seen forged or untrusted content.

### Limitation

Entangled v1 has no in-band revocation list for previously authorized runtime keys.

Clients that already recorded an old runtime key as historically authorized may still verify historical content signed under that key. Operators should explain any suspected runtime compromise window to users.

## 17. Origin key compromise response

Use this procedure if `K_origin_priv` may be compromised.

### Steps

1. Generate a new origin key.
2. Deploy a new carrier endpoint.
3. Generate a fresh runtime key unless intentionally preserving the existing one.
4. Sign a new manifest with `K_publisher_priv` authorizing the new origin.
5. Deploy the new manifest to the new origin.
6. Announce the new address through out-of-band channels together with the same PIP.
7. Retire the old origin if possible.
8. Monitor for continued traffic or malicious content on the old origin.

### Notes

An attacker with the old `K_origin_priv` may continue serving the old address. Clients that have already observed a newer manifest for the same `K_publisher.pub` should reject older manifests as downgrade attempts. New clients without history may require out-of-band freshness information.

## 18. Publisher key compromise response

Use this procedure only if `K_publisher_priv` may be compromised.

This is the most severe failure.

### Consequences

An attacker with `K_publisher_priv` can sign manifests authorizing arbitrary origins and runtime keys.

Entangled v1 cannot distinguish the legitimate publisher from the attacker using only in-band protocol data.

### Steps

1. Stop using the compromised publisher identity.
2. Generate a new `K_publisher` in a clean offline ceremony.
3. Compute a new PIP.
4. Generate fresh origin and runtime keys.
5. Publish a new Entangled deployment under the new publisher identity.
6. Announce the compromise and new PIP through out-of-band channels that users already trust.
7. Do not rely solely on the compromised old identity to announce the new identity.
8. Preserve evidence and logs for investigation.

### User communication

The announcement should say clearly:

* the old publisher identity may be compromised;
* the old PIP must no longer be trusted;
* the new PIP is the new identity anchor;
* users should treat in-band messages from the old identity with suspicion after the suspected compromise time.

## 19. Loss of keys

## 19.1 Loss of `K_runtime_priv`

Generate a new runtime key and sign a new manifest with `K_publisher`.

Previously signed content remains verifiable where clients have appropriate history.

## 19.2 Loss of `K_origin_priv`

Generate a new origin key and sign a new manifest authorizing the new origin.

The address changes for Tor v3.

Publish the new address out-of-band.

## 19.3 Loss of `K_publisher_priv`

If all copies of `K_publisher_priv` are lost, the publisher cannot sign future manifests for that identity.

Existing content may remain verifiable, but the publisher cannot rotate runtime keys, rotate origins, or refresh the canary under that identity.

Recovery requires creating a new publisher identity and distributing a new PIP out-of-band.

## 20. Backup and archival strategy

Operators should preserve enough material to support continuity and auditability.

### Preserve

* `K_publisher_priv` encrypted backups;
* `K_publisher.pub`;
* PIP;
* all signed manifests;
* canary ceremony logs;
* runtime public keys and authorization windows;
* current content source files;
* signed content documents if historical verification is desired;
* image files matching signed hashes;
* origin rotation records;
* incident reports.

### Do not preserve unnecessarily

* old `K_runtime_priv` values after rotation;
* submit bodies containing user data;
* request-state values;
* unencrypted private keys;
* temporary signing files.

## 21. Release checklist

Before publishing a new manifest or release:

* [ ] Manifest validates against the schema.
* [ ] `publisher_pubkey` matches the intended `K_publisher.pub`.
* [ ] PIP derived from `publisher_pubkey` matches the public PIP.
* [ ] Origin address matches `origin_pubkey`.
* [ ] Canary `issued_at` is newer than the previous canary.
* [ ] Canary `next_expected` is within the allowed interval.
* [ ] `updated` is current UTC and not in the future.
* [ ] `state_policy` contains only intended state items.
* [ ] Navigation paths are valid and same-site.
* [ ] Manifest signature verifies.
* [ ] Runtime key in canary matches deployed `K_runtime_priv`.
* [ ] Content documents verify under the current runtime key.
* [ ] Content document paths match serving paths byte-for-byte.
* [ ] Image hashes match deployed image bytes.
* [ ] Submit endpoints return valid transaction documents.
* [ ] Transaction `request_id` and `request_hash` binding works.
* [ ] No cookies, redirects, compression, or unexpected headers are emitted.
* [ ] Clean client test passes over the carrier.
* [ ] Deployment log is updated.

## 22. Incident checklist

When something goes wrong:

* [ ] Identify whether the suspected compromise affects `K_publisher`, `K_origin`, `K_runtime`, or application data only.
* [ ] Stop routine publishing from affected infrastructure.
* [ ] Preserve evidence if appropriate.
* [ ] Rotate `K_runtime` if runtime compromise is possible.
* [ ] Rotate `K_origin` if endpoint compromise is possible.
* [ ] Generate and sign a fresh manifest from the offline ceremony environment.
* [ ] Deploy to clean infrastructure.
* [ ] Verify from a clean client.
* [ ] Communicate clearly to users if trust, canary freshness, or content integrity may have been affected.
* [ ] Update operational logs.
* [ ] Review and improve the procedure after the incident.

## 23. Minimal deployment profile

A minimal responsible Entangled v1 deployment should satisfy all of the following:

* `K_publisher_priv` generated offline;
* `K_publisher_priv` never placed on server or CI;
* at least two encrypted backups of `K_publisher_priv`;
* public PIP distributed out-of-band;
* Tor v3 origin binding verified before manifest signing;
* fresh `K_runtime` generated for each canary cycle;
* old runtime private keys removed after rotation;
* manifest verified independently before deployment;
* clean-client test after every deployment;
* incident procedure documented;
* canary refresh scheduled before `next_expected`;
* server configured without cookies, redirects, compression, or ambient tracking features.

Operators who cannot satisfy this profile should not present their deployment as production-ready.

## 24. Non-goals of this playbook

This playbook does not provide:

* legal advice about warrant canaries;
* a guarantee that any specific hosting provider is safe;
* a complete forensic response plan;
* a complete physical security plan;
* a complete guide to Tor onion-service administration;
* a substitute for external security review.

It is operational guidance for preserving the assumptions made by the Entangled v1 protocol.
