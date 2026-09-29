#!/usr/bin/env python3
"""
Step 1: what is the fleet running, and what can we build for it?

  ./ota_keys.py --org dev > ota_keys.tsv
  ./ota_keys.py --org dev --all-keys -o ota_keys.tsv

Writes a TSV, one row per node, for you to edit: set the "build" column to n for anything you do
not want rebuilt, then feed the file to ota_build.py --manifest.

WHERE THE OTA KEY COMES FROM
────────────────────────────
Not from the `nodes` SQL table. GET /nodes_list/:org reads that, and it has project, nodeid, lora
and enrolled_at - no OTA key at all. The key is a live retained MQTT value, which reaches us via
GET /config.json as nodes[<id>]["ota/key"]; that is also what the dashboard's Nodes table shows.

This matters because it is the key the node ITSELF holds, and therefore the one it will ask for.
A key we think it ought to have is no use.

Both endpoints are joined here, because they answer different questions: /config.json says what
is running, /nodes_list says what an admin has decided (enrolled / approved / denied / failed).
"""

import argparse
import collections
import fnmatch
import getpass
import http.cookiejar
import json
import os
import ssl
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_SERVER = "https://frugaliot.naturalinnovation.org"

Entry = collections.namedtuple("Entry", "example env prefix suffix")

# ota_keymap.py lives with the library, because it describes the library's own examples. It is
# run as a SUBPROCESS rather than imported, because it needs PlatformIO's python (for
# ProjectConfig) and this script does not - and should not be forced into it. PlatformIO's
# interpreter ships without a usable CA bundle, so every HTTPS call from it fails with
# CERTIFICATE_VERIFY_FAILED. Keeping the two apart lets each run where it works.
# An application (frugal-iot-irrigation) carries a copy of these scripts side by side, and may
# have no lib/Frugal-IoT at all - so a sibling ota_keymap.py is used when that one is not there.
KEYMAP_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             os.pardir, "lib", "Frugal-IoT", "scripts", "ota_keymap.py")
if not os.path.exists(KEYMAP_SCRIPT):
    KEYMAP_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ota_keymap.py")


def load_keymap():
    """Ask ota_keymap.py for the map. It re-execs itself into PlatformIO's python as needed."""
    result = subprocess.run([sys.executable, KEYMAP_SCRIPT, "--json"],
                            capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f"Could not read the example map:\n{result.stderr.strip()}")
    data = json.loads(result.stdout)
    return ({k: Entry(*v) for k, v in data["keymap"].items()}, data["problems"])


def ssl_context():
    """A context with a CA bundle that actually exists.

    Python on macOS does not use the system keychain, so an interpreter installed without
    certificates fails every HTTPS request with "unable to get local issuer certificate". certifi
    ships the bundle; use it when it is there, and otherwise trust the default (which is correct
    for Homebrew and python.org builds that ran Install Certificates.command).
    """
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()

COLUMNS = ["build", "otakey", "target_node", "example", "env", "project", "nodeid", "name",
           "lastseen", "state", "note"]


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Stop urllib following redirects, so we can read the Location ourselves.

    POST /login answers 302 on success AND on a wrong password - success goes to the url we asked
    for, failure to the login page with messagetype=error. A "did it 302?" test passes on a bad
    password, so the Location is the only thing that actually distinguishes them.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def make_opener(jar):
    return urllib.request.build_opener(
        urllib.request.HTTPSHandler(context=ssl_context()),
        urllib.request.HTTPCookieProcessor(jar), NoRedirect())


def fetch(opener, url, data=None):
    """GET, or POST when data is given. Returns (status, body, location)."""
    encoded = urllib.parse.urlencode(data).encode() if data else None
    request = urllib.request.Request(url, data=encoded)
    try:
        response = opener.open(request)
        status, body = response.status, response.read().decode("utf-8", "replace")
        location = response.headers.get("Location")
    except urllib.error.HTTPError as err:
        status, body = err.code, err.read().decode("utf-8", "replace")
        location = err.headers.get("Location")
    return status, body, location


def jar_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), ".ota-cookies")


