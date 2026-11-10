#!/usr/bin/env python3
"""Relax module version checks in a rebuilt GKI kernel so the phone's existing
vendor modules keep loading.

Facts measured on the device (Redmi zorn, 6.1.157-android14-11-g2de7246565ac-mi):
  * stock kernel loads a module built for 6.1.68 -> the version *prefix* is already
    ignored for modules that carry __versions (see same_magic(): with CRCs present it
    compares only everything after the first space).  So vermagic is not the problem,
    unless our rebuild changes the flag suffix (SMP preempt mod_unload modversions
    aarch64) - this script removes the whole check as insurance.
  * flipping one __versions CRC breaks loading with
    "disagrees about version of symbol X" + "Unknown symbol X (err -22)" -> CRCs are
    enforced.  Enabling CONFIG_CGROUP_PIDS grows struct cgroup, which changes the CRC of
    the cgroup symbols four already-loaded vendor modules import (cgroup_path_ns,
    cgroup_taskset_first/next, cgroup_add_legacy_cftypes,
    try_to_free_mem_cgroup_pages), so this check has to go too.

Files touched on 6.1:
  kernel/module/main.c    -> check_modinfo()  (vermagic)
  kernel/module/version.c -> check_version()  (modversions CRC)
Older trees keep both in kernel/module.c, which is handled as a fallback.
"""
import sys, pathlib

root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "src")


def body_span(text, sig, filename):
    i = text.find(sig)
    if i < 0:
        return None
    j = text.find("\n}\n", i)
    if j < 0:
        raise SystemExit("FAIL: unterminated %r in %s" % (sig, filename))
    return i, j


def patch_file(rel_paths, edits):
    """edits: list of (signature, [(old, new)], label)"""
    for rel in rel_paths:
        p = root / rel
        if not p.exists():
            continue
        text = p.read_text()
        done = []
        for sig, subs, label in edits:
            span = body_span(text, sig, rel)
            if span is None:
                continue
            i, j = span
            body = text[i:j]
            new = body
            for old, rep in subs:
                if old in new:
                    new = new.replace(old, rep)
            if new == body:
                if "tolerated" in body:
                    done.append(label + ": already patched")
                continue
            text = text[:i] + new + text[j:]
            done.append(label + ": patched")
        if done:
            p.write_text(text)
            print("==", rel)
            for d in done:
                print("   ", d)
            return True
    raise SystemExit("FAIL: none of %s contains the functions to patch" % (rel_paths,))


# ---- gate 1: vermagic (kernel/module/main.c or kernel/module.c) ------------
patch_file(
    ["kernel/module/main.c", "kernel/module.c"],
    [(
        "static int check_modinfo(",
        [
            ('pr_err("%s: version magic \'%s\' should be \'%s\'\\n",',
             'pr_warn("%s: bad version magic tolerated: \'%s\' (kernel \'%s\')\\n",'),
            ("\t\treturn -ENOEXEC;\n\t}", "\t\t/* tolerated: vermagic mismatch */\n\t}"),
        ],
        "check_modinfo/vermagic",
    )],
)

# ---- gate 2: modversions CRC (kernel/module/version.c or kernel/module.c) --
patch_file(
    ["kernel/module/version.c", "kernel/module.c"],
    [(
        "int check_version(",
        [
            ("bad_version:\n\tpr_warn(\"%s: disagrees about version of symbol %s\\n\", info->name, symname);\n\treturn 0;",
             "bad_version:\n\tpr_warn(\"%s: CRC mismatch tolerated for %s\\n\", info->name, symname);\n\treturn 1;"),
            # shape used by older trees (pr_debug + return 0)
            ("pr_debug(\"%s: disagrees about version of symbol %s\\n\",\n\t\t\t info->name, symname);",
             "pr_warn(\"%s: CRC mismatch tolerated for %s\\n\", info->name, symname);"),
        ],
        "check_version/modversions",
    )],
)
print("PATCH-OK")
