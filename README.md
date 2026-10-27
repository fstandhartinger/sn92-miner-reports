# sn92-miner-reports
Unlisted feedback reports for SN92 miners, served at https://miner-reports.app.mintapis.com/r/<unguessable slug>/.
Reports are aggregate public-benchmark numbers only. The bundle is encrypted (AES-256-CBC, PBKDF2); the key lives only in the app's
write-only env `REPORTS_KEY` and the publisher's job folder. Clear-text pages are never committed.
