#!/bin/bash
# Polite downloader: fetch.sh <urls.txt> <outdir>
# Saves each URL as <outdir>/<last-path-segment>.html, skips files already present, waits 1.5 s between requests.
mkdir -p "$2"
while read -r u; do
  [ -z "$u" ] && continue
  u="${u%%#*}"
  slug=$(basename "${u%/}")
  [ -s "$2/$slug.html" ] && continue
  curl -sL -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36" \
       -o "$2/$slug.html" -w "$slug %{http_code} %{size_download}\n" "$u"
  sleep 1.5
done < "$1"
echo DONE
