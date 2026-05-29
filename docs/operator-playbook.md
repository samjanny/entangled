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

### Backup encryption scheme

A backup that "encrypted" implies a passphrase or key strong enough that an offline attacker recovering the storage medium cannot brute-force the contents within the relevant exposure window. Vague guidance of the form "use a strong passphrase" is not sufficient; the operator should adopt a concrete tool and configuration.

The operator SHOULD use one of the following schemes for encrypting `K_publisher_priv` backups:

1. **age with a passphrase** (`age -p`, https://age-encryption.org). The passphrase MUST be drawn from at least 80 bits of entropy. Practical generation: 6 or more words from a published EFF diceware list (~12.9 bits/word; 7 words is approximately 90 bits), or 14 or more random characters from a 64-character alphabet (~6 bits/char). The passphrase MUST be recorded on a durable medium kept separately from the backup itself (paper in a different physical location from any backup copy; never on the same device or in the same backup vault).
2. **GPG symmetric** (`gpg --symmetric --cipher-algo AES256 --s2k-mode 3 --s2k-count 65011712 --s2k-digest-algo SHA512`). The S2K count argument is the operative parameter; the default GPG S2K count is too low for offline attack resistance. Passphrase requirements as above.
3. **age with an SSH or X25519 recipient key** (`age -r <recipient>`). Use when the operator already maintains a recovery key in dedicated hardware (YubiKey, OpenPGP card) and prefers asymmetric-recipient semantics over passphrase semantics. The recipient private key MUST be stored on hardware that resists offline extraction.

The operator SHOULD NOT use:

* ad-hoc passphrase-derived encryption with no documented KDF (e.g., `openssl enc` defaults, which use a low-iteration PBKDF until very recent versions);
* zip/7z password protection (the underlying KDF and cipher choices are file-format-dependent and historically weak);
* full-disk encryption alone (the backup is encrypted only while the disk is locked; mounting it for restore re-exposes the key with no per-file granularity).

The same scheme MUST be documented in the ceremony log (§4 "Ceremony log") so that the recovery operator knows which tool to invoke. Schemes MAY be migrated across rotations as long as the prior scheme remains decryptable for the duration of the migration.

### Backup verification

An encrypted backup that has never been restored is not a backup; it is a hope. The operator MUST exercise each backup at least once per year by performing a test restore in an isolated environment.

The test restore procedure:

1. Mount the backup medium in an offline environment (ideally a fresh boot of the §4 ceremony OS, never on the publishing infrastructure).
2. Decrypt the backup using the documented scheme and passphrase or recipient key.
3. Confirm that the decrypted `K_publisher_priv` matches the recorded `K_publisher.pub` and PIP by deriving the public key from the private key and comparing byte-for-byte against the recorded `K_publisher.pub`.
4. Confirm that signing a test payload with the recovered private key produces a signature that verifies under the recorded public key.
5. Securely wipe the decrypted material from the test environment (see §3.3 "Secure destruction of `K_runtime_priv`" for guidance applicable to any in-memory key material on SSD/swap).
6. Record the verification in the operator log: date, backup identifier, scheme used, verification outcome.

A backup whose verification fails is unusable and the operator MUST immediately create a fresh backup before the next ceremony.

Verification SHOULD also be performed:

* immediately after creating a new backup (the first verification establishes that the encryption scheme and recovery instructions are coherent);
* before rotating to a different backup encryption scheme (so the prior scheme is known-good before the operator commits to the new one);
* after any change to the recovery environment (different OS, different tool version, different hardware).

The verification is the only operational evidence that the backup actually preserves what it is supposed to preserve. Operators who skip verification typically discover backup failure during the very ceremony where the failure matters most.

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

### Secure destruction of `K_runtime_priv`

"Destroy the old `K_runtime_priv`" is non-trivial on modern infrastructure. `rm` deletes a directory entry but does not erase the file's data blocks; SSDs perform wear-leveling that scatters historical block contents across cells the operating system cannot directly address; cloud/VPS hosts retain image snapshots that contain whatever was in memory or on disk at snapshot time; swap and hibernate files persist process memory across reboots. An attacker with later access to the disk (sale, decommission, forensic seizure, snapshot leak) recovers the "destroyed" key if any of these channels was active during the key's lifetime.

The operator's destruction procedure SHOULD be designed around the storage medium actually in use. Concrete guidance:

**For `K_runtime_priv` on a bare-metal server with an HDD (rare):**

* Overwrite the file with random data before unlinking (`shred -uvz` or equivalent), then sync the filesystem. HDD overwrite is reliable because there is no wear-leveling layer.

**For `K_runtime_priv` on a bare-metal server with an SSD (common):**

* Wear-leveling makes per-file overwrite unreliable: the SSD's flash translation layer may re-map the logical block to a different physical cell on the next write, leaving the original cell readable until the controller eventually re-uses it. The operator SHOULD avoid storing `K_runtime_priv` as a plain file on an SSD entirely. Practical options:
  - keep `K_runtime_priv` only in process memory (tmpfs is acceptable; load the key from an encrypted vault at signing-process start, never write the decrypted key to durable storage); on rotation, terminate the signing process and let the OS reclaim the memory pages, which never touched the SSD;
  - if the key MUST be on disk, store it inside a full-disk-encryption (LUKS, FileVault, BitLocker) volume whose passphrase is supplied at boot and not stored on the same machine; destruction is then "forget the passphrase" rather than "overwrite the file";
  - if neither is feasible, accept that bare-file SSD storage cannot be reliably destroyed and treat the SSD itself as a sensitive medium that follows the key through its lifecycle: when the key is destroyed, the SSD is wiped using the manufacturer's secure-erase command or physically destroyed before disposal.

**For `K_runtime_priv` on a cloud or VPS host:**

* Image snapshots taken by the cloud provider during the key's lifetime contain the key. The provider's snapshot deletion is not under the operator's control. The operator SHOULD either:
  - disable provider-managed snapshots for the host that holds `K_runtime_priv`; or
  - treat the cloud provider as an additional trust party and document this in the deployment's threat model (a cloud-hosted Entangled deployment cannot meaningfully reduce `K_runtime` exposure below the provider's snapshot retention horizon).
* Swap and hibernate MUST be disabled on the host (`swapoff -a` + remove swap from `/etc/fstab`; disable systemd hibernation). Otherwise process memory containing `K_runtime_priv` may be written to swap and persist beyond key destruction.

