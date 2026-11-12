#!/usr/bin/env bash
# Build HeartGold QoL + Hard: hg-engine at a pinned commit, plus our patches.
#
#   tools/build.sh /path/to/heartgold-usa.nds [work-dir]
#
# The ROM must be the US release (game code IPKE,
# SHA-1 4fcded0e2713dc03929845de631d0932ea2b5a37). It is copied into the
# work directory and never into this repository.
set -euo pipefail

HG_ENGINE_URL=https://github.com/BluRosie/hg-engine
HG_ENGINE_COMMIT=dbb321327c59b821507f9fc4cb6c41d45a9d2698
ROM_SHA1=4fcded0e2713dc03929845de631d0932ea2b5a37

rom=${1:?usage: tools/build.sh /path/to/heartgold-usa.nds [work-dir]}
here=$(cd "$(dirname "$0")/.." && pwd)
work=${2:-$here/build}

if [ "$(sha1sum "$rom" | cut -d' ' -f1)" != "$ROM_SHA1" ]; then
    echo "error: $rom is not the US HeartGold ROM this hack is built on" >&2
    exit 1
fi

mkdir -p "$work"
if [ ! -d "$work/hg-engine/.git" ]; then
    git clone --recursive "$HG_ENGINE_URL" "$work/hg-engine"
fi
cd "$work/hg-engine"
git fetch origin "$HG_ENGINE_COMMIT"
git checkout -q --force "$HG_ENGINE_COMMIT"
git submodule update --init --recursive

shopt -s nullglob
patches=("$here"/source-patches/*.patch)
if [ ${#patches[@]} -gt 0 ]; then
    git -c user.name=build -c user.email=build@localhost am "${patches[@]}"
fi

cp "$rom" rom.nds
make -j"$(nproc)"
echo "Built $work/hg-engine/test.nds"
