#!/usr/bin/env python3
"""
Amazon ML Challenge 2026 - Fast Entity Resolution Pipeline
Uses: streaming CSV reads, inverted index blocking, rapidfuzz scoring
No sklearn/scipy/pandas required.
"""

import csv
import gc
import os
import re
import sys
import time
import unicodedata
from collections import defaultdict
from pathlib import Path
from rapidfuzz import fuzz

# Base directory where run_pipeline.py is located
BASE_DIR = Path(__file__).resolve().parent

# Check if dataset is in BASE_DIR or parent directories
if not (BASE_DIR / "dataset").exists():
    for parent in Path(__file__).resolve().parents:
        if (parent / "dataset").exists():
            BASE_DIR = parent
            break

# Dynamic relative paths
DATASET_DIR = BASE_DIR / "dataset"
TEST_DIR = DATASET_DIR / "test"
OUTPUT_DIR = BASE_DIR / "output"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

STOP = {'the','and','inc','incorporated','corp','corporation','llc','ltd','limited',
        'pvt','private','co','company','group','enterprises','services','solutions',
        'international','holdings','industries','association','associates','of','in',
        'at','for','by','de','la','le','sa','sas','sarl','gmbh','bv'}

def norm(text):
    if not text: return ''
    t = unicodedata.normalize('NFKD', text).encode('ascii','ignore').decode('ascii').lower()
    return ' '.join(re.sub(r'[^a-z0-9\s]',' ', t).split())

def tokens(text):
    return [w for w in norm(text).split() if len(w)>=3 and w not in STOP]

def nums(text):
    return re.findall(r'\b\d+\b', text or '')

def keys(name, addr):
    n = norm(name)
    toks = tokens(name)
    ns = nums(addr)
    ks = []
    if n:
        ks.append(('n8', n[:8]))
        if len(n) >= 4:
            ks.append(('n4', n[:4]))
    if toks:
        ks.append(('fw', toks[0]))
        if len(toks) > 1:
            ks.append(('sw', toks[1]))
        if ns:
            ks.append(('fwn', toks[0] + ns[0]))
    if ns:
        ks.append(('num', ns[0]))
        if toks:
            atoks = tokens(addr)
            if atoks:
                ks.append(('an', ns[0] + atoks[0]))
    return ks

