# Persistent VFS native launch policy

The native owner launcher previously applied a 64 MiB `RLIMIT_FSIZE` to every
process file. This also bounded the aggregate SQLite database and WAL used by
`vfs_server.server`. An observed production WAL reached exactly 67,108,864 bytes;
subscription writes returned HTTP 500 without advancing their cursors.

An isolated replay using the existing native guard and unchanged VFS source
held a SQLite read transaction while acknowledging subscriptions. After 16,288
writes, `COMMIT` raised `SQLITE_IOERR_WRITE` (778) at exactly the same WAL size.
The filesystem had 17.9 GB available. This distinguishes the process file limit
from filesystem exhaustion. The production HTTP handler suppresses exception
detail; the isolated replay supplies the attributable exception evidence.

The launcher now assigns an explicit `persistent-vfs` file policy only to the
exact native command `[sys.executable, '-m', 'vfs_server.server', ...]`. That
command retains its inherited file-size limits. It retains `CORE=0` and
`NOFILE=256`. Other commands keep the existing bounded-file policy. There is no
environment override or general command exemption. The VFS source is unchanged:
its 64 MiB individual artifact contract still rejects oversized artifacts.

Three policy tests and eleven existing controller tests pass. Qualification in
the new immutable image launched the real native HTTP VFS through the updated
wrapper. A pinned read transaction retained a WAL above 64 MiB while 2,231 real
artifact writes, a verified subscription acknowledgement and artifact SHA-256
readback succeeded. The native oversized artifact rejection also passed.

The resident controller image changed from version 0.3.2 to 0.3.3. Comparing all
installed Python/JavaScript package source files found only `_web4_exec.py`
changed. The controller's read-only root required a controlled replacement of
one family container rather than a live package overwrite. The old container
and image were retained for rollback; mounted state and launch configuration
were retained. All sixteen owned child services returned alive, ten workstations
returned healthy and boot returned completed after 12.17 seconds. The other
thirty-five owner containers retained their original process IDs.

The new live VFS retains inherited unlimited file-size limits on this host.
Finite limits inherited on another host remain finite. Filesystem capacity and
SQLite persistence behavior still apply. This qualification covers the actual
current host; it does not claim physical host-loss or off-site recovery.

Safe qualification, deployment and live readback records are in `docs/evidence/`
under `persistent-vfs-*`. Private container configuration, credentials and state
snapshots are excluded from repository evidence.
