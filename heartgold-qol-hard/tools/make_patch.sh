#!/usr/bin/env bash
# Make the release patch from a build.
#
#   tools/make_patch.sh /path/to/heartgold-usa.nds /path/to/built/test.nds HeartGold-QoL-Hard-vX.Y.xdelta
#
# Build with tools/build.sh from a fresh work directory first, so that the
# ROM holds exactly the committed patches and no test harness. Needs xdelta3.
# The patch is applied back to the original afterwards to check it.
set -euo pipefail
rom=${1:?usage: tools/make_patch.sh ORIGINAL.nds BUILT.nds OUT.xdelta}
built=${2:?}
out=${3:?}
xdelta3 -e -9 -f -s "$rom" "$built" "$out"
check=$(mktemp)
trap 'rm -f "$check"' EXIT
xdelta3 -d -f -s "$rom" "$out" "$check"
cmp "$built" "$check"
echo "Wrote $out; patched ROM SHA-1 $(sha1sum "$built" | cut -d' ' -f1)"
