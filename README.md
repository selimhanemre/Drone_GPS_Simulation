# Drone GPS Simulation

**Code, simulation data, and supplied results for GNSS spoofing research.**

[![License: MIT](https://img.shields.io/badge/License-MIT-167d9a.svg)](LICENSE)
[![Original project](https://img.shields.io/badge/Project-original_source-7254af.svg)](https://github.com/selimhanemre/Drone_GPS_Simulation/releases/tag/v0.1.1)

[Research](#research) · [Project contents](#project-contents) · [Original workflow](#original-workflow) · [Results](#supplied-results) · [Citation](#citation)

## Research

**Defending the Autonomous Airspace: Real-Time Defense of Stealthy GNSS Spoofing via Kinematic Memory**

Selimhan Dagtas · Muzakkiruddin Ahmed Mohammed · Abdelrahman Elfikky

The project contains a PX4/Gazebo flight simulation workflow and an analysis of three detector baselines: Mahalanobis, Isolation Forest, and leaky CUSUM. The dataset contains **40 recorded simulation flights**, with ten flights in each of four categories: nominal, step attack, ramp attack, and stealth attack.

This repository presents the original project supplied in `Drone_GPS_Simulation.zip`. All **291 source, data, requirements, and result files** retain their original paths and byte content. Repository additions are limited to this README, the MIT license, citation metadata, and Git housekeeping files. The archive's embedded `.git` directory is excluded.

## Project contents

```text
Drone_GPS_Simulation/
├── src/
│   ├── missions/
│   │   ├── run_mission.py
│   │   └── gnss_mitm_injector.py
│   └── pipeline/
│       ├── 01_extract_logs.py
│       ├── 02_resample_sync.py
│       ├── 03_evaluate_defenses.py
│       └── 03b_visualize_internals.py
├── data/
│   ├── raw_ulog/                 # 40 original PX4 flight logs
│   └── processed/                # 200 intermediate CSVs
│       └── synced/               # 40 synchronized flight CSVs
├── results/
│   ├── metrics/detector_benchmark.csv
│   └── figures/                  # Three supplied PDF figures
└── requirements.txt              # Original file, supplied empty
```

| Location | Contents |
| :--- | :--- |
| [`src/missions/`](src/missions/) | Waypoint mission and simulated GNSS perturbation scripts |
| [`src/pipeline/`](src/pipeline/) | Original extraction, synchronization, evaluation, and visualization scripts |
| [`data/raw_ulog/`](data/raw_ulog/) | Original `.ulg` files grouped by scenario |
| [`data/processed/`](data/processed/) | Original telemetry tables and synchronized CSVs |
| [`results/metrics/`](results/metrics/) | Supplied per-flight detector benchmark |
| [`results/figures/`](results/figures/) | Supplied research figures |

## Getting the project

```bash
git clone https://github.com/selimhanemre/Drone_GPS_Simulation.git
cd Drone_GPS_Simulation
```

The full dataset is included, so this is a substantial download. You can also download the complete project through **Code → Download ZIP** or the source archives attached to [release v0.1.1](https://github.com/selimhanemre/Drone_GPS_Simulation/releases/tag/v0.1.1).

## Original workflow

The original scripts import NumPy, pandas, Matplotlib, scikit-learn, pyulog, and pymavlink. The simulation injector additionally requires Gazebo's `gz.transport13` and `gz.msgs10` Python bindings, plus a configured PX4/Gazebo simulation environment. The supplied `requirements.txt` is empty; exact dependency versions were not recorded in the archive.

The scripts retain the original environment paths, including `/home/ualr/Documents/Drone_GPS_Simulation`, `~/Documents/Drone_GPS_Simulation`, and the PX4 log directory under `~/PX4-Autopilot/`. Check these paths and the simulator topic configuration before running the collection workflow. The original Gazebo world/model configuration is not included in the archive.

The original pipeline sequence is:

```bash
# Extract the latest local PX4 log into a scenario category.
python src/pipeline/01_extract_logs.py nominal

# Synchronize the extracted telemetry.
python src/pipeline/02_resample_sync.py

# Evaluate the original detector implementation and generate its outputs.
python src/pipeline/03_evaluate_defenses.py

# Display the original diagnostic visualization.
python src/pipeline/03b_visualize_internals.py
```

Valid extraction categories are `nominal`, `step_attack`, `ramp_attack`, and `stealth_attack`. Evaluation writes to the configured project's `results` directory; preserve a copy of the supplied results before running your own experiments.

## Supplied results

The following files are the original outputs delivered with the project. They have not been regenerated or replaced in this release.

| File | Format |
| :--- | :--- |
| [Detector benchmark](results/metrics/detector_benchmark.csv) | CSV containing flight, category, detector, F1, latency, and false-positive fields |
| [CUSUM comparison](results/figures/fig_cusum_comparison.pdf) | PDF |
| [Stealth detector internals](results/figures/fig_stealth_internals.pdf) | PDF |
| [Physical deviation figure](results/figures/fig_physical_deviation.pdf) | PDF |

Use the original scripts and their parameter settings when interpreting these archived outputs. The release verifies faithful preservation of the supplied files; it does not add new experimental results or establish independent validation of the reported performance.

## Citation

The paper title and author order above were supplied by the project contributors. Publication venue and DOI are not specified in this release. Use [`CITATION.cff`](CITATION.cff) or GitHub's **Cite this repository** menu to cite this version of the software and dataset.

```bibtex
@misc{dagtas2026dronegps,
  author = {Dagtas, Selimhan and Mohammed, Muzakkiruddin Ahmed and Elfikky, Abdelrahman},
  title = {{Drone GPS Simulation}},
  year = {2026},
  howpublished = {Research code and simulation dataset, version 0.1.1},
  url = {https://github.com/selimhanemre/Drone_GPS_Simulation},
  note = {Associated research: Defending the Autonomous Airspace: Real-Time Defense of Stealthy GNSS Spoofing via Kinematic Memory}
}
```

## License

Project code, documentation, and project-provided simulation data are available under the [MIT License](LICENSE). External dependencies retain their respective licenses.
