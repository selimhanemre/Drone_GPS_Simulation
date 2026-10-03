"""Deterministic offline detector evaluation and transparent flight-level metrics."""
from pathlib import Path
import hashlib
import importlib.metadata
import json
import platform
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import confusion_matrix, f1_score, precision_score, recall_score

CATEGORIES = ('nominal', 'step_attack', 'ramp_attack', 'stealth_attack')
DETECTORS = ('Mahalanobis', 'IsoForest', 'Leaky_CUSUM')


def validate_config(config):
    positive = ('sample_period_sec','analysis_end_sec','gnss_smoothing_samples',
                'residual_smoothing_samples','z_threshold','cusum_threshold','isolation_estimators')
    for name in positive:
        if not np.isfinite(config[name]) or config[name] <= 0:
            raise ValueError(f'{name} must be finite and positive')
    if not 0 <= config['attack_onset_sec'] < config['analysis_end_sec']:
        raise ValueError('Attack onset must lie within the analysis window')
    if not 0 <= config['cusum_leak'] <= 1 or config['cusum_drift'] < 0:
        raise ValueError('Invalid CUSUM leak or drift')
    if not 0 < config['isolation_contamination'] <= 0.5:
        raise ValueError('Isolation Forest contamination must be in (0, 0.5]')


def load_flight(path, config, allow_degenerate=False):
    frame = pd.read_csv(path)
    columns = ['time_sec','gnss_vel_n','gnss_vel_e','imu_accel_x','imu_accel_y','ekf_y','gt_y_true']
    if missing := set(columns) - set(frame.columns):
        raise ValueError(f'{path}: missing columns {sorted(missing)}')
    frame = frame.loc[frame.time_sec <= config['analysis_end_sec']].reset_index(drop=True)
    if len(frame) < 2 or not np.isfinite(frame[columns].to_numpy()).all():
        raise ValueError(f'{path}: at least two finite rows required')
    if not np.isclose(frame.time_sec.iloc[0], 0) or not np.allclose(np.diff(frame.time_sec),config['sample_period_sec'],rtol=0,atol=1e-8):
        raise ValueError(f'{path}: time must begin at zero with uniform configured spacing')
    if not allow_degenerate and not np.any(frame[['gnss_vel_n','gnss_vel_e']].to_numpy()):
        raise ValueError(f'{path}: both horizontal GNSS velocity channels are all zero; inspect extraction. Use --allow-degenerate-gnss only for legacy replay.')
    return frame


def residuals(frame, config):
    dt = config['sample_period_sec']
    magnitude = np.hypot(np.gradient(frame.gnss_vel_n,dt),np.gradient(frame.gnss_vel_e,dt))
    smoothed = pd.Series(magnitude).rolling(int(config['gnss_smoothing_samples']),min_periods=1).mean().to_numpy()
    raw = np.abs(smoothed - np.hypot(frame.imu_accel_x,frame.imu_accel_y))
    mean = pd.Series(raw).rolling(int(config['residual_smoothing_samples']),min_periods=1).mean().to_numpy()
    return np.asarray(raw),mean


def cusum(scores, leak, drift):
    values = np.empty(len(scores))
    value = 0.0
    for i,score in enumerate(scores):
        value = max(0.0,leak*value+score-drift)
        values[i] = value
    return values


def latch(predictions):
    return np.maximum.accumulate(np.asarray(predictions,dtype=int))


def score_flight(time, predicted, category, onset):
    time = np.asarray(time)
    truth = ((time >= onset) & (category != 'nominal')).astype(int)
    predicted = np.asarray(predicted,dtype=int)
    tn,fp,fn,tp = confusion_matrix(truth,predicted,labels=[0,1]).ravel()
    false_alarm = bool(np.any((truth == 0) & (predicted == 1)))
    hits = np.flatnonzero((truth == 1) & (predicted == 1))
    alarm = np.flatnonzero(predicted)
    latency = float(time[hits[0]]-onset) if len(hits) and not false_alarm else None
    return {'F1_Score':round(float(f1_score(truth,predicted,zero_division=0)),3),
            'Precision':float(precision_score(truth,predicted,zero_division=0)),
            'Recall':float(recall_score(truth,predicted,zero_division=0)),
            'Latency_sec':latency,'False_Positive':int(false_alarm),
            'First_Alarm_sec':float(time[alarm[0]]) if len(alarm) else None,
            'Clean_Detection':int(category != 'nominal' and len(hits)>0 and not false_alarm),
            'Samples':len(time),'TN':int(tn),'FP':int(fp),'FN':int(fn),'TP':int(tp)}


