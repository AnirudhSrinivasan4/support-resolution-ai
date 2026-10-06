# Support Resolution Assistant Evaluation Baseline

- Timestamp: `2026-10-06T09:14:08.851802+00:00`
- Datasets: complaint_understanding=36, retrieval=18, abstention=10

## Model and configuration

| Setting | Value |
| --- | --- |
| llm_provider | `openai-compatible` |
| llm_model | `qwen2.5:3b` |
| llm_base_url | `http://localhost:11434/v1` |
| llm_timeout_seconds | `45` |
| embedding_model | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` |
| embedding_model_revision | `None` |
| embedding_dimension | `384` |
| rrf_constant | `60` |
| knowledge_semantic_candidate_limit | `20` |
| knowledge_lexical_candidate_limit | `20` |
| semantic_candidate_limit | `20` |
| lexical_candidate_limit | `20` |
| resolution_knowledge_evidence_limit | `5` |
| resolution_historical_evidence_limit | `4` |
| resolution_min_knowledge_similarity | `0.4` |
| resolution_min_knowledge_lexical_score | `0.5` |
| taxonomy_intents | `['connectivity_issue', 'esim_activation', 'payment_failed', 'duplicate_charge', 'billing_dispute', 'roaming_issue', 'account_access', 'security_concern', 'device_issue', 'general_inquiry', 'unknown']` |
| taxonomy_categories | `['network', 'esim', 'sim', 'billing', 'payments', 'roaming', 'account', 'device', 'outage', 'general_inquiry', 'unknown']` |
| taxonomy_products | `['broadband', 'mobile_data', 'fifth_generation_mobile', 'esim', 'sim', 'voice', 'payments', 'roaming', 'account', 'device', 'unknown']` |

## Complaint Understanding

Dataset version: `1.0`; examples: 36
Successful responses: 31
Invalid model outputs: 5

| Metric | Value |
| --- | ---: |
| intent_accuracy | 0.5000 |
| category_accuracy | 0.4444 |
| product_accuracy | 0.5000 |
| severity_accuracy | 0.4444 |
| sentiment_accuracy | 0.4722 |
| intent_macro_f1 | 0.4907 |

## Retrieval

Dataset version: `1.0`; examples: 18

| Metric | Value |
| --- | ---: |
| recall_at_5 | 0.8889 |
| recall_at_10 | 0.9444 |
| mrr | 0.7981 |

A query is a hit at K if at least one expected relevant KB source ID appears in the top K results.

Mean reciprocal rank of the first expected relevant source; zero when none is returned.

## Abstention

Dataset version: `1.0`; examples: 10
Successful responses: 9
Invalid model outputs: 1

| Metric | Value |
| --- | ---: |
| accuracy | 0.8889 |
| false_abstention_count | 0 |
| missed_abstention_count | 1 |

## Limitations

- Small manually curated labels are a baseline set, not a representative production benchmark.
- Complaint labels and KB relevance judgments need domain review before drawing broad conclusions.
- No LLM correctness, hallucination, or resolution-quality metric is reported without reviewed ground truth.
- Historical support-ticket answers are not used as authoritative ground truth.
