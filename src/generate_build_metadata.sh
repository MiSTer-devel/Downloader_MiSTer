#!/usr/bin/env bash
# Copyright (c) 2021-2026 José Manuel Barroso Galindo <theypsilon@gmail.com>

set -euo pipefail

release_patch="${RELEASE_PATCH:-}"
if [[ -n "${release_patch}" && ! "${release_patch}" =~ ^(0|[1-9][0-9]*)$ ]] ; then
  echo "RELEASE_PATCH must be a canonical non-negative integer." >&2
  exit 1
fi

printf "default_commit = '%s'\n" "$(git rev-parse --short HEAD)"
if [[ -n "${release_patch}" ]] ; then
  printf "default_release_patch = %s\n" "${release_patch}"
else
  printf "default_release_patch = None\n"
fi
