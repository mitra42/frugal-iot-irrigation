#!/usr/bin/env zsh
#
# Release frugal-iot-irrigation.
#
#   scripts/release.zsh [2.0.4]              stage 1 - set the version, regenerate, check
#   scripts/release.zsh --publish            stage 2 - push, and tag the release on GitHub
#   scripts/release.zsh --build              stage 3 - build every env for OTA, into ./ota-stage
#   scripts/release.zsh --upload --org dev   stage 4 - upload what stage 3 built to the OTA server
#
# The same syntax as frugal-iot-demo's scripts/release.zsh, which releases the library and the
# server; this one releases only this repository, and adds the two OTA stages, which the demo's
# does not have because an application is what a node actually runs.
#
# The version is the Frugal-IoT library this builds against - the Frugal-IoT@^x.y.z line in
# platformio.ini - and the GitHub release is tagged with it. That is deliberate: the demo's
# release.zsh already renumbers that line at every library release, so the two stay one release
# train rather than this repository growing a second numbering scheme nobody can map back.
#
# Stages 1 and 2 are separated by you reading a diff. Stage 1 never commits and never pushes; it
# leaves the checkout changed and tells you what it changed. Stage 2 never edits anything.
#
# The intended run:
#
#   1. Merge into main whatever is going into this release.
#   2. scripts/release.zsh 2.0.4        - and read what it says. Running it again is always safe.
#   3. Review the diff, and commit.
#   4. scripts/release.zsh --publish    - pushes, and creates the 2.0.4 release on GitHub.
#   5. scripts/release.zsh --build      - builds each env, against the PUBLISHED library.
#   6. scripts/release.zsh --upload --org dev
#
# Options:
#   -q, --quiet      only say what is wrong or what changed.
#   -n, --dry-run    say what would be changed, pushed, built or uploaded, and do none of it.
#       --publish    stage 2. Requires the checkout committed and up to date with origin.
#       --build      stage 3. Builds with ota_build.py --project, which stages each build so that
#                    platformio-local.ini is left out (your local library, your debug flags) and
#                    platformio-secrets-local.ini, if there is one, is kept (the enrolment secret).
#       --lib local  stage 3 only: build against lib/Frugal-IoT instead of the published library.
#       --upload     stage 4. Uploads with ota_upload.py, which refuses a build that has no
#                    enrolment secret, mixes library versions, or came from uncommitted work.
#       --org ORG    stage 4: the organization to publish the firmware under.
#       --no-fetch   trust the origin refs already here rather than fetching (offline)
#       --no-tag     stage 2 only: push, but do not create the GitHub release
#       --release-title "..."   the GitHub release's title; the version if you do not give one
#       -- ...       stages 3 and 4: pass everything after this to ota_build.py / ota_upload.py,
#                    e.g. --upload --org dev -- --skip-unchanged
#   -h, --help       this.
#
# publish, build and upload are also accepted without the dashes.

set -euo pipefail

# ---------------------------------------------------------------- options

VERSION=""
QUIET=0
DRYRUN=0
STAGE=prepare
FETCH=1
TAG=1
RELEASE_TITLE=""
LIBMODE=registry
ORG=""
PASSTHROUGH=()

set_stage() {
  if [[ "$STAGE" != prepare && "$STAGE" != "$1" ]]; then
    print -u2 "Only one of --publish, --build and --upload at a time (already have --${STAGE})"
    exit 2
  fi
  STAGE="$1"
}

while (( $# )); do
  case "$1" in
    -q|--quiet)          QUIET=1 ;;
    -n|--dry-run)        DRYRUN=1 ;;
    --publish|publish)   set_stage publish ;;
    --build|build)       set_stage build ;;
    --upload|upload)     set_stage upload ;;
    --no-fetch)          FETCH=0 ;;
    --no-tag)            TAG=0 ;;
    --lib)               LIBMODE="${2:-}"; shift ;;
    --lib=*)             LIBMODE="${1#*=}" ;;
    --org)               ORG="${2:-}"; shift ;;
    --org=*)             ORG="${1#*=}" ;;
    --release-title)     RELEASE_TITLE="${2:-}"; shift ;;
    --release-title=*)   RELEASE_TITLE="${1#*=}" ;;
    --)                  shift; PASSTHROUGH=("$@"); break ;;
    -h|--help)           awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$0"; exit 0 ;;
    -*)                  print -u2 "Unknown option: $1 (try -h)"; exit 2 ;;
    *)
      if [[ -n "$VERSION" ]]; then
        print -u2 "Only one version can be given (already have ${VERSION}, then got $1)"
        exit 2
      fi
      VERSION="$1"
      ;;
  esac
  shift
