# Beta reliability

- Generated simple apps use `src/usePersistentState.js` for ordinary device-local data.
  This is not cross-device sync. Shared data still needs an application database.
- Project preview hostnames remain stable while the preview proxy key remains unchanged.
  Only verified build snapshots are published on port 4174; edits run and are tested on 4173.
  Failed edits leave the published snapshot intact. Restore backs up edits in a Git stash.
- Content checks enforce explicit literal headings/subtitles and detect duplicates.
  Recognized book-list forms are checked for add, refresh persistence and remove behavior.
  Other interactive flows are not comprehensively verified by these checks.
- Defaults: 5 builds/hour, 20 builds/day, 10-second cooldown, one active build per account.
  Set `GENESYS_BUILDS_PER_HOUR`, `GENESYS_BUILDS_PER_DAY` and
  `GENESYS_BUILD_COOLDOWN_SECONDS` to adjust them. Chat does not consume build quota.
  Limit counters are replica-local and reset on restart; distributed/durable enforcement
  requires a shared quota store before scaling to multiple backend replicas.
- Account names are saved in Supabase user metadata; reset email and sign-out remain available.
