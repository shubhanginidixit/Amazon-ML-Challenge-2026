import csv
import os
import zipfile
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path(r"c:\Users\Admin\Downloads\6ab10eb3b23ba_student_resource\student_resource")
TEST_DIR = BASE_DIR / "dataset" / "test"
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("1. Reading S2/S3 test entities for indexing...")
index = defaultdict(lambda: defaultdict(list))
valid_s2_s3 = set()
s2_s3_fallback = defaultdict(list)

for fname in ['test_source2.tsv', 'test_source3.tsv']:
    path = TEST_DIR / fname
    if not path.exists(): 
        continue
    print(f" Reading {fname}...")
    with open(path, encoding='utf-8', errors='replace') as f:
        next(f)
        for line in f:
            p = line.rstrip('\n').split('\t')
            if len(p) < 4: continue
            eid, name, addr, country = p[0], p[1], p[2], p[3]
            valid_s2_s3.add(eid)
            if len(s2_s3_fallback[country]) < 10:
                s2_s3_fallback[country].append(eid)
            words = [w.lower() for w in name.split() if len(w) >= 4]
            if words:
                w0 = words[0]
                if len(index[country][w0]) < 10:
                    index[country][w0].append(eid)

print(f"Indexed {len(valid_s2_s3):,} S2/S3 entities.")

print("2. Generating matching_results.tsv and candidate_pairs.tsv...")
s1_path = TEST_DIR / "test_source1.tsv"
matching_file = OUTPUT_DIR / "matching_results.tsv"
candidate_file = OUTPUT_DIR / "candidate_pairs.tsv"

with open(s1_path, encoding='utf-8', errors='replace') as f_in, \
     open(matching_file, 'w', encoding='utf-8', newline='') as f_m, \
     open(candidate_file, 'w', encoding='utf-8', newline='') as f_c:
    
    wm = csv.writer(f_m, delimiter='\t', lineterminator='\n')
    wc = wc_writer = csv.writer(f_c, delimiter='\t', lineterminator='\n')
    
    wm.writerow(['source1_entity_id', 'matched_entity_ids'])
    wc.writerow(['source1_entity_id', 'candidate_entity_ids'])
    
    next(f_in)
    count = 0
    for line in f_in:
        p = line.rstrip('\n').split('\t')
        if len(p) < 4:
            continue
        eid, name, addr, country = p[0], p[1], p[2], p[3]
        
        words = [w.lower() for w in name.split() if len(w) >= 4]
        cands = []
        if words and words[0] in index[country]:
            cands = index[country][words[0]]
        
        if not cands and country in s2_s3_fallback:
            cands = s2_s3_fallback[country][:5]
            
        matched = cands[:2] if cands else []
        candidates = cands[:10] if cands else []
        
        wm.writerow([eid, ','.join(matched)])
        wc.writerow([eid, ','.join(candidates)])
        count += 1
        if count % 100000 == 0:
            print(f" Processed {count:,} S1 entities...")

print(f"Completed {count:,} rows.")
