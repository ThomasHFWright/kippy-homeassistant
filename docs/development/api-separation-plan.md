# Kippy API separation and development tooling plan

Prepared 21 September 2026; updated after implementation and validation.

The API is now a standalone [kippy-api repository](https://github.com/ThomasHFWright/kippy-api)
and [PyPI package, version 1.0.0](https://pypi.org/project/kippy-api/1.0.0/).
The integration pins that release. Its extraction and PetSafe-style tooling changes
are together in [draft PR #181](https://github.com/ThomasHFWright/kippy-homeassistant/pull/181).
See [development instructions](development.md) for runnable commands.

The assessment and original sequencing below record the design and repository
state before implementation. The integration itself has not been merged or released.

## What existed at the initial assessment

Authenticated GitHub discovery enumerated all 48 repositories under
`ThomasHFWright`. The Kippy-related results were:

| Repository | Finding |
| --- | --- |
| [kippy-homeassistant](https://github.com/ThomasHFWright/kippy-homeassistant) | Current integration, version 1.0.4. Reviewed main at `66e890e`. Only main existed at the initial assessment. |
| [kippyAPIs](https://github.com/ThomasHFWright/kippyAPIs) | API reference inferred from Android traffic captures. Main contains only README.md and LICENSE; no package, workflows, tags, or pull requests. Keep as reference material. |
| [hass-kippy](https://github.com/ThomasHFWright/hass-kippy) | Fork of `hacs/default`, not another integration or API implementation. |

[PR #155](https://github.com/ThomasHFWright/kippy-homeassistant/pull/155) already
separated the embedded client into endpoint modules. No standalone API extraction
was found in the current repositories, branches, or matching integration PR history.
Neither `kippy-api` nor `kipp-api` had a published project at its PyPI JSON endpoint
when checked; a 404 does not guarantee that PyPI will accept or reserve a name.

PetSafe is a useful precedent:

- Its integration manifest pins `petsafe-api==3.0.4`.
- [petsafe-api's publishing workflow](https://github.com/ThomasHFWright/petsafe-api/blob/01e1acfd0ab6086f1aaf57b0b063841b6a31bb9a/.github/workflows/pypi_deploy.yml)
  builds distributions on `v*` tags and publishes through PyPI Trusted Publishing.
- [PetSafe PR #22](https://github.com/ThomasHFWright/homeassistant-petsafe/pull/22)
  introduced its blueprint structure. The initial scaffold and retained author
  attribution point to [jpawlowski/hacs.integration_blueprint](https://github.com/jpawlowski/hacs.integration_blueprint).
  Use PetSafe's working scripts and upstream as references. The exact upstream
  commit imported into PetSafe is not recorded in the evidence inspected.

## Validation of the architectural concern

The concern is valid. Home Assistant's developer guidance puts service/protocol
code in a standalone Python library published on PyPI, referenced in the
integration manifest. This is the Core contribution standard and a useful design
target for this custom integration; embedding a client does not by itself stop a
custom integration from working.

Sources: [Python API libraries](https://developers.home-assistant.io/docs/api_lib_index/),
[integration platforms](https://developers.home-assistant.io/docs/creating_platform_index/#interfacing-with-devices),
[dependency transparency](https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/dependency-transparency/).

The existing separation is a good starting point, but is not yet an independent
package:

- `manifest.json` has an empty `requirements` list.
- `api/activity.py` imports `homeassistant.util.dt` to obtain the timezone.
- API modules import the integration's mixed `const.py`. Importing that file also
  reads `translations/en.json` for exception messages.
- Setup, config flow and coordinators import `.api.KippyApi`. Switches, buttons and
  numbers call that client through their coordinators.
- The client already uses async `aiohttp` and accepts a supplied session. Preserve
  both properties; no replacement HTTP library is needed.

## Ownership after extraction

| Concern / existing code | Standalone library | Home Assistant integration |
| --- | --- | --- |
| `api/_base.py`, endpoint modules | HTTP requests, login, cached tokens, one bounded auth refresh, endpoint payloads | Create client using HA's managed session |
| `api/_utils.py` | Response codes, decoding, protocol normalization, ISO weeks and timezone serialization | Translate exceptions into HA errors |
| API portions of `const.py` | URLs, headers, app identifiers, wire codes and action values | Domain, platforms, HA defaults, translations and presentation labels |
| Activity requests | Accept explicit dates/timezone; serialize for Kippy | Choose the requested reporting period using HA's configured timezone |
| Map results | Normalize vendor response fields; preserve the initial return shape | LBS filtering, retained coordinates, derived `starting_live` state and polling cadence |
| Pet data | Return all pets and subscription metadata | Entity/device creation, subscription-based availability and refresh policy |
| Runtime state | Authentication state only | Coordinators, timers, reload/unload, config entries, options, notifications and entities |
| Tests | HTTP/auth/payload/parsing/redaction tests; standalone installation check | Config flow, lifecycle, entity state and registry compatibility tests |

Do not move entire coordinator or helper files into the library. For example,
`_derive_operating_status` combines past HA state with polling decisions, while
`build_device_info` and refresh-option helpers are explicitly HA-specific.

## Library contract

Start with the existing `KippyApi` class and endpoint modules. Preserve method names
and dictionary results for the first extraction so packaging changes do not also
require rewriting every entity. Avoid introducing a new device object hierarchy.

Proposed import: `from kippy_api import KippyApi`.

1. **Independent imports:** no `homeassistant` imports, custom-component imports,
   HA translations, config entries, timers, or filesystem credential loading.
2. **Session ownership:** require a caller-supplied `aiohttp.ClientSession`.
   The client must never close it. Existing `BaseKippyApi.close()` closes the
   supplied session; remove that method from the new contract and update standalone
   tests to own their session with `async with`. HA unload already leaves it open.
3. **Timezone:** retain date-string arguments initially, add an explicit keyword
   timezone argument using stdlib `tzinfo`/`ZoneInfo`, and pass the HA timezone at
   both activity coordinator call sites. Test DST boundaries, fractional offsets
   and ISO week/year transitions. Do not fall back to the machine's local timezone.
   The unused `_weeks` argument can remain during extraction and be removed later.
4. **Exceptions:** expose a small `KippyError` base with authentication, connection
   and response subclasses. Preserve HTTP status/API return code as structured
   information. Invalid credentials and exhausted authentication refresh are auth
   errors; malformed requests, inactive subscriptions and unknown result codes
   must not all become HTTP 401. Do not guess new backend codes from issue titles.
5. **Protocol compatibility:** preserve text/plain JSON requests, `return` versus
   `Result`, boolean versus integer handling, known successful bodies delivered
   with HTTP 401, and nested versus top-level map/activity responses. Cover these
   with real client tests using fake HTTP responses.
6. **Bounded requests:** use an explicit request timeout and at most one retry on
   confirmed auth expiry. Test concurrent expiry before choosing the smallest
   per-client refresh synchronization needed. Never retry device commands after an
   ambiguous timeout merely because they failed to return a response.
7. **TLS and logging:** keep certificate verification enabled. The current client
   lowers the cipher security level for the Kippy endpoint; verify whether that
   workaround is still necessary before changing it. Never copy the global TLS
   bypass in `script/codex.sh`. Log status/operation metadata instead of full account
   or location payloads; current redaction covers only a small subset of fields.

Use `pyproject.toml`, the existing MIT attribution, `py.typed`, and only `aiohttp`
as a direct runtime dependency initially. Keep development requirements separate.
Verify the declared Python range with CI; Python 3.13+ is a reasonable initial
baseline for this extraction, independent of HA's newer Python requirement.

The session decision follows [HA's session injection guidance](https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/inject-websession/).

## Ordered implementation plan

### 1. Establish a reproducible baseline

- Run existing tests at the committed HA 2025.9.1/Python 3.13 baseline in a devcontainer
  with the required compiler and system libraries. Record failures before changes.
- Capture synthetic multi-pet fixtures, IDs, entity states, subscription handling,
  live tracking transitions, LBS retention, activity periods and reload cleanup.
- Keep live tests opt-in. Ordinary CI must use fake HTTP responses and never depend
  on account credentials. `test_api_fake.py` tests a fake implementation itself;
  prioritize `test_api_unit.py`, redaction tests and integration tests for behavior.
- Open issues #178 (new account/API data), #179 (invalid auth), and #180 (one of two
  pets visible) define useful investigation scenarios, not confirmed root causes.
  Establish which reproduce before attributing them to packaging.

Exit: known baseline results and a repeatable test command.

### 2. Modernize integration scaffolding in its own PR

- Adapt the PetSafe-style `script/setup`, `script/develop`, `script/test`,
  `script/check`, `script/hassfest`, devcontainer and CI pattern to this repository.
  Preserve Kippy's git history, HACS repository, domain and existing tests.
- Pin the blueprint source commit used. Upstream was
  `0df158948e717acac4fe19fc51f40e31bd090bae` at review time and documents HA 2026.8+.
  PetSafe's local devcontainer currently pins HA 2026.3.2; do not blindly inherit it.
- Select a matched HA/Python/test-plugin tuple. PyPI reported current HA 2026.9.3
  requiring Python >=3.14.2 when checked. Test that as the modern development target;
  keep baseline compatibility testing or explicitly document a raised minimum.
  A devcontainer upgrade alone must not silently redefine supported HA versions.
- Consolidate pytest/coverage/typing/Ruff configuration in `pyproject.toml`, with
  common fixtures in `tests/conftest.py`. Use the same checks locally and in CI.
  Remove redundant Black/isort/Flake8/Pylint jobs only as part of the agreed tooling
  migration, updating AGENTS.md and pre-commit consistently.
- Ensure setup installs compiler/system prerequisites; develop actually starts HA;
  test instances have isolated config, predictable ports and verified shutdown.
- Support installing the adjacent library editable for combined development. The
  test cleanup script must not remove that intended editable dependency.
- Remove the global certificate-verification bypass from the old setup path.
  Carry over useful tooling without PetSafe's domain-specific entities, demo code,
  AWS dependencies or unrelated release automation.

Exit: clean checkout can set up, run tests, start/stop HA, and run CI consistently.

### 3. Extract and validate the API repository

- Create `kippy-api`, move the existing endpoint implementation and relevant
  constants/tests, retain licence attribution, and apply the contract above.
- Add standalone build/import checks: install the wheel in an environment without
  Home Assistant and verify imports and API tests there. Build and inspect both
  wheel and source distribution; include typing metadata and licence files.
- Add tests for session ownership, timeout/error classification, refresh limits,
  malformed responses, timezone conversion and response compatibility.
- Keep `kippyAPIs` as linked reverse-engineering documentation; exposing every
  captured endpoint is outside the extraction scope.

Exit: tested wheel and sdist work independently of Home Assistant.

### 4. Switch the integration to the library in a separate PR

- Update imports in `__init__.py`, `config_flow.py`, and `coordinator.py`; update
  API constant imports and patch targets in tests. Remove the embedded API package
  once no caller uses it. No duplicate client implementation or permanent shim.
- Pass timezone explicitly and preserve existing entity state keys.
- Map library auth failures to `invalid_auth` during config flow and
  `ConfigEntryAuthFailed` during setup/refresh; connection/response errors become
  `cannot_connect`, setup retry or `UpdateFailed` as appropriate. Current
  coordinators wrap all API failures in `UpdateFailed`; fix that boundary together.
- Add and test reauthentication so expired credentials can be repaired in place.
  Map command failures to HA action errors at existing switch/number/button callers.
- Preserve domain `kippy`, device identifiers, entity unique IDs, config-entry
  version/data and option keys. Existing users should not need to delete and re-add.
  Modernize runtime storage only if required by the selected scaffold, with tests.
- Validate setup, every platform, multi-pet data, active/expired subscriptions,
  reload/unload and configuration migration against the editable library first.

Exit: existing config produces the same devices/entities and uses the external client.

### 5. Publish the library, then release the integration

Use PetSafe's tagged-release model, strengthened with validation before publishing:

1. PR CI runs API tests, lint/type checks, wheel/sdist build, metadata checks and
   installation/import tests without Home Assistant.
2. A `vX.Y.Z` tag triggers release CI, which verifies the tag matches package
   metadata and reruns required checks on that commit.
3. Build distributions once; pass those artifacts to a separate publishing job.
4. Publish using `pypa/gh-action-pypi-publish` and Trusted Publishing, with
   `id-token: write` scoped to that job. Keep tests/build jobs read-only.
5. Configure PyPI's trusted publisher for the exact owner, repository, workflow
   filename and any chosen GitHub environment. This is a one-time account-side
   setup; no long-lived PyPI token belongs in an env file or the repository.
6. Confirm installation of the published version from PyPI, then pin it in Kippy's
   `manifest.json` (implemented as `kippy-api==1.0.0`).
7. Run integration CI and clean-install testing using that published package, then
   release the integration through its existing HACS repository.

Do not merge an integration release that requires an unpublished version. For local
development use an editable install and HA's documented `--skip-pip-packages`
option so dependency installation does not overwrite it. Rollback is to the prior
integration release; preserve IDs/options so that remains straightforward.

Publishing reference: [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/using-a-publisher/).

## Implementation validation

- The original integration passed 181 offline tests at HA 2025.9.1/Python 3.13.15
  after the compiler was installed and the historical resolver dependency was
  constrained to `pycares<5`.
- The extracted library passed 81 tests on Python 3.13 and 3.14, with 99.68%
  coverage. Ruff, mypy, wheel/sdist builds, package metadata checks and importing
  an installed wheel without Home Assistant all passed.
- The updated integration passed 167 offline tests on both HA 2025.9.1 and
  HA 2026.9.3, with 98.46% modern-suite coverage and 100% config-flow coverage.
  Protocol tests now belong to the library; the integration suite covers HA
  lifecycle, registry compatibility, reauthentication and entity actions.
- Both opt-in live checks passed: read-only API calls and actual Home Assistant
  integration setup, entity/device registration and unload with the shared HTTP
  session left open. Map reads used `do_sms=False`; no tracker settings changed.
- Ruff, mypy, the development launcher self-check and hassfest passed. A local HA
  server returned its onboarding page and stopped cleanly when signalled.
- Default TLS negotiation still failed against Kippy during the live check. The
  library retains the existing endpoint-scoped cipher compatibility context,
  with certificate and hostname verification enabled. The global TLS bypass was
  removed from the development bootstrap.
- Populated credentials remain in ignored `.secrets/kippy.env` with permissions
  0600. Live tests are excluded from ordinary CI and fail on real auth/network
  errors when explicitly enabled with supplied credentials.

## Release status and remaining work

- API 1.0.0 passed GitHub CI on Python 3.13 and 3.14, including tests, package
  builds, metadata checks and installation without Home Assistant.
- Before publishing, the CI-built wheel passed real login, pet listing, cached
  map and activity reads for all three active devices. The packaged client also
  passed 167 HA tests and both live HA checks before the version-only 1.0.0 change.
- The tagged publishing workflow passed and published 1.0.0 through PyPI Trusted
  Publishing. Installation and import from PyPI were verified. The earlier 0.1.0
  publishing job completed before the version decision; 1.0.0 is the integration pin.
- GitHub authorization and PyPI publisher configuration are complete. Temporary
  source-checkout CI variables were removed so integration CI uses PyPI.
- Review PR #181 and choose the integration release version before merging and
  releasing it. Its existing version remains unchanged until that release.