**On rotation in all environments:**

* terminate the signing process before deleting the on-disk key file (otherwise the running process retains the key in memory);
* clear any backup copies, key-management-system entries, or secrets-manager versions of the old key in the same operation (the §16 incident response assumes "destroyed" means "not retrievable from any operator-controlled location");
* record the destruction in the operator log, including which channels (file, KMS, snapshot) were addressed.

A `K_runtime_priv` destruction that omits any of the above leaves residual material that an attacker recovering the storage medium can use to forge content covered by the previous canary cycle. The post-rotation residual window (§16 "The compromise window") assumes the previous key is genuinely destroyed; if it isn't, the residual window extends indefinitely.

### Compromise impact

An attacker with the current `K_runtime_priv` can sign valid current content and transaction documents as long as clients accept the manifest that authorizes that runtime key.

Canary expiration does not cryptographically revoke `K_runtime`. It changes the client presentation state to a warning. Operators who suspect `K_runtime_priv` compromise must perform an out-of-cycle runtime rotation.

The maximum compromise window is bounded by the time elapsed between the compromise and the moment cached clients have observed and accepted a manifest authorizing a replacement runtime key. The protocol's hard upper bound on this window is the canary interval `next_expected - issued_at`, capped at 30 days by §08, plus the §10 clock-skew tolerance of 300 seconds. In practice, operators reduce this window further by choosing shorter canary intervals (see §7 "Choosing canary interval") and by rotating immediately upon discovery (see §16). This window is the rationale for the operational `K_runtime_priv` discipline above and for the §16 incident-response procedure.

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

### Witness and dual-control

The single-operator ceremony described above is the minimum reasonable practice for low-threat and standard deployments. High-threat deployments (journalism with sensitive sources, financial services, multi-stakeholder publications) SHOULD perform the ceremony under a witness or dual-control regime so that no single individual is the unverified author of the publisher identity.

The operator SHOULD adopt one of the following regimes proportionate to the deployment's threat profile:

1. **Witnessed ceremony.** A second trusted individual is physically present for the entire ceremony, observes each step, and counter-signs the ceremony log. The witness does not handle `K_publisher_priv` directly. The witness's role is to attest that the ceremony occurred at the recorded date/time on the recorded equipment and that the recorded PIP corresponds to the public key generated in their presence. The witnessed ceremony defends against later disputes over when the identity was created or which equipment generated it.

2. **Dual-control ceremony with split passphrase.** Two operators are present. Neither knows the full backup passphrase. The passphrase is constructed at ceremony time from two halves, each chosen and recorded independently by one operator, and the halves are stored separately in physical custody of the respective operator. Recovery requires both operators to combine their halves; loss of either half does not lose the key (a third copy exists on durable medium per §3.1 backup) but does require coordination. The dual-control passphrase defends against unilateral exfiltration by either operator and against compelled disclosure from a single party.

3. **Threshold custody (advanced).** `K_publisher_priv` is split using a t-of-n threshold scheme (Shamir Secret Sharing or equivalent) at the end of the ceremony; the share holders are independent parties. Any t of n share holders can reconstruct the key for a future canary ceremony. This regime requires a corresponding ceremony procedure for every signing operation, which is heavy enough that it is appropriate only for deployments where the publisher identity itself represents collective custody (multi-author publications, organizational publishers).

The ceremony log (above) MUST record which regime was used, the witness identity or share-holder identities, and any deviations. A subsequent canary ceremony (§7) under a witnessed or dual-control regime SHOULD follow the same regime; downgrading the regime between ceremonies signals weakened custody and SHOULD be communicated as part of the publisher's operational disclosure.

For deployments that adopt a witness regime, the witness SHOULD also be present for canary rotations that occur in response to suspected compromise (§16, §17, §18), because those rotations are the operationally most consequential ceremonies and benefit most from independent attestation.

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

### Out-of-cycle content correction at indexed paths

When the manifest carries `content_root` (§06 rc.19 N45) and a path is listed in `/content_index.json`, the path is *frozen* between canary ceremonies: serving a different `seq` or body hash than the index declares is non-conformant (§10:616). A publisher who must correct an indexed-path document between ceremonies (typo, factual error, legal request, security correction) has three options, in increasing weight:

1. **Defer the correction to the next scheduled canary ceremony.** Appropriate for non-critical corrections where waiting until the next scheduled rotation is acceptable. The current content remains served unchanged until the ceremony.

2. **Publish the correction at a sibling unindexed path.** Indexed paths are frozen but unindexed paths are not (§06:435). The corrected content can be published at a new path (`/articles/first-post-correction` rather than overwriting `/articles/first-post`), with a fresh content document signed under the current `K_runtime`. The original article remains served at its original path with the original (now-known-incorrect) content; readers reach the correction via navigation or out-of-band reference. This is the lightest weight and preserves the cryptographic invariants for free, at the cost of leaving the incorrect content at its original URL.

3. **Perform an out-of-cycle canary rotation ceremony (§7) that re-computes `content_root`.** Required when the correction MUST appear at the original indexed path (urgent factual correction whose stale form is harmful, legal compulsion to retract specific content, security correction of misleading rendering). Procedure:
   - prepare the corrected content document under a new `seq` (strictly greater than the prior `seq` for that path);
   - re-compute the full `/content_index.json` from the current content set (incorporating the new `seq` and `hash` for the corrected path);
   - compute the new `content_root` as the SHA-256 of the new index bytes;
   - perform the §7 ceremony as usual: new `K_runtime`, new canary, new manifest with the new `content_root`;
   - the canary `issued_at` for this ceremony is strictly newer than the prior canary, so the anti-downgrade rule accepts it;
   - the new manifest, the new `/content_index.json`, and the corrected content document are deployed together (atomicity per §7).

Option 3 is operationally heavy: it consumes a `K_publisher` ceremony, advances `canary.issued_at`, and looks externally indistinguishable from a routine canary refresh. The operator SHOULD log out-of-cycle corrections separately in the operator log so that the rotation history can later be reconciled against the publication intent (e.g., "this rotation was not scheduled; it was an out-of-cycle correction of `/articles/first-post` for a factual error").

For publishers operating high-cadence (7-day) canaries the option-3 cost is modest; for 30-day cadences it represents an early ceremony that may shift the following ceremony's deadline. The cadence floor in §7 "Choosing canary interval" should be chosen with out-of-cycle correction frequency in mind: publishers expecting frequent corrections at indexed paths benefit from shorter intervals.

