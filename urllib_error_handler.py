import json, os, urllib.request, subprocess
from pathlib import Path

diff = "Some diff content"

sys_prompt = ('Classify this pull request diff risk. Output STRICT JSON with one key `risk` whose value is exactly one of "low","med","high". '
       'HIGH: touches build config, security-sensitive code, native DLL boundaries, secrets, CI workflows. '
       'MED: substantive logic change in non-critical code, schema change, public API addition. '
       'LOW: tests, docs, formatting, small bug fix in isolated function. Output only the JSON.')

# Is the model correct now? Let's add HTTPError printing just in case.
