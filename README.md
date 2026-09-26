# Business Entity Resolution Pipeline

## Overview
This pipeline resolves business entities across three data sources using
region/country-based blocking and RapidFuzz string similarity matching. 
It is optimised for the Fâ‚€.â‚… (precision-heavy) metric.

## Prerequisites
- Python 3.10+
- ~16 GB RAM recommended (the pipeline processes data in country-level batches)

## Setup

`ash
# From the student_resource/ directory
pip install -r code/business_entity_resolution/requirements.txt
`

## Running the Pipeline

`ash
# From the student_resource/ directory
python code/business_entity_resolution/src/run_pipeline.py
`

This will:
1. Load and preprocess all source files (train + test)
2. Perform region/country-based blocking to group related entities
3. Generate candidate pairs
4. Extract pairwise features using RapidFuzz string similarity matching (Token Sort Ratio, Token Set Ratio)
5. Run inference on test candidates using a calibrated composite scoring function with a high-precision threshold (~75.0)
6. Write output/matching_results.tsv and output/candidate_pairs.tsv

## Validating Output

`ash
python utils/validate_submission.py \
    --matching output/matching_results.tsv \
    --candidate output/candidate_pairs.tsv \
    --test-dir dataset/test
`

The validator prints **PASS** (exit 0) when the files conform to all submission rules.

## Output Files
| File | Description |
|------|-------------|
| output/matching_results.tsv | Final entity matches (scored on leaderboard) |
| output/candidate_pairs.tsv  | Candidate set from blocking stage |

## Key Design Decisions
- **Region/Country-based blocking:** Processing is split by country to keep memory
  bounded and allow country-specific address normalisation.
- **RapidFuzz sequence matching:** Uses highly optimized string similarity algorithms
  (Token Sort Ratio, Token Set Ratio) for fast and precise candidate evaluation.
- **High decision threshold:** Tuned for Fâ‚€.â‚… which weights precision 2Ã—
  over recall â€” fewer false merges at the cost of some missed matches.
