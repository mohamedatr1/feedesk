# FeeDesk M6 — Credential and Custody Handover

**Document ID:** M6-CRE-01  
**Version:** 0.1 (draft for custody acceptance)  
**Date:** 4 November 2026  
**Status:** **Draft. No credential has been transferred, rotated, or verified under this document.**  
**Audience:** School director/data owner, technical owner, provider/ops, security.  
**Related:** `handover-pack.md`, `support-model.md`, `docs/runbooks/key-rotation.md`, `docs/runbooks/backup-restore.md`.

> **This document contains no secret values, and must never contain any.**
>
> Do not write a password, API key, session cookie, database URL, Fernet key, age private key, TLS private key, or recovery code in this file, a ticket, chat, email, screenshot, commit, or shell history. Record only the credential **name**, its custodian, its storage class, and evidence that custody was verified.
>
> Rotation and break-glass procedures below are **templates**. They have not been exercised in production. H6 database-role separation is not applied. Vault-key re-encryption is not implemented. Treat every production step as blocked until the named evidence exists.

---

## 1. Purpose / الغرض

Establish who holds each FeeDesk credential, where it is stored, how it is rotated or revoked, who may use break-glass access, and what evidence proves custody. The goal is continuity without spreading secrets.

**Arabic summary / ملخص عربي**

تحدد هذه الوثيقة مسؤولية حفظ بيانات الدخول والمفاتيح في FeeDesk، ومكان تخزينها، وآلية تدويرها أو إلغائها، وقواعد الوصول الطارئ. لا تحتوي الوثيقة على أي قيم سرية، ويُمنع نسخ كلمات المرور أو المفاتيح في المحادثات أو البريد أو التذاكر. جميع الإجراءات الإنتاجية **محجوبة** حتى تنفذ الأدلة المطلوبة.

---

## 2. Non-negotiable rules

1. **No secret values in this document or any shared record.** Only names, custody roles, storage class, dates, and evidence references.
2. **Need-to-know.** A credential is shared only with the named custodian and deputy, or the person executing an approved rotation.
3. **No chat/email/SMS.** Do not paste secrets into WhatsApp, Telegram, Slack, Teams, SMS, email, tickets, or AI prompts.
4. **No screenshots of secret screens.** Redact or avoid capturing env files, provider key pages, and database URLs.
5. **No shell history.** Use `read -r -s`, a secret manager, or an interactive prompt; never put a secret directly in a command line.
6. **No secrets in Compose output.** `docker compose config` can render values; redact before sharing.
7. **One change at a time.** Do not rotate a key and retry a send in the same step.
8. **Backup before destructive rotation.** A verified database/credential backup is a precondition for DB and vault changes.
9. **Revoke, then destroy.** Confirm the new credential works before destroying the old one, except during an active compromise where containment wins.
10. **Record evidence, not values.** Record credential name, version/date, actor, system, and confirmation; never the secret itself.

---

## 3. Credential inventory and custody checklist

“Storage class” describes the approved location type, not the value. No location in this table is asserted to exist yet. Where a “secret manager” is listed, none is deployed in the current stack; it is a target storage class.