def load_session(server):
    """Reuse a cached session if it is still good, so two tools do not each prompt."""
    jar = http.cookiejar.MozillaCookieJar(jar_path())
    opener = make_opener(jar)
    live = False
    if os.path.exists(jar_path()):
        try:
            jar.load(ignore_discard=True)
            status, _, _ = fetch(opener, f"{server}/config.json")
            live = (status == 200)
        except (OSError, http.cookiejar.LoadError):
            live = False
    return jar, opener, live


def login(server, jar, opener, user):
    """Log in per D9: the password is prompted for, never taken from the command line.

    A password in argv shows up in shell history and in `ps` output for anyone on the machine.
    FRUGAL_IOT_PASSWORD stays available for unattended runs, where there is nobody to prompt.
    """
    if not user:
        user = input("Username: ").strip()
    password = os.environ.get("FRUGAL_IOT_PASSWORD")
    if not password:
        password = getpass.getpass(f"Password for {user}: ")

    status, _, location = fetch(opener, f"{server}/login",
                                {"username": user, "password": password, "url": "/dashboard"})
    ok = bool(location) and "/dashboard" in location and "messagetype=error" not in location
    if ok:
        jar.save(ignore_discard=True)
        os.chmod(jar_path(), 0o600)  # a session cookie is a credential
    else:
        sys.exit(f"Login failed (status {status}, redirected to {location or 'nowhere'}).")


def get_json(opener, url, what):
    status, body, _ = fetch(opener, url)
    if status != 200:
        sys.exit(f"GET {url} returned {status} - could not read {what}")
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        sys.exit(f"GET {url} did not return JSON - is the server URL right?")


def read_aliases(path):
    """Renamed keys: nodes still ask for the old one, so the new binary is published under both.

        sht30_*              sht_*           # a PREFIX changed (the example was renamed)
        *_ttgo-t-beam-oled   *_tbeam_oled    # a SUFFIX changed (the env was renamed)
        agri_s2_mini_2       agri_s2_mini    # one exact key

    Three shapes rather than general globs, because a rename is always one of these three, and a
    general pattern would need a general substitution language to go with it.
    """
    rules = []
    if path and os.path.exists(path):
        with open(path) as handle:
            for line in handle:
                line = line.split("#")[0].strip()
                if line:
                    fields = line.split()
                    if len(fields) >= 2:
                        rules.append((fields[0], fields[1]))
    return rules


def apply_aliases(otakey, rules, keymap):
    """Return (built_key, note) - the key whose binary this node should be given.

    FIRST MATCH WINS, which is what makes ordering in the file the way one rule beats another: a
    specific rule goes above the general one it is an exception to.

    A rule that matches but names something no example builds is reported rather than passed over
    in silence. These are consulted before the keymap, so a typo in a rule would otherwise look
    exactly like the rule not being there at all - the node would go on being built from the key
    it already reports, which is the thing the rule was written to stop.
    """
    built, note = None, ""
    for published_glob, built_glob in rules:
        if built is None and fnmatch.fnmatch(otakey, published_glob):
            if published_glob.endswith("*") and built_glob.endswith("*"):
                # prefix rename: keep everything the glob's "*" matched
                candidate = built_glob[:-1] + otakey[len(published_glob) - 1:]
            elif published_glob.startswith("*") and built_glob.startswith("*"):
                # suffix rename: keep everything before the fixed tail
                kept = otakey[:len(otakey) - (len(published_glob) - 1)]
                candidate = kept + built_glob[1:]
            else:
                candidate = built_glob
            if candidate in keymap:
                built, note = candidate, f"alias -> {candidate}"
            elif not note:
                # Deliberately not starting "alias ->": that prefix is how main() counts nodes
                # waiting to migrate, and this is a rule that will never resolve however long you
                # wait for it. Counting it there would say "once they take the update" about an
                # update nothing is building.
                note = f"rule names {candidate}, which no example builds"
    return built, note


def nodes_from_config(config, org):
    """Flatten /config.json into (project, nodeid, fields) triples."""
    organizations = config.get("organizations", {})
    projects = (organizations.get(org) or {}).get("projects", {}) or {}
    for project, details in sorted(projects.items()):
        for nodeid, fields in sorted((details.get("nodes") or {}).items()):
            if isinstance(fields, dict):
                yield project, nodeid, fields


