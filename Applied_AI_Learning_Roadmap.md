# Applied AI Learning Roadmap

Owner: Maverick TG. Target role: technically credible Applied AI leader / SME (architect who can design, prototype, evaluate, and explain production GenAI and agentic systems).

Profile assumptions used (correct me if wrong): 18+ years delivery leadership at an SI, Google PCA-certified, ERP and public-sector background, daily user of Claude Code and MCP-connected tools, limited hands-on cloud engineering, GCP-first upskilling plan with a payroll/HCM/pension agent portfolio in progress.

## 1. Competency matrix (baseline 2026-11-23)

Levels: 1 Awareness · 2 Conceptual understanding · 3 Technical understanding · 4 Practical implementation capability · 5 Advanced expertise and architectural judgment.

Baseline levels are PROVISIONAL. They are inferred from profile and prior work, not from assessment. Each will be re-scored at the first monthly assessment (2026-11-30) using checkpoint answers, design discussions, and demonstrated implementations. Nothing moves up because a report covered it.

| # | Competency | Baseline | Target (90 days) | Evidence needed to move up |
|---|------------|----------|------------------|----------------------------|
| 1 | Foundation models & LLM architecture | 2 | 3 | Explain attention/KV cache/MoE unaided; train nanoGPT end to end |
| 2 | Reasoning & inference-time scaling | 2 | 3 | Explain GRPO/RLVR and verifier-vs-revision trade-offs; run a best-of-N vs. single-pass eval |
| 3 | Prompt & context engineering | 3 | 4 | Design a context budget for a long-running agent; measure compaction effects |
| 4 | RAG & enterprise knowledge systems | 2 | 4 | Build and evaluate a hybrid-retrieval RAG with reranking and a retrieval eval set |
| 5 | AI agents & multi-agent architectures | 2 | 4 | Ship an orchestrator-worker agent with evals and failure-mode analysis (MAST) |
| 6 | Tool use, function calling & MCP | 2 | 4 | Build an MCP server with auth; design tool schemas; handle tool errors and retries |
| 7 | Multimodal AI | 1 | 2 | Explain vision-language encoding; run a document-understanding pipeline |
| 8 | Model fine-tuning & adaptation | 1 | 2 | Explain LoRA/DPO/distillation; decide when NOT to fine-tune |
| 9 | AI evaluation & benchmarking | 1 | 3 | Build an eval harness with LLM-judge + human-labeled golden set; detect regressions |
| 10 | AI safety, security & governance | 2 | 4 | Threat-model an agent with the lethal trifecta; apply two securing patterns; map to OWASP LLM Top 10 |
| 11 | AI infrastructure, deployment & optimization | 2 | 3 | Explain serving stack (vLLM/paged KV, quantization, caching); size a deployment |
| 12 | Production observability & reliability | 1 | 3 | Instrument an agent with traces, token/cost metrics, and failure alerts |
| 13 | Enterprise AI architecture & integration | 3 | 4 | Produce a reference architecture (IAM, data boundaries, guardrails, HITL) for a regulated workload |
| 14 | AI-assisted software engineering | 3 | 4 | Codify team workflow: specs, sandboxed agents, review gates, eval-backed CI |
| 15 | AI technology strategy & product evaluation | 3 | 4 | Vendor evaluation framework with independent benchmarks and TCO |

## 2. 90-day arc (2026-11-24 -> 2027-02-21)

- Weeks 1-4 (foundations that pay off immediately): agent patterns, context engineering, MCP, agent security, RAG fundamentals, reasoning/RL vocabulary.
- Weeks 5-8 (build): one end-to-end agentic reference implementation (GCP-first, Claude or Gemini models) with evals, tracing, guardrails; one RAG system with measured retrieval quality.
- Weeks 9-12 (judgment): comparative evaluations (models, frameworks, serving), cost/latency engineering, security hardening, write-ups that teach others.

Daily budget: 30-60 minutes reading; one longer hands-on block (2-3 h) per week.

## 3. First seven days (2026-11-24 -> 2026-11-30)

(See the daily brief for the day-by-day plan. Item IDs refer to `AI_Research_Reading_Tracker.csv`.)

| Day | Focus | Items (min) |
|---|---|---|
| Tue 2026-11-24 | Agent patterns + agent threat model + supply-chain incident | AI-0011 (20), AI-0016 (10), AI-0057 (25) |
| Wed 2026-11-25 | Context engineering, quantified | AI-0012 (20), AI-0064 sections 1-4 (40) |
| Thu 2026-11-26 | Frontier model landscape (light day) | AI-0025 (15), AI-0024 (15) |
| Fri 2026-11-27 | MCP architecture and tool-surface design | AI-0014 (30), AI-0068 skim (30) |
| Sat 2026-11-28 | Hands-on: compaction budget experiment (daily brief Section 6) | 120-180 |
| Sun 2026-11-29 | Securing agents; weekly review | AI-0017 (45), AI-0066 abstract + Table 3 (15) |
| Mon 2026-11-30 | Memory vs RAG; monthly baseline assessment | AI-0065 (60) |

Competency targets for the week: #5 agents and #10 security move from 2 toward 3 (explain the five workflow patterns, the lethal trifecta, and two securing patterns unaided); #3 context engineering toward 4 (run the compaction experiment and read its numbers).

## 4. Monthly assessment log
- 2026-11-30 (planned): first re-score of the baseline using checkpoint answers from the week and the experiment write-up. Levels move only on evidence.