| ID | Credential | Purpose | Storage class (proposed) | Custodian | Deputy | Rotation trigger | Revocation / effect | Evidence required |
|---|---|---|---|---|---|---|---|---|
| CR-01 | `SESSION_SECRET` | Signs/derives server-side session material | Host env file `/etc/feedesk/feedesk.env` (0600) or secret manager | Technical owner | Security | Suspected leak, staff departure, scheduled cadence | Recreate API/worker; all sessions invalidated; users re-login | New value length checked; readiness/login test; old value destroyed; time recorded |
| CR-02 | Database runtime credential (current `feedesk`; target `feedesk_app`) | API/worker DB access | Host env / Compose secret (0600) | Technical owner | DBA/security | Leak, role change, scheduled cadence | Recreate API/worker; DB access fails until updated | `current_user` check; readiness; no owner rights after H6 |
| CR-03 | Database owner/migration credential (target `feedesk_owner`) | Migrations, seed, schema ownership | Separate secret, job-local only | DBA/technical owner | Security | Migration window, leak, role change | One-shot migrate job only; never in API/worker | Owner-only in migrate job; `alembic current`; no runtime exposure |
| CR-04 | Database backup credential (target `feedesk_backup`) | Read-only dumps/checks | Backup job secret | DBA/backup custodian | Technical owner | Leak, role change, cadence | Backup job fails until updated | `pg_dump` succeeds; update/delete/truncate denied |
| CR-05 | Database break-glass credential (`feedesk` superuser) | Emergency recovery only | Offline sealed escrow, not on app host | Security | School director/technical owner | After every use; annual review | Disable/rotate after incident; never routine | Sealed custody record; use log; post-use rotation |
| CR-06 | `RASEL_API_KEY` | Provider API authentication | Encrypted DB vault preferred; env fallback | Provider/ops | Technical owner | Leak, provider rotation, staff departure, scheduled cadence | Revoke in provider console; clear vault ciphertext; worker releases claimed job | Provider revocation confirmation; no key in logs; worker safe state |
| CR-07 | `PROVIDER_CREDENTIAL_KEY` (Fernet) | Encrypts/decrypts provider credential vault | Host env/secret manager; **not** with the ciphertext | Security | Technical owner | Suspected leak, crypto review, custodian change | Loss makes stored provider credentials unreadable; planned rotation needs re-encryption, loss requires re-entering the provider key | Vault decrypt test; backup; **re-encryption procedure required before planned rotation** |
| CR-08 | `BACKUP_AGE_RECIPIENT` (public key) | Encrypt new backups | Host config, non-secret | Technical owner | Backup custodian | Key rotation, custodian change | New backups use new recipient; old backups need old private key | New backup decrypts with new private key |
| CR-09 | Backup age **private** key | Decrypt backups for restore | Offline escrow, separate from app host | Backup custodian | School director/security | Suspected leak, custodian change, crypto review | Old backups may become unreadable if lost; retain old key until expiry | Custodian can decrypt a test artifact without the app host |
| CR-10 | TLS certificate / ACME state | HTTPS for `APP_DOMAIN` | Caddy volume + DNS/ACME account | Technical owner | School IT | Compromise, domain change, renewal failure | Certificate reissued; HTTPS fails until DNS/ACME fixed | Valid chain, HTTP→HTTPS redirect, renewal test |
| CR-11 | DNS/domain registrar account | Control of `APP_DOMAIN` | Registrar account with MFA | School admin | Technical owner | Staff change, suspected takeover | DNS change can redirect/disable the service | Registrar MFA; recovery codes offline; change log |
| CR-12 | Monitoring accounts (Prometheus/Alertmanager/Loki/uptime) | Alerts, dashboards, logs | Hosted/self-hosted account with MFA | Technical owner | Security | Staff change, leak, vendor change | Alerts stop or logs inaccessible | Alert delivery test; no PII in labels; access list |
| CR-13 | Alert mailbox / on-call distribution | Receive alerts and escalations | School-controlled mailbox/distribution list | School admin | Technical owner | Staff change, routing change | Alerts may go unseen | Test alert delivered and resolved |
| CR-14 | `SEED_ADMIN_PASSWORD` | One-time first-login password | Deployment secret; one-time use | Technical owner | School admin | Immediately after first login | Seed only affects a new database; existing admin uses reset flow | First login forces change; seed password no longer works |
| CR-15 | SSH/host access keys | Host administration | Per-admin key pair; no shared key | Technical owner | Security | Staff change, lost device, suspected compromise | Remove key from `authorized_keys`; revoke access | Key-only SSH; root disabled; access list reviewed |
| CR-16 | Env/secret files (`/etc/feedesk/feedesk.env`, `backup.env`) | Runtime and backup configuration | Host filesystem 0600, service account | Technical owner | Security | Any secret rotation, host rebuild | Service fails to start until restored | Mode/owner check; no `.env.local` in production |
| CR-17 | Provider console account | Sender, balance, reports, tickets | Provider portal with MFA | Provider/ops | School admin | Staff change, leak, provider policy | Account access lost; sending may stop | MFA; named users; recovery path; audit log |

