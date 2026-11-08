# SafeHouse

Team PingFloyd, R Systems Hackathon 2026.

SafeHouse checks the home network you are connected to and lists the risky devices and open ports it finds. It explains each problem in plain Romanian or English and tells you how to fix it. It can also analyse Nmap XML files offline.

Only scan networks you own or are allowed to test. SafeHouse refuses public IPs and anything outside the network you are connected to.

## Requirements

- Python 3.10 or newer
- Nmap, for live scans only. Analysing XML files does not need it.

## Installation

### Windows

1. Install Python from https://www.python.org/downloads/ and tick "Add python.exe to PATH" during setup.
2. Install Nmap from https://nmap.org/download. Keep the "Npcap" option checked during setup.
3. Download the repository: `git clone https://github.com/MeZaip/smarthack-2026-pingfloyd.git`, or download the ZIP from GitHub and unzip it.
4. Double-click `SafeHouse.cmd` in the project folder.

The first start takes about a minute because it installs the dependencies. After that, SafeHouse opens in its own window.

Do not run live scans from WSL. WSL cannot see the devices on your Wi-Fi.

### macOS

```bash
brew install python nmap
git clone https://github.com/MeZaip/smarthack-2026-pingfloyd.git
cd smarthack-2026-pingfloyd
./run.sh
```

Open http://127.0.0.1:8000 in your browser.

### Linux (Debian / Ubuntu)

```bash
sudo apt install python3 python3-venv nmap git
git clone https://github.com/MeZaip/smarthack-2026-pingfloyd.git
cd smarthack-2026-pingfloyd
./run.sh
```

Open http://127.0.0.1:8000 in your browser. On Fedora, use `sudo dnf install python3 nmap git` instead of the first line.

`run.sh` creates a virtual environment in `.venv`, installs `requirements.txt` and starts the app. Press Ctrl+C to stop it.

## Live scan

1. Connect the computer to your own network only.
2. In the app, press "Inspect the house" ("Inspectează casa").
3. Confirm that the network is yours.
4. Accept the system permission prompt. Only Nmap runs with admin rights; the rest of the app runs as a normal user. The prompt depends on the OS:
   - Windows: the UAC dialog.
   - macOS: the administrator password dialog.
   - Linux: the pkexec password dialog.
5. Results appear in 1 to 3 minutes. You get:
   - a score out of 100;
   - the risky devices on a map of the network;
   - the steps to fix each problem.

After you fix something, press "I fixed it, check" on that problem to re-test only that problem.

The same scan from the command line:

```bash
python -m netcheck detect            # shows the network you are connected to
python -m netcheck scan --confirm    # scans it
```

On Windows, use `.venv-windows\Scripts\python` instead of `python`. On macOS and Linux, use `.venv/bin/python`.

## File analysis (offline, no Nmap, no admin rights)

In the app, use one of these:
- "Upload a check": opens a single Nmap `.xml` file.
- "Export CSV": analyses a whole folder of files.

From the command line:

```bash
python -m netcheck analyze <folder-with-xml> --out results
```

This writes `results/findings.csv` and `results/scores.csv`. A file that cannot be read gets `ERROR` in `scores.csv` and the other files are still analysed.

Other useful commands:

```bash
python -m netcheck report scan.xml --lang en                 # plain-language report
python -m netcheck report scan.xml --technical --out r.txt   # detailed report for an IT team
python -m netcheck diff before.xml after.xml                 # what changed between two scans
```

The official Validation Set (with its expected answers) is in `tests/fixtures/validation/`; our own hotspot lab scans, with a before/after pair, are in `tests/fixtures/lab/`.

## AI assistant (optional)

The chat answers questions about your scan. It only uses facts from the scan. If the AI is not available, the chat answers from built-in texts instead.

The AI runs through a small gateway that keeps the API key. The app itself never holds a key. To run the gateway on your own machine:

1. Copy `.env.example` to `.env`.
2. Set `ANTHROPIC_API_KEY=` in that file. `.env` is ignored by git.
3. Start the app with `./run.sh` (or `run.cmd` on Windows). The gateway starts by itself when a key is set.

To start without the AI, use `./run.sh --no-ai` (or `run.cmd -NoAI`).

**Free, without an API key (local model):** install [Ollama](https://ollama.com) (`brew install ollama` on macOS) and
download the model once with `ollama pull qwen3.5:9b` (about 7 GB). `./run.sh` then starts Ollama and the gateway by
itself whenever there is no `ANTHROPIC_API_KEY`. The first answer takes ~30 s while the model loads, then a few seconds.

### Voice: "Talk" (speech to speech)

The **Talk** button next to the language opens voice mode: you speak, the assistant answers out loud, briefly.

* It needs a browser that understands speech: **Chrome, Edge or Safari** (Firefox has no speech recognition, so the
  button is hidden there). Open the app at `http://127.0.0.1:8000`, not from the file, and allow the microphone.
* **The natural voice** (Romanian "Mihai", English "Lessac") is made on this computer by Piper: free, nothing is sent
  anywhere. `./run.sh` installs it once (`requirements-voice.txt` + `tools/get_voices.py`, ~130 MB). If that is not
  possible (offline, a Python without Piper packages), the browser's own voice is used. To install it again:
  `rm .venv/.voice-ok && ./run.sh`.
* On a phone opened over the network (`http://192.168.x.x`) the browser blocks the microphone (it needs HTTPS);
  answers are still read aloud.

## Privacy

- Your scans and history stay on your computer in `~/.netcheck/`. "Delete all data" in the app removes them.
- Full MAC addresses are never saved.
- The AI receives the following:
  - device types;
  - private IP addresses;
  - open ports;
  - the problems found.
- The AI never receives hostnames, MAC addresses or raw scan files.

## Tests

```bash
python -m pytest -q
```

## Project layout

| Folder | Contents |
|---|---|
| `netcheck/` | scanner, rules, scoring, explanations, local web server |
| `gateway/` | AI gateway (holds the API key) |
| `ui/` | web interface |
| `tests/` | tests and example scans |

More technical details are in `TECH_SUMMARY.md`.
