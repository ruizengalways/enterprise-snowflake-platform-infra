#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "usage: $0 <azurerm|s3> <terraform-root>" >&2
  exit 2
fi

profile="$1"
root="$2"
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source_file="${repo_root}/terraform/backend-profiles/${profile}/backend.tf"
target_file="${repo_root}/${root}/backend.generated.tf"

case "${profile}" in
  azurerm|s3) ;;
  *)
    echo "unsupported Terraform backend profile: ${profile}" >&2
    exit 2
    ;;
esac

if [[ ! -d "${repo_root}/${root}" ]]; then
  echo "Terraform root does not exist: ${root}" >&2
  exit 2
fi

if [[ ! -f "${source_file}" ]]; then
  echo "Backend profile does not exist: ${source_file}" >&2
  exit 2
fi

cp "${source_file}" "${target_file}"
echo "Selected Terraform backend '${profile}' for ${root}."
