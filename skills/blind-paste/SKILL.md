---
name: blind-paste
description: Use when an API key, token, password, OAuth/device code, or other local credential is required and must not enter the model transcript, command arguments, or tool output. Supports T3 Code's native request_secret card (merging the one-use delivery file into mode-0600 env files), macOS native hidden dialogs, and ephemeral stdin handoff to a trusted CLI. Proactively use it when a required env value is missing, a native login needs a one-time code, or the user says "blind paste", "paste box", "secret card", or "don't put my key in chat".
---

# Blind Paste

Collect single-line credentials without exposing their values to the model.
In T3 Code, use the native `request_secret` card (`delivery: "file"`) and merge
the returned one-use file straight into the authoritative ignored env file via
`scripts/paste_env.py --from-file`. Outside T3 Code on macOS, `scripts/paste_env.py --key`
collects the value through a native hidden macOS dialog. For trusted CLIs
waiting on a one-time code, hand the value to stdin without storing it.

## Non-negotiable rules

- Never ask the user to paste a secret into chat.
- Never put a secret in a command argument, shell history, environment-bearing
  command string, stdout, stderr, or validation output.
- Never `cat`, `echo`, interpolate, or `source` a secret file. Treat env files as
  data, not executable shell.
- Never write a tracked file. Never copy secrets into disposable worktrees or
  add secret files to `.worktreeinclude`.
- If a secret appears in chat, tool output, a log, or Git history, treat it as
  exposed: stop using it, recommend revoke/rotate, and collect the replacement
  through this flow.
- Never persist an OAuth authorization code, device code, one-time password, or
  other ephemeral proof. The stdin helper must own the trusted child process,
  suppress its post-submit output, and pass the value only after a deterministic
  prompt is observed.
- A stored-login/status response is metadata, not proof that a credential can
  make a real request. Use the smallest safe authenticated probe before asking
  the user to sign in again.

## Choose the owning credential path

1. Reuse a provider-native session first. Run the smallest real authenticated
   request that proves the needed capability. A separate status or identity
   command is useful context but cannot replace this probe.
2. If the probe fails specifically at authentication, use the provider's
   read-only doctor/status command, then its native login or refresh flow. Let
   the provider own OAuth tokens in its OS credential store; do not copy those
   tokens into a project env file.
3. Use the persistent env path below for a long-lived local API key or secret
   that the repository's checked loader owns.
4. Use the ephemeral stdin path below only for a trusted CLI that is already
   waiting for a one-time value. Do not use it for arbitrary commands.
5. Production, CI, shared-team, and unattended automation credentials belong in
   the platform/provider secret store, workload identity, or a provider-supported
   key helper. A local env file is only a development fallback.

## Persistent env secret

1. Resolve the one authoritative target before prompting:
   - Follow the repository's checked env command or documented loader when one
     exists. In linked worktrees, use its canonical shared file; a worktree-local
     file is only an intentional override.
   - Otherwise use
     `~/.codex/secrets/<service>/<project-or-account>.env` (or the equivalent
     `CODEX_HOME` location when configured).
   - Production, CI, shared-team, and high-value long-lived credentials belong
     in the platform/provider secret store or a password-manager integration,
     not a local env file.
2. Check readiness by filename or a redacted status command only. Do not inspect
   or print file contents.
3. Collect and merge the missing value(s):
   - **In T3 Code:** collect through T3 Code's native `request_secret` card with
     `delivery: "file"` (pass `url` when a verified key-creation console is
     known, and use `fields` when collecting multiple keys in one card). Call
     the `request_secret` MCP tool directly when available; in an ACP harness
     where `request_secret` is absent from the tool list and `T3_ACP_MCP_NODE`
     is set, invoke it via `acp-mcp-call` (lift any shell virtual-memory cap
     first if Electron exits 133):

     ```bash
     ELECTRON_RUN_AS_NODE=1 "$T3_ACP_MCP_NODE" ${T3_ACP_MCP_ENTRYPOINT:+"$T3_ACP_MCP_ENTRYPOINT"} \
       acp-mcp-call request_secret '{"delivery":"file","label":"Service API Key","reason":"Needed for ..."}'
     ```

     Then merge the returned one-use file(s) into the target with
     `scripts/paste_env.py --from-file` (one `--from-file KEY=PATH` per key):

     ```bash
     python3 <skill-dir>/scripts/paste_env.py \
       --target /absolute/path/to/ignored.env \
       --from-file SERVICE_API_KEY=/path/returned/by/request_secret
     ```

     Do not launch the macOS JXA dialog (`--key`) inside T3 Code.
   - **Outside T3 Code on macOS:** run `scripts/paste_env.py --key` (one `--key`
     per variable) to open a native hidden macOS dialog with clipboard paste and
     a masked text field, or use a local password manager:

     ```bash
     python3 <skill-dir>/scripts/paste_env.py \
       --target /absolute/path/to/ignored.env \
       --key SERVICE_API_KEY
     ```

   - **Outside T3 Code on non-macOS:** do not fall back to chat or a visible
     terminal prompt; ask the user to populate the ignored env file directly via
     a password manager or local secret store.

   The helper enforces the untracked/worktree/dotenv guards, merges atomically
   with mode `0600`, deletes any one-use delivery file(s), and prints only
   `ready`, `saved`, `cancelled`, or a non-secret error code. Never `cat` or
   inspect a delivery file yourself.
