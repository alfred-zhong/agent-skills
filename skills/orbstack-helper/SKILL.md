---
name: orbstack-helper
description: Use this skill whenever the user mentions OrbStack, orb, orbctl, Mac 上的 Linux 虚拟机, Mac 上跑 Linux, creating / starting / stopping / restarting / deleting a Linux VM on macOS, SSH-ing into an OrbStack machine, running a command inside an OrbStack Linux machine, copying files to or from a Linux VM (push / pull), or asks how to manage OrbStack Linux machines in general. Trigger even for indirect phrasing like "在 Mac 上开台 Linux 装个 X" or "我的 orb 里有个 VM 跑不起来" — this skill is the entry point for all OrbStack Linux-machine operations. Out of scope - Docker containers (use the `docker` CLI directly), Kubernetes (`orbctl k8s`), and the OrbStack menu-bar app GUI; this skill only manages Linux machines.
---

# OrbStack Helper

Use OrbStack to create and manage Linux virtual machines on macOS from the terminal. This skill covers **Linux machines only** — containers and Kubernetes are out of scope.

> **Verified against OrbStack v2.2.1 on 2026-07-21.** Command syntax examples in the *Command reference* section may drift; the *Core concepts* and *Risks* sections are stable mechanism, not version-bound.

## When to use this skill

- User wants to spin up a Linux VM on their Mac (any distro OrbStack supports).
- User needs to run a one-shot command inside an OrbStack Linux VM.
- User wants to push / pull files between macOS and a Linux VM.
- User asks about `orb` or `orbctl` commands.
- User reports a Linux VM is broken and wants to restart, inspect logs, or delete it.

Do **not** use for: Docker container questions (`docker run` / `docker compose`), Kubernetes, the OrbStack menu-bar app, anything Windows / Linux native (OrbStack is macOS-only), or backing up a VM (OrbStack has no built-in snapshot feature).

## Core concepts

| Term | Meaning |
|---|---|
| **machine** | The only artifact this skill manages — an OrbStack Linux VM. |
| **host** | Your macOS machine. |
| **guest** | The Linux VM. |
| **orb** | Convenience command. `orb` with no args opens an interactive login shell into the **default machine**. Also accepts all `orbctl` subcommands. |
| **orbctl** | Explicit machine-control CLI: `create` / `start` / `stop` / `delete` / `list` / `info` / `rename` / `default` / `logs` / `status`. Equivalent to `orb <subcommand>`. |
| **default machine** | The single machine that `orb` (no args) targets. Set with `orbctl default <name>`. When you have one machine, it is automatically default. |
| **distro** | Linux distribution (e.g., `ubuntu`, `debian`, `fedora`). |
| **distro:version** | Either form works: `ubuntu:24.04` (numeric) or `ubuntu:noble` (codename). Use codenames in scripts for clarity; use numbers when talking to humans. |
| **arch** | `arm64` or `amd64`. Does **not** equal your Mac's architecture — you can create an `amd64` VM on an arm64 Mac (slower, Rosetta-translated). |
| **isolated machine** | A VM with file-sharing and OrbStack integration disabled — closer to a sandbox. Requires explicit `--mount` to access host paths. |
| **isolated-network** | A network mode where the VM can reach the internet but not other VMs / host IPs. Independent of `--isolated`. |
| **cloud-init / user-data** | A YAML file passed to `orbctl create --user-data` for first-boot provisioning (packages, users, files). |
| **push / pull** | File copy host ⇄ guest. The `-p` flag translates absolute paths so `/Users/you/...` on macOS becomes the correct Linux path. |
| **run** | `orbctl run CMD` runs one command and exits. Non-interactive — does **not** source `.bashrc`, so PATH additions in `~/.bashrc` won't apply. Use `orb` (no args) for an interactive login shell. |
| **login shell** | `bash -lc` / `zsh -l` / `orb -s`. Sources `.profile` / `.bashrc`. `bash -c` (no `-l`) does not. |

## Typical workflows

### Create a dev VM and install something inside it

```bash
# 1. Create (auto-starts; one-machine setup makes it default).
orbctl create ubuntu:24.04 dev

# 2. Install something in one shot. Wrap in sh -c when the inner command uses |.
orbctl run -m dev sh -c "curl -fsSL https://example.com/install.sh | bash"

# 3. Iterate: drop into an interactive shell (this DOES source .bashrc).
orb -m dev
```

### Run a one-shot command without creating a long-lived VM

```bash
orbctl run uname -a                    # on default machine
orbctl run -m ci-runner whoami         # on a named machine, specific user
orbctl run -m dev -w /tmp sh -c "ls | wc -l"   # pipe inside the VM
```

### Copy files in / out

```bash
orbctl push -m dev ./local.txt /home/alfred/remote.txt
orbctl pull -m dev /var/log/app.log ./   # drops into ./app.log
orbctl push -p -m dev /Users/you/project /home/alfred/project   # -p translates absolute macOS paths
```

### SSH into the VM from outside OrbStack

```bash
ssh orb                          # default machine
ssh alfred@orb                   # specific user
ssh orb -p 32222                 # explicit port (matches default config)
```

SSH config lives at `~/.orbstack/ssh/id_ed25519`; replace or symlink to your own key. OrbStack auto-forwards your SSH agent — no extra flags needed.

### Tear down

```bash
orbctl stop dev                  # keep VM, free CPU/RAM
orbctl delete dev                # destructive — interactive confirmation, no -f
# orbctl delete -f dev           # NEVER use -f on a machine with work in it
```

## Command reference

> **Last verified 2026-07-21 against OrbStack v2.2.1.** Source of truth: <https://docs.orbstack.dev/machines/commands>. Subcommands in the table below all accept `-m <name>` to target a non-default machine and `-u <user>` to run as a different user.

