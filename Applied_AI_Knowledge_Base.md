# Applied AI Knowledge Base

Searchable, cumulative. Each entry links to tracker item IDs (`AI-xxxx`). Append; never rewrite history. Sections: 1 Core concepts · 2 Architecture patterns · 3 Security patterns · 4 Comparisons · 5 Recent developments log (dated) · 6 Glossary.

---

## 1. Core concepts (foundations)

### 1.1 Transformer, attention, and the KV cache (AI-0001, AI-0008)
- A decoder-only LLM predicts the next token from all previous tokens. Each layer computes, for every token, query (Q), key (K), and value (V) vectors; attention weights are `softmax(QK^T / sqrt(d_k)) V`. Multi-head attention runs several of these in parallel on sub-spaces.
- At inference, K and V for past tokens are cached (the **KV cache**) so each new token costs one forward pass over itself plus attention over the cache. KV cache memory grows linearly with context length x layers x heads, which is why long contexts are expensive and why serving engines fight for memory.
- **PagedAttention** (vLLM) stores the KV cache in fixed-size blocks mapped through a block table, like virtual memory pages. Result: near-zero fragmentation, memory sharing across sequences (prefix caching, parallel sampling), and much higher batch sizes and throughput.
- Architect takeaways: (1) prompt caching works because of KV reuse; keep stable prefixes stable. (2) Throughput is memory-bound; quantizing KV cache and weights buys batch size. (3) Mixture-of-Experts (MoE) models route each token to a few experts, giving large total parameters with lower per-token compute; costs are in memory, not FLOPs.

### 1.2 Scaling laws and the three scaling axes (AI-0021, AI-0007)
- Pre-training loss follows power laws in parameters, data, and compute (Kaplan 2020). Chinchilla (Hoffmann 2022) corrected the allocation: for a fixed compute budget, train smaller models on more tokens (~20 tokens/parameter), which is why modern models are "over-trained" on trillions of tokens.
- Post-training scaling: RL on verifiable tasks adds capability beyond pre-training (see 1.3).
- Test-time (inference) scaling: spend more compute per query via longer reasoning, best-of-N sampling with a verifier, or iterative revision. Snell et al. 2024 show the optimal strategy depends on prompt difficulty; on easy prompts a small model with adaptive test-time compute can beat a 14x larger model, on hard prompts it cannot.

### 1.3 Post-training: SFT, RLHF, DPO, RLVR/GRPO (AI-0005, AI-0020, AI-0006)
- **SFT**: supervised fine-tuning on demonstrations. **RLHF** (InstructGPT): train a reward model on human preference pairs, then optimize the policy with PPO against it, with a KL penalty to the reference model.
- **DPO**: removes the explicit reward model and RL loop. The RLHF objective has a closed-form optimal policy; DPO rewrites it as a classification loss over (chosen, rejected) pairs. Cheaper and stable; limits: offline, sensitive to preference data quality.
- **RLVR** (RL with verifiable rewards): for math/code/structured tasks, reward = checkable correctness (unit tests, exact match). **GRPO** (DeepSeekMath, used in DeepSeek-R1): sample a group of G outputs for a prompt, compute each sample's advantage as its reward normalized by the group mean and std, and update the policy with a clipped PPO-style objective plus KL penalty, with no separate value/critic model. R1-Zero showed that pure RL from a base model elicits long chains of thought, self-verification, and "aha" behaviors; R1 adds a cold-start SFT stage and multi-stage RL for readability and general capability. Distilling R1 outputs into small dense models transfers much of the reasoning gain.
- Architect takeaways: reasoning models trade latency and tokens for accuracy; budget "thinking" like any other cost; verifiable-reward design is the lever when you fine-tune for a domain.

### 1.4 Prompting, reasoning, and agent loops (AI-0003, AI-0002)
- **Chain-of-Thought**: exemplars with intermediate steps elicit multi-step reasoning in large models; small models do not benefit the same way. Modern reasoning models internalize this via RL.
- **ReAct**: alternate Thought (reasoning about what to do), Action (call a tool), Observation (tool result) until an answer. It is the template of the "agent loop" in every framework: model proposes a tool call, runtime executes it, result is appended to context, repeat.
- Related patterns: Tree of Thoughts (branching search over reasoning states), Reflexion (verbal self-feedback stored across attempts), self-consistency (majority vote over sampled chains).

