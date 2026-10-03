"""Evaluate the three supplied detector formulations with explicit provenance."""
import argparse
import json
from pathlib import Path
from analysis import evaluate

ROOT = Path(__file__).resolve().parents[2]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir',type=Path,required=True,help='Synchronized category/flight_XX.csv folders')
    parser.add_argument('--output',type=Path,default=ROOT/'results/local')
    parser.add_argument('--config',type=Path,default=ROOT/'configs/research.json')
    parser.add_argument('--protocol',choices=['held-out','legacy'],default='held-out')
    parser.add_argument('--allow-degenerate-gnss',action='store_true',help='Explicitly allow known-broken all-zero historical GNSS channels')
    args = parser.parse_args()
    try:
        evaluate(args.data_dir,args.output,json.loads(args.config.read_text(encoding='utf-8')),args.protocol,args.allow_degenerate_gnss)
    except (ValueError,FileNotFoundError) as exc:
        parser.error(str(exc))

if __name__ == '__main__': main()
