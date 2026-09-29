#!/usr/bin/env python3
"""
Step 3: publish a built staging tree to the server.

  ./ota_upload.py --check                 # is the staging tree fit to upload?
  ./ota_upload.py --org dev --dry-run
  ./ota_upload.py --org dev
  ./ota_upload.py --org dev --skip-unchanged

Walks <stage>/firmware/*/ and POSTs each firmware.bin to /ota_update, reading that directory's
build.json to decide where it goes:

  target=key   ->  <org>/<project|+>/<otakey>/firmware.bin
  target=node  ->  <org>/<project|+>/<nodeid>/firmware.bin

The server looks for [project, node], ['+', node], [project, attribs], ['+', attribs] in that
order, so a node-pinned binary outranks the key its node reports - which is the whole point of
pinning - and '+' is the broadest match, which is what a fleet-wide push wants.

WHAT THIS REFUSES TO UPLOAD, and why it is worth the fuss
─────────────────────────────────────────────────────────
A staging tree can look perfectly healthy and still be wrong in ways that only show up on a node
in a field. Three of those are cheap to detect here, so they are:

  * enrol_secret false   - built without --secrets. The binary is indistinguishable from a good
                           one, works fine on an enrolled node, and cannot re-enrol after a
                           factory reset.
  * mixed lib_fingerprint - some binaries predate a fix that others include, which is exactly
                           what --skip-built leaves behind. Fine while iterating, not fine to
                           ship as a set.
  * lib_git_sha "-dirty" - built from uncommitted work, so it cannot be reproduced later. The
                           same for project_git_sha, on an application built with --project.

--force overrides all three, deliberately in one flag, because each of them is a decision rather
than a mistake to be waved through by habit.
"""

import argparse
import collections
import glob
import hashlib
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid

# Login, cookie jar and the SSL context all live in ota_keys.py - same directory, same session.
# Sharing the jar is what stops the two tools each prompting during one round of work.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ota_keys import DEFAULT_SERVER, load_session, login  # noqa: E402


def multipart(fields, filedata, filename="firmware.bin"):
    """Encode a multipart body, PRESERVING FIELD ORDER.

    Order is load-bearing, not cosmetic. multer fills req.body only from the parts that arrive
    BEFORE the file, and the server checks the OTAUPDATE permission and builds the destination
    directory while the file is being stored - so a field sent after the file is simply not there
    yet, and the upload is rejected as a permission problem.
    """
    boundary = "----frugaliot" + uuid.uuid4().hex
    out = []
    for name, value in fields:
        out.append(f"--{boundary}\r\n".encode())
        out.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        out.append(f"{value}\r\n".encode())
    out.append(f"--{boundary}\r\n".encode())
    out.append(
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode())
    out.append(b"Content-Type: application/octet-stream\r\n\r\n")
    out.append(filedata)
    out.append(f"\r\n--{boundary}--\r\n".encode())
    return boundary, b"".join(out)


def post_firmware(opener, server, org, project, name, data):
    """One upload. Returns (ok, detail)."""
    fields = [
        ("url", "/dashboard/"),
        ("lang", "EN"),
        ("organization", org),
        ("project", project),
        ("otakey", name),          # the server uses this for a node id too
    ]
    boundary, body = multipart(fields, data)
    request = urllib.request.Request(f"{server}/ota_update", data=body)
    request.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    try:
        response = opener.open(request)
        status, location = response.status, response.headers.get("Location")
        text = response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as err:
        status, location = err.code, err.headers.get("Location")
        text = err.read().decode("utf-8", "replace")
    # Success is a redirect carrying the server's own confirmation message.
    if location and "OTA%20binary%20uploaded" in location.replace("+", "%20"):
        return True, ""
    return False, f"status {status}, location {location or '-'}, body {text[:200]}"


def remote_md5(opener, server, org, project, name):
    """md5 of what is already published there, or None.

    Reads the body as BYTES. ota_keys.fetch() decodes utf-8 with errors="replace", which is right
    for JSON and destroys a firmware image - every invalid sequence becomes U+FFFD, so the md5
    would never match and every binary would look changed.
    """
    path = "/".join(urllib.parse.quote(p, safe="") for p in (org, project, name))
    digest = None
    try:
        response = opener.open(urllib.request.Request(f"{server}/ota_get/{path}"))
        if response.status == 200:
            digest = hashlib.md5(response.read()).hexdigest()
    except urllib.error.HTTPError:
        digest = None       # not published yet - upload it
    return digest


def load_staged(stage):
    """Every directory under <stage>/firmware that has both a binary and its build.json."""
    items, broken = [], []
    for record_path in sorted(glob.glob(os.path.join(stage, "firmware", "*", "build.json"))):
        directory = os.path.dirname(record_path)
        binary = os.path.join(directory, "firmware.bin")
        if not os.path.exists(binary):
            broken.append(f"{os.path.basename(directory)}: build.json but no firmware.bin")
        else:
            try:
                record = json.load(open(record_path))
            except ValueError as err:
                broken.append(f"{os.path.basename(directory)}: unreadable build.json ({err})")
                continue
            items.append((os.path.basename(directory), binary, record))
    return items, broken