### 1.5 Retrieval-Augmented Generation (AI-0004, AI-0009, AI-0010)
- Pipeline: ingest -> chunk -> embed -> index (vector + lexical) -> query -> retrieve top-k -> (rerank) -> assemble context -> generate -> cite. Lewis et al. 2020 introduced the parametric/non-parametric memory framing with DPR + BART.
- Production reality: hybrid retrieval (BM25 + dense) and a cross-encoder reranker usually beat pure vector search; chunking strategy and metadata filters matter more than the embedding model choice; evaluate retrieval (recall@k, MRR) separately from generation (faithfulness, answer correctness).
- **Lost in the middle**: models attend best to the start and end of context; relevant passages placed mid-context are used worse. **Context rot** (Chroma, 18 models): performance degrades with input length even on trivially simple tasks, non-uniformly across models. Implication: retrieve less, rank better, put the most important content at the edges, and do not treat a 1M-token window as 1M tokens of reliable working memory.

### 1.6 Context engineering (AI-0012)
- Context is a finite, degrading resource (attention budget). Levers: system prompt at the right "altitude" (clear heuristics, not brittle rules or vague guidance); minimal, non-overlapping tool set; just-in-time retrieval (load references by pointer, not up front); compaction (summarize and restart when near limits); structured note-taking outside the window (files, memory stores); sub-agent isolation (each sub-agent gets a clean window and returns a distilled result).
- Memory architectures: short-term (window), episodic (session notes/logs), long-term (vector or file store with retrieval), procedural (instructions, skills). Decide what persists, who can write it, and how it is validated, because memory is an injection surface.

### 1.7 Tool use and the Model Context Protocol (AI-0014, Anthropic "Writing tools for agents")
- Function calling: the model emits a structured call matching a JSON schema; the runtime executes and returns the result. Tool quality is prompt quality: names, descriptions, parameter semantics, and error messages shape agent behavior.
- **MCP**: open protocol with three roles. Host (the application, e.g. Claude Code, an IDE, a chat client) runs one or more Clients, each maintaining a 1:1 session with a Server. Servers expose **tools** (model-invoked actions), **resources** (app-controlled data), and **prompts** (user-invoked templates). Transport: JSON-RPC 2.0 over stdio (local) or Streamable HTTP (remote), with capability negotiation at initialize, and OAuth-based authorization for remote servers. Enterprise relevance: one integration surface for many agents; also a new supply-chain and injection surface (tool descriptions and results are untrusted input).

## 2. Architecture patterns (AI-0011, AI-0013, AI-0018)

- **Workflow vs. agent**: a workflow orchestrates LLM calls through predefined code paths; an agent lets the model direct its own tool use and control flow. Use workflows when the path is known; use agents only when the flexibility is worth the cost and unpredictability.
- **Five composable workflow patterns**: prompt chaining (sequential steps with gates), routing (classify then dispatch to specialized prompts/models), parallelization (sectioning or voting), orchestrator-workers (dynamic task decomposition and delegation), evaluator-optimizer (generate -> critique -> revise loop).
- **Orchestrator-worker multi-agent research** (Anthropic): lead agent plans and spawns parallel sub-agents with narrow, explicit briefs; sub-agents return distilled findings, not raw dumps; costs are 15x a single chat; evaluate with LLM judges on factual accuracy, citation accuracy, completeness, source quality, and tool efficiency; production needs resumability, tracing, and rainbow deploys for long-running agents.
- **Why multi-agent systems fail (MAST)**: 14 failure modes in three groups: specification/system design (role violation, task disobedience, step repetition, loss of conversation history), inter-agent misalignment (ignored input, withheld information, reasoning-action mismatch), task verification (premature termination, no or incorrect verification). Most failures are organizational design problems; better prompts help a little, better verification and topology help more.
- **Human-in-the-loop**: place checkpoints before irreversible or outward-facing actions; make approvals legible (what will happen, with what data); log for audit. Regulated-industry default.

## 3. Security patterns (AI-0015, AI-0016, AI-0017)