done

if [[ -n "$VERSION" && ! "$VERSION" =~ '^[0-9]+\.[0-9]+\.[0-9]+([-+][0-9A-Za-z.-]+)?$' ]]; then
  print -u2 "\"${VERSION}\" is not a version like 2.0.4 - PlatformIO would reject it"
  exit 2
fi
if [[ -n "$VERSION" && "$STAGE" != prepare ]]; then
  print -u2 "A version is only given to stage 1. --${STAGE} uses the one already in platformio.ini."
  exit 2
fi
if [[ "$LIBMODE" != registry && "$LIBMODE" != local ]]; then
  print -u2 "--lib is local or registry, not \"${LIBMODE}\""
  exit 2
fi

# ---------------------------------------------------------------- saying things

say()     { (( QUIET )) || print -r -- "$@" }
heading() { (( QUIET )) || { print; print -r -- "=== $* ===" } }
note()    { print -r -- "$@" }

PROBLEMS=()
problem() { PROBLEMS+=("$1"); print -u2 -r -- "  ! $1" }

WOULD=""
(( DRYRUN )) && WOULD="would "

# ---------------------------------------------------------------- where things are

REPO="${0:A:h:h}"                       # the checkout this script is in
INI="${REPO}/platformio.ini"
OTASTAGE="${REPO}/ota-stage"            # gitignored, and excluded by build_src_filter
SECRETS="${REPO}/platformio-secrets-local.ini"
SCRIPTS="${REPO}/scripts"

# The Frugal-IoT@^x.y.z in platformio.ini, which is this repository's version too
current_version() {
  sed -nE 's/.*Frugal-IoT@\^([^[:space:];]+).*/\1/p' "$INI" | head -1
}

# ---------------------------------------------------------------- git state

check_git_state() {
  heading "Checking the repository is on main and up to date"
  local branch behind ahead
  branch=$(git -C "$REPO" symbolic-ref --short HEAD 2>/dev/null || print "(detached)")
  if [[ "$branch" != "main" ]]; then
    problem "on ${branch}, not main. Nothing has been changed."
    return
  fi
  if (( FETCH )) && ! git -C "$REPO" fetch --quiet origin main 2>/dev/null; then
    problem "could not fetch origin/main - offline? Use --no-fetch to go on with what is here."
    return
  fi
  if ! git -C "$REPO" rev-parse --verify --quiet origin/main >/dev/null; then
    problem "there is no origin/main to compare against."
    return
  fi
  behind=$(git -C "$REPO" rev-list --count HEAD..origin/main)
  ahead=$(git -C "$REPO" rev-list --count origin/main..HEAD)
  if (( behind )); then
    problem "${behind} commit(s) behind origin/main. Pull before releasing, or you will release without them."
  elif (( ahead )); then
    say "  main, ${ahead} commit(s) to push"
  else
    say "  main, up to date"
  fi
}

is_dirty() { [[ -n "$(git -C "$REPO" status --porcelain)" ]] }

# ---------------------------------------------------------------- stage 1

# Same approach as the demo's set_text: via a temporary file and a compare, so a file is left
# byte-for-byte alone when there is nothing to change.
set_version() {
  heading "Setting the version to ${VERSION}"
  if ! grep -Eq 'Frugal-IoT@\^' "$INI"; then
    # A range written some other way (a git url, >=, a bare name) is not something this can
    # renumber, and would otherwise be left at the old version without a word
    problem "platformio.ini has no Frugal-IoT@^<version> lib_deps entry to set - has it been restructured?"
    return
  fi
  local tmp="${INI}.release-tmp"
  sed -E "s|(Frugal-IoT@\\^)[^[:space:];]*|\\1${VERSION}|g" "$INI" > "$tmp"
  if cmp -s "$INI" "$tmp"; then
    rm -f "$tmp"
    say "  already ${VERSION}"
  else
    note "  platformio.ini: ${WOULD}set the Frugal-IoT dependency to ^${VERSION} (was ^$(current_version))"
    if (( DRYRUN )); then rm -f "$tmp"; else mv "$tmp" "$INI"; fi
  fi
}

