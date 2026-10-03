"""Synchronize extracted telemetry to a bounded, uniform offline timeline."""
import argparse
import json
from pathlib import Path
from telemetry import CATEGORIES, sync_flight

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--period-ms',type=int,default=20)
    parser.add_argument('--max-gap-sec',type=float,default=2.0)
    parser.add_argument('--time-origins',type=Path,help='JSON mapping category/flight to original 50 Hz timeline origin in PX4 microseconds')
    args = parser.parse_args()
    if args.period_ms <= 0 or args.max_gap_sec <= 0: parser.error('Period and maximum gap must be positive')
    records = []
    origins = json.loads(args.time_origins.read_text()) if args.time_origins else {}
    for category in CATEGORIES:
        for flight in sorted((args.input/category).glob('flight_*')):
            if not flight.is_dir(): continue
            key = f'{category}/{flight.name}'
            if args.time_origins and key not in origins: parser.error(f'Time origin missing for {key}')
            metadata = sync_flight(flight,args.output/category/(flight.name+'.csv'),args.period_ms,args.max_gap_sec,origins.get(key))
            records.append({'flight':f'{category}/{flight.name}', **metadata})
            print(records[-1],flush=True)
    if not records: parser.error('No extracted flight folders found')
    (args.output/'synchronization.json').write_text(json.dumps(records,indent=2)+'\n',encoding='utf-8')

if __name__ == '__main__': main()