def main():
    parser = argparse.ArgumentParser(description="Build the OTA key table for one organization.")
    parser.add_argument("--org", required=True, help="organization, e.g. dev")
    parser.add_argument("--server", default=DEFAULT_SERVER)
    parser.add_argument("--user", help="login name (not secret; the password is prompted for)")
    parser.add_argument("--aliases", default=os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "ota_aliases.tsv"))
    parser.add_argument("--all-keys", action="store_true",
                        help="also list buildable keys that no node is running, at build=n")
    parser.add_argument("-o", "--output", help="write here instead of stdout")
    args = parser.parse_args()

    keymap, problems = load_keymap()
    rules = read_aliases(args.aliases)

    jar, opener, live = load_session(args.server)
    if not live:
        login(args.server, jar, opener, args.user)

    config = get_json(opener, f"{args.server}/config.json", "the node list")
    nodes_list = get_json(opener, f"{args.server}/nodes_list/{args.org}", "enrolment states")
    ota_list = get_json(opener, f"{args.server}/ota_list/{args.org}", "existing OTA files")

    states = {row.get("nodeid"): row.get("state", "") for row in nodes_list}

    rows = []
    seen_keys = set()
    for project, nodeid, fields in nodes_from_config(config, args.org):
        otakey = fields.get("ota/key") or ""
        state = states.get(nodeid, "")
        build, example, env, note, target = "n", "-", "-", "", "-"

        if not otakey:
            note = "node reports no ota/key - pin firmware to the node id instead"
            target = nodeid
        else:
            seen_keys.add(otakey)
            # The alias file is consulted BEFORE the keymap. A line in it is a deliberate
            # instruction; the keymap is only what the key would mean if nobody had said otherwise.
            # The key a node is being moved off is normally still perfectly buildable - that is the
            # usual case and not an exception - so looking the keymap up first would quietly ignore
            # the line that says to move it, which is how it behaved until 2026-09-29.
            built, note = apply_aliases(otakey, rules, keymap)
            entry = keymap[built] if built else keymap.get(otakey)
            if entry is None:
                note = note or "no such key in examples/, and no alias"
            else:
                build, example, env = "y", entry.example, entry.env

        rows.append({
            "build": build, "otakey": otakey or "-", "target_node": target,
            "example": example, "env": env, "project": project, "nodeid": nodeid,
            "name": fields.get("frugal_iot/name", ""),
            "lastseen": fields.get("lastseen", ""), "state": state, "note": note,
        })

    if args.all_keys:
        for otakey in sorted(set(keymap) - seen_keys):
            entry = keymap[otakey]
            rows.append({
                "build": "n", "otakey": otakey, "target_node": "-", "example": entry.example,
                "env": entry.env, "project": "-", "nodeid": "-", "name": "", "lastseen": "",
                "state": "", "note": "buildable, but no node is running it",
            })

    handle = open(args.output, "w") if args.output else sys.stdout
    try:
        handle.write("\t".join(COLUMNS) + "\n")
        for row in rows:
            handle.write("\t".join(str(row[c]) for c in COLUMNS) + "\n")
    finally:
        if args.output:
            handle.close()

    # Everything below is commentary, so it goes to stderr and stays out of the TSV.
    buildable = sum(1 for r in rows if r["build"] == "y")
    print(f"{len(rows)} row(s), {buildable} marked build=y", file=sys.stderr)

    # Orphans: on the server, but nothing runs them and nothing builds them. Reported, never
    # deleted - /ota_delete exists, but a wrong guess here strands a board.
    published = {path.split("/")[-1] for path in ota_list if isinstance(path, str)}
    orphans = sorted(published - seen_keys - set(keymap))
    if orphans:
        print(f"{len(orphans)} orphaned OTA file(s) on the server "
              f"(no node runs them, no example builds them):", file=sys.stderr)
        for orphan in orphans:
            print(f"  {orphan}", file=sys.stderr)

    stale = sorted(r["otakey"] for r in rows if r["note"].startswith("alias"))
    if stale:
        print(f"{len(stale)} node(s) still on a renamed key. Once they take the update they "
              f"report the new one, and the alias line can be deleted.", file=sys.stderr)
    if problems:
        print(f"{len(problems)} keymap lint problem(s) - to list them:\n"
              f"  {os.path.relpath(KEYMAP_SCRIPT)} --problems", file=sys.stderr)


if __name__ == "__main__":
    main()
