# NaviXav 1.4.15

Released on 2026-08-08.

## Fixed

- Commercial licensing and contribution enquiries now use the dedicated NaviXav contact address.
- The automatic update now really installs itself: the helper that waits for NaviXav to close was started without any console and died immediately, so the update was announced as scheduled and the application reopened on the previous version. The helper also keeps its own log next to the installer, so a future failure can be diagnosed.
- Downloaded installers no longer pile up: each update sweeps the previous ones, and the installer does the same once it finishes. Half a gigabyte had accumulated on a machine followed since the first versions. The logs are kept, so a failure can still be examined.

## Changed

- Nettoyage des installateurs telecharges.
- Correctif mise a jour automatique.
- Update NaviXav contact email.

The installer is verified against its SHA-256 checksum before any automatic update.
