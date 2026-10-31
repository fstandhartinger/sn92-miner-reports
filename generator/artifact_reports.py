#!/usr/bin/env python3
"""Allocate and embed stable registry IDs before a report is encrypted/published.

The page and ID cache stay outside Git, inside the publisher's ignored pages/.
Only generic information already visible on every report enters the registry.
Registry failure stops publication; reruns reuse the cache or embedded page ID.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess

APP_ID = 'da15a7'
SURFACE = 'report:sn92-miner-reports'
SUMMARY = 'Zeigt einen Feedbackbericht für Miner mit zusammengefassten Benchmark-Ergebnissen. Tabellen und Erläuterungen beschreiben die im Bericht sichtbaren Messungen.'
CSS = '.artifact-report-header{position:relative;padding-top:32px}.aid{position:absolute;right:0;top:5px;font:11px/1.4 monospace;opacity:.55;cursor:pointer;color:inherit;user-select:none}.aid:hover,.aid:focus-visible{opacity:1}.aid-app{top:20px}'
JS = '''document.addEventListener('click',async function(event){const badge=event.target.closest('.aid');if(!badge)return;event.preventDefault();try{await navigator.clipboard.writeText('a#'+badge.dataset.aid);badge.title='Kopiert'}catch{badge.title='Kopieren nicht möglich'}});document.addEventListener('keydown',function(event){if(event.target.matches('.aid')&&['Enter',' '].includes(event.key)){event.preventDefault();event.target.click()}});'''

def cli(*args):
    return subprocess.run([os.environ.get('ARTIFACT_CLI', str(Path.home() / 'bin/artifact')), *args], check=True, text=True, capture_output=True, timeout=30).stdout.strip()

def badge(aid, cls=''):
    return f'<span class="aid {cls}" data-aid="{aid}" tabindex="0" role="button" title="Artefakt-ID – klicken zum Kopieren" aria-label="Artefakt-ID a#{aid} kopieren">a#{aid}</span>'

def register(page, state, board_ids=()):
    page, state = Path(page), Path(state)
    slug = page.parent.name
    if not re.fullmatch(r'[a-z0-9-]{20,}', slug):
        raise ValueError('report path must contain an existing unlisted slug')
    state.parent.mkdir(parents=True, exist_ok=True)
    with open(str(state) + '.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        cache = json.loads(state.read_text()) if state.exists() else {}
        source = page.read_text()
        match = re.search(r'<meta name="artifact-id" content="([a-f0-9]{6})">', source)
        if match and slug in cache and cache[slug] != match.group(1):
            raise ValueError('cached ID conflicts with the embedded report ID')
        aid = cache.get(slug) or (match.group(1) if match else None)
        if not aid:
            aid = cli('new', '--kind', 'page', '--title', 'Miner-Feedbackbericht', '--surface', SURFACE,
                      '--summary', SUMMARY, '--access', 'public', '--parent', APP_ID,
                      '--url', f'https://miner-reports.app.mintapis.com/r/{slug}/',
                      '--selector', '.artifact-report-header',
                      '--ref', 'code=github:fstandhartinger/sn92-miner-reports@HEAD:generator/artifact_reports.py#L1').removeprefix('a#')
        if not re.fullmatch(r'[a-f0-9]{6}', aid):
            raise ValueError('registry did not return an artifact ID')
        cache[slug] = aid
        temp = state.with_suffix('.tmp')
        temp.write_text(json.dumps(cache, indent=2) + '\n')
        os.chmod(temp, 0o600)
        temp.replace(state)
        # Source references make the known announcement discoverable without copying its text.
        for board_id in dict.fromkeys(board_ids):
            if not str(board_id).isdigit(): raise ValueError('board ID must be numeric')
            cli('add-ref', aid, f'board=board:{board_id}', '--label', 'Ankündigung des Berichts')
        if not match:
            source = source.replace('</head>', f'<meta name="artifact-id" content="{aid}"><style>{CSS}</style></head>')
            heading = re.search(r'<h1\b[^>]*>.*?</h1>', source, re.S)
            header = '<header class="artifact-report-header">' + badge(aid) + badge(APP_ID, 'aid-app')
            if heading:
                source = source[:heading.start()] + header + heading.group() + '</header>' + source[heading.end():]
            else:
                source = re.sub(r'(<body\b[^>]*>)', r'\1' + header + '</header>', source, count=1)
            source = source.replace('</body>', '<script>' + JS + '</script></body>')
            page.write_text(source)
        return aid

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('page', type=Path)
    parser.add_argument('--state', required=True, type=Path)
    parser.add_argument('--board', action='append', default=[])
    args = parser.parse_args()
    print('a#' + register(args.page, args.state, args.board))

if __name__ == '__main__':
    main()
