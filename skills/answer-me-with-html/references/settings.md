# Settings, clean-up and updates

Read this when SKILL.md section 0 sends you here.

When the arguments for this call (shown in section 0 of SKILL.md) start with `config` (for example `/answer-me-with-html config open off`), this turn handles settings only and produces no page:

- `config`: run `am config` to show the current settings, then let the user choose. Where the agent has a choice tool such as AskUserQuestion, use it: at most 4 settings at a time, these first: `open`, `theme`, `mode`, `style`, with the current value marked in the options. Otherwise ask in plain text.
- `config <key> <value>`: run `am config set <key> <value>`.
- `config reset [key]`: run `am config reset [key]`.

When the user asks in natural language ("stop opening the browser", "use the card theme by default"), also convert it to `am config set`. Settings: `open` (auto-open the browser), `theme`, `mode`, `style`, `voice` (video narration), `update_check` (new-version notices), `close_after_reply` (close the page tab after the reply is copied). Run `am config` to see all descriptions.

Update checks are off in this copy: the launcher sets `AM_NO_UPDATE_CHECK`, so the CLI makes no request to GitHub and never prints an `! Update hint`. Do not turn them back on; the hint points at the upstream package, and installing that would replace this port.

When the user asks for a ready-made theme ("use the comic theme", "install the manga theme"): run `am theme add <name> --use`. Names come from the catalog at https://answer-me-with-html.com/themes/ (at the time of writing: `comic`, `manga`, `pop`); if the name is not there, the command lists the available ones. It downloads, checks and saves the theme and makes it the default, and it asks the user nothing else. If it stops because a file of that name already exists, tell the user it may be their own theme and run it again with `--force` only if they agree. `am theme list` shows the installed themes (`--remote` also shows the catalog), `am theme update` updates them, and `am theme remove <name>` deletes one. The command prints only theme names and versions; it needs Answer me with HTML 0.5.3 or newer. Themes are saved in the temporary data directory, so the system may clear them; to keep a theme, set `AM_HOME` to a persistent folder and install it there.

When the arguments start with `clean`, or the user asks to clean up pages / the cache: first run `am clean --dry-run` and tell the user how many items and how much space will be deleted. Run `am clean` only after the user agrees (add `--all` to delete all pages and videos, `--days N` to change how many days to keep).

When the arguments start with `update`, or the user asks to update this skill: this is a fork pinned to Answer me with HTML 0.5.5, with the CLI vendored at `scripts/vendor/am-cli.mjs`. Update it from the user's repository, never from the upstream package: installed with `npx skills`, run `npx skills update answer-me-with-html -y`; installed from a git checkout, run `git pull` in that checkout. Do not run `npm install`, `claude plugin update` or any upstream installer: they would replace this port and bring back `~/.answer-me-with-html`.
