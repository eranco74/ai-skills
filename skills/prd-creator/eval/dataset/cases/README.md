# OSAC PRD Evaluation Dataset

This directory contains evaluation cases for the OSAC prd-creator tool. Each case represents a real Jira feature with a known-good merged PRD that serves as the gold standard.

## Dataset Structure

Each case is a directory containing:

1. **input.yaml** — Test input parameters:
   - `jira_key`: The Jira issue key (e.g., OSAC-1269)
   - `title`: Feature title from Jira
   - `priority`: Feature priority (High, Medium, Low)

2. **annotations.yaml** — Expected quality metrics:
   - `expected_score`: The score the PRD reviewer gave (0-10 scale)
   - `expected_pass`: Whether the PRD passes (score >= 7, no dimension scores of 0)
   - `gold_prd_path`: Relative path to the merged PRD in enhancement-proposals repo
   - `notes`: (optional) Additional context about scoring

3. **gold-prd.md** — The actual merged PRD content from enhancement-proposals

## Dataset Cases

| Jira Key | Title | Score | Path |
|----------|-------|-------|------|
| OSAC-1269 | ClusterVersion — Managed Version Catalog | 10/10 | OSAC-1269-cluster-version-api |
| OSAC-1270 | Base OS Management for Bare-Metal Instances | 10/10 | OSAC-1270-base-os-management-bmaas |
| OSAC-2917 | GPU-Enabled Compute Instances | 9/10 | OSAC-2917-gpu-instance-types |
| OSAC-2872 | OSAC Storage Control Plane | 9/10 | storage-control-plane-osac-2872 |
| OSAC-1330 | Type-Safe Resource References | 9/10 | type-safe-resource-references |
| OSAC-1110 | StorageTier API | 9/10 | OSAC-1110-storage-tier |
| OSAC-2540 | DiskImage Resource | 9/10 | OSAC-2540-disk-image |
| OSAC-1567 | Secret Management | 8/10 | OSAC-1567-secret-management |
| OSAC-1332 | CaaS Cluster Storage | 8/10 | OSAC-1332-caas-cluster-storage |
| OSAC-1319 | BareMetal Instance UI | 8/10 | OSAC-1319-bare-metal-instance-ui |

## Score Distribution

- **10/10 (Perfect)**: 2 cases (20%)
- **9/10 (Excellent)**: 5 cases (50%)
- **8/10 (Good)**: 3 cases (30%)

All cases pass the quality threshold (>= 7/10 with no zero scores).

## Usage

The prd-creator evaluation harness should:

1. Read `input.yaml` to get the Jira key and metadata
2. Generate a PRD using the prd-creator tool
3. Compare the generated PRD against `gold-prd.md`
4. Score the generated PRD using the same rubric that produced `expected_score`
5. Verify the score meets or exceeds `expected_score`

## Notes

- Scores for OSAC-1567, OSAC-1332, and OSAC-1319 are estimated from merged PR reviews as exact scores were not documented in the dataset request
- All gold PRDs are copies of the actual merged content from the enhancement-proposals repository as of 2026-07-23
- The gold PRD paths are relative to the enhancement-proposals/enhancements/ directory
