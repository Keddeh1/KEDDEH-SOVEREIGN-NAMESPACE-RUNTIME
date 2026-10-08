# BRAINK Media Console — separate reusable branch

This package extends the existing BRAINK runtime; it does not replace its agent engine. It includes a media control surface, Node SDK, official MCP stdio server, native processing worker, deployment definitions, market evidence and execution evidence.

Status: development candidate. Local processing and browser flows have been verified. Production deployment, Google consent, live YouTube uploads and speech transcription are not yet qualified. See research/unresolved.json.

## Run and reuse

Node 22 or newer: `npm ci`, then `npm test`. Import `BrainkMediaClient` from `sdk/index.mjs`. Set `BRAINK_MEDIA_ENDPOINT` to the owner-only host endpoint and supply `BRAINK_MEDIA_AGENT_TOKEN` privately. Run `npm run mcp` for the MCP stdio interface. Tools expose status, library, scripts, processing and queued-job cancellation. Public posting is reviewed in the owner release surface.

For native processing use Linux, FFmpeg with libx264, AAC, MP3 and Flite support, Python 3.12 and `linux/requirements.txt`. The tested Python dependency resolution is in `linux/python-lock.txt`. `deployment/compose.yaml` provides a worker container and persistent state. Build the container and qualify its actual FFmpeg configuration before deployment; its Debian packages may differ from the locally measured build. Mount a private JSON configuration with `agentToken`, `python` and optional `modelPath`; never commit credentials. A systemd definition is also supplied. Neither definition is evidence of an installed permanent service.

## Integrate existing BRAINK

Apply the append-only D1 migrations through the existing runtime deployment pipeline, export `media-schema.ts` from the database schema and mount the route adapters under `app/api/media`. Copy `runtime/media-service.mjs` into the existing runtime's `lib/`. Route governance calls to the existing `cloudAgentDispatch`, capability `skill://engineering/translation-ledger`. Preserve owner authentication, D1 and R2 bindings. Route files retain existing runtime imports and require that runtime rather than operating independently.

The existing cinematic frontage mounts `console/media-sector.mjs` at `/sector` and the script and stylesheet at `/media/studio.js` and `/media/studio.css`. The owner-only website proxy retains the existing website bridge credential. The downloadable delivery archive also includes full source changes in `integrations/frontage.patch` and `integrations/runtime.patch`; those archive-only patches are not stored in this module branch. base commit identities are recorded in research/source-custody.json. Do not apply a patch blindly to a different base.

## Owner workflow

Sign in, upload a source, select it, set in/out points and save an edit revision. Render a browser export or queue native shorts, long video or mastered podcasts. Write narration and on-screen copy at the production desk. Queue synthetic voice-over after reviewing the script. Freeze a decoded video frame, change its brightness and caption, save it as PNG and queue an animation. Screen recording prompts for a selected source and saves actual recorded bytes when stopped; source audio depends on browser support. Keyboard controls and reduced motion are supported.

Connect Google OAuth using the configured client and exact callback `https://www.keddeh.com/api/media/oauth/callback`. A Google/YouTube account and channel must already exist; this package does not create Google accounts. Review visibility, publication time, rights and children's-content settings before queueing a release. YouTube observations determine completion; BRAINK execution receipts record governance separately.

## Lifecycle and limits

Atomic job claims prevent overlapping workers. Errors are saved. Expired leases become `needs-reconciliation`, never fabricated completion. Ambiguous provider uploads require inspection rather than duplicate retries. Processing profiles create actual files and probe durations. Scene cuts are editorial candidates, not semantic quality or audience-growth predictions. Comment review retrieves actual threads and produces clearly labelled drafts; no customer reply is posted.

## Attribution and rights

Keddeh-authored additions retain reserved rights pending owner licence designation. Third-party code and models retain their own licences. FFmpeg's effective licence depends on build flags; the measured binary enables GPL components. No upstream ownership transfer is claimed. Market evidence distinguishes open-source projects from source-available or commercial services. Formal Keddeh publication layout is pending access to the mandated template; the research here is a working evidence package, not an approved formal publication.
