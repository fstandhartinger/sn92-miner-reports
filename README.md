# sn92-miner-reports
Unlisted feedback reports for SN92 miners, served at https://miner-reports.app.mintapis.com/r/<unguessable slug>/.
Reports are aggregate public-benchmark numbers only. The bundle is encrypted (AES-256-CBC, PBKDF2); the key lives only in the app's
write-only env `REPORTS_KEY` and the publisher's job folder. Clear-text pages are never committed.

## Artifact IDs

`artifacts.manifest.json` describes the report service. Each generated report has a
separate public page ID under `report:sn92-miner-reports`, allocated by the registry
before encryption. Registry summaries describe only the report's existing public
content. Known announcement entries are attached as `board:N` source references.

The host publisher is maintained under
`/home/flori/jobs/sn92-miner-feedback-20261027/code/`. The reviewed copies in
`generator/` must be installed there together: `publish_report.sh` invokes the
sibling `artifact_reports.py` after rendering and before packing. The helper uses
`~/bin/artifact` and its existing local authentication; no registry token enters
this repository, the encrypted bundle, or a report page.

Keep `site/pages/.artifact-ids.json` across report updates: it maps the existing
unlisted slug to its allocated ID. The helper can recover an ID from the page's
`artifact-id` meta tag if that cache is missing. Both the cache and clear-text
pages remain ignored; only the encrypted bundle is committed. Registry failures
stop the publisher before push/deploy. Re-rendering the same slug reuses its ID.

For a local backfill, run the helper on each decrypted page with
`--state pages/.artifact-ids.json`, optionally passing repeatable `--board N`
arguments. Re-encrypt the bundle with the existing publisher key. Keep the
backfill cache when installing the publisher so later renders preserve those IDs.

Run the generator checks with:

```sh
python3 -m unittest discover -s generator/tests -v
bash -n generator/publish_report.sh
```
