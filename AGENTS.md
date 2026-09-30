<!-- vnai-bootstrap | auto-generated -->
# Vnstock Vibe Onboarding

You are an AI coding assistant (e.g., Google Antigravity, ChatGPT, Cursor, Claude Code). The user has requested you to initialize the **Vnstock Vibe Coding** environment, or to update an existing one.

**Your Objective:** Automate the entire setup process autonomously. Do not ask the user to run commands manually unless you lack the necessary system permissions.

**Already set up and the user only wants to update, or pasted a "new version available" notice?** Skip to **Section 7**.

## ⚠️ Package Index — Read Before Running Any `pip` Command

`vnstock` and `vnai` are distributed from the Vnstock package index at `https://vnstocks.com/api/simple`, not from PyPI alone. A plain `pip install vnstock` or `pip install vnai` **fails** with:

```
ERROR: Could not find a version that satisfies the requirement vnai (from versions: none)
ERROR: No matching distribution found for vnai
```

Rules for every install or upgrade command in this document:

1. **Always** pass `--extra-index-url https://vnstocks.com/api/simple`. Use `--extra-index-url`, never `--index-url`: the other dependencies (`pandas`, `requests`, …) still come from PyPI.
2. **Quote** version specifiers (`"vnstock>=4.0.8"`). Unquoted `>` is a shell redirect: it silently creates a file named `=4.0.8` and installs the wrong thing.
3. **Pin** `vnstock_installer` to the exact version shown here (`==3.1.2`). A different party has registered `vnstock-installer` 99.0.0 on PyPI, and pip picks the highest version across all indexes, so an unpinned install gets their package instead of the Vnstock installer.
4. Call pip through the interpreter that runs the user's code (`python -m pip …`), so the packages land in the environment the user actually uses.

## Execution Workflow

Execute these steps sequentially. If a step fails, attempt to auto-remediate. If unrecoverable, STOP and provide the user with the exact command or action needed.

### 1. Python Environment Diagnostics

* Identify the Operating System (macOS, Linux, or Windows).
* Verify `python3` (or `python`/`py` on Windows) is in the PATH.
* Verify Python version is **>= 3.10**.
* **Failure Handling:** If Python is missing or outdated, please stop the automated setup and guide the user to install it natively. Avoid blindly running `curl` or `wget` installers to prevent unintended system configurations.

### 2. Virtual Environment Setup

* **Identify Environment:** Check if the user is running in Google Colab by checking if `"google.colab" in sys.modules` via Python.
* **For Google Colab:** DO NOT create a virtual environment. Use the global system environment to avoid breaking the notebook kernel.
* **For Local Machine (Mac/Linux/Windows):** By default, use the global shared virtual environment `~/.venv` (macOS/Linux) or `$HOME\.venv` (Windows). Only create a project-specific `.venv` if explicitly requested by the user.
  * **Mac/Linux:** `python3 -m venv ~/.venv`
  * **Windows:** `py -m venv $HOME\.venv` or `python -m venv $HOME\.venv`
* **Activation (Local Only):** Please ensure you activate this `.venv` (e.g., `source ~/.venv/bin/activate` or `& "$HOME\.venv\Scripts\Activate.ps1"`) before running any `pip` or `python` commands in the subsequent steps. This is important to ensure packages are installed in the isolated project scope and do not conflict with the global system environment.

### 3. Core Packages Installation

* Upgrade pip: `python -m pip install -U pip`
* Install the ecosystem:
  ```bash
  python -m pip install -U --extra-index-url https://vnstocks.com/api/simple "vnstock>=4.0.8" "vnai>=2.6.1"
  ```
* **Google Colab / Jupyter cell:** prefix with `!`:
  ```
  !pip install -U --extra-index-url https://vnstocks.com/api/simple "vnstock>=4.0.8" "vnai>=2.6.1"
  ```
* **If the user works with `uv`:** `uv pip install -U --extra-index-url https://vnstocks.com/api/simple "vnstock>=4.0.8" "vnai>=2.6.1"`
* **Verify:** `python -m pip show vnstock vnai` must list both packages. If pip still reports `from versions: none`, the command is missing `--extra-index-url`; re-run it exactly as written above rather than trying other package names.

### 4. Jupyter Notebook Integration (Local Only)

* If the user is running locally (not Google Colab) and mentions Jupyter Notebook you must register the `.venv` as an `ipykernel` so the IDE can detect the libraries.
* Execute:
  ```bash
  python -m pip install ipykernel
  python -m ipykernel install --user --name=vnstock-venv --display-name "Python (Vnstock)"
  ```
