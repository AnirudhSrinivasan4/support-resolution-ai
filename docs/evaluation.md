# Evaluation plan

Evaluate the system as separate components. Do not treat the historical dataset's answer text as verified resolution ground truth: the public corpus is heterogeneous and its answers include generic support responses. Evaluate telecom guidance against the separately curated telecom knowledge base and domain review.

## Evaluation data

- Create a versioned set of complaints with reviewed intent/category, product, severity, and sentiment labels.
- For retrieval, annotate relevant historical tickets and KB articles separately, including source provenance.
- Split examples by time or conversation/customer thread where possible; keep near-duplicates and related tickets in one split to reduce leakage.
- Record the evaluation-set version and any taxonomy or model version used for each run.
- Do not include the full public dataset or private customer data in Git.

## Metrics by stage

| Stage | Suggested measures |
| --- | --- |
| Complaint classification | Macro F1 and per-class precision/recall; severity recall; confidence calibration where sample size allows |
| Retrieval | Recall@k, MRR, and nDCG, with historical tickets and telecom KB articles reported separately |
| Reranking | Change in MRR/nDCG over the hybrid candidate ranking |
| Generation and grounding | Human review for correctness, completeness, actionability, and support by cited evidence; citation validity; unsupported-claim rate |
| Abstention and escalation | Appropriate abstention/escalation rate on low-evidence and high-risk cases, alongside false-abstention rate |
| System performance | Latency percentiles, error rate, throughput, and cost per request |

## Baselines and review

Compare keyword-only, semantic-only, hybrid RRF, and hybrid plus reranking on the same held-out set. Keep a small qualitative review queue of successes and failures, including cases with no relevant source, contradictory sources, unseen classes, and stale knowledge. LLM-as-judge scores may help triage examples but should not be the sole quality measure.

Set acceptance thresholds after collecting a baseline and reviewing label quality. Report dataset limitations and sample sizes with all results; do not present historical answer agreement as factual resolution accuracy.