4. Use elevated write modes only with matching user authorization:
   - Use `--replace` only when the user explicitly asks to rotate or replace an
     existing credential. Without it, populated values are preserved.
   - The helper refuses targets inside linked worktrees by default. Use
     `--allow-worktree-local` only when the user explicitly authorizes an
     independent checkout-local override; never use it to work around a missing
     canonical shared file.
5. Validate through the repository's redacted preflight or a cheap authenticated
   identity/status request whose credential is injected by a trusted child
   process. Report only set/missing status, identity, or HTTP result.

## Ephemeral one-time code

Prerequisite: macOS (uses the native hidden macOS dialog for masked input) and a
POSIX PTY.

1. Confirm that the command is trusted, the value is single-use, and the exact
   prompt emitted immediately before the command reads it is known.
2. Tell the user to complete the provider's normal browser flow, copy the
   one-time value, and click **Paste from Clipboard** when the native dialog
   appears.
3. Launch the provider command through `scripts/paste_stdin.py`; pass arguments
   as an argv list after `--`, never through `sh -c` or another shell string:

   ```bash
   python3 <skill-dir>/scripts/paste_stdin.py \
     --label "Service authorization code" \
     --prompt-pattern "Paste code here" \
     -- service-cli auth login
   ```

   The helper runs the child in a no-echo PTY, waits for the prompt before
   collecting anything, sends the value once, suppresses all post-submit child
   output, and never stores the value. It prints only `submitted`, `cancelled`,
   or a non-secret error code.
4. Prove success with the smallest real authenticated request. Do not treat the
   helper's `submitted` status or the provider's cached-login metadata as proof.
5. If the real probe still rejects authentication, use the provider's official
   diagnosis before repeating login. Repeated failures can indicate missing
   scopes, a locked OS credential store, clock drift, conflicting credentials,
   or a network boundary; do not rotate unrelated credentials speculatively.

## Claude subscription setup token

Claude may print its 108-character setup token across multiple terminal lines.
Do not copy the visible first line or use the stdin helper, which intentionally
discards output after authorization. Run the dedicated capture helper instead:

```bash
python3 <skill-dir>/scripts/capture_claude_setup_token.py \
  --target ~/.codex/secrets/claude/subscription.env
```

The helper widens the private terminal, reconstructs wrapped output, and refuses
to save anything except a complete 108-character `sk-ant-oat01-` token. It emits
only `saved` or a non-secret error code. If Claude requests a manual browser
authorization code, the helper collects it through the native masked dialog on
macOS. Use `--replace` only with explicit rotation authorization.

Prove the saved token with one request through its real consumer. Consumers
must set `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB=1` so Claude keeps the credential for
model requests while removing it from Bash, hooks, and MCP subprocesses.

## Storage contract

- Single-line dotenv-compatible values only; multiline keys and certificates
  require a managed secret store or a service-native file mechanism.
- Secret directories created by the helper use mode `0700`; target files are
  atomically written with mode `0600`.
- Tracked `.env.example` files may document variable names, purpose, safe
  defaults, owner, and validation method, but never values.
- Prefer T3 Code's native `request_secret` card (`delivery: "file"`) for all
  secret intake in T3 sessions. Outside T3 Code, use `paste_env.py --key` on
  macOS or ask the user to use a secure local/password-manager mechanism; never
  fall back to chat or a visible prompt.

## Known key consoles

Only give a console path when it has been verified. Extend this list when a
provider's official documentation confirms a new one.

| Service | Key console | Verified |
|---|---|---|
| Linear | `linear.app/settings/account/security` | 2026-08-10 |
| GitHub | `github.com/settings/tokens` | stable |
| Anthropic | `console.anthropic.com/settings/keys` | stable |
