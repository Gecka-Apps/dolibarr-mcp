#!/usr/bin/env python3
"""Extract the full permission catalog from Dolibarr core module descriptors.

Each core module declares its permissions in ``core/modules/mod*.class.php`` via
a series of ``$this->rights[$r][N] = ...;`` assignments (N is either a numeric
index or a named class constant such as ``self::KEY_FIRST_LEVEL``):

    [0] numeric id            (ignored)
    [1] human label
    [2] default state         (ignored)
    [3] enabled-by-default     (ignored)
    [4] perms      -> first  permission segment
    [5] subperms   -> second permission segment (optional)

The permission path used by the REST API tree (and by ``$user->hasRight()``) is
``<rights_class>.<perms>[.<subperms>]``, where ``rights_class`` is declared as
``$this->rights_class = '...';`` in the same descriptor.

This script walks every descriptor of a Dolibarr source tree and emits:
  - a Python data module consumed by the MCP capability layer
  - a human-readable Markdown reference

Point it at any Dolibarr checkout with ``--dolibarr`` (its ``htdocs/core/modules``
is derived automatically) and regenerate whenever the target Dolibarr version
changes:

    uv run --no-sync python scripts/extract_permissions.py --dolibarr /path/to/dolibarr
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

RIGHTS_CLASS_RE = re.compile(r"\$this->rights_class\s*=\s*'([^']+)'")
# Descriptors address the right tuple either by numeric index ([0], [1], [4], [5])
# or by the named class constants used since Dolibarr modernized the descriptors.
RIGHT_ASSIGN_RE = re.compile(r"\$this->rights\[\$r\]\[(\d|self::KEY_\w+)\]\s*=\s*(.*?);")
FIRST_LITERAL_RE = re.compile(r"""^(['"])(.*)\1""")

# Map the named constants onto the numeric slots we care about.
KEY_CONST_TO_INDEX = {
    "self::KEY_ID": 0,
    "self::KEY_LABEL": 1,
    "self::KEY_DEFAULT": 2,
    "self::KEY_FIRST_LEVEL": 4,
    "self::KEY_SECOND_LEVEL": 5,
}


def _slot(raw_index: str) -> int | None:
    if raw_index.isdigit():
        return int(raw_index)
    return KEY_CONST_TO_INDEX.get(raw_index)


def _literal(raw: str) -> str:
    """Return the leading quoted literal of a PHP RHS, else the raw expression."""
    raw = raw.strip()
    m = FIRST_LITERAL_RE.match(raw)
    if m:
        return m.group(2)
    return raw


def parse_descriptor(path: Path) -> tuple[str, str, list[dict[str, str]]] | None:
    text = path.read_text(encoding="utf-8", errors="replace")

    rc_match = RIGHTS_CLASS_RE.search(text)
    if not rc_match:
        return None
    rights_class = rc_match.group(1)

    # "modFacture.class.php" -> "Facture". $this->name is usually a preg_replace
    # on the class name, so the filename is the reliable display source.
    module_name = path.name.removeprefix("mod").removesuffix(".class.php")

    rights: list[dict[str, str]] = []
    current: dict[int, str] = {}

    def flush() -> None:
        # A usable right needs at least a first-level perms segment ([4]).
        if 4 in current:
            perms = _literal(current[4])
            subperms = _literal(current[5]) if 5 in current and current[5].strip() not in ("''", '""') else ""
            # Skip entries whose perms could not be resolved to a literal.
            if perms and not perms.startswith("$"):
                path_segments = [rights_class, perms] + ([subperms] if subperms else [])
                rights.append({
                    "path": ".".join(path_segments),
                    "label": _literal(current[1]) if 1 in current else "",
                })
        current.clear()

    for line in text.splitlines():
        m = RIGHT_ASSIGN_RE.search(line)
        if m:
            idx = _slot(m.group(1))
            if idx is None:
                continue
            if idx == 0 and current:
                flush()
            current[idx] = m.group(2)
        elif "$r++" in line:
            flush()
    flush()

    return rights_class, module_name, rights


def build_catalog(modules_dir: Path) -> dict[str, dict]:
    catalog: dict[str, dict] = {}
    for descriptor in sorted(modules_dir.glob("mod*.class.php")):
        parsed = parse_descriptor(descriptor)
        if not parsed:
            continue
        rights_class, module_name, rights = parsed
        if not rights:
            continue
        entry = catalog.setdefault(rights_class, {"module": module_name, "permissions": {}})
        for r in rights:
            # First writer wins for the human label; keep the path deduplicated.
            entry["permissions"].setdefault(r["path"], r["label"])
    return catalog


def render_python(catalog: dict[str, dict]) -> str:
    lines = [
        '"""Dolibarr core permission catalog.',
        "",
        "Auto-generated from the Dolibarr core module descriptors by",
        "``scripts/extract_permissions.py``. Do not edit by hand: regenerate it",
        "when targeting a new Dolibarr version.",
        "",
        "Keys are the module ``rights_class`` (the first segment of a permission",
        "path, e.g. ``facture``). Each permission maps its full dotted path",
        '(``<rights_class>.<perms>[.<subperms>]``) to its upstream English label.',
        '"""',
        "",
        "from __future__ import annotations",
        "",
        "CORE_PERMISSIONS: dict[str, dict] = {",
    ]
    for rights_class in sorted(catalog):
        entry = catalog[rights_class]
        lines.append(f"    {rights_class!r}: {{")
        lines.append(f"        {'module'!r}: {entry['module']!r},")
        lines.append(f"        {'permissions'!r}: {{")
        for perm_path in sorted(entry["permissions"]):
            label = entry["permissions"][perm_path]
            lines.append(f"            {perm_path!r}: {label!r},")
        lines.append("        },")
        lines.append("    },")
    lines.append("}")
    lines.append("")
    lines.append("")
    lines.append("def permission_exists(path: str) -> bool:")
    lines.append('    """Return True if *path* is a known core permission path."""')
    lines.append("    segments = path.split('.')")
    lines.append("    module = segments[0] if segments else ''")
    lines.append("    entry = CORE_PERMISSIONS.get(module)")
    lines.append("    return bool(entry) and path in entry['permissions']")
    lines.append("")
    return "\n".join(lines)


def render_markdown(catalog: dict[str, dict]) -> str:
    total = sum(len(e["permissions"]) for e in catalog.values())
    lines = [
        "# Dolibarr Core Permission Reference",
        "",
        "Auto-generated from the Dolibarr core module descriptors "
        "(`core/modules/mod*.class.php`) by `scripts/extract_permissions.py`. "
        "Regenerate when targeting a new Dolibarr version.",
        "",
        f"**{len(catalog)} modules — {total} permissions.**",
        "",
        "Each permission path is what `$user->hasRight()` and the REST rights tree "
        "expose: `<rights_class>.<perms>[.<subperms>]`.",
        "",
    ]
    for rights_class in sorted(catalog):
        entry = catalog[rights_class]
        lines.append(f"## `{rights_class}` — {entry['module']}")
        lines.append("")
        lines.append("| Permission path | Label |")
        lines.append("| --- | --- |")
        for perm_path in sorted(entry["permissions"]):
            label = entry["permissions"][perm_path].replace("|", "\\|")
            lines.append(f"| `{perm_path}` | {label} |")
        lines.append("")
    return "\n".join(lines)


def resolve_modules_dir(args: argparse.Namespace) -> Path:
    if args.modules_dir:
        return args.modules_dir
    if args.dolibarr:
        return args.dolibarr / "htdocs" / "core" / "modules"
    sys.exit("error: provide --dolibarr <dolibarr root> or --modules-dir <path>")


def main() -> None:
    repo = Path(__file__).resolve().parents[1]  # scripts/ -> repo root
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--dolibarr",
        type=Path,
        help="Path to a Dolibarr source tree (its htdocs/core/modules is used).",
    )
    parser.add_argument(
        "--modules-dir",
        type=Path,
        help="Direct path to a core/modules directory (overrides --dolibarr).",
    )
    parser.add_argument(
        "--py-out",
        type=Path,
        default=repo / "src" / "dolibarr_mcp" / "permissions_catalog.py",
    )
    parser.add_argument(
        "--md-out",
        type=Path,
        default=repo / "docs" / "dolibarr-permissions-reference.md",
    )
    args = parser.parse_args()

    modules_dir = resolve_modules_dir(args)
    if not modules_dir.is_dir():
        sys.exit(f"error: not a directory: {modules_dir}")

    catalog = build_catalog(modules_dir)
    if not catalog:
        sys.exit(f"error: no module descriptors found under {modules_dir}")

    args.py_out.write_text(render_python(catalog), encoding="utf-8")
    args.md_out.write_text(render_markdown(catalog), encoding="utf-8")

    total = sum(len(e["permissions"]) for e in catalog.values())
    print(f"Source:  {modules_dir}")
    print(f"Modules: {len(catalog)}  Permissions: {total}")
    print(f"Wrote {args.py_out}")
    print(f"Wrote {args.md_out}")


if __name__ == "__main__":
    main()
