#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
pdflatex -interaction=errorstopmode -halt-on-error -file-line-error enonce.tex || true
awk '/^!/{flag=1} flag{print}' enonce.log | head -n 120