# Generate platform.h and keywords.txt into a scratch directory, from what is in the checkout now,
# and say which of them differ from the committed ones. This is how --dry-run and --publish check
# them without writing anything. platform.h is the one that matters: it has been left stale twice
# (see CLAUDE.md), and nothing PlatformIO does will ever notice.
stale_generated() {
  local tmp out
  tmp=$(mktemp -d "${TMPDIR:-/tmp}/irrigation-release.XXXXXX")
  cp "$INI" "$tmp/"
  if ! out=$(cd "$tmp" && python3 "$SCRIPTS/generate_platform_h.py" --esp32 --no-readme 2>&1 \
             && python3 "$SCRIPTS/generate_keywords.py" "$REPO" 2>&1); then
    print -u2 -r -- "$out"
    problem "the generators failed"
  else
    cmp -s "$tmp/platform.h" "$REPO/platform.h" || print platform.h
    cmp -s "$tmp/keywords.txt" "$REPO/keywords.txt" 2>/dev/null || print keywords.txt
  fi
  rm -rf "$tmp"
}

regenerate() {
  heading "Regenerating platform.h and keywords.txt"
  if (( DRYRUN )); then
    local stale=(${(f)"$(stale_generated)"})
    if (( ${#stale} )); then
      note "  would update ${(j:, :)stale}"
    else
      say "  both already up to date"
    fi
    return
  fi
  local out
  # platform.h: --esp32 because every board here is an ESP32, so there is no ESP8266 file to
  # write; --no-readme because README.md is hand-written and already says how to build this
  if ! out=$(cd "$REPO" && python3 scripts/generate_platform_h.py --esp32 --no-readme 2>&1); then
    print -u2 -r -- "$out"
    problem "generate_platform_h.py failed"
  else
    say "  ${out//$'\n'/$'\n'  }"
  fi
  # keywords.txt, from this repository's own headers - "." because src_dir = . here
  if ! out=$(cd "$REPO" && python3 scripts/generate_keywords.py . 2>&1); then
    print -u2 -r -- "$out"
    problem "generate_keywords.py failed"
  else
    say "  ${out}"
  fi
}

# ---------------------------------------------------------------- stage 2

tag_release() {
  local v title url
  v=$(current_version)
  title="${RELEASE_TITLE:-$v}"
  heading "Releasing ${v} on GitHub"
  if ! command -v gh >/dev/null; then
    problem "gh is not installed, so ${v} was not tagged. Make it on GitHub under Releases > Draft a new release"
    return
  fi
  # Tagged with the bare version, as mitra42/frugal-iot is - a "v2.0.4" would read as another scheme
  if (cd "$REPO" && gh release view "$v" >/dev/null 2>&1); then
    # Not an error - a second --publish is meant to be safe - but it usually means stage 1 was run
    # without a version, and this release is going out under the last one's number
    note "  ${v} is already released: $(cd "$REPO" && gh release view "$v" --json url --jq .url)"
    note "  if this is meant to be a new release, run stage 1 with the new version first"
    return
  fi
  if (( DRYRUN )); then
    note "  would create release ${v} (\"${title}\")"
    return
  fi
  if ! url=$(cd "$REPO" && gh release create "$v" --title "$title" --generate-notes --target main); then
    problem "could not create release ${v} - make it on GitHub by hand"
  else
    note "  created ${url}"
    [[ -z "$RELEASE_TITLE" ]] && note "  it is titled \"${v}\" - edit it there to say what is in the release"
    git -C "$REPO" fetch --quiet --tags origin || true
  fi
}

do_publish() {
  if is_dirty; then
    problem "there are uncommitted changes - commit them before publishing"
    return
  fi
  heading "Checking the generated files are current"
  local stale=(${(f)"$(stale_generated)"})
  if (( ${#stale} )); then
    problem "${(j: and :)stale} out of date with platformio.ini - run stage 1, review and commit"
    return
  fi
  say "  platform.h and keywords.txt match platformio.ini and the headers"

  heading "Pushing"
  local ahead
  ahead=$(git -C "$REPO" rev-list --count origin/main..HEAD)
  if (( ! ahead )); then
    say "  origin/main already has everything"
  elif (( DRYRUN )); then
    note "  would push ${ahead} commit(s)"
  elif git -C "$REPO" push origin main; then
    note "  pushed ${ahead} commit(s)"
  else
    problem "git push failed"
    return
  fi

  (( TAG )) && tag_release
}

# ---------------------------------------------------------------- stages 3 and 4

do_build() {
  heading "Building every env for OTA, against the ${LIBMODE} library"
  local args=(--project "$REPO" --all --lib "$LIBMODE" --stage "$OTASTAGE")
  if [[ -f "$SECRETS" ]]; then
    say "  with the enrolment secret from ${SECRETS:t}"
    args+=(--secrets "$SECRETS")
  else
    # ota_upload.py refuses these by default, so this is caught before it reaches a node
    note "  no ${SECRETS:t} - these builds will carry no enrolment secret"
  fi
  (( DRYRUN )) && args+=(--list)
  if [[ "$LIBMODE" == registry ]]; then
    say "  Frugal-IoT@^$(current_version) from the PlatformIO registry - it has to be published already"
  fi
  (cd "$REPO" && python3 scripts/ota_build.py "${args[@]}" "${PASSTHROUGH[@]}") \
    || problem "ota_build.py failed"
}

do_upload() {
  if [[ -z "$ORG" && ${PASSTHROUGH[(I)--org*]} -eq 0 && ${PASSTHROUGH[(I)--check]} -eq 0 ]]; then
    problem "--upload needs --org, the organization to publish the firmware under (e.g. --org dev)"
    return
  fi
  heading "Uploading ${OTASTAGE:t} to the OTA server"
  local args=(--stage "$OTASTAGE")
  [[ -n "$ORG" ]] && args+=(--org "$ORG")
  (( DRYRUN )) && args+=(--dry-run)
  (cd "$REPO" && python3 scripts/ota_upload.py "${args[@]}" "${PASSTHROUGH[@]}") \
    || problem "ota_upload.py failed"
}

# ---------------------------------------------------------------- run

if [[ "$STAGE" == prepare || "$STAGE" == publish ]]; then
  check_git_state
  if (( ${#PROBLEMS} )); then
    print -u2
    print -u2 "${#PROBLEMS} problem(s) with the repository - nothing has been changed."
    exit 1
  fi
fi

case "$STAGE" in
  prepare)
    is_dirty && say && say "Already uncommitted, before this run: $(git -C "$REPO" status --porcelain | wc -l | tr -d ' ') file(s)"
    [[ -n "$VERSION" ]] && set_version
    regenerate
    ;;
  publish) do_publish ;;
  build)   do_build ;;
  upload)  do_upload ;;
esac

# ---------------------------------------------------------------- what now

print
if (( ${#PROBLEMS} )); then
  print -u2 "${#PROBLEMS} problem(s):"
  for p in $PROBLEMS; do print -u2 -r -- "  - $p"; done
  exit 1
fi

case "$STAGE" in
  prepare)
    if (( DRYRUN )); then
      print "Dry run: nothing was changed."
    elif is_dirty; then
      print "Nothing wrong. Uncommitted:"
      git -C "$REPO" status --short
      print "Review the diff, commit, then: ${0:t} --publish"
    else
      print "Nothing wrong, and nothing to commit. Next: ${0:t} --publish"
    fi
    ;;
  publish)
    if (( DRYRUN )); then print "Dry run: nothing was pushed or released."
    else print "Published $(current_version). Next: ${0:t} --build"; fi
    ;;
  build)
    (( DRYRUN )) || print "Built. Next: ${0:t} --upload --org <org>   (or --upload -- --check first)"
    ;;
  upload)
    (( DRYRUN )) && print "Dry run: nothing was uploaded."
    ;;
esac
