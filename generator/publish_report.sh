#!/usr/bin/env bash
# Publish (or update) one miner feedback report as an unlisted page:
#   https://miner-reports.app.mintapis.com/r/<name>-<16 random>/
# Usage: publish_report.sh <REPORT.md> <name>     (name: lowercase a-z0-9-, e.g. uid114-xflud)
# Renders with pandoc, re-packs + encrypts ALL pages (key: <jobdir>/.reports-key), pushes the public repo, redeploys, waits for 200.
set -euo pipefail
JOB=/home/flori/jobs/sn92-miner-feedback-20261027; SITE=$JOB/site; KEY=$JOB/.reports-key
APP=${MINER_REPORTS_APP_UUID:-$(cat $JOB/site/.app-uuid 2>/dev/null || true)}
MD=$(realpath "${1:?report.md}"); NAME=${2:?name}
[[ "$NAME" =~ ^[a-z0-9-]{3,40}$ ]] || { echo "bad name" >&2; exit 1; }
~/bin/author-message-guard "$MD" >/dev/null || { echo "author-message-guard BLOCKED $MD" >&2; exit 2; }
mkdir -p $SITE/pages; touch $SITE/pages/.slugs
SLUG=$(awk -v n="$NAME" '$1==n{print $2}' $SITE/pages/.slugs | tail -1)
[ -n "$SLUG" ] || { SLUG="$NAME-$(head -c 512 /dev/urandom | tr -dc 'a-z0-9' | head -c 16)"; echo "$NAME $SLUG" >> $SITE/pages/.slugs; }
mkdir -p $SITE/pages/$SLUG
TITLE=$(grep -m1 '^# ' "$MD" | sed 's/^# //')
if command -v pandoc >/dev/null; then
  pandoc "$MD" -f gfm -t html5 -s --metadata title="$TITLE" --css style.css -o $SITE/pages/$SLUG/index.html
else  # Sandy has no pandoc: python-markdown fallback, same standalone shape
  python3 - "$MD" "$TITLE" "$SITE/pages/$SLUG/index.html" <<'PY'
import sys,html,markdown
md,title,out=sys.argv[1:4]
body=markdown.markdown(open(md).read(),extensions=["tables","fenced_code","sane_lists"])
open(out,"w").write(f'<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n<title>{html.escape(title)}</title>\n<link rel="stylesheet" href="style.css">\n</head>\n<body>\n{body}\n</body>\n</html>\n')
PY
fi
sed -i 's#<head>#<head>\n<meta name="robots" content="noindex,nofollow">#' $SITE/pages/$SLUG/index.html
# pandoc -s repeats the H1 as title block; drop its header to avoid a duplicate heading
python3 -I - "$SITE/pages/$SLUG/index.html" <<'PY'
import re,sys;p=sys.argv[1];s=open(p).read();s=re.sub(r'<header id="title-block-header">.*?</header>','',s,flags=re.S);open(p,'w').write(s)
PY
python3 "$(dirname "${BASH_SOURCE[0]}")/artifact_reports.py" "$SITE/pages/$SLUG/index.html" --state "$SITE/pages/.artifact-ids.json" || echo "artifact registration skipped (registry unavailable); publishing without an id" >&2
cp $SITE/style.css $SITE/pages/$SLUG/style.css
(cd $SITE/pages && tar --exclude=.slugs --exclude=.artifact-ids.json --exclude=.artifact-ids.json.lock -czf - */) | REPORTS_KEY=$(cat $KEY) openssl enc -aes-256-cbc -pbkdf2 -iter 200000 -salt -pass env:REPORTS_KEY -out $SITE/reports.tar.gz.enc
cd $SITE
git add -A; git -c user.name="miner-reports bot" -c user.email=noreply@mintapis.com commit -qm "publish $NAME" || echo "unchanged"
git push -q origin main
URL="https://miner-reports.app.mintapis.com/r/$SLUG/"
if [ -n "$APP" ]; then
  python3 ~/.agents/skills/explainer-video-webpage/scripts/paas_call.py deploy_application "{\"application_uuid\":\"$APP\",\"confirm\":true,\"force\":true,\"idempotency_key\":\"miner-report-$NAME-$(date +%s)\"}" | head -c 300; echo
  for i in $(seq 1 50); do sleep 10
    if curl -s "$URL" | cmp -s - "$SITE/pages/$SLUG/index.html"; then echo "LIVE: $URL"; exit 0; fi; done
  echo "not live after 10 min ($URL)" >&2; exit 1
fi
echo "PUSHED (no app uuid yet): $URL"
