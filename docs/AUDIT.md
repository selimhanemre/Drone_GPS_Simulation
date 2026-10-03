# Audit and correction record

The supplied ZIP was inspected before publication. Original source files, CSV metrics, and PDF figures are preserved. The versioned release contains the original flight data without the embedded `.git` directory.

| Finding | Evidence | Release treatment |
| :--- | :--- | :--- |
| GNSS extraction used incompatible fields | Horizontal GNSS velocity, latitude, longitude, and altitude are all zero in all 40 supplied synchronized CSVs; the raw logs contain nonzero values | Recover `vehicle_gnss.receiver.*` telemetry; required missing fields raise errors |
| Innovation field mismatch | Supplied code looks for `gps_vvel[0]` / `gps_vvel[1]`; logs expose `gps_hvel[0]` / `gps_hvel[1]` | Correct horizontal field mapping and retain separate test-ratio timestamps |
| Attack labeling disagreed with plots | Original evaluator labels from 20 s, plots mark 25 s, and injector CLI uses 25 s | Project contributor confirmed 25 s on 2 October 2026; revised configuration and figures agree |
| Flight origin can shift when GNSS topic changes | Original sparse GNSS topic starts later than the populated `vehicle_gnss` stream | Persist original 20 ms bin origins in `configs/time_origins.json` and reuse them |
| Nominal training/evaluation overlap | Original analysis trains on all ten nominal flights and evaluates those same flights | Add held-out nominal 06–10 evaluation; retain the original convention as a separate comparison |
| Offline operations were described as real-time | Interpolation and central differences use future samples | Describe this artifact as offline; no measured online runtime is claimed |
| Residual compares different coordinate-frame quantities | IMU body-frame specific force vs NED GNSS acceleration magnitude | Preserve the supplied formulation, document the limitation, and report its false alarms |
| Dependencies, paths, and simulator setup were incomplete | Empty requirements, hard-coded home paths, missing SDF/model modification | Pin dependencies; add explicit CLI paths and reproduction instructions; document missing collection configuration |

## Historical replay comparison

The portable replay intentionally uses the supplied zero-GNSS data, original 20-second labels, sorted input order, and all-nominal training. The reference results remain unchanged.

| Detector | Rounded F1 matches | False-alarm flag matches | Maximum absolute F1 difference |
| :--- | ---: | ---: | ---: |
| IsoForest | 11/40 | 28/40 | 0.090 |
| Leaky_CUSUM | 40/40 | 40/40 | 0.000 |
| Mahalanobis | 40/40 | 40/40 | 0.000 |

The original Isolation Forest environment and training-row order were not recorded. A fixed random seed alone does not guarantee identical fits under reordered input or changed library versions. The present environment and input hashes are recorded in each `run.json`. The replay is therefore a documented comparison, not a claim of full bit-for-bit recovery.

## Scope of corrected results

All 40 ULogs were re-extracted and resynchronized. Both corrected protocols use 25 s, preserve original time origins, and analyze 0–50 s. All three detectors alarm on all five held-out nominal flights with unchanged detector parameters. No threshold tuning was performed to improve this result. See [the full report](RESULTS.md).

The original `fig_physical_deviation.pdf` title refers to physical trajectory divergence, but its plotted quantity is the difference between estimated east position and simulated ground-truth east position. Updated figures name that quantity **east position estimation error**; it does not directly measure deviation from the commanded mission path.