- **Prompt injection** is the top LLM application risk (OWASP LLM01). Indirect injection arrives via retrieved documents, web pages, emails, tool results, and MCP tool descriptions. It is not solvable by "better prompting"; it must be designed around.
- **Lethal trifecta**: private data access + exposure to untrusted content + an exfiltration channel (outbound HTTP, email, writable tickets, even a markdown image). Remove at least one leg per agent; if all three are required, isolate them in separate agents with constrained channels.
- **Six securing patterns** (Beurer-Kellner et al. 2025): action-selector (LLM picks from fixed actions, no feedback loop); plan-then-execute (plan fixed before reading untrusted data); LLM map-reduce (isolated per-document processing, aggregated by code); dual LLM (privileged LLM never sees untrusted text; quarantined LLM has no tools; data passes via symbolic references); code-then-execute (LLM writes a program that is then run, DSL-constrained); context-minimization (strip user prompt before processing untrusted results). Each trades generality for assurance; pick per task.
- Other OWASP 2025 items to design for: sensitive information disclosure, supply chain (models, datasets, MCP servers, plugins), data/model poisoning, improper output handling (treat model output as untrusted when it reaches a browser, shell, or SQL), excessive agency (least-privilege tools, scoped credentials), system prompt leakage (never store secrets in prompts), vector/embedding weaknesses (tenant isolation in indexes), misinformation, unbounded consumption (token budgets, rate limits).

## 4. Comparisons (maintained)

(Populated as items are studied.) Current comparison tables live in Section 5: frontier model market (5.A, 2026-11-23) and managed agent runtimes (5.B, 2026-11-23).

## 5. Recent developments log

### 2026-11-23 — Baseline scan (window 2026-10-24 → 2026-11-23): frontier models, platforms, security

#### A. State of the frontier model market (all benchmark figures vendor-reported unless marked)
| Tier | Model (ID) | Price in/out per 1M | Context | Notes | Tracker |
|------|-----------|---------------------|---------|-------|---------|
| Frontier | Claude Fable 5.2 (`claude-fable-5-2`) / Mythos 5.2 (gated) | $8 / $40 (fast $16/$80) | 1M, 128k out | GA on Claude Platform, Bedrock, GCP, Foundry; FrontierCode 2.0 49.1% | AI-0025, AI-0048 |
| Frontier | GPT-6.2 Astra (`gpt-6.2-astra`) | $8 / $40 ($0.40 cached) | not stated | Critical cyber rating -> Daybreak gating; system card notes obstacle-omission regression | AI-0024 |
| Frontier | Gemini 4 Carbon | $2/$10 intro -> $4/$20 from 2026-12-01 | not stated | Vendor: 0% Gray Swan IPI success; leads AutomationBench in Anthropic's table | AI-0026 |
| Mid | GPT-6.2 Sol (`gpt-6.2-sol`) | $2 / $10 | not stated | within 0.5 pts of Astra on FrontierCode 2.0 at ~1/5 cost (vendor) | AI-0024 |
| Mid | Gemini 4 Neon (`gemini-4-neon`) | $3 / $15 ($0.15 cached) | 1M | AA Intelligence Index 61 (xhigh); four thinking levels | AI-0027 |
| Fast | Gemini 4 Hydrogen | $1.50 / $7.50 flat | 1M in, 1M out | free tier; Terminal-Bench 4.1 57% | AI-0028 |
| Executor | Meta Muse Ember 1.0 (`muse-ember-1.0`) | $0.10 / $0.50 | 1M, 512K out | closed, hosted; four input modalities | AI-0037 |
| Open | Kimi K3.1 Pro (2.8T/104B-A) | weights (HF) | 1M | strongest open by AA (46); hybrid KDA + gated DSA attention; MXFP4 QAT | AI-0032 |
| Open | Mistral Large 4 (1T/52B-A) | $0.70/$2.10 or weights | not stated | modified-MIT licence, MaaS resale excluded; EU sovereign option | AI-0031 |
| Open | Tencent Hy4 (770B/49B-A) | weights | 1M | multimodal + computer use; built-in speculative drafter | AI-0033 |
| Open-edge | Inkling 2 Mini (26.4B/3.4B-A, looped) | weights, ~20 GB | n/s | first production looped transformer; laptop-class | AI-0034 |