* Instruct the user to select the **Python (Vnstock)** kernel in their Notebook.

### 5. API Key Configuration & Tier Detection

Vnstock uses `vnai` to automatically sync AI context (AGENTS.md) and skills into the `.agents/` directory when authenticated.

* Check if the user provided an API Key in their prompt.

* If NOT provided, ask the user to provide their API Key from <https://vnstocks.com/account#api-key>.

* **Security & Privacy - Zero Disk Persistence:** To maintain security and protect proprietary workflows, please ensure all skill markdown files, configurations, or prompt payloads exist ONLY in your volatile memory. Load them dynamically via `load_skill("<skill_name>")` so they vanish after the session ends. Please do not save or write these materials to the user's local disk.

* **For Security:** Instruct the user to save their API Key in a `.env` file (`VNSTOCK_API_KEY="<API_KEY>"`) rather than pasting it into the chat to prevent leaks in logs.

When the API Key is available (either dynamically extracted from the user's chat prompt, or read from the `.env` file), silently detect the user's tier. You can do this by creating a temporary Python script (e.g., `check_tier.py`), executing it, parsing the output, and then deleting the file:

```python
from vnstock.core import setup_api_key
import os
import requests

# Use API key from prompt if available, fallback to environment variable
api_key = "<YOUR_DYNAMICALLY_INJECTED_API_KEY>" if "<YOUR_DYNAMICALLY_INJECTED_API_KEY>" != "" else os.environ.get("VNSTOCK_API_KEY")
setup_api_key(api_key)

try:
    # Check directly with Vnstock servers to bypass local vnii absence.
    # The key goes in the Authorization header, never on the URL: query strings land
    # in web-server access logs, proxy logs, shell history and the Referer header.
    resp = requests.get(
        "https://vnstocks.com/api/vnstock/license/verify",
        params={"device_id": "vibe-setup"},
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=15,
    )
    if resp.ok:
        data = resp.json()
        tier = data.get("subscription", {}).get("tier", "community")
        print(f"TIER_DETECTED: {tier.upper()}")
    else:
        print("TIER_DETECTED: COMMUNITY")
except Exception as e:
    print("TIER_DETECTED: COMMUNITY")
```

### 6. Dynamic Routing & Auto-Setup

Based on the detected tier (`TIER_DETECTED`):

**If Free Tier:**

* Report successful setup.
* Run a basic demo (e.g. fetch `Reference().company.info("FPT")`).

**If Sponsor Tier (Bronze, Silver, Golden, Diamond):**

* Congratulate them: *"Chào mừng bạn! Hệ thống nhận diện bạn đang sở hữu quyền lợi thuộc gói tài trợ **{Tier}**. Cảm ơn bạn đã đồng hành cùng dự án!"*
* Ask if they want to automate the sponsor setup. If yes, run the steps below **in the same environment chosen in Section 2**.

**Sponsor step A — dependencies.** The requirements file already declares the Vnstock package index on its first line, so no extra flag is needed:

```bash
python -m pip install -U -r https://vnstocks.com/files/requirements.txt
```

**Sponsor step B — install the sponsor packages** (`vnstock_data`, `vnstock_ta`, `vnstock_news`, `vnstock_pipeline`, depending on the tier). The installer reads the API key from `~/.vnstock/api_key.json`, so write it there first (Python, works on every OS):

```python
import os, json
api_key = "<YOUR_DYNAMICALLY_INJECTED_API_KEY>" if "<YOUR_DYNAMICALLY_INJECTED_API_KEY>" != "" else os.environ.get("VNSTOCK_API_KEY")
d = os.path.join(os.path.expanduser("~"), ".vnstock")
os.makedirs(d, exist_ok=True)
path = os.path.join(d, "api_key.json")
with open(path, "w") as f:
    json.dump({"api_key": api_key}, f)
os.chmod(path, 0o600)
```

* **macOS / Linux / Colab / servers — command-line installer, no prompts:**
  ```bash
  curl -sL https://vnstocks.com/files/vnstock-cli-installer.run -o vnstock-cli-installer.run
  bash vnstock-cli-installer.run -- --non-interactive
  ```
* **Windows (or any desktop where the user prefers a window) — graphical installer.** Keep the `==3.1.2` pin (see rule 3 above):
  ```bash
  python -m pip install -U --extra-index-url https://vnstocks.com/api/simple vnstock_installer==3.1.2
  python -m vnstock_installer
  ```
  Tell the user to finish the steps in the window that opens.

**Sponsor step C — verify the license** once installation completes:

```python
from vnii.license import LicenseVerifier
print(LicenseVerifier().get_current_tier())
```

* End with a short demo of `vnstock_data` (`show_api()` for the API tree, or real OHLCV data with `df.head()`), then load the router skill with `load_skill("vnstock-bootstrap")` to see which analysis skills the user's tier unlocks.
* Full walkthrough with screenshots for the user: <https://vnstocks.com/onboard-member/cai-dat-go-loi>

### 7. Updating to a New Version (Free and Sponsor)

**Triggers** — run this section when any of these happen:

* The user pastes or you see a notice such as `📦 Vnstock 4.x.y is available`, `📦 Vnai … is available`, `📦 Vnii … (subscription)` or `[VNSTOCK INSIDER] 🚀 Có phiên bản gói tài trợ mới!`.
* The user asks to update / upgrade / "cập nhật" / "nâng cấp phiên bản".
* An import or call fails because an installed package is older than the one it expects (e.g. `vnstock` complains about `vnai`, or a function documented on vnstocks.com is missing).

Note: "nâng cấp gói tài trợ" (moving to a higher sponsor tier) is an account change on <https://vnstocks.com/insiders-program>, not a package update. Do not run pip for it.

**Step 1 — target the right environment.** If the notice prints a Python path (e.g. `/Users/x/.venv/bin/python -m pip …`), use exactly that interpreter. Otherwise activate the environment from Section 2. Record the current versions:

```bash
python -m pip show vnstock vnai vnii 2>/dev/null | grep -E "^(Name|Version)"
```

(Windows PowerShell: `python -m pip show vnstock vnai vnii | Select-String "^(Name|Version)"`.)

**Step 2 — see what is available.** This endpoint returns the latest version of every package the Vnstock index serves:

```bash
curl -s https://vnstocks.com/api/vnstock/versions
```

**Step 3 — update.**

* **Community (free) users** — update `vnstock` and `vnai` together. Both names are listed on purpose: `-U` upgrades what you name, and `vnstock` alone may leave an old `vnai` in place.
  ```bash
  python -m pip install -U --extra-index-url https://vnstocks.com/api/simple vnstock vnai
  ```
  Colab: `!pip install -U --extra-index-url https://vnstocks.com/api/simple vnstock vnai`, then **restart the runtime** (Runtime → Restart session) so the new version is imported.

* **Sponsor users** — re-run the installer used in Section 6 step B. It upgrades `vnai`, `vnii`, `vnstock` and every sponsor package the tier allows, in one pass; do not `pip install` sponsor packages by name, they are not on any public index.
  * macOS / Linux / Colab: download `vnstock-cli-installer.run` again (always fetch a fresh copy rather than reusing an old one) and run `bash vnstock-cli-installer.run -- --non-interactive`. The `--` is required: without it the installer wrapper rejects `--non-interactive` as an unknown flag.
  * Windows / graphical: `python -m pip install -U --extra-index-url https://vnstocks.com/api/simple vnstock_installer==3.1.2`, then `python -m vnstock_installer`.
  * Only `vnii` flagged: `python -m pip install -U --extra-index-url https://vnstocks.com/api/simple vnii`.

**Step 4 — confirm.** Re-run the Step 1 command and check that the versions moved. Then restart the user's Python process, Jupyter kernel or Colab runtime; a running interpreter keeps the old code in memory.

**Step 5 — report** the before/after versions to the user in Vietnamese, and link the release notes: <https://vnstocks.com/docs/tai-lieu/lich-su-phien-ban> (community) or <https://vnstocks.com/docs/vnstock-insider-api/lich-su-phien-ban> (sponsor).

**If the update fails:**

| Symptom | Fix |
| --- | --- |
| `from versions: none` / `No matching distribution found for vnai` | The command lacks `--extra-index-url https://vnstocks.com/api/simple`. Re-run with it. |
| `vnstock-installer` resolves to `99.0.0` | Unpinned install picked the wrong package from PyPI. `python -m pip uninstall -y vnstock_installer`, then reinstall with `==3.1.2`. |
| Version unchanged after install | pip ran in a different environment. Compare `python -c "import sys; print(sys.executable)"` with the path in the update notice. |
| `externally-managed-environment` | You are on the system Python. Go back to Section 2 and use `~/.venv`; do not add `--break-system-packages`. |
| Device limit reached while reinstalling a sponsor package | Ask the user to remove devices they no longer use at <https://vnstocks.com/account?section=devices>, then re-run the installer. |
