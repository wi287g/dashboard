---
name: Pipeline broken / fetch failure
about: Report that the automated data pipeline failed or produced bad output
title: "[PIPELINE] <script name> — <brief description of failure>"
labels: pipeline, bug
assignees: ""
---

## Which script failed
<!-- fetch_287g.py | parse_aclu_reports.py | merge_datasets.py | GH Actions workflow -->

## Error or symptom
<!-- Paste the error message, log output, or describe what bad data appeared -->
```
<paste error or log here>
```

## When it started failing
<!-- Date, GH Actions run URL, or commit SHA if known -->

## Suspected cause
<!-- e.g. ICE changed their page structure, ACLU report PDF has a new layout,
     BJS changed column names, rate limit hit, etc. -->

## Steps to reproduce locally
```bash
# e.g.
pip install -r requirements.txt
python scripts/fetch_287g.py
```

## Proposed fix / investigation needed
<!-- If you have a patch or know where to look, describe it here -->