def select_protocol(paths, protocol):
    nominal = [p for p in paths if p.parent.name == 'nominal']
    if not nominal: raise ValueError('At least one nominal training flight is required')
    if protocol == 'legacy': return nominal,paths
    if len(nominal) < 2: raise ValueError('Held-out protocol requires at least two nominal flights')
    train = nominal[:len(nominal)//2]
    test = [p for p in paths if p not in train]
    return train,test


def evaluate(data_dir, output, config, protocol='held-out', allow_degenerate=False):
    from plots import plot_diagnostics
    validate_config(config)
    paths = [p for category in CATEGORIES for p in sorted((Path(data_dir)/category).glob('*.csv'))]
    train,test = select_protocol(paths,protocol)
    flights = {p:load_flight(p,config,allow_degenerate) for p in paths}
    for p in test:
        if p.parent.name != 'nominal' and flights[p].time_sec.iloc[-1] <= config['attack_onset_sec']:
            raise ValueError(f'{p}: flight ends before attack onset')
    features = {p:residuals(d,config) for p,d in flights.items()}
    baseline = np.concatenate([features[p][1] for p in train])
    mean,std = float(np.mean(baseline)),float(np.std(baseline))
    if not np.isfinite(std) or std <= np.finfo(float).eps:
        raise ValueError('Nominal residual has zero variance; cannot standardize detectors')
    forest = IsolationForest(n_estimators=int(config['isolation_estimators']),contamination=config['isolation_contamination'],random_state=int(config['random_seed']))
    forest.fit(baseline.reshape(-1,1))
    records,examples = [],{}
    for path in test:
        frame = flights[path]
        raw,rolling = features[path]
        z = (rolling-mean)/std
        memory = cusum(z,config['cusum_leak'],config['cusum_drift'])
        predictions = {'Mahalanobis':rolling > mean+config['z_threshold']*std,
                       'IsoForest':forest.predict(rolling.reshape(-1,1)) == -1,
                       'Leaky_CUSUM':memory > config['cusum_threshold']}
        for detector,predicted in predictions.items():
            records.append({'Flight':f'{path.parent.name}/{path.stem}','Category':path.parent.name,'Detector':detector,
                            **score_flight(frame.time_sec,latch(predicted),path.parent.name,config['attack_onset_sec'])})
        examples.setdefault(path.parent.name,{'frame':frame,'raw':raw,'rolling':rolling,'z':z,'cusum':memory,'flight':path.stem})
    output = Path(output)
    (output/'metrics').mkdir(parents=True,exist_ok=True)
    result = pd.DataFrame(records)
    result.to_csv(output/'metrics/detector_benchmark.csv',index=False)
    summary = result.groupby(['Category','Detector'],sort=False).agg(
        Flights=('Flight','count'),F1_mean=('F1_Score','mean'),F1_std=('F1_Score','std'),
        False_alarm_flights=('False_Positive','sum'),Clean_detections=('Clean_Detection','sum'),
        Latency_mean_sec=('Latency_sec','mean'),Latency_count=('Latency_sec','count')).reset_index()
    summary.to_csv(output/'metrics/summary.csv',index=False)
    manifest = {'protocol':protocol,'config':config,'nominal_mean':mean,'nominal_std':std,
                'training_flights':[f'{p.parent.name}/{p.stem}' for p in train],
                'evaluation_flights':[f'{p.parent.name}/{p.stem}' for p in test],
                'allow_degenerate_gnss':allow_degenerate,'python':platform.python_version(),'platform':platform.platform(),
                'packages':{n:importlib.metadata.version(n) for n in ['numpy','pandas','scikit-learn','matplotlib','pyulog']},
                'inputs':{f'{p.parent.name}/{p.name}':hashlib.file_digest(p.open('rb'),'sha256').hexdigest() for p in paths},
                'limitations':['Offline resampling and central numerical derivatives use future samples; not a real-time performance measurement.',
                               'IMU body-frame horizontal specific force is compared with NED GNSS acceleration magnitude without attitude/gravity compensation.',
                               'Latency excludes flights with any pre-onset false alarm; read latency_count and false_alarm_flights together.']}
    (output/'run.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    plot_diagnostics(examples,config,output/'figures',protocol)
    print(summary.to_string(index=False))
    return result
