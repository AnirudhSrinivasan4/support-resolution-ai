# Project development rules

- Use typed Python and keep domain concepts independent of HTTP, model vendors, and storage vendors.
- Keep provider calls behind interfaces in `app/domain/ports.py`; put concrete implementations in `app/infrastructure`.
- Keep route handlers thin. Put application orchestration in `app/services`.
- Do not add a database schema, AI pipeline, model integration, frontend, or dataset before the project milestone calls for it.
- The historical corpus is heterogeneous public customer-support data, not telecom data. Never describe it as telecom-specific.
- Treat historical answers as imperfect evidence, not verified resolutions or ground truth. Keep telecom-specific knowledge in a distinct knowledge base.
- Make classification categories data-driven so new ticket classes do not require enum changes throughout the codebase.
- Design future response flows to validate citations and abstain or escalate when evidence is insufficient.
- Read secrets from environment variables or an approved secret manager. Never commit credentials, `.env` files, customer data, or the downloaded public dataset.
- Avoid logging raw complaint text or other personal information unless an explicit, reviewed requirement justifies it.
- Keep dependencies focused. Explain new runtime dependencies in the change that introduces them.
- Add or update focused tests with behavior changes; do not claim evaluation results without a recorded dataset, split, and metric.
