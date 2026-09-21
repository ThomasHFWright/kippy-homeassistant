# Development

The development layout follows PetSafe's small setup/develop/test/check entry
points and the [jpawlowski blueprint at
0df158948e717acac4fe19fc51f40e31bd090bae](https://github.com/jpawlowski/hacs.integration_blueprint/tree/0df158948e717acac4fe19fc51f40e31bd090bae).
It retains this repository's integration, history and tests; no blueprint domain
or cleanup framework is imported.

## Environment

The current tuple is Python 3.14.2+, Home Assistant 2026.9.3, and
pytest-homeassistant-custom-component 0.13.366. The test plugin pins the matching
pytest and asyncio versions. These versions were checked against PyPI metadata
on September 21, 2026. Runtime/test/tool requirements are separate. Ruff handles
formatting, import sorting and linting, and MyPy handles typing. The pinned Core
requirements also supply the base component dependencies needed by the UI and
hassfest; these are not all included in the published HA wheel.

Open the devcontainer to install system prerequisites and run setup, or install
Python 3.14.2+ and the following Debian/Ubuntu prerequisites yourself:

```bash
sudo apt-get update
sudo apt-get install build-essential libffi-dev libssl-dev libjpeg-dev zlib1g-dev libturbojpeg0-dev ca-certificates
KIPPY_API_PATH=../kippy-api ./script/setup
./script/test --cov --cov-report=term-missing
./script/check
.venv-dev/bin/python script/hassfest --integration-path custom_components/kippy
```

`script/setup` creates `.venv-dev` and installs the adjacent API package editable
only when `KIPPY_API_PATH` is explicitly supplied. Without it, setup installs the
requirements from the integration manifest using PyPI. Until the first API release
is published, supply the local checkout. `KIPPY_PYTHON` selects the interpreter and
`KIPPY_VENV` selects an alternate virtual environment. Scripts do not uninstall
editable packages or modify system trust settings. Install hooks optionally with
`.venv-dev/bin/pre-commit install`. `script/check` includes the standalone
`script/test-scaffold` check for configuration and signal forwarding.

The previous baseline is preserved separately for compatibility checks:

```bash
python3.13 -m venv .venv-baseline
.venv-baseline/bin/python -m pip install -r requirements-baseline.txt -e ../kippy-api
KIPPY_VENV="$PWD/.venv-baseline" ./script/test
```

That tuple is Python 3.13.15, HA 2025.9.1 and test plugin 0.13.278. Its pycares
constraint preserves the API required by aiodns 3.5. Raising the development
version alone does not change HACS's supported minimum. Compatibility must be
verified before changing that declared minimum.

## Run Home Assistant

```bash
./script/develop
# For a second isolated instance:
KIPPY_DEV_CONFIG="$PWD/dev-config/second" KIPPY_DEV_PORT=8124 ./script/develop
```

Open `http://127.0.0.1:8123`, complete onboarding and add Kippy through the UI.
Configuration and state live under the ignored `dev-config` directory. The
initial configuration binds to localhost; existing configuration files are
preserved. The process runs in the foreground. Stop it with Ctrl+C (or SIGTERM),
which reaches HA directly through `exec` and lets it perform normal cleanup.
No other HA processes are killed. The integration is symlinked into this isolated
configuration and `--skip-pip-packages kippy-api` preserves the installed API
checkout. Restart HA to pick up integration edits.

Ordinary tests mock the API and require no credentials. Live tests are opt-in;
put credentials only in the ignored `.secrets/kippy.env` and follow the live-test
instructions in the test module. Never commit that file or capture tokens,
location data or account payloads in fixtures/logs.

## Two-repository CI and release order

CI runs the same `script/setup`, `script/check` and `script/test` commands. By
default it installs the pinned API release from PyPI. Before that release exists,
use the sibling checkout locally. For combined CI once the API source has been
pushed, set repository variables `KIPPY_API_REPOSITORY` (`owner/repo`) and
`KIPPY_API_REF` (the full reviewed 40-character commit SHA). The workflow checks
out that exact source and installs it editable. You can override these values
with the corresponding manual workflow inputs. No nonexistent remote is assumed,
no credentials are embedded and dependency failures remain failures.

Until an API remote or PyPI release exists, a clean remote CI run cannot test the
extracted integration. Local two-repository checks are the review baseline.
Source-based CI establishes integration compatibility but does not validate PyPI
availability. After publishing the API, clear those repository variables, run CI
against the exact manifest pin from PyPI, and only then release the integration.
The API repository owns its separate build and PyPI publishing workflow.

Coverage retains the existing 91% CI threshold during migration; the documented
project target is above 95% overall and 100% for config flows. Report the measured
coverage and remaining gaps rather than lowering the gate to accommodate failures.