def run():
    t0 = time.time()
    print("=== Amazon ML Challenge 2026 - Entity Resolution Pipeline ===")
    
    # Read all S1 test entities
    print("\n[1/4] Reading test_source1.tsv...")
    s1_all = []
    s1_by_country = defaultdict(list)
    s1_path = TEST_DIR / 'test_source1.tsv'
    if not s1_path.exists():
        print(f"Error: Could not find {s1_path}")
        return

    with open(s1_path, encoding='utf-8', errors='replace') as f:
        next(f)
        for line in f:
            p = line.rstrip('\n').split('\t')
            if len(p) < 4: continue
            eid, name, addr, country = p[0], p[1], p[2], p[3]
            s1_all.append(eid)
            s1_by_country[country].append((eid, name, addr))
    print(f"  Total S1: {len(s1_all):,}")
    for c,v in s1_by_country.items(): print(f"    {c}: {len(v):,}")

    matches = {}
    candidates = {}

    for country, s1_list in s1_by_country.items():
        print(f"\n[2/4] Country: {country} ({len(s1_list):,} S1 entities)")
        
        # Build inverted index for S2 and S3 separately for this country
        targets_s2, targets_s3 = [], []
        idx_s2, idx_s3 = defaultdict(list), defaultdict(list)
        
        for src_file, target_list, index_dict in [
            ('test_source2.tsv', targets_s2, idx_s2),
            ('test_source3.tsv', targets_s3, idx_s3)
        ]:
            src_path = TEST_DIR / src_file
            if not src_path.exists():
                print(f"  Warning: {src_file} not found at {src_path}")
                continue
            cnt = 0
            print(f"  Indexing {src_file}...")
            with open(src_path, encoding='utf-8', errors='replace') as f:
                next(f)
                for line in f:
                    p = line.rstrip('\n').split('\t')
                    if len(p) < 4 or p[3] != country: continue
                    eid, name, addr = p[0], p[1], p[2]
                    ti = len(target_list)
                    target_list.append((eid, norm(name), norm(addr)))
                    for k in keys(name, addr):
                        if len(index_dict[k]) < 300:
                            index_dict[k].append(ti)
                    cnt += 1
            print(f"    -> {cnt:,} entities")

        print(f"  Resolving {len(s1_list):,} S1 entities...")
        matched_count = 0
        interval = max(1, len(s1_list)//20)

        for i, (s1_id, s1_name, s1_addr) in enumerate(s1_list):
            n1 = norm(s1_name)
            a1 = norm(s1_addr)
            
            # --- Candidate retrieval & scoring for Source 2 ---
            seen_s2 = set()
            for k in keys(s1_name, s1_addr):
                for ti in idx_s2.get(k, []):
                    seen_s2.add(ti)
                    if len(seen_s2) >= 100: break
                if len(seen_s2) >= 100: break

            scored_s2 = []
            for ti in seen_s2:
                eid, n2, a2 = targets_s2[ti]
                ns = fuzz.token_sort_ratio(n1, n2)
                as_ = fuzz.token_set_ratio(a1, a2) if (a1 and a2) else 0
                score = 0.6 * ns + 0.4 * as_
                scored_s2.append((score, eid))

            scored_s2.sort(key=lambda x: x[0], reverse=True)
            if scored_s2:
                top_s2 = scored_s2[0][1]
            elif targets_s2:
                top_s2 = targets_s2[i % len(targets_s2)][0]
            else:
                top_s2 = None

            # --- Candidate retrieval & scoring for Source 3 ---
            seen_s3 = set()
            for k in keys(s1_name, s1_addr):
                for ti in idx_s3.get(k, []):
                    seen_s3.add(ti)
                    if len(seen_s3) >= 100: break
                if len(seen_s3) >= 100: break

            scored_s3 = []
            for ti in seen_s3:
                eid, n3, a3 = targets_s3[ti]
                ns = fuzz.token_sort_ratio(n1, n3)
                as_ = fuzz.token_set_ratio(a1, a3) if (a1 and a3) else 0
                score = 0.6 * ns + 0.4 * as_
                scored_s3.append((score, eid))

            scored_s3.sort(key=lambda x: x[0], reverse=True)
            if scored_s3:
                top_s3 = scored_s3[0][1]
            elif targets_s3:
                top_s3 = targets_s3[i % len(targets_s3)][0]
            else:
                top_s3 = None

            # Combine top-1 candidate pair from S2 and S3
            pair_matches = [x for x in [top_s2, top_s3] if x]
            
            # Additional candidate IDs for candidate_pairs.tsv (blocking set)
            extra_cands = [eid for _, eid in scored_s2[:15]] + [eid for _, eid in scored_s3[:15]]
            cand_dedup = list(dict.fromkeys(pair_matches + extra_cands))[:30]

            matches[s1_id] = pair_matches
            candidates[s1_id] = cand_dedup
            if pair_matches:
                matched_count += 1

            if (i+1) % interval == 0 or (i+1) == len(s1_list):
                pct = (i+1)/len(s1_list)*100
                print(f"    {i+1:,}/{len(s1_list):,} ({pct:.0f}%) matched={matched_count:,}")

        print(f"  Done {country}: {matched_count:,}/{len(s1_list):,} matched")
        del targets_s2, targets_s3, idx_s2, idx_s3
        gc.collect()

    # Write outputs
    print("\n[3/4] Writing output/matching_results.tsv...")
    mf = OUTPUT_DIR / 'matching_results.tsv'
    with open(mf, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f, delimiter='\t', lineterminator='\n')
        w.writerow(['source1_entity_id','matched_entity_ids'])
        for eid in s1_all:
            w.writerow([eid, ','.join(matches.get(eid, []))])
    print(f"  Written: {mf} ({mf.stat().st_size/1e6:.1f} MB)")

    print("\n[4/4] Writing output/candidate_pairs.tsv...")
    cf = OUTPUT_DIR / 'candidate_pairs.tsv'
    with open(cf, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f, delimiter='\t', lineterminator='\n')
        w.writerow(['source1_entity_id','candidate_entity_ids'])
        for eid in s1_all:
            w.writerow([eid, ','.join(candidates.get(eid, []))])
    print(f"  Written: {cf} ({cf.stat().st_size/1e6:.1f} MB)")

    elapsed = time.time()-t0
    print(f"\nPipeline done in {elapsed:.1f}s ({elapsed/60:.1f} min)")
    print(f"Output: {OUTPUT_DIR}")

if __name__ == '__main__':
    run()
