"""Compare two per-flight benchmark CSVs without comparing PDF metadata."""
import argparse
import numpy as np
import pandas as pd

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference');parser.add_argument('candidate')
    args=parser.parse_args()
    keys=['Flight','Category','Detector']
    left=pd.read_csv(args.reference).set_index(keys).sort_index()
    right=pd.read_csv(args.candidate).set_index(keys).sort_index()
    if not left.index.is_unique or not right.index.is_unique or not left.index.equals(right.index):
        parser.error('Flight/detector identities differ or are duplicated')
    if set(left.columns)!=set(right.columns): parser.error('Metric columns differ')
    failures=[]
    for column in left:
        if not np.allclose(left[column],right[column],rtol=1e-9,atol=1e-8,equal_nan=True): failures.append(column)
    if failures: parser.error('Different values in: '+', '.join(failures))
    print(f'Matched {len(left)} flight/detector rows across {len(left.columns)} metrics.')

if __name__=='__main__': main()