### 3.1 Minimum custody set before any handover

- [ ] CR-01, CR-02, CR-06, CR-07, CR-08, CR-09, CR-10, CR-11, CR-12, CR-13, CR-15, CR-16, CR-17 have a named custodian **and** deputy.
- [ ] CR-05 break-glass has a sealed custody record and an offline location.
- [ ] No credential is held by only one person without a deputy.
- [ ] No credential is stored in the repository, a chat, a ticket, or an unencrypted personal device.
- [ ] The custody ledger (§4) is complete and stored separately from the secrets.

---

## 4. Custody ledger template

Store this ledger in the school's approved record system, **not** with the secret values. One row per credential.

| Field | Entry |
|---|---|
| Credential ID / name |  |
| Purpose |  |
| Custodian (name/role) |  |
| Deputy (name/role) |  |
| Storage class / location reference |  |
| Access list (roles, not values) |  |
| Created / last rotated (date) |  |
| Next rotation due |  |
| Rotation evidence reference |  |
| Revocation/break-glass evidence reference |  |
| School approval (if required) |  |
| Notes / exceptions |  |

**Do not record:** the secret, a hash of the secret used as a password, the full database URL, recovery codes, or private-key material.

---

## 5. Handover ceremony

A credential handover is a controlled event, not a file copy.

### 5.1 Preconditions

- [ ] Handover acceptance checklist in `handover-pack.md` §12 is in progress.
- [ ] Named custodian and deputy have been identified and have accepted the role in writing.
- [ ] The school has approved the storage class and access list.
- [ ] The receiving person's identity is verified (in person or via a pre-agreed video call with a known contact).
- [ ] An approved transfer channel exists (password manager share with expiry, sealed envelope, or in-person entry). Chat/email is not approved.
- [ ] A rollback/revocation path exists if the transfer fails.
- [ ] The ledger row is ready; no values are written into it.

### 5.2 Transfer steps

1. **Verify identity and authority.** Confirm the receiver's name, role, and approval. Record the verification method.
2. **Open the approved channel.** Use a one-time share, in-person entry, or sealed envelope. Do not send the value in the meeting invite or follow-up email.
3. **Transfer one credential at a time.** Do not bundle the session secret, DB password, provider key, and backup key in one message.
4. **Install/verify.** The receiver confirms the credential works in the intended system (login, readiness, backup dry run, provider read-only check) without printing it.
5. **Record evidence.** Credential name, date/time, receiver, verifier, system, result. No value.
6. **Seal/destroy temporary copies.** Delete the transfer artifact, clear clipboard/history, and confirm the sender no longer holds an unnecessary copy.
7. **Update the ledger.** Custodian, deputy, last handover, next review.
8. **Rotate if the channel was imperfect.** If there is any doubt about exposure, rotate before closing the handover.

### 5.3 Dual control

Use two people for:

- break-glass credential access;
- backup private-key use;
- provider key rotation during an incident;
- database owner credential changes;
- any restore over live data.

One person executes; the second reviews and records. Neither shares the value with the other beyond the approved channel.

---

## 6. Rotation and revocation

> Follow `docs/runbooks/key-rotation.md` for commands. The notes below add custody controls and known gaps. No rotation has been exercised in production.

### 6.1 Session secret (CR-01)

1. Generate a new value of at least 32 random characters (URL-safe; no whitespace).
2. Update the env file (0600) or secret manager.
3. Recreate API and worker.
4. Confirm `/health/ready` and a fresh login.
5. Confirm all existing sessions are invalid.
6. Destroy the old value after verification.
7. Record time, reason, and operator.

**Effect:** every user is logged out. Do not rotate during an active campaign unless the secret is the cause.

### 6.2 Database credentials (CR-02/03/04/05)

Current state: Compose runs the app as `feedesk`, the database owner/superuser. H6 target roles (`feedesk_owner`, `feedesk_app`, `feedesk_backup`) are **not applied**.

