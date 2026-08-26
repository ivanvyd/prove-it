# Setup — from a fresh Free Edition account to a running app

Written to be followed by someone who has never seen this repo. Roughly 40 minutes, most
of it waiting.

> **Paths in this document are Windows.** On macOS or Linux, read
> `.venv/Scripts/python.exe` as `.venv/bin/python` throughout — or activate the venv
> (`source .venv/bin/activate`) and just use `python`. The commands are otherwise identical.
>
> You will also need [uv](https://docs.astral.sh/uv/) for the first step, or substitute
> `python -m venv .venv` and `pip install -e ".[dev]"`.

## 0. Run it with no workspace at all

Worth doing first, because it shows you what you are building towards. The app ships with
a recorded conversation and needs no credentials:

```bash
uv venv --python 3.12
uv pip install -e ".[dev]"
.venv/Scripts/python.exe -m streamlit run src/prove_it/ui/app.py    # Windows
# .venv/bin/python -m streamlit run src/prove_it/ui/app.py          # macOS / Linux
```

Open <http://localhost:8501> and click through: pick a case → sealed query → lock your call
and stake → reveal → cross-examine → receipt. The banner says "Offline demo" so nobody
mistakes it for live.

## 1. Create the workspace

1. Sign up at <https://www.databricks.com/learn/free-edition>.
2. Verify with LinkedIn if prompted — it widens the outbound-domain allowlist, which you
   do not need for this app but will want if you extend it.

Free Edition gives you one workspace, one 2X-Small SQL warehouse, and up to three apps
that stop themselves after 24 hours. All of that is enough. The 24-hour stop matters at
judging time: restart the app before you share the link.

## 2. Build the tables

The docket needs **four** tables, built by **two** scripts. Missing either script leaves
cases that cannot run: without `load_cases.py` there is no Berkeley paradox, which is the
case the demo is built around.

| Table | Script | Cases |
|---|---|---|
| `student_scores` | `setup_workspace.py` | The average, The gap that stays |
| `country_indicators` | `setup_workspace.py --indicators-csv` | The window |
| `berkeley_admissions` | `load_cases.py` | The paradox |
| `emissions` | `load_cases.py --emissions-csv` | The denominator |

### 2a. The generated pupil data

The script is the one to prefer — it uses the same generator the app and the
tests quote, then checks the built table against it, so the numbers cannot drift.

```bash
databricks auth login --host https://<your-workspace>.cloud.databricks.com
.venv/Scripts/python.exe scripts/setup_workspace.py

# or, to load the real public-data table at the same time:
.venv/Scripts/python.exe scripts/setup_workspace.py --indicators-csv ~/Downloads/API_SE.XPD.csv
```

Free Edition restricts outbound internet, so the real CSV has to be downloaded by you —
from [World Bank Open Data](https://data.worldbank.org/indicator) (e.g.
`SE.XPD.TOTL.GD.ZS`, government spending on education as % of GDP) or
[Our World in Data](https://ourworldindata.org/) — and passed as a file. The script does
the rest. Without it you lose the second demo rumour, not the product.

It creates the schema and a volume, uploads the generated pupil data, builds the Delta
table, documents every column for Genie, and finishes by printing the group statistics
alongside what `prove_it.demo_data.OBSERVED` says they should be. It must report
`Matches prove_it.demo_data.OBSERVED exactly.` and an effect size under 0.2. If it does
not, stop — the demo will not work and no amount of UI polish saves it. It is idempotent,
so re-running converges rather than duplicating.

The notebook route does the same thing by hand: **Workspace → Import** →
`notebooks/01_generate_data.py`, attach serverless compute, **Run all**, and read the
effect-size check near the bottom. Use it if you would rather see the steps, or if the CLI
is not available to you.

### 2b. The case tables

`setup_workspace.py` deliberately does not build these: one of them is a 13 MB download,
and neither needs the pupil generator to run again to be refreshed.

```bash
.venv/Scripts/python.exe scripts/load_cases.py                          # Berkeley only
.venv/Scripts/python.exe scripts/load_cases.py --emissions-csv ~/Downloads/owid-co2-data.csv
```

Berkeley is transcribed in the repo (`src/prove_it/case_data.py`) and needs no download —
it is 12 cells from the 1975 *Science* paper, and the script verifies the built table
reproduces the published percentages before it returns. Emissions is the same
download-it-yourself arrangement as `--indicators-csv`, from
[OWID](https://nyc3.digitaloceanspaces.com/owid-public/data/co2/owid-co2-data.csv).

`CREATE OR REPLACE` throughout, so re-running converges rather than duplicating.

Either way, optionally follow the notebook's last cell to upload a real public CSV as
`country_indicators`, so the demo can close on genuine data.

## 3. Create the Genie space

Creating one is still four clicks; configuring one is scripted, because the instructions
decide whether every case works and hand-editing them in the UI is how they drift.

1. **Genie → New space**. Point it at your SQL warehouse.
2. Copy the space id out of the URL: `/genie/rooms/<space-id>`.
3. Push the repo's tables and instructions into it:

   ```bash
   .venv/Scripts/python.exe scripts/update_space.py --space-id <id> --dry-run
   .venv/Scripts/python.exe scripts/update_space.py --space-id <id>
   ```

Do **not** paste instructions out of a document — the authoritative text is
`src/prove_it/genie/space.py`, and
[`genie-space-instructions.md`](./genie-space-instructions.md) explains what it says and
why. That file used to hold a hand-copied duplicate, and the duplicate drifted a long way
behind the docket before anyone noticed.

## 4. Run the day-one gate — do not skip this

Three assumptions carry the whole product. This is where you find out whether they hold,
and it costs ten minutes against the eight days you would otherwise spend finding out the
hard way.

```bash
# Git Bash / macOS / Linux
export DATABRICKS_HOST=https://<your-workspace>.cloud.databricks.com
export DATABRICKS_TOKEN=<a personal access token>
.venv/Scripts/python.exe scripts/probe.py --space-id <space-id> --repeats 3 --record
```

```powershell
# PowerShell. `export` is not a cmdlet, so the lines above fail here.
$env:DATABRICKS_HOST = "https://<your-workspace>.cloud.databricks.com"
$env:DATABRICKS_TOKEN = "<a personal access token>"
.venv\Scripts\python.exe scripts\probe.py --space-id <space-id> --repeats 3 --record
```

Read the summary block it prints:

| What it says | What to do |
|---|---|
| `PASS` (≥90% usable) | Build as specified. |
| `WARN` (60–90%) | Set `PROVE_IT_FREE_TEXT=0` and ship the curated deck as the only input. |
| `FAIL` (<60%) | Stop. Reshape the concept before writing more UI — this is what day one is for. |
| `Genie is volunteering the spread in its FIRST answer` | The most important line in the output. Fix the space instructions before anything else. |
| `thoughts is empty in every response` | Not fatal. Beat 2 falls back to SQL plus the one-line description. |

The **naive first draft** figure matters more than the hit rate. The app's whole lesson is
the difference between Genie's first answer and its repaired one; if the first query already
reports a standard deviation, a range or percentiles, there is no gap for the child to open
and no verdict to overturn. The probe reads this straight off the emitted SQL, so you find
out in ten minutes rather than on demo day.

`--record` writes `probe-runs/demo-investigation.json`. Point the app at it with
`PROVE_IT_FIXTURE=probe-runs/demo-investigation.json` and the offline mode replays a real
recorded conversation instead of the hand-written stand-in — which is what the demo video
should be built on.

Also check the refusal list it prints. If *boys are better at maths* comes back refused,
that is the loaded-question risk firing, and the deck entries need rephrasing as
comparisons rather than assertions.

## 5. Run it live, locally

```bash
# Git Bash / macOS / Linux
export GENIE_SPACE_ID=<space-id>
.venv/Scripts/python.exe -m streamlit run src/prove_it/ui/app.py
```

```powershell
# PowerShell
$env:GENIE_SPACE_ID = "<space-id>"
.venv\Scripts\python.exe -m streamlit run src/prove_it/ui/app.py
```

The "Offline demo" banner disappears. Every query on screen is now one Genie really wrote.

## 6. Deploy as a Databricks App

1. **Compute → Apps → Create app**, name it `prove-it`.
2. Add a resource: **Genie space** → your space → permission **Can run**. The resource key
   must be `genie-space` to match `app.yaml`.
3. Grant the app's service principal `USE CATALOG` on `workspace`, `USE SCHEMA` on
   `prove_it`, and `SELECT` on both tables. Missing grants show up as Genie refusing to
   answer anything, which reads confusingly like a model problem.
4. Sync this repo to the workspace and deploy:

   ```powershell
   databricks sync . /Workspace/Users/<you>/prove-it --full
   databricks apps deploy prove-it --source-code-path /Workspace/Users/<you>/prove-it
   ```

   Run these from PowerShell rather than Git Bash. MSYS rewrites a leading `/Workspace/...`
   into a Windows path before the CLI sees it, and the error it produces
   (`Path (C:/Program Files/Git/Workspace/...) doesn't start with '/'`) does not obviously
   point at the shell.

   The same two commands push later code changes to the running app.

## 7. A public link, with no Databricks account

A Databricks App cannot be opened without a workspace identity, so the link a stranger can
click is the offline build, hosted for free on [Streamlit Community Cloud](https://share.streamlit.io).
It runs the same code from the same repository and replays the recorded Genie conversations.
It needs no credentials of any kind, and you should give it none: with no `GENIE_SPACE_ID`
in the environment the app is offline by default, so the Secrets field stays empty.

1. Sign in at share.streamlit.io with GitHub and choose **Create app**, deploying from
   GitHub. A private repository works too, but Streamlit then asks GitHub for access to
   every private repository on the account, not just this one; making the repository
   public first is the smaller grant.
2. Repository `ivanvyd/prove-it`, branch `main`, main file path `src/prove_it/ui/app.py`.
3. **App URL**: `prove-it`, the address the README and the project story already carry.
   Under **Advanced settings** pick Python 3.12 (the form defaults to a newer release than
   this project is tested on) and leave Secrets empty.
4. Deploy. The first build installs `requirements.txt` and takes a few minutes; later
   pushes to `main` redeploy on their own.
5. If the repository was private when you deployed, the app is private too: only viewers
   you invite can open it, and an account may hold one such app at a time. Once the
   repository is public, open the app's settings and make the app public under Sharing.
   The URL does not change and nothing redeploys.

Two things to know before sharing the link. Community Cloud puts an app to sleep after a
stretch with no visitors, and the next visitor sees a "wake up" button that takes about half
a minute, so open the link yourself shortly before anyone else will. And do not add
`DATABRICKS_HOST` or a token to the secrets to make it live: a public URL with a working
token behind it lets any visitor spend your workspace's quota, and the recordings are real
Genie conversations already.

## Troubleshooting

**Genie answers nothing, or refuses everything.** Almost always the service principal
grants in step 6.3 rather than the model.

**The first query already includes the spread.** The instructions are not landing. This
kills the lesson, so fix it before anything else — tighten the first paragraph of the
space instructions and re-run the probe.

**The app is unreachable.** Free Edition apps stop after 24 hours. Restart it.

**Everything is slow.** One 2X-Small warehouse, cold. The first query of a session pays
the start-up cost. The app spends that wait in the interrogation room — a case clock and a
board of the phases Genie is actually moving through — rather than on a spinner, so a slow
warehouse reads as suspense instead of a hang.

**`ModuleNotFoundError: No module named 'prove_it'`.** An editable install can register its
metadata without writing the `.pth` file that puts `src` on the path, and the failure only
shows when the app is launched for real — the server still returns HTTP 200 and its health
endpoint still says `ok`, because Streamlit runs the script when a browser connects. The app
now bootstraps its own path so the documented command works regardless, but if you see this
from anything else, `uv pip install -e .` again and check with
`.venv/Scripts/python.exe -c "import prove_it"`. `pytest -m slow` covers this.
