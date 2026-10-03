# Reproducing the artifact

Use Python 3.12 and install `requirements.txt`. Exact versions of the analysis dependencies are pinned; `requirements-lock.txt` records the complete tested Python environment, including optional simulation and validation packages. Each analysis output also records its actual package versions in `run.json`.

## Full corrected evaluation

Run from the repository root:

```bash
python scripts/download_data.py corrected
python src/pipeline/03_evaluate_defenses.py --data-dir data/corrected/synced --output results/local/full --protocol held-out
python scripts/compare_results.py results/corrected-held-out/metrics/detector_benchmark.csv results/local/full/metrics/detector_benchmark.csv
```

`held-out` trains on nominal flights 01–05 and evaluates nominal 06–10 plus all 30 attack flights. It never trains on an attack flight. `configs/research.json` sets the 25-second onset and a 0–50-second evaluation window. Output has 105 detector/flight rows. A missing required field, nonfinite value, irregular time grid, or degenerate horizontal GNSS channels causes a clear error.

## Rebuild from the 40 raw logs

```bash
python scripts/download_data.py raw
python src/pipeline/01_extract_logs.py --raw-dir data/raw_ulog --output results/local/rebuilt/extracted
python src/pipeline/02_resample_sync.py --input results/local/rebuilt/extracted --output results/local/rebuilt/synced --time-origins configs/time_origins.json
python src/pipeline/03_evaluate_defenses.py --data-dir results/local/rebuilt/synced --output results/local/rebuilt/evaluation --protocol held-out
python scripts/compare_results.py results/corrected-held-out/metrics/detector_benchmark.csv results/local/rebuilt/evaluation/metrics/detector_benchmark.csv
```

The extractor explicitly selects instance 0. For this archive it uses the populated `vehicle_gnss.receiver.*` fields. It also supports the modern `sensor_gnss` schema and legacy `vehicle_gps_position` names when those topics are available. Missing required telemetry raises an error. Innovations and test ratios are exported with separate timestamps before resampling.

The fixed origins in `configs/time_origins.json` preserve the original 50 Hz flight clock. They were recovered from each supplied CSV's first timestamp, rounded down to its 20,000-microsecond resampling bin. They are dataset-specific; do not reuse them for newly collected flights. The new synchronization drops unobserved endpoints rather than extrapolating them.

## Historical replay

```bash
python scripts/download_data.py supplied
python src/pipeline/03_evaluate_defenses.py --data-dir data/supplied/processed/synced --output results/local/legacy --config configs/legacy.json --protocol legacy --allow-degenerate-gnss
```

This intentionally allows the broken zero-GNSS channels and reproduces the historical 20-second label convention. It exists for auditing, not for drawing conclusions about detector effectiveness. The supplied CSV and PDF figures remain unchanged in `results/supplied/`.

Mahalanobis and leaky CUSUM reproduce the supplied rounded F1 and false-alarm flags for all 40 flights. Isolation Forest differs: the original package environment and nominal input order were not recorded. This release sorts files and records a fixed seed and environment. See [the comparison report](AUDIT.md).

To isolate the effect of the nominal split on the corrected dataset:

```bash
python src/pipeline/03_evaluate_defenses.py --data-dir data/corrected/synced --output results/local/all-nominal --protocol legacy
```

This uses the corrected 25-second configuration but trains on all ten nominal flights and evaluates them again. Treat its nominal false-alarm result as in-sample.

## Files and verification

The downloader checks the published ZIP hash before extracting into `data/`. It rejects unsafe paths and refuses to overwrite differing local files. To use a manually downloaded asset:

```bash
python scripts/download_data.py corrected --archive /path/to/drone-gps-corrected-v0.1.0.zip
```

The `data/manifests/` files record per-file SHA-256 hashes and sizes. `data/release-assets.json` pins ZIP filenames, URLs, sizes, and hashes. Figures may have different PDF metadata across machines; compare numerical CSVs rather than PDF bytes. Latency comparison uses a small floating-point tolerance.

## Scope of verification

All 40 raw logs were extracted and synchronized, and both corrected evaluation protocols were executed. The included example and automated tests run without a simulator. Fresh PX4/Gazebo flight collection and real-time deployment were not executed for this release.
