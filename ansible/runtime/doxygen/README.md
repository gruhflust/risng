# RISng Doxygen runtime playbook

Alias: `doxyris`
Playbook: `ansible/runtime/doxygen/doxygen.yml`

## What it does
- ensures `doxygen` + `graphviz` are installed
- generates a timestamped documentation run under `~/docdeliver/<timestamp>-doxygen/`
- creates HTML docs with recursive input from the configured source tree
- writes `RUNINFO.txt` with source path + detected git branch/commit

## Defaults
- Source tree: `~/botrepo/risng_code`
- Output root: `~/docdeliver`

## Override via env
- `DOXYGEN_SOURCE_DIR=/path/to/code doxyris`
- `DOXYGEN_OUTPUT_ROOT=/path/to/output doxyris`

## Next step recommendation
Add a project-specific `Doxyfile.in` and tune:
- `FILE_PATTERNS`
- `EXCLUDE`/`EXCLUDE_PATTERNS`
- diagram options (`DOT_GRAPH_MAX_NODES`, `CALL_GRAPH`, `CALLER_GRAPH`)
for faster and more focused docs.
