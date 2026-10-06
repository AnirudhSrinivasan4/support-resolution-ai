# Evaluation plan

Evaluate the system as separate components. Do not treat the historical dataset's answer text as verified resolution ground truth: the public corpus is heterogeneous and its answers include generic support responses. Evaluate telecom guidance against the separately curated telecom knowledge base and domain review.

## Evaluation data

- Create a versioned set of complaints with reviewed intent/category, product, severity, and sentiment labels.
- Record the taxonomy version with each classification run; include unseen or ambiguous examples where `unknown` is the desired outcome.
- For retrieval, annotate relevant historical tickets and KB articles separately, including source provenance.
- Split examples by time or conversation/customer thread where possible; keep near-duplicates and related tickets in one split to reduce leakage.
- Record the evaluation-set version and any taxonomy or model version used for each run.
- Do not include the full public dataset or private customer data in Git.

## Metrics by stage

| Stage | Suggested measures |
| --- | --- |
| Complaint classification | Macro F1 and per-class precision/recall for intent/category/product; severity recall and override review; sentiment agreement; unknown-class precision/recall |
| Retrieval | Recall@k, MRR, and nDCG, with historical tickets and telecom KB articles reported separately |
| Reranking | Change in MRR/nDCG over the hybrid candidate ranking |
| Generation and grounding | Human review for correctness, completeness, actionability, and support by cited evidence; citation validity; unsupported-claim rate |
| Abstention and escalation | Appropriate abstention/escalation rate on low-evidence and high-risk cases, alongside false-abstention rate |
| System performance | Latency percentiles, error rate, throughput, and cost per request |

## Baselines and review

Compare keyword-only, semantic-only, hybrid RRF, and hybrid plus reranking on the same held-out set. Keep a small qualitative review queue of successes and failures, including cases with no relevant source, contradictory sources, unseen classes, and stale knowledge. LLM-as-judge scores may help triage examples but should not be the sole quality measure.

For grounded resolutions, separately record the evaluation set and measure answer/step correctness by human review, whether procedural claims are supported by authoritative KB content, citation precision and coverage against retrieved source IDs, policy adherence, correct escalation, and abstention precision/recall on insufficient-evidence cases. Track p50/p95 end-to-end latency, provider errors/timeouts, and token usage when the provider exposes it. Do not tune the deterministic KB semantic/lexical abstention floors against the same set used to report final performance; retain the selected thresholds and split with every metric. These measures are plans until a labeled set and results are recorded.

Set acceptance thresholds after collecting a baseline and reviewing label quality. Report dataset limitations and sample sizes with all results; do not present historical answer agreement as factual resolution accuracy.

## First reproducible baseline runner

`evaluation/datasets/` contains small, manually curated synthetic telecom complaint, KB retrieval, and abstention datasets. Run them from the project root with `python -m app.evaluation.cli`; it loads simple `KEY=VALUE` entries from `.env` by default while preserving shell-variable precedence. The runner calls the existing complaint-understanding, knowledge-retrieval, and resolution services; it does not reimplement those paths. It fails on the first unavailable service or malformed example and writes `evaluation/reports/latest.json` and `latest.md` only after the selected suites complete successfully.

The current retrieval `recall_at_k` definition is a query hit rate: a query counts as a hit if at least one of its expected relevant KB IDs appears in the top K results. MRR averages the reciprocal rank of the first expected relevant ID, or zero if none is present. Complaint accuracy is calculated for intent, category, product, severity, and sentiment; intent macro F1 averages over intent labels present in the labelled examples. Abstention accuracy is accompanied by false-abstention and missed-abstention counts. Detailed schemas, invocation options, and limitations are in `evaluation/README.md`. Scores from this small curated set are a baseline only; no LLM resolution correctness or hallucination metric is reported.
