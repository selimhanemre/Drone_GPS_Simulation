import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src/pipeline'))
from telemetry import gnss_frame, sync_flight
from analysis import cusum, latch, load_flight, score_flight, select_protocol, validate_config

@pytest.fixture
def config():
    return json.loads((ROOT/'configs/research.json').read_text())

def test_modern_nested_gnss_units_are_preserved():
    data={'receiver.'+k:np.array(v) for k,v in {
        'timestamp':[1000000,1100000], 'latitude':[47.,47.1], 'longitude':[8.,8.1],
        'altitude_msl':[5.,6.], 'vel_north':[2.,3.], 'vel_east':[4.,5.], 'vel_down':[0.,0.]}.items()}
    frame=gnss_frame(data,'receiver.')
    np.testing.assert_array_equal(frame.vel_e,[4.,5.])
    np.testing.assert_array_equal(frame.lat,[47.,47.1])
    np.testing.assert_array_equal(frame.alt,[5.,6.])

def test_legacy_gnss_units_are_converted():
    data={k:np.array(v) for k,v in {'timestamp':[1000000], 'lat':[473000000], 'lon':[85000000],
          'alt':[5000], 'vel_n_m_s':[2.], 'vel_e_m_s':[4.], 'vel_d_m_s':[0.]}.items()}
    frame=gnss_frame(data)
    assert frame.lat.iloc[0] == pytest.approx(47.3)
    assert frame.alt.iloc[0] == 5

def test_missing_gnss_field_never_becomes_zero():
    with pytest.raises(ValueError,match='Missing required field'):
        gnss_frame({'timestamp':np.array([0])})

def test_onset_boundary_and_latency():
    metrics=score_flight([24.98,25,25.02,25.04],[0,0,1,1],'stealth_attack',25)
    assert metrics['Latency_sec'] == pytest.approx(.02)
    assert metrics['TP']==2 and metrics['FN']==1 and metrics['TN']==1

def test_pre_onset_latched_alarm_is_not_zero_latency_detection():
    pred=latch([0,1,0,0])
    assert pred.tolist()==[0,1,1,1]
    metrics=score_flight([24,24.98,25,25.02],pred,'step_attack',25)
    assert metrics['False_Positive']==1
    assert metrics['Latency_sec'] is None and metrics['Clean_Detection']==0

def test_cusum_resets_and_retains_memory():
    np.testing.assert_allclose(cusum([-.5,2,0,-10],.85,.5),[0,1.5,.775,0])

def test_held_out_flights_do_not_leak():
    paths=[Path('nominal')/f'flight_{n:02d}.csv' for n in range(1,11)] + [Path('step_attack/flight_01.csv')]
    train,test=select_protocol(paths,'held-out')
    assert len(train)==5 and len(test)==6
    assert set(train).isdisjoint(test)
    assert all(p.parent.name=='nominal' for p in train)

def test_zero_gnss_data_rejected_by_default(tmp_path,config):
    frame=pd.read_csv(ROOT/'data/example/nominal/flight_01.csv')
    frame[['gnss_vel_n','gnss_vel_e']]=0
    p=tmp_path/'broken.csv';frame.to_csv(p,index=False)
    with pytest.raises(ValueError,match='all zero'): load_flight(p,config)
    assert len(load_flight(p,config,allow_degenerate=True))>0

def test_irregular_time_grid_rejected(tmp_path,config):
    frame=pd.read_csv(ROOT/'data/example/nominal/flight_01.csv').iloc[:5].copy()
    frame.loc[2,'time_sec']+=.01
    p=tmp_path/'irregular.csv';frame.to_csv(p,index=False)
    with pytest.raises(ValueError,match='uniform'): load_flight(p,config)

def test_sync_preserves_microsecond_units_and_original_origin(tmp_path):
    folder=tmp_path/'flight';folder.mkdir()
    for name in ['imu','gnss','ekf_estimated','ground_truth','ekf_innovations','ekf_test_ratios']:
        pd.DataFrame({'timestamp':[1000000,1020000,1040000,1060000],'value':[1.,2.,3.,4.]}).to_csv(folder/f'{name}.csv',index=False)
    # The synchronization report checks the actual GNSS velocity channels.
    pd.DataFrame({'timestamp':[1000000,1020000,1040000,1060000],'vel_n':[1,2,3,4],'vel_e':[0,0,0,0]}).to_csv(folder/'gnss.csv',index=False)
    out=tmp_path/'synced.csv'
    info=sync_flight(folder,out,time_origin_us=1020000)
    frame=pd.read_csv(out)
    np.testing.assert_array_equal(frame.timestamp,[1020000,1040000,1060000])
    np.testing.assert_allclose(frame.time_sec,[0,.02,.04])
    assert info['time_origin_px4_us']==1020000

@pytest.mark.parametrize('key,value',[('sample_period_sec',0),('attack_onset_sec',60),('isolation_contamination',0),('cusum_leak',2)])
def test_invalid_config_rejected(config,key,value):
    config[key]=value
    with pytest.raises(ValueError): validate_config(config)
