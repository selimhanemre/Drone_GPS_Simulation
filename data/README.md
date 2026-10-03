# Dataset card

This project-provided simulation dataset contains **40 PX4 ULogs**, ten per scenario (`nominal`, `step_attack`, `ramp_attack`, `stealth_attack`). It is intended for offline research on GNSS perturbations and detector behavior in the supplied simulated mission.

## Download options

| Dataset | Command | Extracted location |
| :--- | :--- | :--- |
| Corrected extraction + synchronized flights | `python scripts/download_data.py corrected` | `data/corrected/` |
| Original supplied intermediate + synchronized CSVs | `python scripts/download_data.py supplied` | `data/supplied/processed/` |
| Original 40 ULog files | `python scripts/download_data.py raw` | `data/raw_ulog/` |

All assets are attached to [release v0.1.0](https://github.com/selimhanemre/Drone_GPS_Simulation/releases/tag/v0.1.0). Exact byte sizes and SHA-256 hashes are in [`release-assets.json`](release-assets.json); per-file manifests are in [`manifests/`](manifests/). The ZIP's embedded `.git` directory is not distributed.

## Small example

`example/` contains four unchanged corrected synchronized CSVs: nominal flights 01 and 06, step flight 01, and stealth flight 01. It supports a quick run and CI. Its one-flight nominal training set is different from the five-flight training set in the full benchmark.

## Provenance and schema

Raw logs are preserved byte-for-byte from the supplied `Drone_GPS_Simulation.zip`. `manifests/raw.json` and `manifests/supplied.json` use paths relative to the original archive root; downloaded supplied paths gain the `data/supplied/` prefix. `manifests/corrected.json` uses final extracted paths. The original data contains 200 intermediate CSVs and 40 synchronized CSVs. Corrected extraction adds independent ratio CSVs and per-flight metadata.

| Corrected synchronized field | Meaning / units |
| :--- | :--- |
| `timestamp` | Exact 20 ms grid timestamp, microseconds since PX4 boot |
| `time_sec` | Seconds from the preserved original synchronized origin |
| `gnss_lat`, `gnss_lon`, `gnss_alt` | Logged latitude/longitude in degrees and altitude in meters |
| `gnss_vel_n`, `gnss_vel_e`, `gnss_vel_d` | GNSS velocity components, m/s, NED |
| `imu_accel_x/y/z` | Body-frame accelerometer specific force, m/s² |
| `imu_gyro_x/y/z` | Body-frame angular rate, rad/s |
| `ekf_x/y/z`, `ekf_vx/vy/vz` | Estimated local NED position (m) and velocity (m/s) |
| `gt_x_true/y_true/z_true`, `gt_vx_true/vy_true/vz_true` | Simulated ground-truth local state, m and m/s |
| `innov_*` | Horizontal GNSS velocity/position innovations |
| `ratio_*` | Corresponding innovation test ratios |

The corrected extractor prefers `vehicle_gnss.receiver.*`, which is populated at a higher logged rate than `sensor_gnss` in these files. It uses real field names and retains separate topic timestamps. `manifests/synchronization.json` records each flight's origin, duration, row count, and nonzero GNSS velocity count. The corrected files end at the last common observed interval; the historical interpolation extrapolated some endpoints.

## Labels and limits

Scenario comes from the original folder label. The 25-second onset relative to the supplied synchronized flight clock was confirmed by the project contributor on 2 October 2026. The archive has no independent injection-event log, so the labeling provenance is contributor confirmation, not a detected event marker. The fixed per-flight origins are stored in `configs/time_origins.json`.

These are simulated trajectories with one mission design and a small number of repeated trials. They do not establish performance across real aircraft, receivers, environments, or attack conditions. See the [methodology](../docs/METHODOLOGY.md) for residual-frame and offline-processing limitations.

The project-provided dataset is distributed under the repository's [MIT License](../LICENSE). Cite the software version and identify the exact dataset variant used in any derived study.
