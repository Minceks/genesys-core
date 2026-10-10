# Durable background builds

Accepted `/agent/jobs` requests are committed to SQLite before HTTP 202 is returned.
Production stores `/data/jobs.sqlite3` on the attached Railway volume. Do not delete or detach this volume.
Local development uses `.genesys-data/jobs.sqlite3`; `GENESYS_JOB_DB` overrides the path.
No access tokens are stored. Existing authenticated project ownership checks protect all job reads.

A dispatcher claims persisted jobs, renews leases every five seconds, and executes up to two jobs per process.
A job interrupted by a dead worker becomes eligible for recovery after its 90-second lease expires.
The request ID, original prompt, recent conversation, last stage, and eventual result survive restart.
Recovery reopens the existing Daytona workspace, inspects preserved files and finishes missing work,
then repeats mandatory build/browser verification. It does not resume an interrupted model call byte for byte.
Up to two restart recoveries are allowed; repeated interruptions produce an explicit failure while keeping files.
Completed records are retained for 24 hours and pruned on subsequent submissions.

Run one Gunicorn worker and one Railway replica with this volume. SQLite is not a distributed queue.
Volume availability is required in Railway; startup fails if the mount is missing.
A deleted Daytona sandbox cannot be recovered by the job database alone. Model calls may repeat after interruption,
so recovery can incur additional provider cost. Existing quotas remain process-local.

Frontend saves the active job identifier and reconnects on reopening, focus, or network recovery.
After deployment, restart recovery should be verified with a controlled build and worker restart before broad beta use.
