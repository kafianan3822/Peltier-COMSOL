# Running the whole simulation with an AI agent (Claude Code) on your PC

This guide sets up Claude Code on a Windows PC so that it runs the complete pipeline for you:
tests, COMSOL model build, variant runs, checks and report. It also fixes script errors on the
way and tells you what it did.

The agent must run **on the PC that has COMSOL installed**. COMSOL and its licence are only
reachable there.

Claude Code changes quickly. If a command below does not work, check the current instructions at
https://code.claude.com/docs/en/setup.

## What you need

| Item | Why |
|---|---|
| Windows 10 or 11, COMSOL Multiphysics 6.3 with the Semiconductor Module | Runs the simulation |
| A Claude account with Claude Code access (Pro or Max plan, or an Anthropic Console account with API credit) | Runs the agent |
| About 2 GB free disk space, internet access | Installation |

## Step 1. Install Git for Windows

1. Download from https://git-scm.com/download/win and run the installer with the default options.
2. Open **PowerShell** (Start menu, type `powershell`) and check:

```bash
git --version
```

## Step 2. Install Python 3.11 or newer

1. Download from https://www.python.org/downloads/windows/.
2. In the installer, tick **Add python.exe to PATH**, then *Install Now*.
3. Close and reopen PowerShell, then check:

```bash
python --version
```

## Step 3. Get the repository

```bash
cd $HOME\Documents
```

```bash
git clone https://github.com/kafianan3822/Peltier-COMSOL.git
```

```bash
cd Peltier-COMSOL
```

The germanium version is on the branch `claude/compassionate-newton-jvnu49` until it is merged
into `main`:

```bash
git checkout claude/compassionate-newton-jvnu49
```

## Step 4. Install the Python packages

```bash
python -m pip install mph numpy scipy pandas matplotlib pyyaml pytest
```

Check that the package itself is healthy. This needs no COMSOL and should end with `44 passed`:

```bash
python -m pytest -q
```

## Step 5. Tell the scripts where COMSOL is

Only needed if COMSOL is not in `C:\Program Files\COMSOL\COMSOL63\Multiphysics`. Replace the
path with yours:

```bash
setx COMSOL63_PATH "C:\Program Files\COMSOL\COMSOL63\Multiphysics"
```

Close and reopen PowerShell afterwards, go back to the repository folder, and check that
COMSOL answers. This starts COMSOL in the background and can take a minute:

```bash
python comsol/python/check_comsol.py
```

If this fails, fix it before going on (user manual, section 3). The agent cannot repair a
missing licence.

## Step 6. Install Claude Code

In PowerShell:

```bash
irm https://claude.ai/install.ps1 | iex
```

Close and reopen PowerShell, then check:

```bash
claude --version
```

Alternative, if you already have Node.js 18 or newer:

```bash
npm install -g @anthropic-ai/claude-code
```

## Step 7. Sign in

From the repository folder:

```bash
claude
```

The first start opens your browser. Sign in with your Claude account and approve. When asked
whether you trust the files in this folder, answer yes.

## Step 8. How the agent knows what to do

The repository contains `CLAUDE.md`. The agent reads it at every start. It holds the pipeline
order and the rules: never change physical parameters to pass a check, stop on a `BUG`, how to
fix an `ApiNameError`, never commit unless asked. You do not need to edit it.

By default the agent asks you before it runs a command or edits a file. Keep it that way for
the first run. Each prompt offers "yes, and don't ask again for this command", which is the
easiest way to stop repeated questions for commands you have seen and trust, such as
`python comsol/python/build_model.py`.

## Step 9. First run, supervised

Start `claude` in the repository folder and paste this:

```
Run the pipeline in CLAUDE.md up to and including step 6 (core set only).
After each step tell me in one line whether it passed. If a step fails,
diagnose it, fix script or API-name problems, and rerun that step. Do not
change anything in config/params_base.yaml or config/variants.yaml. Stop and
ask me if COMSOL cannot be started or if a check reports BUG.
```

What to expect:

1. The agent runs the tests and the reference model (about 2 minutes).
2. It builds the COMSOL model stage by stage. This is where problems appear the first time,
   because some COMSOL property names could not be verified without COMSOL. The agent reads the
   error, corrects the name in `config/api_names_override.yaml` and reruns.
3. It runs V0 and V1, then the report, and summarises checks C1 to C9.

Read `results/summary.md` yourself afterwards. Compare the V0 and V1 numbers with section 6 of
`docs/GERMANIUM_PARAMETERS.md`; COMSOL should show less cooling than the reference model.

## Step 10. Full run

When the core set passes its checks, in the same session:

```
Now run step 7 of CLAUDE.md (full variant set, 49 runs) and regenerate the
report. Summarise every check and list any variant that failed.
```

This takes 1 to 3 hours. Leave the PowerShell window open and keep the PC awake (Settings >
System > Power > Screen and sleep > Never, while plugged in).

## Step 11. Unattended runs (optional, your decision)

Do this only after a supervised run has worked from start to finish.

Claude Code can run one task without the chat window:

```bash
claude -p "Run the full pipeline in CLAUDE.md, steps 1 to 7. Follow the rules there. Write a final summary to results/agent_run.md."
```

In this mode nobody is there to answer permission questions, so any command that is not
pre-approved is refused. Pre-approving commands is a setting you make yourself, in
`.claude/settings.json` in the repository or with the `/permissions` command inside `claude`.
The current syntax is described at https://code.claude.com/docs/en/settings. Approve only what
the pipeline needs: the `python ...` commands listed in `CLAUDE.md`. That file is deliberately
not shipped with the repository, because it decides what an agent may do on your PC without
asking you.

To repeat the run on a schedule, put the command in a `.bat` file and add it to Windows Task
Scheduler.

Do not use `--dangerously-skip-permissions` on your working PC. It allows any command.

## Step 12. Keep your results

The agent does not commit or push unless you ask. To save a finished run:

```
Commit the results folder and the api_names_override.yaml file with a short
message and push to the current branch.
```

## If something goes wrong

| Symptom | What to do |
|---|---|
| `claude` is not recognised | Close and reopen PowerShell. If it persists, rerun step 6 |
| `check_comsol.py` fails | COMSOL path or licence. See `docs/USER_MANUAL.md` section 3. Not an agent problem |
| The agent stops with `ApiNameError` several times | Normal on the first build. Each stop fixes one name. `docs/VERIFY_API_NAMES.md` explains how to read the true name from the COMSOL GUI if the agent cannot find it |
| `BUG: net cooling >= 0.1 K` | The agent must stop here. Read `docs/GERMANIUM_PARAMETERS.md` section 5 before deciding anything |
| The agent wants to change a parameter in `config/` | Refuse, unless you decided that change yourself |
| The session got long or confused | Type `/clear`, then ask it to continue from the step that was running. The stage files in `comsol/models/` let it resume |