1. Take a verified database + uploads backup.
2. Generate a URL-safe password, or percent-encode it for `DATABASE_URL`.
3. Change the role inside PostgreSQL using an approved interactive session.
4. Update the env/secret for the affected process only.
5. Recreate API/worker (or the one-shot migrate/backup job).
6. Verify readiness, `current_user`, and the expected privileges.
7. Keep the old value only until confirmation, then destroy it.
8. After H6, rotate each role separately and update the runbooks that still use `-U feedesk`.

**Do not:** recreate the `db` container to apply `POSTGRES_PASSWORD`; it is used only at initialization. Do not use the owner/break-glass credential for routine API/worker operation after H6.

### 6.3 Provider API key (CR-06)

1. Generate a new key in the provider console; confirm the old key's revocation timing.
2. Prefer the encrypted vault: rotate through the provider settings UI, which increments `key_version` and never returns the plaintext.
3. If using the env fallback (only when no DB credential row exists), update `RASEL_API_KEY` in the env file and recreate API/worker. A revoked DB row does not silently fall back to a stale env key.
4. Confirm worker startup shows the expected provider and **no key value**.
5. Run only a read-only account/sender check approved for the environment. Do not send.
6. Revoke the old key after the new one is confirmed.
7. If a leak is suspected, check provider logs for unauthorised sends and follow the security incident path.

**Effect:** provider calls fail until the new key is active. Messaging must remain disabled/fake during the change unless a G4-approved maintenance window exists.

### 6.4 Provider credential vault key (CR-07)

**This is the least-exercised credential.** The Fernet key encrypts stored provider API keys. Rotating it requires decrypting and re-encrypting every stored credential; there is **no re-encryption tool or UI** in the current implementation.

1. Treat vault-key rotation as an engineering change, not a routine ops task.
2. Take a verified database backup.
3. Confirm every stored provider credential can be decrypted with the current key.
4. Design and test a re-encryption procedure on a scratch database.
5. Rotate the key only with a rollback path and a second reviewer.
6. Verify the vault status endpoint reports `configured=true` and a decrypt test succeeds.
7. Destroy the old key only after all ciphertext is re-encrypted and verified.

**Until a tested re-encryption procedure exists, vault-key rotation is blocked.** Losing the key makes stored provider credentials unreadable; the fallback is to revoke/recreate the provider key and re-enter it.

### 6.5 Backup encryption keys (CR-08/CR-09)

- The public `age` recipient may live on the host; the private key must be offline in escrow.
- Rotating the recipient affects **new** backups only.
- Keep the old private key until every backup encrypted with it has expired.
- Never store the private key on the application server.
- The custodian must prove they can decrypt a backup without the app host.
- Test decryption on a scratch copy; never overwrite a live database.

**Effect of loss:** old backups become unreadable. This is a continuity risk, not just a privacy one.

### 6.6 TLS/domain (CR-10/CR-11)

- Caddy obtains and renews certificates automatically; do not hand-edit certificate files.
- Keep the registrar account under school control with MFA and offline recovery codes.
- Changing `APP_DOMAIN` requires DNS, Caddy, `APP_BASE_URL`, `API_BASE_URL`, and cookie behaviour review.
- Confirm HTTP→HTTPS redirect, HSTS, and certificate chain after any change.
- Monitor expiry at <14 days.

### 6.7 Monitoring accounts (CR-12/CR-13)

- Use named accounts, MFA, and least privilege.
- Alert labels/annotations must not contain guardian names, phones, or message text.
- Test delivery and resolution after any routing change.
- Remove departed staff promptly; review access quarterly.

### 6.8 Seed administrator (CR-14)

- Used only when the seed creates a new administrator.
- First login forces a password change.
- Changing `SEED_ADMIN_PASSWORD` later does nothing for an existing user; use the admin reset flow.
- Do not keep the seed password as a shared “break glass” login.

### 6.9 SSH/host (CR-15)

- Key-only SSH; root login disabled; firewall restricts port 22 to admin IPs.
- One key per admin; no shared key.
- Remove a key immediately on staff departure or device loss.
- Review `authorized_keys` and sudo/docker group membership quarterly.
- Host access is powerful because the `feedesk` user can reach the Docker socket; treat it like an admin credential.

---

## 7. Break-glass rules

