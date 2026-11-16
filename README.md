# Retro Poker | TEPDK

Live True / False retrospective survey for the TEPDK accelerator retrospective with TotalEnergies, Cognite, and Capgemini.

**Live site:** [https://sendils-cognite.github.io/tepdk-retro-poker/](https://sendils-cognite.github.io/tepdk-retro-poker/)

GitHub Pages serves `index.html` from the `main` branch root. After a deploy, append `?v=<commit>` to skip a stale browser or CDN cache (Pages can hold a copy for about 10 minutes).

## Purpose

Run a short, timed poll in the room so every participant answers the same ten statements, then discuss the statements that landed mostly False.

- Host creates a room, shares a link or QR code, opens the poll, and later closes it.
- Participants join with a display name, answer True or False under a per-statement timer, revisit skips, then submit.
- The host sees who joined and who submitted, but only **aggregate** True / False percentages per statement. Answers are never shown against a name.

## How it works

```text
Host browser  ──POST ops──►  ntfy.sh/{room}  ◄──SSE──  Participant browsers
                              (message bus)
GitHub Pages serves the static app (HTML + Tailwind CDN + admin-config.js)
```

1. **Host** signs in with the admin user ID and password, creates a room, and shares the invite URL / QR.
2. **Participants** open the invite, enter a name, and wait until the host starts the poll.
3. Each statement has a countdown (default **45 seconds**). Choosing True or False fills the whole button. Unanswered statements can be revisited before final submit.
4. After submit, the participant sees a thank-you screen with their name.
5. When the host finishes the poll, results show True / False percentages, highlight statements where False is over 50% (**Discuss**), and support sorting by most / least True or False.

Room state is rebuilt on every client from a shared op log on [ntfy.sh](https://ntfy.sh). There is no app server and no database.

### Sync ops

| Op | Meaning |
| --- | --- |
| `create` | Host opens the room and picks the template |
| `join` | Participant enters with a display name |
| `phase` | Host sets `open` or `closed` |
| `vote` | One True / False answer for statement index `i` |
| `submit` | Participant locks in their answers |
| `batch` | Several ops in one ntfy message (used by the demo) |

Ops are ordered by `at`. Only the host’s `phase` ops control the poll. Identity for the current browser tab lives in `sessionStorage` (`retro-me`, `retro-name`, and flow progress under `retro-flow-<room>`).

## Tools and stack

| Piece | Role |
| --- | --- |
| Static `index.html` | Whole app (UI + client logic) |
| [GitHub Pages](https://pages.github.com/) | Hosting from `main` |
| [ntfy.sh](https://ntfy.sh) | Free pub/sub over HTTP POST + Server-Sent Events |
| [Tailwind CSS Play CDN](https://tailwindcss.com/docs/installation/play-cdn) | Styling |
| [Phosphor Icons](https://phosphoricons.com/) | Icons |
| [qrcode-generator](https://github.com/kazuhikoarase/qrcode-generator) (jsDelivr) | Invite QR on the host screen |
| [Atkinson Hyperlegible](https://fonts.google.com/specimen/Atkinson+Hyperlegible) | Readable UI font |
| Web Crypto (PBKDF2-SHA256) | Admin password check in the browser |
| Python 3 + `Makefile` | Offline demo that seeds a finished five-person poll |

No build step, bundler, Node app, or Firebase / GCP backend.

## Repository layout

```text
tepdk-retro-poker/
├── index.html        # App UI and client logic
├── admin-config.js   # Public admin user id + salted password hash only
├── Makefile          # make demo-setup
├── demo/setup.py     # Creates a room, five random respondents, closes the poll
└── README.md
```

## Run locally

Any static file server from the repo root is enough:

```bash
cd tepdk-retro-poker
python3 -m http.server 8765
```

Open [http://127.0.0.1:8765/](http://127.0.0.1:8765/). Sync still uses the public ntfy topic for the room, so local and Pages clients in the same room see each other.

## Host and participant flow

### Host

1. Open the site and sign in as the survey admin.
2. Create a room and share the invite link or QR.
3. Watch the people board for join / answering / submitted status (no answers attached to names).
4. Start the poll, then Finish when ready.
5. Review aggregate percentages, Discuss badges, and the sort control.

### Participant

1. Open the invite link and enter a display name.
2. When the poll opens, answer each statement True or False within the timer.
3. At the end, review unanswered items, optionally revisit them, then submit.
4. See the thank-you page.

Names are kept for greeting and the people board status only. They are not linked to individual answers in the host results.

## Admin setup

`admin-config.js` is loaded by the page and is public. Store **only** a salted PBKDF2-SHA256 hash — never a plain password in the repo or in chat.

```js
window.RETRO_ADMIN = {
  userId: "RetroAdmin",
  displayName: "Survey Admin",
  salt: "<hex salt>",
  iterations: 200000,
  passwordHash: "<hex derived key>"
};
```

To generate a new salt and hash in a local shell (replace the password yourself; do not paste it into tickets or chat):

```bash
python3 - <<'PY'
import hashlib, os, getpass
password = getpass.getpass("Admin password: ").encode()
salt = os.urandom(16)
iterations = 200000
digest = hashlib.pbkdf2_hmac("sha256", password, salt, iterations)
print(f'salt: "{salt.hex()}"')
print(f"iterations: {iterations}")
print(f'passwordHash: "{digest.hex()}"')
PY
```

Update `admin-config.js` with those values and redeploy.

## Demo setup

Seed a finished room with five fictional participants (Amina, Lars, Priya, Chen, Sofia), each with a random True / False pattern, then close the poll:

```bash
make demo-setup
```

Optional: point the printed links at a local server:

```bash
make demo-setup BASE_URL=http://127.0.0.1:8765
```

The script prints a **host dashboard** URL (`?room=…&host=…`) and an **invite** URL. The host query parameter opens that room’s dashboard without the admin login form. Use it for demos only; anyone with the host id can open the same view, and the id is visible on the public ntfy topic for that room.

## Useful URL parameters

| Parameter | Effect |
| --- | --- |
| `room` | Join an existing room |
| `host` | Demo-only: open as that room’s host without the login form |
| `t` | Seconds per statement (default `45`; use `t=3` for a quick manual test) |
| `v` | Cache-busting query for Pages (any unique value, often the commit SHA) |

Examples:

```text
https://sendils-cognite.github.io/tepdk-retro-poker/?v=fa51750
https://sendils-cognite.github.io/tepdk-retro-poker/?room=<room>&t=3
```

## Privacy and limits

- Votes are synced as anonymous aggregates on the host results screen; the people board shows progress only.
- Room traffic rides a **public** ntfy topic named like the room id. Treat rooms as short-lived session channels, not a confidential store.
- ntfy free-tier rate limits apply; the demo batches ops to stay within them.
- Safari quirks are not a support target for this tool.

## License / ownership

Internal TEPDK accelerator tooling maintained under [sendils-cognite/tepdk-retro-poker](https://github.com/sendils-cognite/tepdk-retro-poker).
