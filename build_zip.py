import os
import csv
import zipfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if not (BASE_DIR / "dataset").exists():
    for parent in Path(__file__).resolve().parents:
        if (parent / "dataset").exists():
            BASE_DIR = parent
            break

TEST_DIR = BASE_DIR / "dataset" / "test"
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

matching_file = OUTPUT_DIR / "matching_results.tsv"
candidate_file = OUTPUT_DIR / "candidate_pairs.tsv"

if not matching_file.exists() or not candidate_file.exists():
    print("Output files not found in output directory. Please run run_pipeline.py first.")
else:
    print(f"Using generated output files from {OUTPUT_DIR}")

# Build ZIP Archives
zip_paths = [
    BASE_DIR / "submission.zip",
    BASE_DIR / "amazon_ml_challenge_submission.zip",
]

for zip_path in zip_paths:
    print(f"Creating ZIP archive: {zip_path}")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
        if matching_file.exists():
            z.write(matching_file, "output/matching_results.tsv")
        if candidate_file.exists():
            z.write(candidate_file, "output/candidate_pairs.tsv")
        
        doc_path = BASE_DIR / "student_resource" / "Documentation_template.md"
        if not doc_path.exists():
            doc_path = BASE_DIR / "Documentation_template.md"
        if doc_path.exists():
            z.write(doc_path, "Documentation_template.md")
            
        code_dir = BASE_DIR / "student_resource" / "code"
        if not code_dir.exists():
            code_dir = BASE_DIR / "code"
        if code_dir.exists():
            for root, _, files in os.walk(code_dir):
                for file in files:
                    fp = Path(root) / file
                    base_ref = BASE_DIR / "student_resource" if (BASE_DIR / "student_resource").exists() else BASE_DIR
                    rel = fp.relative_to(base_ref)
                    z.write(fp, rel)

print("ZIP archives successfully created!")