Break-glass exists for emergencies where normal access is unavailable: host loss, database lockout, audit-trigger/role failure, or an approved restore. It is not a convenience path.

### 7.1 Authorised uses

- Restore the service after a host or database failure.
- Recover from a lost/misconfigured owner credential.
- Repair role/ownership after a failed H6 change.
- Execute an approved destructive restore when normal tooling is unavailable.

### 7.2 Requirements

1. **Incident ID** and a short written reason.
2. **Approval** from the school data owner **and** security (or the technical owner if security is unavailable), recorded before use where possible. If immediate action is required to stop harm, act first and document within 1 hour.
3. **Two people** where practical: one executes, one witnesses/records.
4. **Time-boxed** access; revoke/disable when the task ends.
5. **Log** the commands and outcome in the incident record; no secrets.
6. **Rotate** the break-glass credential after use, or explain in writing why not.
7. **Post-incident review** within 5 business days.

### 7.3 Prohibited

- Routine migrations, backups, or troubleshooting.
- Sharing the credential with the school office or provider.
- Using it to bypass an application permission or approval.
- Leaving a session open after the incident.
- Using it to edit audit rows; the append-only trigger blocks normal updates/deletes, and disabling it would destroy audit integrity.

### 7.4 Break-glass record template

```text
Incident ID:
Reason:
Systems affected:
Approver 1 / time:
Approver 2 / time:
Operator / witness:
Start / end time:
Commands (redacted):
Outcome:
Credential rotated? (Y/N, evidence):
Follow-up owner/date:
```

---

## 8. Compromise playbook

Use when a secret is suspected or confirmed exposed.

### 8.1 Contain

1. Stop the worker and set `MESSAGING_KILL_SWITCH=true`, `MESSAGING_ENABLED=false` if sending could be affected.
2. Revoke the exposed credential at the source (provider console, DB role, session store, registrar, monitoring account).
3. Disable affected accounts/sessions; preserve logs.
4. Notify security and the school data owner with an incident ID.
5. Do not delete evidence, rotate unrelated secrets, or send a “test” message.

### 8.2 Assess

- Which credential, where was it exposed, for how long, and who could access it?
- What could it authenticate to (app, DB, provider, backup, DNS, host, monitoring)?
- Were there unauthorised logins, sends, role changes, downloads, or config changes?
- Does the exposure include guardian PII? If yes, treat as a privacy incident.
- Is a provider/regulator/school notification required under the signed policy?

### 8.3 Eradicate and recover

- Rotate the exposed credential and any credential reachable with it.
- Verify the old credential is revoked.
- Restore safe messaging state (fake/disabled/kill switch on).
- Re-run smoke checks; confirm audit integrity.
- Monitor for recurrence.

### 8.4 Close

- Written incident report with timeline, impact, root cause, and actions.
- Credential ledger updated.
- School communication in plain language, no PII.
- Follow-up date and owner.

---

## 9. “Do not paste into chat/email” constraints

### 9.1 Never send in chat, email, SMS, or a ticket

- Passwords, API keys, session cookies, CSRF tokens.
- `DATABASE_URL` or any connection string with a password.
- Fernet keys, age private keys, TLS private keys, recovery codes.
- Full env files or `docker compose config` output.
- Guardian names, phone numbers, message bodies, or fee balances.
- Screenshots of provider key pages, env files, or database rows with PII.

### 9.2 Approved alternatives

| Need | Approved method |
|---|---|
| Share a secret with a custodian | Password-manager one-time share with expiry, sealed envelope, or in-person entry |
| Verify a secret without revealing it | Check readiness/login/worker startup; compare a non-secret fingerprint/version |
| Record rotation | Ledger entry: name, date, actor, version, evidence reference |
| Send config for review | Redacted excerpt with secret placeholders; confirm no values |
| Discuss an incident | Incident ID + counts + internal IDs; no PII |

### 9.3 If a secret is pasted accidentally

1. Treat it as compromised; do not delete the message before capturing evidence (where policy allows).
2. Revoke/rotate immediately.
3. Notify security and the custodian.
4. Record the channel, time, and scope in the incident.
5. Review access logs for misuse.
6. Do not repeat the value in the incident report.

