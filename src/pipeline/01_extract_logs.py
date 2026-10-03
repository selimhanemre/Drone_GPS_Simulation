"""Extract one explicitly selected log, or a categorized collection."""
import argparse
from pathlib import Path
from telemetry import CATEGORIES, extract_log

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--raw-dir', type=Path, help='Folder with category/flight_XX.ulg files')
    group.add_argument('--ulog', type=Path, help='One explicitly selected ULog')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    files = [(args.ulog, args.output)] if args.ulog else [(p,args.output/c/p.stem) for c in CATEGORIES for p in sorted((args.raw_dir/c).glob('*.ulg'))]
    if not files: parser.error('No ULog files found')
    for path, output in files:
        if not path.is_file(): parser.error(f'File not found: {path}')
        metadata = extract_log(path, output)
        print(f'{path.name} -> {output} ({metadata["gnss_topic"]}, {metadata["gnss_samples"]} GNSS samples)', flush=True)

if __name__ == '__main__': main()