## 7. Canary and runtime rotation ceremony

The canary ceremony refreshes publisher-control attestation and authorizes a new runtime key.

It requires `K_publisher_priv`, so it must occur in the offline ceremony environment.

### Choosing canary interval

The canary interval `next_expected - issued_at` (§08) bounds the maximum time during which a compromised `K_runtime_priv` can be used to forge content before the publisher is required to rotate. The protocol cap is 30 days; the operational floor depends on the deployment's threat profile.

Recommended floors by threat profile:

* **High-threat** - journalism with sensitive sources, financial services, sites whose readers face physical or legal risk: **7 days**. Aligns with the most aggressive end of the §08-permitted range. Lower bound for operators willing to invest in weekly ceremonies. The 7-day floor keeps the worst-case post-rotation residual exposure (§16 "The compromise window") to approximately one week.
* **Standard** - all other deployments (most editorial sites, advocacy, professional communications, personal publications): **14 to 30 days**. Balances ceremony overhead against exposure window. The 30-day upper end matches the §08:89 MUST ceiling; intervals longer than 30 days are no longer permitted by §08.

A publisher whose content has unequal threat across cycles MAY use shorter intervals during high-risk periods (for example, during active reporting on a sensitive subject) and longer intervals during quieter periods, provided each interval is independently within the §08 bounds and the rotation cadence remains consistent enough that readers do not perceive the canary as broken.

The chosen interval is not a normative commitment to readers, but readers reasonably expect consistency. Communicate the chosen interval and any planned changes through the same out-of-band channel used to distribute the PIP.

### When to rotate

Rotate before `next_expected`.

Recommended margin:

* high-risk deployment: at least 24 hours before `next_expected`;
* normal deployment: at least 3 days before `next_expected`;
* low-risk deployment: at least 7 days before `next_expected` if using long canary intervals.

Rotate immediately if `K_runtime_priv` may have been exposed.

### Pre-staging discipline

A canary ceremony performed on demand against a near `next_expected` deadline is brittle: the operator may discover at ceremony time that the offline machine no longer boots, that backup media has degraded, that the encryption tool version has changed, that the witness is unavailable, or that the publishing infrastructure has drifted since the last ceremony. For high-threat deployments operating at a 7-day canary cadence, on-demand discovery of any of these issues consumes the rotation margin and may force a canary gap.

The operator SHOULD maintain a continuously-ready ceremony posture: every component of the ceremony is verified ready at least one full cadence ahead of the next ceremony deadline, not at the deadline itself.

Pre-staging checklist (perform after each ceremony, not before the next):

* [ ] Offline ceremony machine boots, current ceremony tool version installed and tested against a dummy keypair.
* [ ] Removable media for backup and transfer is functional and readable.
* [ ] Backup decryption succeeds (per §3.1 "Backup verification").
* [ ] A fresh `K_runtime` keypair has been generated and is staged in an encrypted container ready for ceremony use; the corresponding public key is recorded but not yet committed to a manifest. (This is a *staged candidate*; until the next manifest is signed, the publisher is still operating under the previously deployed `K_runtime`.)
* [ ] Witness availability is confirmed for the ceremony window (for witnessed/dual-control deployments per §4).
* [ ] Out-of-band channel templates (PIP announcement, status page entry, social channel post) are pre-drafted and ready to publish on rotation completion.
* [ ] Publishing infrastructure deployment path has been exercised with a dry run since the last ceremony (typically by deploying a minor content update via the existing `K_runtime`).

For 7-day cadences, the pre-staging checklist is the operative defense: the rotation deadline is too close to allow on-demand recovery from any failure. For 14-to-30-day cadences, the checklist is recommended but not load-bearing; the rotation margin is wide enough that one round of on-demand recovery is feasible.

A pre-staged `K_runtime` candidate that is not used by the next ceremony (because the ceremony was deferred, the keypair was suspected exposed, or the operator chose a fresh generation at ceremony time) MUST be destroyed per §3.3 "Secure destruction of `K_runtime_priv`" rather than retained for later use; reusing a long-staged candidate weakens the rotation-fresh-key property.

### Freshness proofs

The `canary.freshness_proof` field (§08) is optional and not validated by the protocol. Its operational purpose is to anchor `canary.issued_at` to an external public event whose timestamp the publisher could not have predicted, defending against a backdated canary that an attacker (or compelled publisher) might have produced earlier than the recorded `issued_at`.

Operators SHOULD include a `freshness_proof` whenever the threat model includes:

* compelled publication of a backdated canary under a previously-compromised `K_publisher_priv` (the attacker forces the publisher to sign a canary at time `t_canary` but back-dates the recorded `issued_at` to `t_pre_compromise`);
* targeted attack where the publisher's identity is high-value enough that a content-history forgery using a stolen `K_publisher` is plausible;
* any deployment that publishes `canary.statement` text whose meaning depends on the publisher being free at the time of issuance ("no warrants have been received as of *issued_at*").

A `freshness_proof` reference event SHOULD be:

* **public**: visible to every reader, not requiring the publisher's cooperation to verify (a tweet from the publisher is not a freshness proof; a tweet from a well-known third party with a verifiable timestamp is);
* **unpredictable**: not derivable from a published schedule or from prior reference events (a bitcoin block header hash is unpredictable; "the BBC headline at 12:00 UTC" is unpredictable to a few hours in advance; "tomorrow's stock market close" is predictable);
* **timestamped externally**: the external system records when the event occurred so that any reader can verify the event was not available before `issued_at - tolerance`;
* **stable**: the reference text or hash is not rewritten or deleted by the external system (avoid social-media posts that the publisher could delete in coordination with the attacker).

Concrete reference options ordered by ease of use:

1. **Recent bitcoin block header hash with the block number and timestamp.** Public, unpredictable, externally timestamped (the block must have been mined no earlier than its declared timestamp), stable (rewriting block history requires reversing the proof-of-work). Format: `"bitcoin block 871234 0000000000000000000abc...def issued at 2026-05-07T11:42:18Z"`. Choose the most recent block whose timestamp is within the 5-minute clock-skew tolerance (§10) of the `issued_at` value being signed.
2. **Recent headline from one or more major news outlets, with date and outlet name(s).** Public, unpredictable on the same-day horizon, externally timestamped (the outlet's publication time is verifiable), reasonably stable for major outlets. Format: `'"<headline>" - <outlet>, 2026-05-07'`. Two independent outlets provide redundancy against any one being controlled or deleted.
3. **A recent commit hash from a well-known, third-party-controlled, public git repository.** Public, unpredictable for hashes whose corresponding commit is not the publisher's own. Format: `"github.com/torvalds/linux commit abc123def... at 2026-05-07T08:34:00Z"`.

The publisher SHOULD NOT use:

* their own social media posts, blog entries, or other self-published content (the publisher controls the timestamp); the entire point of a freshness proof is to commit to an event the publisher cannot have authored;
* timestamps from services the publisher operates (NTP servers, status pages) for the same reason;
* schedules or recurring events known in advance.

Recording: the chosen reference is placed in `canary.freshness_proof` as a UTF-8 string with enough context (block number/hash, outlet name, commit hash) that any reader can re-fetch and verify the event. A reader's verification step is informal: the reader observes that the reference event existed at or near `issued_at` and could not have been predicted earlier; this is sufficient to corroborate `issued_at` without requiring protocol-level validation.

A freshness proof does not protect against compromise after `issued_at`; it only protects against backdated `issued_at`. The canary mechanism's broader properties (rotation, anti-downgrade, runtime-key reuse rejection) handle post-issuance compromise.

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
15. Destroy the previous `K_runtime_priv` per the procedure in §3.3 "Secure destruction of `K_runtime_priv`". "Where practical" is replaced by the §3.3 medium-specific guidance: SSD/swap/cloud-snapshot residue must be addressed at this step, not deferred.
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

### Overlap window

When the rotation is intentional (not driven by `K_origin` compromise), the publisher SHOULD operate the old and new origins in parallel for at least one full canary cycle before retiring the old origin. The overlap window allows clients that fetch from the old origin to observe the `migration_pointer` announcement (§06 rc.13), perform the §10 successor verification, and adopt the new origin under the publisher profile while the migration is still announceable.

Minimum overlap window:

* **Intentional address rotation under the same threat profile**: at least one full canary cycle (7 days for high-threat deployments, 14-30 days for standard) plus one additional rotation cadence on the old origin so that any client that fetches the old origin sees both the `migration_pointer` and one canary refresh demonstrating the old origin is still actively maintained.
* **Reactive rotation following `K_origin_priv` suspected compromise**: no overlap. The compromised origin MUST be taken down as soon as the new origin is deployed; an attacker holding the old `K_origin_priv` can serve content on the old address indistinguishably from the legitimate publisher, defeating the purpose of overlap.
* **Voluntary decommissioning of the publisher identity**: see §19.4.

During the overlap window the publisher MUST:

* publish a `migration_pointer` on the old origin's manifest pointing to the new origin (`announced_at` SHOULD be the moment the new origin's manifest is deployed);
* keep the old origin's manifest fresh: each canary refresh on the new origin SHOULD be accompanied by a canary refresh on the old origin, preserving the migration announcement and demonstrating that the publisher is still in control of the old origin (an old origin that stops refreshing while announcing a migration is hard for readers to distinguish from a compromised origin that an attacker has stopped serving);
* announce the impending decommission of the old origin via out-of-band channels (PIP channel, status page, social) at the start of the overlap and again at half-overlap and at decommission.

After the overlap window:

* take down the old origin's service (stop serving manifests, content, and transaction endpoints);
* if the publisher controls the old origin's address registration (DNS for clearnet draft profiles), do not release the address back to general allocation; for Tor v3 the onion address is derived from `K_origin.pub` and ceases to be reachable when the service is taken down;
* leave one final out-of-band notice that the old origin is no longer authoritative; the new origin is the only operative endpoint.

The overlap window is a SHOULD because deployments that have no continuity expectation with prior clients (a publisher migrating origins as part of a broader identity rotation) MAY skip the overlap. The default for any publisher with an existing reader base is to overlap.

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

### Rollback procedure for partial deployment failure

Multi-origin deployments are not protocol-atomic: each origin's manifest is served independently and clients fetch from one origin at a time. If a deployment to N origins succeeds on k origins and fails on N-k, the publisher is in a divergent state where some clients see the new manifest with `issued_at = t_new` and others continue to see the prior manifest with `issued_at = t_old`. Because anti-downgrade (§08:71) is cumulative per `K_publisher.pub`, any client that has observed the new `t_new` will reject subsequent fetches from origins still serving the old `t_old` as a downgrade attempt.

This means the publisher cannot simply "undeploy" the partial rollout by reverting the k successful origins to `t_old`: the clients that have observed `t_new` will reject the reverted manifest as a downgrade. The only protocol-conformant resolution paths are forward.

Rollback procedure:

1. **Pause further rollout.** Stop attempting to deploy to the failing origins until the failure is diagnosed. Continuing to retry while diverged extends the window in which clients see inconsistent state.
2. **Diagnose the per-origin failure.** Common causes: stale `K_runtime_priv` on the failing origin's publishing infrastructure; the failing origin's onion service is down; CDN/proxy in front of the failing origin is serving a stale cached manifest; the failing origin's clock is skewed beyond the §10 300-second tolerance. Fix the root cause before proceeding.
3. **Complete the rollout forward.** Once the failing origins are reachable, deploy the same `t_new` manifest to them. The clients that fetched the old origins continue to see the manifest they have already accepted; once they refresh, they observe `t_new` consistent with what other clients have already accepted. No anti-downgrade conflict arises because all origins now serve the same `t_new` manifest.
4. **If forward completion is impossible** (the failing origins are permanently unreachable, or the new manifest is itself defective and cannot be served), the publisher MUST perform a new canary rotation ceremony (§7) producing a `t_newer > t_new` manifest that the publisher can deploy to all remaining reachable origins. The old `t_new` manifest at the k successful origins remains accepted by the clients that have already seen it; on next refresh those clients observe `t_newer` consistent with what the other origins serve. The "failed" k origins are not rolled back; they are superseded forward.

A genuine downgrade rollback (revert all origins to `t_old`) is not possible under the protocol's anti-downgrade rule for the same `K_publisher.pub`. The only way to recover from a deployment whose outcome the publisher needs to repudiate is forward rotation with a new manifest that the publisher chooses to deploy.

The asymmetry between "deploy forward" (cheap, reversible only by another forward deploy) and "rollback" (impossible at the protocol level) is the operational consequence of the §08:71 anti-downgrade guarantee. Publishers SHOULD treat each multi-origin manifest deploy as a one-way commitment: the deploy succeeds across all origins or the publisher is committed to forward-resolving the divergence.

