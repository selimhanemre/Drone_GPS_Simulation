# Simulation collection notes

The bundled mission scripts describe the original PX4/Gazebo collection. This release verifies offline processing of the recorded flights; it does not claim a fully reconstructed simulator environment.

## Known environment

- The inspected ULog metadata identifies `PX4_SITL` and PX4 revision `f19558335bc978ec1eb4eae0787b48808100bcfe` for nominal flight 01. Per-flight extraction metadata records each log's revision.
- `gnss_mitm_injector.py` imports `gz.transport13` and `gz.msgs10`, matching the Gazebo Harmonic library family. The exact Gazebo build and operating-system image used for collection were not supplied.
- `run_mission.py` connects to UDP port 14540 and commands a 5 m altitude / 10 m square mission.

Use the upstream [PX4 Gazebo vehicle guide](https://docs.px4.io/main/en/sim_gazebo_gz/vehicles) and [Gazebo Harmonic installation guide](https://gazebosim.org/docs/harmonic/install/) for simulator setup. The upstream x500 launch command is `make px4_sitl gz_x500` from the PX4 checkout. Python transport bindings are documented in [Gazebo Transport 13](https://gazebosim.org/api/transport/13/python.html). Do not assume that installing the pip requirements installs Gazebo or PX4.

## Missing collection prerequisite

The supplied injector subscribes to:

```text
/world/default/model/x500_0/link/base_link/sensor/navsat_sensor/navsat_raw
```

and publishes to the corresponding `.../navsat` topic. This requires a world/model configuration that routes the raw simulated sensor stream through that bridge. That SDF/model modification is absent from the ZIP; stock PX4/Gazebo cannot be assumed to provide the expected routing. The missing configuration must be recovered from the collection environment before claiming repeatable fresh flight generation.

The supplied scripts are retained in `src/missions/`, with only the injector constructor's default onset aligned to its existing CLI value of 25 s. The original copies are in `archive/original-code/`. The mission routine does not verify every command acknowledgement, and some blocking receives can interrupt continuous setpoint streaming. These collection limitations are separate from the verified offline analysis.

For new collection, record the PX4 and Gazebo revisions, world/model files, PX4 parameter export, simulator speed factor, topic routing, random seeds if applicable, and per-flight injection timestamps. Preserve ULogs and an experiment manifest. Run collection only in the intended simulation environment; the mission script issues arming and flight commands to its MAVLink endpoint.

To extract an explicitly selected log after collection:

```bash
python src/pipeline/01_extract_logs.py --ulog /path/to/flight.ulg --output results/local/new-flight
```

The new extractor never guesses the newest file or copies a log to a hard-coded home directory.
