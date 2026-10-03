"""Download a pinned research dataset, verify SHA-256, and extract safely."""
import argparse
import hashlib
import json
from pathlib import Path,PurePosixPath
import shutil
import urllib.request
import zipfile

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dataset',choices=['corrected','supplied','raw'])
    parser.add_argument('--archive',type=Path,help='Use an already downloaded ZIP instead of the network')
    args=parser.parse_args()
    spec=json.loads((ROOT/'data/release-assets.json').read_text())[args.dataset]
    archive=args.archive or ROOT/'data/downloads'/spec['filename']
    archive.parent.mkdir(parents=True,exist_ok=True)
    if not archive.exists():
        if args.archive: parser.error(f'Archive does not exist: {archive}')
        temporary=archive.with_suffix('.download')
        print(f'Downloading {spec["filename"]} ({spec["bytes"]/1e6:.1f} MB)',flush=True)
        with urllib.request.urlopen(spec['url'],timeout=120) as response,temporary.open('wb') as dest:
            shutil.copyfileobj(response,dest)
        temporary.replace(archive)
    with archive.open('rb') as stream: digest=hashlib.file_digest(stream,'sha256').hexdigest()
    if digest != spec['sha256']: parser.error('SHA-256 mismatch; archive was not extracted')
    with zipfile.ZipFile(archive) as bundle:
        members=[]
        prefix={'raw':('data','raw_ulog'),'supplied':('data','supplied'),'corrected':('data','corrected')}[args.dataset]
        for member in bundle.infolist():
            path=PurePosixPath(member.filename)
            target=(ROOT/Path(*path.parts)).resolve()
            if path.is_absolute() or '..' in path.parts or tuple(path.parts[:2]) != prefix or not target.is_relative_to(ROOT):
                parser.error('Unsafe archive path')
            if (member.external_attr >> 16) & 0o170000 == 0o120000: parser.error('Symbolic links are not accepted')
            members.append((member,target))
        # Refuse to overwrite local edits. Matching files make repeated runs safe.
        for member,target in members:
            if target.is_file():
                with target.open('rb') as current,bundle.open(member) as supplied:
                    if hashlib.file_digest(current,'sha256').digest() != hashlib.file_digest(supplied,'sha256').digest():
                        parser.error(f'Local file differs; preserve or move it before extracting: {target.relative_to(ROOT)}')
        for member,target in members:
            if member.is_dir(): target.mkdir(parents=True,exist_ok=True)
            elif not target.exists():
                target.parent.mkdir(parents=True,exist_ok=True)
                with bundle.open(member) as source,target.open('wb') as dest: shutil.copyfileobj(source,dest)
    print(f'Verified and extracted {args.dataset} dataset to {ROOT/"data"}')

if __name__=='__main__': main()