Pre-deploy mitigations: deploy the new manifest to a *staging origin* first (a separate origin under the same `K_publisher.pub` that is not advertised to readers; deploys to staging exercise the deploy pipeline without committing the publisher's reader-facing origins). Staging deploys SHOULD use a `migration_pointer`-only path so they are visible to test clients but do not commit reader-facing publisher history.

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

### Sizing max_size with wire headroom

`max_size` (07) is a raw UTF-8 byte length: it caps the value's own UTF-8 bytes, not the value's JSON-escaped length on the wire. The two differ when a value contains characters JSON must escape - the double-quote, the backslash, and control characters in U+0000 through U+001F. A double-quote or backslash costs 2 wire bytes; a control character costs 6 (`\u00XX`). A value at its raw `max_size` can therefore be up to roughly 6 times larger on the wire than its `max_size` number.

The Stage 5 submit-budget check (`E_SUBMIT_BUDGET`, 09 "Submit body budget partition") evaluates a manifest's aggregate request-mode `max_size` as a raw-byte envelope bound. It is a necessary condition: it accepts a policy whose values, kept well-formed, fit the budget. It is not sufficient. At submit time the client measures the actual JSON-escaped wire bytes of the retained values, and a `set` whose retained state would overflow the partition is rejected at runtime with `E_STATE_TRANSMIT_BUDGET` (07 "Request-state transmit budget") even when the policy passed the Stage 5 check.

Operators should size `max_size` with headroom relative to the expected value content for any request-mode item that can hold values with escaped characters - control bytes, quotes, backslashes, or non-BMP code points. For values that are known to be escape-free (base64url tokens, slugs, hex digests), the raw `max_size` and the wire contribution coincide and no headroom is needed. For free-form text or binary-bearing values, leave margin so that the worst-case escaped wire form of a maximally-filled value still fits alongside the form fields, or the client will reject the `set` at runtime.

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

### Non-Tor carriers

The §09 transport section in the specification covers only the Tor v3 carrier; "Other carrier profiles, such as I2P, freenet, or signed clearnet HTTPS, are draft profiles and not part of v1 conformance" (§09:5). Operators evaluating a non-Tor carrier should treat the following as the operational floor for any deployment until a published draft profile supersedes this guidance.

**For a clearnet HTTPS draft profile** (a publisher choosing to serve Entangled documents over public HTTPS instead of, or alongside, Tor v3):

* TLS 1.3 only; disable TLS 1.2 and below at the server. TLS 1.2 cipher selection is rich enough that a downgrade attack against a misconfigured peer is plausible; TLS 1.3 simplifies the negotiation surface and forces forward secrecy.
* HSTS enabled with `max-age` >= 1 year, `includeSubDomains`, and `preload`. The HSTS preload list is the closest available approximation to address-pinning on clearnet; without preload, a first-visit reader is exposed to a downgrade-to-HTTP attack the protocol does not address.
* Certificate transparency: publish via a CT-logged CA (the default for any major CA, but verify the operator's chosen CA logs to a published CT log). The CT log is the reader-side defense against certificate substitution that a compromised CA could attempt.
* Pinning: the publisher SHOULD publish the expected certificate fingerprint or public key in their out-of-band channel (the same channel as the PIP). Without pinning, a reader who fetches over clearnet HTTPS has the same trust model as any HTTPS site (trust the CA system), which is weaker than the Tor v3 address-to-key binding the spec is designed around.
* OCSP stapling enabled; OCSP-Must-Staple configured on the certificate if the CA supports it. Without stapling, the reader's client makes an OCSP request that reveals the visit to the OCSP responder, leaking metadata the Tor profile avoids by design.
* No mixed-content: every resource referenced by content documents (images per §03) MUST be served over HTTPS from the same origin. Mixed-content allowance defeats the entire transport hardening posture.

**For an I2P or other anonymity-network draft profile:**

* Same logical posture as Tor v3: rely on the network's address-to-key binding rather than a CA system; the operator's job is to choose a carrier whose address-derivation rule is cryptographically equivalent to Tor v3's onion-address derivation. Document the derivation rule in the publisher's deployment notes.
* Avoid clearnet bridges or exits on the publisher side; those reintroduce the clearnet trust model on a per-connection basis and defeat the carrier's anonymity properties.

**Universal posture for any draft carrier:**

* No HTTP redirects (clearnet HTTPS draft included; the Tor profile already forbids these per §09).
* No HTTP compression.
* No cookies, even as transport-level metadata.
* The deployment cannot rely on browser security features that depend on cookie or storage-partitioning semantics (the Entangled client is not a browser; state is governed by §07 and managed inside the client).
* The publisher's deployment documentation MUST state which draft profile is in use and which non-§09 properties the carrier provides. Readers who choose to connect to a non-Tor deployment do so with knowledge of the substituted trust model.

These rules are operational guidance, not normative spec text. Until a non-Tor carrier becomes part of v1 conformance (no current plan), the publisher is fully responsible for the transport's security posture; the protocol's address-to-key binding (§09 for Tor v3) is the only carrier security property the spec endorses.

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

### Alerting and baselines

Logs without alerting are forensic artifacts, not operational defenses. The §16 compromise window's pre-discovery phase ends when the publisher *notices* something is wrong; "the publisher's monitoring" is the operational floor of the security model, and that monitoring is only as fast as the alerting on top of the logged events.

The operator SHOULD configure alerts on the following indicators, with thresholds calibrated against baseline values observed during normal operation:

**Signature verification failure rate (publisher-side):**

* Baseline: near-zero in steady state. A publisher with a stable `K_runtime` and well-behaved publishing infrastructure produces signatures that verify; any non-trivial rate of signature failures (publisher self-verification after signing, conformance-client probes after deploy) indicates infrastructure drift or active manipulation.
* Alert threshold: any signature verification failure during publisher self-verification (zero tolerance). One failure SHOULD page on-call; the cost of a false positive is investigation, the cost of a true positive is forged content.

**Manifest fetch status codes (publisher-side via clean-client probe):**

* Baseline: 200 OK for `/manifest.json`, `/content_index.json` (when `content_root` is present), and content documents.
* Alert threshold: any non-200 status on `/manifest.json` for more than 60 seconds (probe interval permitting). 404 indicates a deployment failure; 5xx indicates infrastructure failure; 4xx other than 404 indicates middleware misconfiguration. Any of these makes the publisher invisible to clients.

**Canary freshness margin (publisher-side):**

* Baseline: the time between `clock_now` and `canary.next_expected` decreases linearly until the next rotation. The operator's rotation cadence (§7) sets the expected curve.
* Alert threshold: time remaining to `next_expected` falls below the rotation margin documented in §7 "When to rotate" (24 hours for high-risk, 3 days for normal, 7 days for low-risk). The alert fires when the next rotation should be in flight. A canary that reaches `next_expected` without rotation produces the Expired state in clients (§08) and the §10 block-by-default rendering.

**Content-index hash consistency (publisher-side, when `content_root` is present):**

* Baseline: the SHA-256 of the deployed `/content_index.json` equals the `content_root` value in the deployed manifest at all times between ceremonies.
* Alert threshold: any deviation between the deployed index hash and the manifest's `content_root`. A drift here means clients reject the content index with `E_CONTENT_INDEX_HASH_MISMATCH` (§11), making all indexed-path content unrenderable.

**Refresh-cadence drift (publisher-side derived from server logs):**

* Baseline: refresh requests for `/manifest.json` follow a Poisson-like distribution tracking reader population. The aggregate rate is stable across days.
* Alert threshold: a sudden drop of more than 50% over a 24-hour window suggests clients can no longer fetch the manifest (carrier issue, certificate issue for clearnet draft profiles, address-resolution issue). A sudden rise of more than 5x suggests either a content event drove traffic up or an automated probe / scraper has discovered the deployment.

**Unexpected runtime-key reuse rejection (reader-side feedback):**

* If the publisher operates a reader feedback channel: any reader report of an `E_CANARY_RUNTIME_REUSE` rejection (§11 rc.19 N55) at a fresh canary indicates that the publisher's rotation procedure failed silently and the same `K_runtime.pub` was emitted twice. This is a publisher-side correctness bug, not a security event, but it makes the latest manifest unacceptable to clients.

**Freshness-unverified reports (reader-side feedback, weak signal only):**

* If the publisher operates a reader feedback channel: reader reports of clients entering freshness-unverified mode (§10 "Clock reliability and the verified-time reference") are a *weak diagnostic signal*, not an actionable infrastructure event. The condition lives client-side (the reader's device has no reliable clock, distrusts its own clock, or is offline beyond the meaningful lifetime of its last verified manifest), and the publisher cannot remediate it: no infrastructure change on the publisher side gives a reader's clock-less device a reliable current time.
* A *correlated spike* of freshness-unverified reports across the reader base may indicate that the canary interval (§7 "Choosing canary interval") is longer than the typical online cadence of the reader base, so that clients are routinely offline between successive canary issuances and lose freshness reference between them. This is worth a §7 interval review, not an alert action: shortening the canary interval reduces the fraction of the reader base in freshness-unverified mode at steady state. A correlated spike may also be benign: a deployment whose reader base includes many clock-less or intermittently-online devices (embedded readers, archive-only access, deliberately-offline operational environments) is expected to report freshness-unverified at non-trivial rates, and that rate is itself the baseline.
* Do not alert on freshness-unverified reports per se. The signal is qualitative: changes in the rate may indicate carrier or cadence drift; absolute rate is a publisher-deployment characteristic, not an anomaly.

**Origin reachability (publisher-side):**

* Baseline: the publisher's origin is reachable from a clean-client probe positioned independently from the publishing infrastructure.
* Alert threshold: probe failure for more than 5 minutes. Independent positioning matters: a probe co-located with the publishing infrastructure measures the local network, not what readers see.

For each alert, the runbook entry SHOULD include: the underlying log field or query, the threshold expression, the on-call action, and the corresponding §-section in this playbook that the on-call should consult while responding.

Alerts that fire repeatedly without operator response train the on-call to ignore them. The operator SHOULD review false-positive alert rates at least quarterly and tighten thresholds (raising the false-positive cost) only after the alert rule has been demonstrated under load.

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

### The compromise window

A `K_runtime` compromise has a bounded effective window even without explicit in-band revocation. The window has three temporal phases:

1. **Pre-discovery exposure** (`t_compromise` -> `t_discovery`): the attacker has the key. The publisher does not know. Forged content signed during this phase verifies against the current manifest and is accepted as current publication. Duration is unbounded by the protocol; in practice it is bounded by the publisher's monitoring (§14) and by external indicators of compromise.
2. **Pre-rotation exposure** (`t_discovery` -> `t_rotation_deployed`): the publisher knows but has not yet deployed the rotation manifest. Forged content continues to verify until the new manifest is accepted by each client. The publisher controls this phase by responding quickly; the §7 ceremony can complete within hours given prepared offline ceremony state.
3. **Post-rotation residual** (`t_rotation_deployed` -> all clients have observed the new manifest): the new manifest authorizes a new `K_runtime`, but cached clients that have not refreshed may still accept content signed by the old `K_runtime` as current. This phase is bounded by `min_refresh_interval` (§06) plus the client refresh policy (§10), in the worst case by the previously declared `next_expected` for the old canary (capped at 30 days by §08), plus the §10 300-second clock-skew tolerance.

The post-rotation residual is the protocol-level upper bound. For a publisher with a 30-day canary interval, the worst-case residual is approximately 30 days; for a 7-day interval, approximately 7 days. This is the operational rationale for the cadence floors in §7 "Choosing canary interval".

### Steps

1. Stop using the compromised runtime key on the publishing infrastructure immediately. Block the key file from being used to sign anything further.
2. Note the suspected compromise window: `t_compromise` (best estimate), `t_discovery` (now), and the corresponding canary `issued_at` of the manifest under which the compromise occurred. Record these in the operator log.
3. Generate a new `K_runtime` keypair offline or in a trusted environment.
4. Compose a fresh canary with a newer `issued_at`. Set `next_expected` short - for high-threat deployments, 7 days from `issued_at` is appropriate even if the deployment normally uses a longer interval. Returning to the regular cadence happens at the subsequent rotation, not this one.
5. Sign a new manifest with `K_publisher_priv` in the offline ceremony environment.
6. Deploy the new manifest and new runtime key together (atomicity guidance in §7).
7. Re-sign current content with the new runtime key. Content that was previously published and remains correct does not need to be modified, only re-signed under the new key authorization.
8. Review content signed during the suspected compromise window using the §14 monitoring logs. Identify any document that the publisher did not author.
9. Issue the out-of-band announcement (next subsection).
10. Continue at the accelerated cadence for at least one full cycle to demonstrate active control.

### Out-of-band announcement

Because Entangled v1 has no in-band revocation list, the publisher's out-of-band channels - the same channels used for PIP distribution: Mastodon, Signal, mailing list, conference talks, printed material - are the primary mechanism for informing readers about a `K_runtime` compromise.

Announce as soon as the rotation is deployed. The announcement SHOULD include:

* the **publisher PIP** (24-word identifier under `K_publisher`), to authenticate the announcement against the publisher identity readers have already pinned;
* the **compromised `K_runtime.pub`**, in base64url form, so readers can identify exactly which authorization-history entry is suspect;
* the **compromise window**: best-estimate `t_compromise` and `t_discovery`, in UTC;
* the **affected canary**: the `issued_at` of the manifest under which the compromise occurred;
* the **new `K_runtime.pub`**, base64url, so readers can verify their client picks up the rotation;
* a **reader instruction**: at minimum, "Clear cached content from this site in your client for the period [`t_compromise`, `t_discovery`]. Do not trust any document published in that window. Historical content from before that window remains valid; the publisher PIP and identity are unchanged."
* an **incident description**: brief, factual, no marketing or speculation. State what happened, what changed, what the reader should do. Do not promise future safety.

A template:

```text
[ENTANGLED RUNTIME KEY COMPROMISE - site.example]

Publisher PIP: <24 words>
Compromised K_runtime.pub: <base64url>
Compromise window (UTC):
  from: YYYY-MM-DDTHH:MM:SSZ
  to:   YYYY-MM-DDTHH:MM:SSZ
Affected canary issued_at: YYYY-MM-DDTHH:MM:SSZ
Replacement K_runtime.pub: <base64url>
Replacement deployed: YYYY-MM-DDTHH:MM:SSZ

Reader action:
  - Clear cached content from this site in your Entangled client for the
    compromise window above.
  - Do not trust any document published in that window.
  - Historical content from before <t_compromise> remains cryptographically
    valid and is not affected.
  - The publisher identity (PIP) is unchanged.

Incident: <one short factual paragraph>
```

The publisher SHOULD repeat the announcement on each out-of-band channel and pin or highlight it for at least 30 days. Do not delete the announcement after this period; archive it as part of publisher history.

### Channel diversity

The §16 out-of-band announcement procedure (and the §18 publisher-key compromise announcement) is only as resilient as the diversity of the channels used. A publisher who maintains "out-of-band" channels that are all hosted by the same provider, accessed from the same account, or protected by the same authentication factor offers an attacker who has compromised the publisher one extra path to suppress the announcement.

The operator's out-of-band channel set MUST satisfy the following diversity properties:

**Hosting diversity.** Channels MUST be hosted by at least two independent providers. A publisher whose "channels" are a Mastodon account, a Signal channel, and a personal website all hosted under the same cloud account is hosting on one provider; the diversity is illusory. Practical diversity: a Mastodon account on instance A, a personal mailing list hosted by provider B, a verified social account on platform C, a printed handout distributed at venue D. The set spans different administrative domains; an attacker who compromises one does not gain access to the others.

**Authentication diversity.** Each channel MUST be accessible via a credential or factor that is *not* derived from the same root credential as the others. A publisher who uses the same email address for password recovery across all channels is operating one channel as far as compromise resistance is concerned. Practical diversity: hardware tokens for the most sensitive channels (signing-related, PIP-distribution); separate password-manager vaults for less sensitive channels; physical keys for any printed/in-person fallback. The recovery path of each channel SHOULD be documented in the operator log so a recovery operator can trace the authentication chain.

**Geographic and legal diversity.** For high-threat deployments (journalism, publications subject to jurisdictional pressure), at least one channel SHOULD be hosted under a different legal jurisdiction from the others. A publisher and all their out-of-band channels under the same legal jurisdiction are subject to a single compelled-disclosure order; geographic diversity is the operational floor of resistance to legal compulsion.

**Anti-co-location checklist.** Before relying on a channel as part of the out-of-band set, the operator SHOULD verify:

* [ ] not hosted by the same provider as the publishing infrastructure (a channel hosted by the same provider falls under the same compromise as the publisher);
* [ ] not authenticated via the same email/phone/credential as the publishing infrastructure;
* [ ] not accessible from the same hardware that holds `K_publisher_priv` (the channel access credential should not co-locate with the most sensitive key);
* [ ] readers know about the channel from a prior verified context (a channel announced for the first time as part of a compromise notice is not a recoverable signal; readers cannot verify it).

A publisher whose out-of-band channel set fails any of these checks SHOULD treat the deficiency as a v1.0 operational gap rather than relying on the channel set as the rotation-of-trust mechanism. The §16 and §18 announcements depend operationally on the channel set being meaningfully diverse; without that property the protocol's identity-rotation story for publisher-key compromise has no working endpoint.

### Reader guidance

The Entangled protocol cannot retroactively invalidate documents in a reader's authorization history; this is a v1.0 limitation (§00). Readers must take action manually based on the publisher's out-of-band announcement. The announcement should make the reader's situation explicit:

* **What is safe**: any content signed before `t_compromise`. Cryptographic validity is unaffected. The publisher identity is unchanged. The reader does not need to abandon the publisher.
* **What is suspect**: any content signed during [`t_compromise`, `t_discovery`] under the compromised `K_runtime`. The reader's client cannot distinguish publisher-authored from attacker-authored content in this window.
* **What the reader should do**: clear local cache for the affected period; refetch current content under the new manifest; verify the chrome shows the new `K_runtime.pub` matches the announcement. If the client exposes authorization history, the reader can specifically remove or mark suspect the compromised `K_runtime.pub` entry.
* **What the reader should not do**: do not abandon the publisher identity unless the announcement also indicates `K_publisher` compromise - that is a different, much more serious incident (§18) that is signalled differently.

A reader who declines to take action will continue to see suspect-window content as historical content, with the standard historical-content chrome treatment defined in §10. The publisher's out-of-band announcement is the only signal that elevates the reader's risk assessment of that content above the chrome's default.

### Limitation

Entangled v1 has no in-band revocation list for previously authorized runtime keys (§00 v1.0 limitations). The mitigations in this section are operational, not protocol-level: they reduce the practical impact of `K_runtime` compromise but do not close the underlying gap.

Concretely, this means:

* a reader who never sees the out-of-band announcement continues to treat suspect-window content as authentic historical content indefinitely;
* a reader without a maintained PIP-confirmed out-of-band channel to the publisher has no path to receive the announcement;
* the reader's client has no protocol-level signal distinguishing pre-compromise from suspect-window content from the compromised `K_runtime`.

A future protocol version (v1.1 or v2) is expected to introduce an in-band revocation mechanism that bounds the post-discovery window without requiring publisher-controlled out-of-band channels. Until then, the operator's posture should treat shorter canary intervals (§7 "Choosing canary interval") and prepared offline ceremony state (§4 setup) as the primary mitigations: they shrink the exposure window enough that the out-of-band announcement remains the secondary signal rather than the primary defense, and they bound the worst-case residual to a duration that matches the deployment's threat profile.

## 17. Origin key compromise response

Use this procedure if `K_origin_priv` may be compromised.

### Steps

1. Generate a new origin key.
2. Deploy a new carrier endpoint.
3. Generate a fresh runtime key unless intentionally preserving the existing one.
4. Sign a new manifest with `K_publisher_priv` authorizing the new origin.
5. Deploy the new manifest to the new origin.
6. Announce the new address through out-of-band channels together with the same PIP.
7. Retire the old origin per the §8 "Overlap window" rules: for reactive origin-compromise rotation (this section's case), no overlap - take the old origin down as soon as the new origin is verified, because an attacker holding the old `K_origin_priv` can continue serving the old address indistinguishably from the legitimate publisher.
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
6. Announce the compromise and new PIP through out-of-band channels that users already trust. The channel set MUST satisfy the diversity properties in §16 "Channel diversity": if every channel in the publisher's set is hosted by the same provider, accessed via the same root credential, or sited in the same jurisdiction, an attacker who has compromised `K_publisher` likely has access to suppress the announcement on most or all channels. Channel diversity is the operational precondition for §18 working at all.
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

## 19.4 Voluntary decommissioning of a publisher identity

A publisher who wishes to retire a publisher identity intentionally (the publication is ending, the publisher is handing the site to a successor, the publisher is consolidating multiple identities into one) SHOULD perform a structured decommissioning rather than letting the identity expire silently. Silent expiration leaves readers with an Expired canary indefinitely and is operationally indistinguishable from a publisher unable or unwilling to maintain the canary (i.e., compromise).

### When to use

* the publication is ending and the publisher wants to make the closure explicit;
* the publisher is migrating to a different identity (e.g., institutional rebranding) and wants readers to follow;
* the publisher is consolidating multiple identities under a single `K_publisher` and wants the deprecated identities to be marked closed;
* the publisher is handing off to a successor publisher with a different `K_publisher`.

### When not to use

* the publisher's identity has been compromised - use §18 instead, never §19.4;
* the publisher is uncertain whether they will resume publishing - use a longer canary interval (within §08 bounds) instead of decommissioning;
* `K_publisher_priv` has been lost - decommissioning requires signing the final manifest, which §19.3 forbids; the publisher is in §19.3, not §19.4.

### Steps

1. **Decide the successor relationship.** Three cases:
   - **No successor.** The publication is ending; readers should not look elsewhere. The decommissioning is informational only.
   - **Same publisher, new identity.** The publisher is creating a new `K_publisher` and inviting readers to migrate. The new PIP MUST be distributed via the same out-of-band channels as the original PIP (§16 "Channel diversity"); the protocol cannot carry the identity migration in-band because the two identities have different `K_publisher.pub`.
   - **Different publisher (handoff).** A different organization is taking over the site. The successor's PIP MUST be distributed via the original publisher's out-of-band channels; readers verify the handoff through the diversity of channels, since in-band cryptographic continuity between two `K_publisher` identities does not exist in v1.
2. **Perform a final canary ceremony (§7).** This is the last manifest the publisher will sign under the retiring identity. The canary `statement` SHOULD make the decommissioning explicit (e.g., "This publication is ending. The final canary is `<issued_at>`. After `<next_expected>` no further canaries will be issued under this `K_publisher`."). For a successor case, include the successor's PIP or address in the statement; for no-successor, state the closure plainly.
3. **Publish a final content document** describing the decommissioning in detail: dates, successor (if any), what readers should expect, where archived material will continue to be served (if at all). Sign with the current `K_runtime` under the final manifest.
4. **Out-of-band announcement.** Use the channels per §16 "Channel diversity". The announcement SHOULD mirror the final content document's information and SHOULD repeat at least three times across the final canary cycle.
5. **Let the final canary cycle complete.** During the cycle the publisher continues to serve the final manifest and content; readers fetching the site see the canary approaching `next_expected` with the final-cycle statement. The publisher SHOULD NOT rotate again.
6. **At `next_expected`**, allow the canary to expire. The site enters the §08 Expired state and, per §10 rc.19 N51, clients render the block notice with the final-cycle statement visible in chrome. The publisher's intent (decommissioning, not compromise) is conveyed by the in-band `canary.statement` plus the corroborating out-of-band announcement.
7. **Take down the publishing infrastructure** at the operator's convenience after canary expiration. The expired manifest may continue to be served indefinitely for archive purposes, or the publisher may take the origin offline. Document the choice in the final out-of-band announcement.
8. **Destroy `K_publisher_priv` and the corresponding backups.** After the decommissioning is announced and the final canary is signed, retaining `K_publisher_priv` only preserves the risk of post-decommission compromise. Destruction: encrypt the backups with a fresh ephemeral key and discard the key; or physically destroy the backup media. Record the destruction in the operator log.
9. **Preserve the public material** (manifests, content documents, PIP) for the archive horizon the publisher considers appropriate. The public material remains cryptographically valid under the retired `K_publisher.pub` indefinitely.

### What this is not

The decommissioning is not an in-band signal that readers' clients understand structurally; v1 has no `decommissioned` manifest field. Readers perceive a publisher who is "winding down" through (a) the canary `statement` text, (b) the out-of-band announcement, and (c) the eventual canary expiration without rotation. The reader's client treats the expired state per §08 / §10 like any other expired canary; the *meaning* of the expiration (intentional vs failed-to-rotate) is carried by the human-readable announcement, not by the protocol.

A future protocol version may add an explicit `decommissioned` field to the manifest to make this distinction structural; v1 leaves it to operator practice.

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
