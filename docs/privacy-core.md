# Privacy core

Mr Hide now ships a provider-neutral privacy core, but the current proxy does not yet apply it to OpenAI or Anthropic payload fields. RDM-003 and RDM-004 own that protocol integration.

## Protection modes

- Conversational text uses stable compact aliases by default. Detection is local, supports English and Spanish model packages, and is best effort rather than a guarantee that every sensitive value will be found.
- `safe-tool-calls` applies the compact aliases to model-visible tool definitions, arguments, results, and history. This can break tools whose identifiers, paths, commands, schemas, or values cannot tolerate substitution.
- `tool-compatibility` uses deterministic realistic surrogates for PII and visibly non-working stand-ins for secrets across conversation and tool traffic.
- Default tool policy leaves provider-bound tool data unchanged. It emits the `tool-data-unprotected` warning; only aliases already known from conversational text are restored on the provider-to-local boundary.

All known privacy-processing and state failures block without returning raw or partially transformed text. Raw passage is allowed only after an explicit warning is accepted for one conversation. That bypass remains visible and persists only in that conversation's encrypted vault.

## Conversation vault

Each conversation has a canonical UUID and an authenticated AES-256-GCM vault. A random installation master key is held by the approved operating-system keyring, while HKDF derives a separate key for each conversation. Copying the ciphertext directory alone does not provide the key or reveal original mapped values.

Vault writes use an exclusive lock, revision check, same-directory temporary file, flush, fsync, and atomic replacement. State expires at 30 days of inactivity. Reuse before that boundary refreshes activity; at or after the boundary the ciphertext is deleted and the old mapping identity is reported expired rather than recreated.

Run `mr-hide doctor` to see redacted keyring and English/Spanish model availability. It reports package names and availability only; it does not display credentials, mappings, prompts, or model contents.

## Development evidence

Run the deterministic synthetic benchmark with:

```shell
python scripts/bench_aliases.py --check
```

The output names its metric (`utf8-bytes`) and reports original cost, substitute cost, and claimed savings. It uses only synthetic non-working values and verifies restoration before reporting.
