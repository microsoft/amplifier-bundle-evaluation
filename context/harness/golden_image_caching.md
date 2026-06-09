# Golden Image Caching for DTU Harnesses

Heavyweight DTU profiles (Docker-in-Incus, full package installs, building a
container image) can a while to provision, and a profile that runs
`docker build` from Docker Hub will hit anonymous pull rate limits (HTTP 429)
when launched many times. When you run the same profile over and over (a sweep
of tasks against one environment), bake the provisioning once into a reusable
local Incus image and relaunch from it cheaply.

This is a convention, not a built-in harness stage. The harness already supports
it: the DTU engine passes `base.image: local:<alias>` straight through to
`incus launch`, so a profile pointing at a baked image just works. The only new
pieces are an `incus publish` to create the image and a second profile to reuse
it.

## The two-profile pattern

Author two profiles per environment:

- `<name>-bake.yaml` — your full provisioning. Built once.
- `<name>-task.yaml` — `base.image: local:<name>`, provisioning reduced to
  restarting services. Launched per task.

```yaml
# <name>-task.yaml — slim relaunch from the baked image
base:
  image: local:nanoclaw-golden       # the published alias, not ubuntu:24.04
  config:
    security.nesting: "true"
provision:
  setup_cmds:
    - dockerd > /var/log/dockerd.log 2>&1 &   # start daemons, do not reinstall
    # ... remount any tmpfs, restart your service, etc.
```

Everything on disk in the bake (installed packages, built Docker images, a
cloned repo) is captured by the publish. Only volatile runtime state (daemons,
tmpfs mounts, sockets) must be re-established in the task profile.

## Baking the image

`DTU.launch` only takes a profile path, so baking is a short shell-out to
`incus` around a normal launch. Bake on first run, reuse forever:

```python
import asyncio
from amplifier_evaluation.harness.dtu import DTU

async def ensure_golden_image(bake_profile: str, alias: str,
                              variables: dict[str, str] | None = None) -> None:
    # Idempotent: skip if the image already exists.
    exists = await asyncio.create_subprocess_exec(
        "incus", "image", "info", alias,
        stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
    )
    if await exists.wait() == 0:
        return

    build = f"{alias}-build"
    dtu = await DTU.launch(bake_profile, name=build, variables=variables,
                           launch_timeout_s=1800)
    try:
        await _run("incus", "stop", dtu.id)
        await _run("incus", "publish", dtu.id, "--alias", alias)
    finally:
        await _run("incus", "delete", "--force", dtu.id)

async def _run(*args: str) -> None:
    proc = await asyncio.create_subprocess_exec(*args)
    if await proc.wait() != 0:
        raise RuntimeError(f"command failed: {' '.join(args)}")
```

Then in your harness, call it once before the run and point trials at the task
profile:

```python
await ensure_golden_image("profiles/nanoclaw-bake.yaml", "nanoclaw-golden")
dtu = await DTU.launch("profiles/nanoclaw-task.yaml")   # ~1 min, no Docker Hub pulls
```

## Gotchas that will bite you

- Incus >= 6.0.1 is required. On 6.0.0 + a `dir` storage pool, `incus publish`
  writes a valid image but the unpack on launch silently drops files under any
  `dev/`-named directory and fails on hardlinks into them (a Docker store and
  `node_modules` both contain such paths). See the published-image entries in
  `amplifier-bundle-digital-twin-universe` troubleshooting docs. A `btrfs`/`zfs`
  pool also avoids it (no tar on publish).

- Avoid Docker Hub 429s in the bake. If the profile builds an image, route pulls
  through a mirror before starting dockerd:

  ```bash
  mkdir -p /etc/docker
  echo '{"registry-mirrors": ["https://mirror.gcr.io"]}' > /etc/docker/daemon.json
  ```

- Keep Docker's storage backend identical between bake and reuse. If the bake
  builds images under the containerd image store but the relaunch daemon reads
  `overlay2` (or vice versa), `docker images` is empty at run time and anything
  that `docker run`s the built image hangs. Do not toggle
  `features.containerd-snapshotter` in `daemon.json` between bake and task.

- Prune build cache before publish so the image is smaller and tars cleanly:
  `docker builder prune -af`.

- One image per distinct environment (e.g. per agent backend). Alias them
  clearly and delete to force a re-bake: `incus image delete <alias>`.
