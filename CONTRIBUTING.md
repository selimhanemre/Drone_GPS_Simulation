# Contributing

Open an issue describing the problem or proposed experiment. For analysis changes, submit a pull request with the configuration, input file hashes, flight split, and before/after metrics. Include false-alarm counts and the number of observations behind any reported average latency.

Use Python 3.12, install `requirements-dev.txt`, and run `python -m pytest -q`. Run the four-flight example before submitting changes. Keep downloaded datasets under the ignored `data/raw_ulog`, `data/supplied`, or `data/corrected` directories; put local outputs under `results/local`.

Preserve `results/supplied` and `archive/original-code` as historical evidence. New benchmark results belong in a clearly named directory with a `run.json` manifest. Do not replace a reference result without explaining the data, label, environment, or method change that caused the difference.

For collection improvements, include the missing Gazebo world/model routing, versioned simulator configuration, and event timestamps. Use separate training and evaluation flights when choosing new parameters. Contributions are accepted under the MIT License.