Patterns worth remembering:
- **Four-tier ladders are now standard** (Google: Hydrogen/Neon/Argon/Carbon; OpenAI: Sol/Astra + Luna; Anthropic: Haiku/Sonnet/Opus 5.5 + Fable 5.2). Vendors explicitly pitch *planner/executor* splits (Carbon plans, Hydrogen executes). Design agent systems with a routing layer from day one.
- **Prices converge at $8/$40 for the frontier tier** and $2/$10 for the mid tier; cached-input discounts (90-95%) make prompt-prefix stability a first-order cost lever.
- **Gated dual-use access is now an industry pattern**: OpenAI Daybreak, Anthropic Cyber/Life-Sciences Verification (Mythos), Google Fairwind. Procurement for security use cases must plan for verification programs.
- **Looped / recurrent-depth transformers** (Inkling 2 Mini, GLM-5.4) re-run blocks to buy depth without parameters; a trend to watch alongside hybrid linear-attention stacks (Kimi KDA, FlashMorph2) and MoE diffusion LMs (Clover).
- **Benchmark names churn fast** (FrontierCode 2.0, Terminal-Bench 4.x, Agents' Last Exam, AutomationBench); independent indices (Artificial Analysis, Vals, Arena) are the only cross-vendor comparables and still lag releases.

#### B. Agent platforms: the "managed agent runtime + governance" race (AI-0043, AI-0044, AI-0046, AI-0048, AI-0052)
All three hyperscalers and Anthropic now sell the same shape: a sandboxed per-session runtime for your agent code, an identity for the agent, policy-controlled egress, a managed MCP surface, and tracing/evals.
| Capability | Azure (Foundry Agent Service + Agent 365) | AWS (Bedrock AgentCore) | Google (Gemini Enterprise Agent Platform) | Anthropic (Managed Agents) |
|-----------|------|------|------|------|
| Runtime isolation | VM-isolated sandbox; BYO-AKS preview Dec | Firecracker microVM per session (V2); committed baseline + 4x burst; GPU G7 instances | Agent Runtime (ADK/A2A) | Self-hosted Managed Agents (run service on your infra) |
| Agent identity | Entra Agent ID + Conditional Access (incl. 3rd-party agents) | IAM + `InboundJwtClaim/*` condition keys; org-level RCPs | 3-legged OAuth on behalf of user; Agent Identity | Org/workspace keys; linked billing for ISVs |
| Egress / network | Ordered egress rules (audit -> enforce), private CA, Azure Policy | VPC mode; Gateway interceptors (STREAM) | Agent Gateway via PSC or Cloud NAT static IPs (2 regions) | n/a (self-hosted) |
| MCP governance | Tools Registry, MCP Firewall, Defender discovery of local agents + MCP servers | Gateway as MCP; Agent Registry skill packages (SKILL.md zips) | custom MCP egress | MCP in Claude Code/Agent SDK; managed settings |
| Feedback loop | Insights -> Agent Optimizer -> Programmed Training (preview) | Evaluations + FailureAnalysis insights | — | Analytics/Cost API; EFS sealed safety data |
Takeaway for enterprise design: pick the runtime by where identity and data live (Entra vs IAM vs Google Cloud IAM), not by model, since the frontier models are on all three clouds.

#### C. Coding-agent lifecycle moves to the PR (AI-0047, AI-0049, AI-0050, AI-0045)
- GitHub Copilot Fusion routes across models with Cascade (cheap draft, escalate on failed check) and Critique (draft/review/revise) workflows; billing per underlying model. Claude Ship adds policy-as-file approvals enforced via branch protection (not for ZDR/HIPAA/CMEK orgs). Codex adds SPIFFE workload identity and remote sessions. Copilot SDK 2.0 makes the harness itself an embeddable multi-tenant runtime.
- Pattern: **the agent harness is a product surface**. Research in the same window (Harness-S, ToolSpace, MCP-vs-CLI) treats harness and tool-interface design as measurable performance levers. See Section 1.7 and the papers log below.
- Deprecations with deadlines: OpenAI Agent Builder + Prompt Objects shut down 2026-11-30; Google Jules read-only since 2026-11-11, off 2026-12-31; Langfuse Cloud legacy ingestion removed 2026-11-16; Opus 4.5 retires 2027-01-22.

#### D. Security: the supply chain is the attack surface (AI-0057, AI-0056, AI-0044)
- **Dragos canary study (P1)**: inference routers/marketplaces leaked prompts; stolen credentials were used; ZDR flags on some stolen requests. Controls: one first-tier provider contract or self-host for sensitive data; pin upstream providers; seed canary credentials in agent context and alert on any hit; rotate every secret that was ever in a prompt. This is the operational version of OWASP LLM03 (supply chain) and LLM02 (sensitive information disclosure).
- **MCP reference-server advisories**: Git server config could execute programs; filesystem symlink TOCTOU; fetch SSRF bypasses; Todoist HTTP transport DNS-rebinding (CVSS 9.3). Controls: inventory vendored MCP servers and versions (date-versioned npm packages do not auto-upgrade); prefer stdio or authenticated HTTP with Origin/Host checks; never auto-approve on `readOnlyHint`; per-server scoped credentials.
- Platform response: Microsoft MCP Firewall + Defender discovery/blocking of local agents; Kiro enforced sandboxing for stdio MCP; AgentCore RCPs; Claude Code managed settings/`deniedMcpServers`. Expect "agent identity + MCP allow-list" to become a baseline control in regulated clients.

#### E. Inference stack notes (AI-0058, AI-0062, AI-0042)
- vLLM 0.34: Model Runner V2 only; extensible KV cache on by default (more cache, 6-18% decode latency cost on some workloads); block size 64; CRIU checkpoint/restore; CUDA 13 only since 0.33. Re-benchmark before upgrading.
- Prefill/decode disaggregation is spreading to heterogeneous hardware (Cerebras: GPU prefill, wafer-scale decode, RDMA KV transfer). Research (Evolving Infra, below) shows agent workloads need *runtime* re-balancing of the P/D split and KV eviction that respects agent branch reuse.
- llama.cpp hit 1.0 (official ggml-org post on Hugging Face; GitHub still uses build tags). Local inference for looped/small models (Inkling 2 Mini) is now mainstream.

#### F. Research papers from the window, by subject (all preprints unless stated; numbers as reported by the papers)

**Context, memory, and cost (AI-0064, AI-0065, AI-0076, AI-0075, AI-0080)**
- *You don't need long context* (NVIDIA, AI-0064): compaction is near-lossless for frontier models. Two regimes: end-of-conversation compaction (write a compact state near a budget threshold, restart from task + state) and single-action compaction (every step starts fresh from task + state, one action per context). Claude Opus 4.5 and GPT 5.6 Sol stay within roughly -4/+6 points of full-history baselines on SWE-bench Verified, Terminal-Bench 2.1, tau2-bench and BFCLv3 at 2-9x modeled savings; long-input tasks (RULER, BABILong, LongBench v2) matched or beat baselines at far larger savings. Open-weight models are not uniformly robust (Qwen3 Coder Next collapsed at tight budgets). A good compaction preserves the verbatim task, current intentions/next steps, and needed artifacts. Caveat: cost is modeled; one table/text inconsistency; compaction is lossy by construction.
- *Memory Tax* (UIUC et al., AI-0065): 11 agent-memory systems (flat, hierarchical, graph, trained) lose to 2-round RAG over raw history in 90 of 99 configurations. The "tax" is evidence dropped or obscured by reorganization. Implication: raw-history retrieval is the baseline every memory product must beat on your data.
- *Length Is Cheap, Competition Is Not* (UCSD, AI-0076): in small models, context rot in retrieval is driven by competing evidence-formatted content and rival values, not raw length; attention mass on the evidence predicts loss (up to 58% variance explained). Implication for RAG: deduplicate and resolve conflicts between chunks.
- *Context Language Models* (AI-0075, ICLR 2027 submission): the model edits its own context as a file; reported gains on BrowseComp-Plus with fewer FLOPs. *Tools Need Not Speak in Text* (AI-0080): tool observations compressed to latent tokens, 70-89% fewer tokens.
- Synthesis: context engineering (Section 1.6) now has quantitative backing. Budget contexts aggressively, compact with structured state, retrieve from raw history, dedupe retrieved evidence. Validate per model.

**Agent security (AI-0066, AI-0067, AI-0073)**
- *Task-tampering injection* (Amazon, AI-0066): attacks that keep the task but corrupt one decision component (objective, rules, consequences, actions, observation interpretation, world-state beliefs). Content-detection defenses handle objective hijacks but miss observation/state tampering (9.5-12.1% success); tool allow-lists barely help; capability-based CaMeL holds (~1%). Reinforces Section 3's pattern guidance: control-flow and data-flow separation beats filtering.
- *Agent-swarm attackers* (Google DeepMind, AI-0067): an automated attacker with a shared strategy database reaches 90-99% success on several current models within a few hundred queries and 34% on Gemini 4 Argon (with external classifiers disabled). Static benchmark "robustness" is not evidence against adaptive attackers.
- *Nine dimensions* (Microsoft MSRC et al., AI-0073): taxonomy for auditing which injection classes a benchmark or defense covers; 13% of pairwise classes untested anywhere.

**Tool interfaces and agent training (AI-0068, AI-0069, AI-0074, AI-0077, AI-0082)**
- *MCP vs CLI* (AI-0068): identical capabilities exposed as MCP schemas vs a CLI produce divergent behavior in 94% of paired episodes; fixing the interface realization (DART) gains up to 9 points and saves up to 27k tokens per task. Tool-surface design is a measured lever (see also Anthropic "Writing tools for agents").
- *ToolSpace* (AI-0069) and *RepoFactory* (AI-0082): training environments synthesized from real MCP traces / real repositories move 35B-A3B open models near frontier on tool-use and repo-building benchmarks. "Environments are the scarce asset" is the theme of the month.
- *Decision models* (AI-0074): typed single-pass models are weak actors on ordered tasks but cheap, effective judges and RL teachers ("did this action help?").
- *Multiscale Policy Optimization* (AI-0077): turn-level advantage estimation for multi-turn agent RL.

**Retrieval (AI-0070, AI-0072)**
- *Embeddings vs Grep* (Ant Group, AI-0070): dense's edge over BM25 in code search mostly came from unfair baselines; whole-file BM25 + LLM-generated identifiers beats dense; fusion beats either. *EmbeddingGemma 2* (AI-0072): one 744M open model for text/image/audio/video embeddings with on-device footprints.

**Inference and serving (AI-0071, AI-0083, AI-0084, AI-0087, AI-0079)**
- *Evolving Infra* (AI-0071): agent workloads shift prefill/decode balance at runtime; symmetric engines that switch roles in seconds plus agent-aware KV eviction give 1.1-2.7x throughput over Dynamo on replayed Claude Code traces.
- *DICE* (AI-0083): exact-distribution speculative decoding speedups by synchronizing verification randomness. *LoCo* (AI-0079): cut 25-45% reasoning tokens via local stop/continue preference pairs.
- *SteerDistill* (AI-0084) recovers W4A16 agent task success to within ~1 point of BF16; *Jagged Robustness* (AI-0087) warns that safety behaviors degrade unevenly under quantization: re-run safety evals after quantizing.

**Training and meta-research (AI-0078, AI-0081, AI-0086, AI-0088, AI-0089)**
- *Single algorithm* (CMU, AI-0078): RL-as-MLE unification of pretrain/SFT/RL at small scale, with better retention. *OPD mismatch budget* (AI-0081): FP8 and async rollouts are tolerable for on-policy distillation. *Beam* (AI-0086): a transparent 501B MoE training report. *AltRA-Test* (AI-0088): a statistical gate for LLM-as-judge. *The novelty exposed* (AI-0089): most open-weight technical reports lack ablations; read vendor reports accordingly.

**Conference and lab notes (window)**: EMNLP 2026 (Budapest, Oct 24-29) best papers reported by institutions: "DiscoTrace" and "Don't Read Everything: A Curvature-Conditioned Query for Linear Attention" (arXiv 2606.01294); official awards page not retrieved. ICLR 2027 reviews released Nov 5, decisions Dec 16. NeurIPS 2026 is in December (Sydney, Atlanta, Paris). Anthropic Alignment Science posted on multi-user multi-agent breakdowns, poisoned fine-tuning dilution, and neuron-basis interpretability (day-level dates not captured). OpenAI published a research-acceleration report on Nov 18 (internal agent success on 2-4 hour tasks 23% -> 46% March to October; vendor figures).


## 6. Glossary

- **Agent loop**: model proposes action -> runtime executes -> observation appended -> repeat until stop condition.
- **Compaction**: summarizing a conversation to free context budget while preserving decisions and state.
- **GRPO**: Group Relative Policy Optimization; critic-free RL using group-normalized rewards.
- **KV cache**: stored keys/values of previous tokens enabling incremental decoding.
- **Lethal trifecta**: private data + untrusted content + exfiltration channel.
- **MCP**: Model Context Protocol; host/client/server protocol for tools, resources, prompts.
- **MoE**: Mixture of Experts; sparse routing of tokens to expert sub-networks.
- **PRM / ORM**: process vs. outcome reward model; scores each reasoning step vs. only the final answer.
- **RAG**: retrieval-augmented generation.
- **RLVR**: RL with verifiable rewards (unit tests, exact-match checks).
- **Speculative decoding**: a small draft model proposes tokens; the large model verifies in parallel; same output distribution, lower latency.
- **Test-time compute**: extra inference compute per query (longer reasoning, sampling + verification, revision).