### Lifecycle

| Command | What it does |
|---|---|
| `orbctl create DISTRO[:VERSION] [NAME]` | Create and auto-start. Omit `VERSION` for the latest stable. See *Supported distros* below. |
| `orbctl start [NAME]` / `stop [NAME]` / `restart [NAME]` | Power control. Omit `NAME` for default. |
| `orbctl delete [NAME]` (`-f` to skip confirm) | **Permanent.** Wipes the VM. Without `-f`, prompts for confirmation. |
| `orbctl list` | One row per VM: `NAME  STATE  DISTRO  VERSION  ARCH  DISK  IP`. |
| `orbctl info NAME` | Full JSON-ish dump: ID, state, distro/version/arch, disk usage, IPv4 + IPv6. |
| `orbctl logs NAME` | VM boot / runtime logs. |
| `orbctl rename OLD NEW` | Rename a VM. |
| `orbctl default [NAME]` | Get or set the default machine. |
| `orbctl status` | Whether OrbStack itself is running (not the VM). |

**`create` flags** (combine freely):

| Flag | Effect |
|---|---|
| `-a, --arch arm64\|amd64` | Override default arch. |
| `--memory 4G` | RAM cap (accepts `MiB` / `GiB`). |
| `--cpus 2` | CPU core cap. |
| `--disk 64G` | Disk cap (GiB). |
| `-u, --user NAME` | Default Linux username (defaults to your macOS user). |
| `-p, --set-password` | Set a password for the user **and** root. Note: `-p` here means *set password*. |
| `--isolated` | Disable file sharing & integration. |
| `--isolate-network` | Block access to other VMs and host IPs. |
| `--mount SRC[:DST]` | Selective host mount (repeatable). Only effective on `--isolated` VMs. |
| `--user-data PATH` | Cloud-init user-data YAML for first-boot provisioning. |
| `--forward-ssh-agent` | Enable SSH-agent forwarding. |

### Access

| Command | What it does |
|---|---|
| `orb` | Interactive login shell into the default machine. Sources `.bashrc`. |
| `orb -m NAME` | Interactive login shell into a named machine. |
| `orbctl run [flags] CMD` | One-shot, non-interactive. Flags: `-m`, `-u`, `-s` (login shell — sources rc files), `-w DIR` (working dir), `-p` (translate absolute macOS paths). |
| `orbctl shell` / `orb -s` | Interactive login shell (equivalent to `orb`). |

### File transfer

| Command | What it does |
|---|---|
| `orbctl push [-m NAME] [-p] SRC DST` | host → guest. |
| `orbctl pull [-m NAME] [-p] SRC` | guest → host (writes to `./SRC`). |

`-p` translates absolute macOS paths (`/Users/you/...`) into the equivalent Linux path inside the guest. Use it when you're pasting paths from macOS.

### Supported distros (curated)

Use any of these 5 for 95% of work:

| Distro | Default version | Other versions |
|---|---|---|
| `ubuntu` | `noble` (24.04 LTS) | `jammy` (22.04), `questing` (25.10), `resolute` (26.04) |
| `debian` | `bookworm` (12) | `bullseye` (11), `trixie` (13), `forky` (14) |
| `fedora` | latest stable | 41, 42, 43, 44 |
| `arch` | current | — |
| `alpine` | `edge` | 3.21, 3.22, 3.23 |

Other 11 distros (alma, centos, devuan, gentoo, kali, nixos, openeuler, opensuse, oracle, rocky, void) are supported — full list at <https://docs.orbstack.dev/machines/distros>.

## Risks and pitfalls

These are real bugs in workflows people actually hit. Read once.

1. **`orbctl run "cmd | bash"`** — the `|` is interpreted by your **outer** shell, not by OrbStack. The string never reaches the VM. Wrap inner pipelines with `sh -c "..."`:
   ```bash
   # WRONG — runs `ls` on macOS, then `bash` on macOS with an empty pipe
   orbctl run -m dev "ls | bash"

   # RIGHT — runs the whole pipeline inside the VM
   orbctl run -m dev sh -c "ls | bash"
   ```

2. **`-p` means different things in different commands** — in `orbctl create`, `-p` / `--set-password` sets the user/root password. In `orbctl run` / `push` / `pull`, `-p` translates absolute macOS paths. Don't mix them up.

3. **`orbctl run` does not source `.bashrc`** — commands installed into `~/.local/bin` or `~/.kimi-code/bin` won't be on PATH inside `orbctl run`. Use one of:
   - `orb` (no args) → interactive login shell that *does* source rc files.
   - `orbctl run -s CMD` → login shell.
   - `orbctl run sh -c "PATH=/home/me/.kimi-code/bin:\$PATH cmd"`.

4. **Delete is permanent and silent** — `orbctl delete dev` (no `-f`) prompts for confirmation. Add `-f` to bypass the prompt; **never use `-f` on a machine that holds work you haven't backed up**. OrbStack has no recycle bin or snapshot.

## Out of scope (do not use this skill for)

- Docker containers — use the `docker` CLI directly.
- Kubernetes — use `orbctl k8s` (not covered here).
- OrbStack app GUI: menu bar, Debug Shell, Domains, HTTPS, USB passthrough, Sound.
- Non-macOS hosts (Windows / Linux install paths).
- VM backup / snapshot — OrbStack does not ship a snapshot feature.

## References

- OrbStack docs home: <https://docs.orbstack.dev/>
- Linux machine commands: <https://docs.orbstack.dev/machines/commands>
- Supported distros + versions: <https://docs.orbstack.dev/machines/distros>
- File sharing: <https://docs.orbstack.dev/machines/file-sharing>
- Network: <https://docs.orbstack.dev/machines/network>
- SSH: <https://docs.orbstack.dev/machines/ssh>
