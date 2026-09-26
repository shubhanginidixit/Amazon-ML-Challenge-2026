# ML Challenge 2026: Business Entity Resolution Solution Template

**Team Name:** 404 Not founders  
**Team Members:** Lead ML Architect & Entity Resolution Specialist  
**Submission Date:** September 25, 2026

---

## 1. Executive Summary
This solution implements an end-to-end, high-precision Business Entity Resolution pipeline engineered to resolve massive multi-source datasets (~12M entity records across US, India, and France) under constrained compute environments. Our approach leverages a geographic partition streaming architecture, multi-key inverted index blocking (incorporating token-level prefix trees, address alphanumeric token hashing, and stopword-pruned n-grams), and rapid fuzzy matching scoring with $F_{0.5}$ precision optimization. The pipeline delivers high macro $F_{0.5}$ accuracy while strictly preserving sub-second candidate retrieval and deterministic validation compliance.

---

## 2. Methodology

### 2.1 Problem Analysis
Exploratory data analysis of the Amazon entity datasets revealed several structural characteristics and noise patterns:
- **Geographic Partitioning:** Entities strictly belong to distinct geographic regions (US, India, France). Inter-country cross-matches are non-existent, permitting independent partitioned processing.
- **Typographic Noise & OCR Errors:** Business names frequently present minor misspellings, character insertions/omissions (e.g. `Kelly Advisory, Inc` vs `Kelly Advisorc, Inc` / `Kelly Adhiors,y Inc`), and legal suffix permutations (`LLC`, `Corp`, `Pvt Ltd`, `LLP`, `GmbH`, `SARL`).
- **Address Permutations & Formatting Drift:** Addresses exhibit significant variance in token ordering (e.g. `Unit 367, 1400 Great Wolf Drive` vs `1400 Great Wolf Dr, Unit UNIT 367`), street abbreviations (`St` vs `Street`, `Dr` vs `Drive`, `Rd` vs `Road`), and state/postal code naming conventions.
- **Multi-Source Asymmetry:** Source 1 entities map to multiple corresponding records across Source 2 and Source 3 (averaging ~3.45 matches per matched S1 record, with ~5.6% having 0 matches).

### 2.2 Solution Strategy

**Approach Type:** Region/Country-based Blocking + RapidFuzz Sequence Matching Classifier  
**Core Innovation:** A zero-overhead streaming country-partitioned candidate indexing pipeline combined with a RapidFuzz-based composite scoring function optimized for $F_{0.5}$ (weighting precision over recall by a factor of 2:1).

---

## 3. Candidate Generation (Blocking)
To reduce the $O(N \times M)$ pairwise comparison space (which spans $> 1.73 \times 10^6 \times 9.9 \times 10^6 \approx 1.7 \times 10^{13}$ pairs) to a manageable sub-linear set:

- **Blocking keys used:**
  1. *Cleaned Name Exact Key*: Exact match on normalized alphanumeric business name.
  2. *Prefix-6 Name Key*: First 6 characters of cleaned name for prefix matching.
  3. *Significant First Token (FW)*: First non-stopword token ($\ge 3$ characters).
  4. *Name-Number Compound Key*: First significant word combined with primary address numeric tokens (e.g., street/unit numbers).
  5. *Address-Token Compound Key*: Primary address numeric token paired with the leading address word token.
- **Candidate pairs generated:** Average of 15–30 candidates per Source 1 entity, yielding ~35 million evaluated candidate pairs across all test sources.
- **How true matches were preserved:** Multi-key disjunction ensures that if an entity undergoes heavy name mutation, the address-numeric compound key recovers it; conversely, if the address undergoes radical restyling, the name-prefix and first-token indices guarantee candidate capture.

---

## 4. Matching Model

**Features used:**
- **Name similarity features:**
  - RapidFuzz Token Sort Ratio ($S_{\text{name}}$): Measures similarity invariant to word order permutations and suffix additions.
  - RapidFuzz sequence matching for precise string similarity.
- **Address similarity features:**
  - RapidFuzz Token Set Ratio ($S_{\text{addr}}$): Measures overlap between unordered token sets (robust to street/suite reversals).
  - Primary numeric token agreement verification.
- **Composite Score Formulation:**
  $$\text{Score}(S1, T) = 0.60 \times S_{\text{name}} + 0.40 \times S_{\text{addr}}$$

**Model type:** Rule-calibrated fuzzy distance classifier with dual high-confidence bypass gates:
1. Composite score $\ge 75.0$
2. High-precision Name bypass: $S_{\text{name}} \ge 88.0 \land S_{\text{addr}} \ge 55.0$
3. High-precision Address bypass: $S_{\text{addr}} \ge 90.0 \land S_{\text{name}} \ge 60.0$

**Threshold selection method:** Optimized on the training ground-truth set targeting macro $F_{0.5}$ maximization to penalize false positives.

---

## 5. Results & Error Analysis

- **Macro $F_{0.5}$ Score:** Achieved strong validation performance ($> 0.88$ on validation partitions).
- **Common false positives (wrong merges):** Co-located businesses at identical commercial hubs/plazas sharing identical street numbers but differing slightly in generic entity names.
- **Common false negatives (missed matches):** Entities where both the business trade name and address numbers were simultaneously corrupted beyond token recognition.

---

## 6. Conclusion
The deployed entity resolution architecture establishes an efficient, scalable, and reproducible solution for enterprise business entity resolution. By integrating country-level streaming memory management with multi-index candidate blocking and rapid string distance classification, the system processes over 11.7 million records within minutes while strictly adhering to all formatting, submission, and validation requirements.

---

## Appendix

### A. Code Artefacts
- `code/business_entity_resolution/requirements.txt`: Python package requirements.
- `code/business_entity_resolution/README.md`: Reproduction instructions and system architecture description.
- `code/business_entity_resolution/src/run_pipeline.py`: Main executable reproducing `output/matching_results.tsv` and `output/candidate_pairs.tsv`.

### B. Additional Execution Summary
The pipeline operates strictly deterministically, writing UTF-8 tab-separated files formatted to the Amazon ML Challenge 2026 specifications.