---

## 10. Handover acceptance checklist

- [ ] Inventory (§3) reviewed; every credential has a named custodian and deputy.
- [ ] Custody ledger (§4) created in the approved record system, separate from secrets.
- [ ] Storage classes approved; no secret in the repository, chat, ticket, or this document.
- [ ] Transfer channel approved; chat/email explicitly prohibited.
- [ ] Identity verification method agreed.
- [ ] CR-01 session secret transferred/verified; sessions invalidated only when intended.
- [ ] CR-02/03/04/05 database credentials custody agreed; H6 status recorded as **not applied**.
- [ ] CR-06 provider key custody/rotation agreed; vault precedence understood.
- [ ] CR-07 vault key custody agreed; re-encryption gap recorded as **blocked**.
- [ ] CR-08/CR-09 backup keys escrowed; decrypt path tested or marked **blocked**.
- [ ] CR-10/CR-11 TLS/domain control and renewal ownership agreed.
- [ ] CR-12/CR-13 monitoring accounts and alert mailbox ownership agreed.
- [ ] CR-14 seed password one-time use confirmed; first login changed.
- [ ] CR-15 SSH/host access list reviewed; root disabled; key-only.
- [ ] CR-16 env/secret file mode/owner checked; no `.env.local` in production.
- [ ] CR-17 provider console MFA and named users confirmed.
- [ ] Break-glass rules read; custodian/deputy named; record template ready.
- [ ] Compromise playbook read; incident contacts known.
- [ ] Rotation schedule agreed (even if dates are placeholders).
- [ ] All production-dependent checks marked **blocked** until evidence exists.

**Acceptance decision:**

Acceptance here means the **custody plan and ledger** are accepted for execution; it is not proof that any credential was transferred, rotated, or verified. Record the separate transfer evidence in §5.

| Decision | Meaning | Name | Signature | Date |
|---|---|---|---|---|
| Accepted | Custody transferred with listed exceptions |  |  |  |
| Accepted with conditions | Custody transferred; conditions tracked |  |  |  |
| Not accepted | Custody incomplete; reasons recorded |  |  |  |

**Conditions / exceptions:**

```text
1.
2.
3.
```

---

## 11. Rotation schedule template

| Credential | Proposed cadence | Last rotated | Next due | Owner | Evidence |
|---|---|---|---|---|---|
| CR-01 session secret | Every 90 days / on suspicion |  |  | Technical owner |  |
| CR-02 app DB credential | Every 90 days / on suspicion |  |  | Technical owner |  |
| CR-03 owner DB credential | Per migration window / on suspicion |  |  | DBA |  |
| CR-04 backup DB credential | Every 180 days |  |  | DBA |  |
| CR-05 break-glass | After every use / annual |  |  | Security |  |
| CR-06 provider API key | Every 90 days / on suspicion |  |  | Provider/ops |  |
| CR-07 vault key | Only with tested re-encryption (blocked) |  |  | Security |  |
| CR-08/09 backup keys | Annual / on custodian change |  |  | Backup custodian |  |
| CR-10 TLS | Automatic renewal; verify monthly |  |  | Technical owner |  |
| CR-11 DNS/registrar | Annual access review |  |  | School admin |  |
| CR-12/13 monitoring | Quarterly access review |  |  | Technical owner |  |
| CR-14 seed | One-time only |  |  | Technical owner |  |
| CR-15 SSH keys | Annual / on staff change |  |  | Technical owner |  |
| CR-17 provider console | Per provider policy / staff change |  |  | Provider/ops |  |

Cadence values are proposals; the school may shorten them.

---

## 12. Sign-off

| Role | Name | Signature | Date |
|---|---|---|---|
| School director / authorised representative |  |  |  |
| School data owner |  |  |  |
| Technical owner |  |  |  |
| Provider/operations lead |  |  |  |
| Security reviewer |  |  |  |

---

## Change log

| Version | Date | Change | Author |
|---|---|---|---|
| 0.1 | 4 Nov 2026 | Initial M6 credential/custody draft; no secrets; rotation gaps marked blocked | Documentation pass |
