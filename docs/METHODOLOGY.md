# Methodology and interpretation

## Simulation scenarios

The supplied collection code commands a 10 m × 10 m waypoint box at a nominal altitude of 5 m. The four directory labels describe the intended collection scenarios; the full world/model configuration was not supplied.

| Scenario | Supplied simulated perturbation after onset |
| :--- | :--- |
| `nominal` | No perturbation |
| `step_attack` | 15 m east position offset and 5 m/s east velocity offset |
| `ramp_attack` | East displacement 0.5 × 0.25 × t² m and velocity 0.25 × t m/s |
| `stealth_attack` | East displacement 0.5 × 0.05 × t² m and velocity 0.05 × t m/s |

Here `t` is elapsed time after injection. The collector uses wall-clock time from its first received message. The analysis uses the preserved synchronized flight clock, with **25 s** confirmed by the project contributor on 2 October 2026. An independent injector event log was not present in the ZIP. New collections should record the injection event in the same clock as their telemetry.

## Offline feature pipeline

1. Extract required ULog fields, retaining independent sensor timestamps.
2. Sort and deduplicate timestamps, average within 20 ms bins, and interpolate inside observed spans. Reject internal gaps exceeding the configured two-second limit. Preserve the supplied time origin for each archived flight.
3. Analyze samples from 0 through 50 s inclusive. This is a fixed evaluation horizon, not an automatically detected crash time.
4. Differentiate north/east GNSS velocities numerically at 50 Hz. Smooth the horizontal acceleration magnitude over ten samples.
5. Take the absolute difference between this value and the body-frame horizontal IMU acceleration magnitude; smooth that residual over 25 samples.

In compact form, with rolling mean operator `MA`:

```text
g[k] = MA_10(sqrt((dv_n/dt)^2 + (dv_e/dt)^2))
r[k] = abs(g[k] - sqrt(imu_x[k]^2 + imu_y[k]^2))
m[k] = MA_25(r[k])
z[k] = (m[k] - nominal_mean) / nominal_std
```

The IMU quantity is body-frame specific force; it is not rotated into NED or gravity-compensated. Changes in attitude can therefore contribute to the residual. Interpolation and NumPy's central gradient use future samples. This implementation is an offline baseline and cannot establish causal, real-time detection latency.

## Detectors and evaluation

| CSV detector label | Implemented rule |
| :--- | :--- |
| `Mahalanobis` | One-sided scalar rule `m > mean + 3 × std`; this is not a multivariate Mahalanobis-distance implementation |
| `IsoForest` | Isolation Forest on the single smoothed residual; 100 trees, contamination 0.01, random seed 42 |
| `Leaky_CUSUM` | `S[k] = max(0, 0.85 × S[k-1] + z[k] - 0.5)`; alarm when `S > 10` |

Alarms are latched for the remainder of a flight. Attack flights are labeled positive at and after 25 s; nominal flights contain no positive labels. The main run trains only on nominal 01–05, evaluating nominal 06–10 and all attack flights. These are flight-level partitions, not shuffled time samples. This is one fixed split, not cross-validation or independent real-world validation.

`F1_Score`, precision, and recall are sample-based. Summary F1 is an unweighted mean across flights, and its sample standard deviation is reported. F1 is zero by convention on all-negative nominal flights; **use the nominal false-alarm count instead**.

`False_Positive` indicates any alarm before onset (or anywhere in a nominal flight). `Latency_sec` is defined only if a flight has a true-positive alarm and no earlier false alarm. An empty latency is not zero: it means no qualifying clean detection. `Latency_count` states how many flights contributed to the conditional mean. `Clean_Detection`, `First_Alarm_sec`, and the sample confusion counts allow independent inspection.

## What remains to establish

The present parameters produce false alarms on every held-out nominal flight. Before using the artifact to support a reliable-defense claim, investigate frame/gravity compensation, causal feature computation, training-only calibration, and independent validation. Record collection configuration and injection timestamps, and evaluate multiple held-out partitions. Do not tune thresholds against the held-out flights while continuing to call them an independent test set.
