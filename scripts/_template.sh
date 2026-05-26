#!/usr/bin/env bash
#
# template.sh — Template para scripts nuevos del repo.
#
# Usage:
#   ./template.sh [INPUT] [--flag VALUE]

set -euo pipefail

INPUT=${1:-}
FLAG_VALUE=""

while [ $# -gt 0 ]; do
  case $1 in
    --flag) FLAG_VALUE="$2"; shift 2 ;;
    -*) echo "Unknown flag: $1" >&2; exit 1 ;;
    *) shift ;;
  esac
done

if [ -z "$INPUT" ]; then
  echo "Usage: $0 [INPUT] [--flag VALUE]" >&2
  exit 1
fi

cat <<EOF
================================================================================
SCRIPT NAME
================================================================================
Input: $INPUT
Flag:  ${FLAG_VALUE:-(none)}
Started: $(date -u)
EOF

# Acciones (queries, no destructivas por default)
echo ""
echo "## Sección 1"
# aws ... | jq '...'

echo ""
echo "## Sección 2"
# aws ... | jq '...'

echo ""
echo "================================================================================"
echo "Next steps recomendados:"
echo "  - "
echo "  - "
echo "================================================================================"