def main():
    parser = argparse.ArgumentParser(description="Publish a built staging tree to the server.")
    parser.add_argument("--org", help="organization, e.g. dev (not needed with --check)")
    parser.add_argument("--server", default=DEFAULT_SERVER)
    parser.add_argument("--user", help="login name (not secret; the password is prompted for)")
    parser.add_argument("--stage", default=os.path.join(os.getcwd(), "ota-stage"))
    parser.add_argument("--project", default="+",
                        help="project to publish under; '+' (default) means every project")
    parser.add_argument("--dry-run", action="store_true",
                        help="say what would be sent, send nothing, and do not log in")
    parser.add_argument("--skip-unchanged", action="store_true",
                        help="download what is published and skip anything already identical")
    parser.add_argument("--check", action="store_true",
                        help="report what is staged and whether it is internally consistent, "
                             "then exit. Touches nothing and does not log in.")
    parser.add_argument("--force", action="store_true",
                        help="upload despite the safety checks - see the module docstring")
    args = parser.parse_args()
    args.stage = os.path.abspath(args.stage)
    if not args.check and not args.org:
        parser.error("--org is required (except with --check, which is purely local)")

    items, broken = load_staged(args.stage)
    if broken:
        print("Staging tree has problems:", file=sys.stderr)
        for problem in broken:
            print(f"  {problem}", file=sys.stderr)
    if not items:
        sys.exit(f"Nothing to upload under {os.path.join(args.stage, 'firmware')}")

    # ---- the three safety checks ----
    complaints = []
    no_secret = [n for n, _, r in items if not r.get("enrol_secret", False)]
    if no_secret:
        complaints.append(f"{len(no_secret)} built WITHOUT an enrolment secret: "
                          f"{', '.join(no_secret[:6])}{' ...' if len(no_secret) > 6 else ''}")
    fingerprints = {r.get("lib_fingerprint", "unknown") for _, _, r in items}
    if len(fingerprints) > 1:
        complaints.append(f"{len(fingerprints)} different library fingerprints in one tree "
                          f"({', '.join(sorted(fingerprints))}) - some binaries predate a fix. "
                          f"Re-run ota_build.py without --skip-built.")
    # project_git_sha is only there for an ota_build.py --project build - an application in its
    # own repository, whose own uncommitted work matters as much as the library's.
    dirty = [n for n, _, r in items
             if str(r.get("lib_git_sha", "")).endswith("-dirty")
             or str(r.get("project_git_sha", "")).endswith("-dirty")]
    if dirty:
        complaints.append(f"{len(dirty)} built from an uncommitted tree: "
                          f"{', '.join(dirty[:6])}{' ...' if len(dirty) > 6 else ''}")

    if args.check:
        summary = collections.Counter(
            (r.get("lib_fingerprint", "?"), r.get("lib_git_sha", "?"),
             r.get("lib_mode", "?"), bool(r.get("enrol_secret", False)))
            for _, _, r in items)
        print(f"{len(items)} binary/binaries under {os.path.join(args.stage, 'firmware')}")
        for (fingerprint, sha, mode, secret), count in sorted(summary.items()):
            print(f"  {count:3} x  fingerprint {fingerprint}  sha {sha}  "
                  f"{mode}  enrol_secret={secret}")
        keys = sum(1 for _, _, r in items if r.get("target", "key") == "key")
        print(f"  {keys} published by OTA key, {len(items) - keys} pinned to a node")

    if complaints:
        if args.check:
            heading = "NOT consistent:"
        elif args.force:
            heading = "Uploading anyway (--force):"
        else:
            heading = "Refusing to upload:"
        # In --check this is a report, not an error, and mixing the two streams reorders it.
        stream = sys.stdout if args.check else sys.stderr
        print(heading, file=stream)
        for complaint in complaints:
            print(f"  {complaint}", file=stream)
        if not args.force:
            sys.exit(1)
    elif args.check:
        print("  consistent - one library, all with an enrolment secret, none dirty")

    if args.check:
        sys.exit(0)

    record = items[0][2]
    print(f"{len(items)} binary/binaries from library {record.get('lib_git_sha')} "
          f"({record.get('lib_mode')}), publishing to {args.org}/{args.project}/")

    opener = None
    if not args.dry_run:
        jar, opener, live = load_session(args.server)
        if not live:
            login(args.server, jar, opener, args.user)

    sent = skipped = failed = 0
    for name, binary, record in items:
        data = open(binary, "rb").read()
        kind = record.get("target", "key")
        label = f"node:{name}" if kind == "node" else name

        if args.dry_run:
            print(f"  would send {label:38} {len(data):>9,} bytes  "
                  f"md5 {record.get('md5','?')[:12]}")
            sent += 1
        else:
            if args.skip_unchanged and remote_md5(opener, args.server, args.org,
                                                  args.project, name) == record.get("md5"):
                print(f"  unchanged  {label:38} skipped")
                skipped += 1
                continue
            ok, detail = post_firmware(opener, args.server, args.org, args.project, name, data)
            if ok:
                print(f"  uploaded   {label:38} {len(data):>9,} bytes")
                sent += 1
            else:
                print(f"  FAILED     {label:38} {detail}", file=sys.stderr)
                failed += 1

    verb = "would upload" if args.dry_run else "uploaded"
    print(f"\n{verb} {sent}, skipped {skipped}, failed {failed}")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
