"""Portable, schema-aware extraction and offline synchronization of PX4 logs."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from pyulog import ULog

CATEGORIES = ('nominal', 'step_attack', 'ramp_attack', 'stealth_attack')


def required(data, *candidates):
    """Select a real field; never replace missing telemetry with zero."""
    for key in candidates:
        if key in data:
            return data[key]
    raise ValueError(f'Missing required field; expected one of {candidates}')


def gnss_frame(data, prefix=''):
    modern = prefix + 'latitude' in data
    fields = {'lat': ('latitude', 'lat'), 'lon': ('longitude', 'lon'),
              'alt': ('altitude_msl', 'alt'), 'vel_n': ('vel_north', 'vel_n_m_s'),
              'vel_e': ('vel_east', 'vel_e_m_s'), 'vel_d': ('vel_down', 'vel_d_m_s')}
    values = {'timestamp': required(data, prefix + 'timestamp', 'timestamp')}
    for out, names in fields.items():
        values[out] = required(data, *(prefix + n for n in names))
    frame = pd.DataFrame(values)
    if not modern:
        frame[['lat', 'lon']] /= 1e7
        frame['alt'] /= 1e3
    return frame


def extract_log(path, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    ulog = ULog(str(path))
    def dataset(name):
        try:
            return ulog.get_dataset(name, multi_instance=0).data
        except (KeyError, IndexError) as exc:
            raise ValueError(f'{path}: required topic {name} instance 0 is absent') from exc

    available = {d.name for d in ulog.data_list if d.multi_id == 0}
    if 'vehicle_gnss' in available:
        gnss_topic, prefix = 'vehicle_gnss', 'receiver.'
    elif 'sensor_gnss' in available:
        gnss_topic, prefix = 'sensor_gnss', ''
    else:
        gnss_topic, prefix = 'vehicle_gps_position', ''
    frames = {'gnss': gnss_frame(dataset(gnss_topic), prefix)}
    mappings = {
        'ekf_estimated': ('vehicle_local_position', {k: k for k in ('x','y','z','vx','vy','vz')}),
        'ground_truth': ('vehicle_local_position_groundtruth', {k+'_true': k for k in ('x','y','z','vx','vy','vz')}),
        'imu': ('sensor_combined', {**{f'accel_{axis}': f'accelerometer_m_s2[{i}]' for i,axis in enumerate('xyz')},
                                  **{f'gyro_{axis}': f'gyro_rad[{i}]' for i,axis in enumerate('xyz')}}),
        'ekf_innovations': ('estimator_innovations', {'vel_innov_n':'gps_hvel[0]', 'vel_innov_e':'gps_hvel[1]',
                                                   'pos_innov_n':'gps_hpos[0]', 'pos_innov_e':'gps_hpos[1]'}),
        'ekf_test_ratios': ('estimator_innovation_test_ratios', {'vel_ratio_n':'gps_hvel[0]', 'vel_ratio_e':'gps_hvel[1]',
                                                             'pos_ratio_n':'gps_hpos[0]', 'pos_ratio_e':'gps_hpos[1]'})}
    for name, (topic, fields) in mappings.items():
        data = dataset(topic)
        frames[name] = pd.DataFrame({'timestamp':required(data,'timestamp'), **{k:required(data,v) for k,v in fields.items()}})
    for name, frame in frames.items():
        frame.to_csv(output / f'{name}.csv', index=False)
    metadata = {'raw_file':Path(path).name, 'gnss_topic':gnss_topic, 'gnss_instance':0,
                'gnss_samples':len(frames['gnss']), 'timestamp_unit':'microseconds since PX4 boot',
                'px4_git_revision':ulog.msg_info_dict.get('ver_sw'), 'hardware':ulog.msg_info_dict.get('ver_hw'),
                'field_policy':'required fields raise errors; no silent zero filling'}
    (output / 'extraction.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    return metadata


def sync_flight(flight_dir, output, period_ms=20, max_gap_sec=2.0, time_origin_us=None):
    """Offline interpolation inside each sensor's observed time span only."""
    names = {'imu':'imu', 'gnss':'gnss', 'ekf':'ekf_estimated', 'gt':'ground_truth',
             'innov':'ekf_innovations', 'ratio':'ekf_test_ratios'}
    frames = []
    for prefix, name in names.items():
        frame = pd.read_csv(Path(flight_dir) / f'{name}.csv')
        if len(frame) < 2 or 'timestamp' not in frame:
            raise ValueError(f'{name}: at least two timestamped rows required')
        frame = frame.sort_values('timestamp').drop_duplicates('timestamp')
        frame.index = pd.to_datetime(frame.pop('timestamp'), unit='us')
        frame = frame.add_prefix(prefix + '_')
        sampled = frame.resample(f'{period_ms}ms').mean()
        interpolated = sampled.interpolate(method='time', limit_area='inside')
        # Reject long unobserved spans instead of bridging sensor outages.
        observed = sampled.notna().all(axis=1)
        time = pd.Series(sampled.index, index=sampled.index).where(observed)
        gaps = (time.bfill() - time.ffill()).dt.total_seconds()
        interpolated.loc[gaps > max_gap_sec] = np.nan
        frames.append(interpolated)
    combined = pd.concat(frames, axis=1).dropna()
    if time_origin_us is not None:
        combined = combined.loc[combined.index >= pd.to_datetime(time_origin_us, unit='us')]
    if len(combined) < 2:
        raise ValueError('No common finite telemetry interval')
    diffs = np.diff(combined.index.as_unit('ns').asi8) / 1e9
    if not np.allclose(diffs, period_ms / 1000):
        raise ValueError(f'Telemetry contains an internal gap; segment the flight before evaluating: {diffs[diffs > period_ms / 1000 + 1e-6]}')
    origin = int(combined.index[0].value // 1000)
    if time_origin_us is not None and origin != time_origin_us:
        raise ValueError('Requested time origin is outside the complete telemetry interval')
    combined.insert(0, 'timestamp', combined.index.as_unit('ns').asi8 // 1000)
    combined['time_sec'] = (combined.index - combined.index[0]).total_seconds()
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(output, index=False)
    return {'samples':len(combined), 'time_origin_px4_us':origin, 'duration_sec':float(combined.time_sec.iloc[-1]),
            'gnss_nonzero_horizontal_values':int(np.count_nonzero(combined[['gnss_vel_n','gnss_vel_e']].values))}
