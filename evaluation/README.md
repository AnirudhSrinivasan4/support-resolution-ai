# Curated evaluation baseline

These versioned JSON files are small, manually curated synthetic evaluation sets. They provide a repeatable starting baseline, but are not a representative production benchmark or an independent final test set. Review labels with telecom domain reviewers before interpreting scores.

Run all three suites from the project root after configuring the same database, embeddings, and LLM environment used by the API:

```powershell
python -m app.evaluation.cli
```

The command loads simple `KEY=VALUE` entries from project `.env` by default without overriding variables already set in the shell. Use `--env-file PATH` to select another file. It writes `evaluation/reports/latest.json` and `evaluation/reports/latest.md` only after every selected example succeeds. Use `--suite complaint_understanding`, `--suite retrieval`, or `--suite abstention` to run one suite; `--dataset-dir` and `--report-dir` can point to alternate versioned inputs and output locations. Missing services or a failing example produce a non-zero exit and no new report; examples are never silently skipped.

Complaint metrics compare all five predicted fields to the manually labelled values. An invalid structured model response is recorded as `invalid_model_output`, counts as an incorrect prediction for each field, and is included in the denominator; provider/service failures abort the suite. Intent macro F1 averages over intent labels present in the expected set; the confusion matrix includes expected and predicted labels. Retrieval `recall_at_k` is the proportion of queries with at least one judged relevant KB source ID in the top K, per the project's baseline hit definition. MRR is the mean reciprocal rank of the first judged relevant source, and is zero when no relevant source is returned. Abstention false positives are false abstentions (supported example abstained); missed abstentions are unsupported examples answered without abstaining. When the model returns invalid structured output, the abstention example is recorded with a null prediction and excluded from binary accuracy; the report gives both total examples and successful response count. Provider/service failures abort the suite. No confidence probability is produced.

Retrieval source IDs are checked against `knowledge_base/seeds/v1/documents.json` each run. The historical ticket corpus is not used as authoritative ground truth; its agent answers are excluded from these labels and metrics. No generation correctness, hallucination, or grounding score is claimed because there is no reviewed answer-level ground truth set.
