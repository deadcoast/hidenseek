# **Hide N’ Seek Directory Manager**

Welcome to **Hide N’ Seek (HNS)** – an all-in-one, cross-platform CLI toolkit that lets you

- **Hide / reveal** files or folders (macOS chflags, Windows attrib, Linux dot-rename)
- **Sanitise & reorganise** messy directories in a single pass
  - Randomised privacy-friendly filenames
  - Auto-sorted by file-type, date, or both
  - Recursive traversal, empty-folder cleanup, full undo
- **Work interactively** with a Rich-powered TUI **or** run one-shot commands from your shell

---

## **Table of Contents**

- [**Hide N’ Seek Directory Manager**](#hide-n-seek-directory-manager)
  - [**Table of Contents**](#table-of-contents)
  - [**Key Features**](#key-features)
  - [**Installation**](#installation)
  - [**Quick Start**](#quick-start)
  - [**Interactive Menus**](#interactive-menus)
    - [**Main Menu**](#main-menu)
    - [**File Sanitizer Module**](#file-sanitizer-module)
      - [**Presets**](#presets)
  - [**Command-line Flags**](#command-line-flags)
  - [**Architecture Overview**](#architecture-overview)
  - [**Undo \& History**](#undo--history)
  - [**Configuration Files**](#configuration-files)
  - [**Extending HNS**](#extending-hns)
  - [**Contributing**](#contributing)
  - [**License**](#license)

## **Key Features**

| **Module**         | **Highlights**                                                                                                                           |
| ------------------ | ---------------------------------------------------------------------------------------------------------------------------------------- |
| **Hide / Seek**    | • Instant hide / reveal for any folder• Works recursively if desired• Dry-run preview                                                    |
| **File Sanitizer** | • Privacy-safe renaming ([NNN_DDMMYY]) • Sorting by file-type / date / both • Empty-folder cleanup• “Complete Sanitize” one-click preset |
| **Rich TUI**       | • Keyboard-only navigation• Clear status icons:  ● on / ▶ has sub-options / ↔ separator / 🔒 lock                                        |
| **History & Undo** | • Every hide/seek/sanitize operation is logged to ~/.hns_history.json• One-command revert                                                |

---

## **Installation**

> Requires **Python 3.8+**.

```bash
git clone https://github.com/yourname/hide-n-seek.git
cd hide-n-seek
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"   # installs hns + dev extras
```

After installation the command **hns** is available globally (within the venv).

---

## **Quick Start**

```bash
# Launch interactive UI
hns

# One-shot hide (non-recursive)
hns ~/Documents/Secret --hide

# Reveal recursively and stage a dry-run preview
hns ~/Documents/Secret --seek --recursive --dry-run
```

---

## **Interactive Menus**

### **Main Menu**

```bash
Welcome to Hide N Seek Directory Manager
[1] Hide
[2] Seek
[3] Config
[4] File Sanitizer
[h] Help  [q] Quit
```

**Hide / Seek Module:**

- Press **Enter** to supply a path.
- Toggle **Recursive** or **Dry-run** with [1] / [2].
- Config opens the shared settings screen.

### **File Sanitizer Module**

```bash
File Sanitizer – MainMenu
[1] Metadata Options
[2] SaniSort Options
[3] Master Options
[u] Undo last sanitise
[q] Quit
```

Icons & meaning

| **Icon** | **Meaning**                       |
| -------- | --------------------------------- |
| ●        | Option/sub-option is **active**   |
| ▶        | Option **has sub-options**        |
| ↔        | Separator between sub-options     |
| 🔒       | Lock – forces parent OFF globally |

#### **Presets**

- **CompleteSanitize** – strict, privacy-first: random names, type+date sort, recursion, cleanup.

---

## **Command-line Flags**

| **Flag / Arg**               | **Description**                     |
| ---------------------------- | ----------------------------------- |
| PATH                         | Folder to operate on                |
| --hide                       | Hide folder                         |
| --seek                       | Reveal folder                       |
| --recursive / --no-recursive | Override global recursive setting   |
| --dry-run                    | Show intended changes, perform none |
| --help                       | Full CLI help                       |

_(File Sanitizer currently operates only via the interactive menu for safety.)_

---

## **Architecture Overview**

```
src/hns/
├── fs.py              # Hide / Seek engine (OS-specific back-ends)
├── sanitizer.py       # Sanitiser engine (rename, sort, cleanup)
├── cli.py             # Main Typer + Rich UI
├── sanitizer_menu.py  # Dedicated File Sanitizer TUI
└── __init__.py        # Public API + version helper
tests/                 # Pytest suite covering fs & sanitizer
```

- **Pure-Python, no native extensions.**
- Shared **history log** (~/.hns_history.json) ensures a single undo stack for all modules.
- **Config** persists to ~/.hns_config.json.

---

## **Undo & History**

- Every operation appends a JSON entry:

```json
{
  "timestamp": 1721234567.89,
  "op": "hide",        # or "seek" / "sanitize"
  "path": "/Users/…",
  "recursive": false
}
```

- Use:
  - **Hide/Seek menu → Config → “Revert last change”**
  - **File Sanitizer main menu → u**

---

## **Configuration Files**

| **File**            | **Purpose**                                    |
| ------------------- | ---------------------------------------------- |
| ~/.hns_config.json  | Default path, recursive flags, dry-run setting |
| ~/.hns_history.json | Append-only log for undo/forensics             |

Example ~/.hns_config.json:

```json
{
  "default_path": "/Users/deadcoast/Desktop/Files",
  "recursive_global_hide": false,
  "recursive_global_seek": true,
  "dry_run": false
}
```

---

## **Extending HNS**

- **Add new modules** – `create <name>.py engines + <name>_menu.py UIs, import into cli.py.`
- **Icons** – follow the iid index (●, ▶, ↔, 🔒) for instant visual consistency.
- **Unit tests** – place under tests/, rely on temporary paths (tmp_path fixture).

---

## **Contributing**

1. Fork → feature branch → PR.
2. Ensure **pytest -q** passes & ruff --fix . produces no warnings.
3. Update README.md and CHANGELOG.md if user-visible changes occur.

Found a bug or have an idea? Open an issue – feedback is welcome!

---

## **License**

**MIT License** – see [LICENSE](LICENSE) for full text.
© 2025 deadcoast. Feel free to use, modify, and distribute with attribution.
