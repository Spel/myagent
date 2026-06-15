# What is BenchGen?

**BenchGen is an AI agent evaluation and fine-tuning harness that scores agent quality across five dimensions using real operational trajectory data and exports clean trajectories for model fine-tuning.**

In simple terms: BenchGen is a **flight simulator for AI agents** — a platform where agents can execute thousands of decisions inside simulated environments, fail safely, and be measured, improved, and made production-ready before they ever touch real operations.

> **Quick answer:** BenchGen evaluates AI agents in simulated operational environments that replicate real business systems. It captures full decision trajectories, scores agent quality across five measurable dimensions, identifies failure patterns, and turns evaluation data into training data for continuously improving AI systems.

---

## The Problem

88% of AI agent pilots never reach production (Forrester 2026).

The single largest reason — cited by 64% of enterprises — is the inability to evaluate agent quality reliably (Anaconda 2026).

AI agents are moving from demos to real work. They write code, operate software, interact with APIs, and make decisions inside real business processes. But the infrastructure to test them properly does not exist.

Today, most AI systems are evaluated using **static benchmarks** — academic tests designed to measure knowledge and reasoning. These benchmarks were never designed to evaluate how AI behaves inside real operations.

Real environments are messy. They include:

- Multiple interconnected systems
- Unpredictable inputs
- Long multi-step workflows
- Cascading errors and recovery requirements

An agent that performs well on a standard benchmark may still fail completely when asked to complete a real task. There is a **37% average gap** between benchmark scores and real-world performance (BCG 2026). Organizations discover this gap after deployment — when failures are expensive.

---

## The Gap in the AI Ecosystem

The AI stack today includes:

- Foundation models
- Tools and integrations
- Agent frameworks
- Deployment platforms

What is missing is the layer between development and production: **infrastructure to answer whether an agent can be trusted in the real world.**

Without realistic testing environments, companies deploy agents blindly. Failures surface only after customers are affected. Evaluation happens too late, with too little data, and with no path to improvement.

---

## The Solution: BenchGen

BenchGen provides an end-to-end platform for simulating, evaluating, benchmarking, and continuously improving AI agents.

**BenchGen is an AI agent evaluation and fine-tuning harness** that enables organizations to:

1. Simulate real-world operational environments
2. Run agents through multi-step workflows and complex tool interactions
3. Score agent quality across five measurable dimensions
4. Identify failure patterns before they reach production
5. Export filtered trajectory data for model fine-tuning
6. Repeat continuously to compound improvements over time

The core CLI workflow:

```bash
pip install benchgen
benchgen scan # quality report in under 5 minutes
benchgen export --min-score 78 --output ./training-data/
```

BenchGen reads agent trajectory data generated during real and simulated operation, applies deterministic scoring logic across five dimensions, and produces actionable quality reports — telling you not just what score your agent has, but exactly which failure patterns are causing it.

---

## The Two-Layer Improvement Model

Every article and product decision at BenchGen is grounded in a two-layer model for agent improvement.

**Layer 1 — Skills and Memory**

Agents self-improve by writing skill files and updating persistent memory. This layer works with any model, is instant, and requires no GPU. It is the most powerful and least understood layer — most agent quality problems live here, not in the model.

- Skills: structured instruction files the agent invokes for recurring task types
- Memory: persistent context the agent reads and updates across sessions

**Layer 2 — LLM Fine-Tuning**

When Layer 1 improvements are insufficient, model weights can be updated using trajectory data collected during real operation. This requires open-weight models (Llama 4, Qwen 3 72B, Gemma 4) and GPU compute.

**BenchGen sits between the layers.** It scores Layer 1 trajectories to determine whether problems are in skills, memory, or the model itself — and identifies which trajectories are clean enough to feed into Layer 2 fine-tuning. Training on unfiltered production data makes models worse. BenchGen is the filter that makes fine-tuning work.

---

## The Five Quality Dimensions

BenchGen evaluates agent quality across five dimensions. Each one targets a different failure source.

| Dimension | What It Measures | Production Target |
|---|---|---|
| **Tool-Call Accuracy** | Did the agent call the right tools with correct parameters? | ≥ 85% |
| **Skill Coverage** | Does a skill exist for each task type? Is it being used? | ≥ 80% |
| **Goal Completion** | Did the agent fully finish the task without early stopping? | ≥ 78% |
| **Memory Utilisation** | Is memory read before tasks and updated when new context is learned? | ≥ 75% |
| **Regression Stability** | Does quality hold after model or skill changes? | ±5 points max |

**Score interpretation:**

| Score | Status |
|---|---|
| Below 60 | Not production-ready — significant failures in at least one dimension |
| 60–69 | Experimental / internal only |
| 70–79 | Acceptable for internal tools where output is reviewed |
| 80–89 | User-facing ready — standard production threshold |
| 90+ | Enterprise-grade — appropriate for regulated industries |

The 88% of agent pilots that fail (Forrester 2026) are predominantly stuck in the 60–74 range: capable enough to pass a demo, unreliable enough to generate user complaints at scale.

---

## From Benchmarking to Learning

Traditional benchmarks measure answers. BenchGen measures **behavior**.

Agents are evaluated through full decision trajectories:

**State → Action → Tool Response → Outcome → Reward**

Every trajectory is a record of the complete decision sequence that produced a result. This makes it possible to understand not just whether the agent succeeded, but how it failed, whether it recovered, and how reliably it performs across long workflows.

These trajectories become the foundation for improvement. Once scored and filtered, they can be used directly for LoRA fine-tuning:

```bash
# Export clean trajectories above quality threshold
benchgen export --min-score 78 --output ./training-data/

# Fine-tune on compatible open-weight model
python train.py \
 --model Qwen/Qwen3-72B \
 --data ./training-data/ \
 --method lora \
 --output ./adapters/agent-custom-v1
```

Evaluation becomes **training infrastructure**. Benchmarking is the starting point for improvement, not the final step.

Agents that reach production-ready thresholds see an average **171% ROI over 18 months** (BCG 2026). The compounding loop — better evaluation → cleaner training data → stronger model → higher quality trajectories → better next fine-tune — is what drives that number.

---

## Digital-Twin Environments

At the core of BenchGen are simulated operational environments: digital replicas of real organizations that agents can operate inside exactly as they would in production.

A digital-twin environment can simulate:

- Customer support systems and ticket resolution workflows
- Financial operations and ERP processes (invoicing, CRM, approvals)
- Internal automation and document processing
- Compliance workflows for regulated industries

Agents execute tasks, call tools, encounter edge cases, and make mistakes — all inside a safe simulation. Every action is recorded. Every outcome is measured. Every failure becomes training data.

This is how pilots train before flying real aircraft. How traders test strategies before risking real capital. How robots are trained before deployment on the factory floor.

AI agents should be no different.

---

## Competitive Landscape

BenchGen occupies a position no other evaluation tool currently fills.

| Capability | LangSmith | Arize Phoenix | Confident AI | Braintrust | **BenchGen** |
|---|---|---|---|---|---|
| Trajectory format (JSONL/Atropos) | ✗ | ✗ | ✗ | ✗ | **✓** |
| Skill file evaluation | ✗ | ✗ | ✗ | ✗ | **✓** |
| Memory utilisation scoring | ✗ | ✗ | ✗ | ✗ | **✓** |
| Filtered LoRA export for fine-tuning | ✗ | ✗ | ✗ | ✗ | **✓** |
| OpenClaw / NemoClaw trajectory support | ✗ | ✗ | ✗ | ✗ | **✓** |
| LLM tracing and spans | ✓ | ✓ | ✓ | ✓ | — |
| Red teaming / AI governance | ✗ | ✗ | ✓ | ✗ | — |
| Purpose-built eval database | ✓ | ✗ | ✗ | ✓ | — |

**LangSmith** is the right tool for teams building LLM-powered products on any framework. It has no model of skill files, memory systems, or the trajectory → fine-tuning loop. That gap is what BenchGen fills.

**Arize Phoenix** is the strongest OSS observability option — excellent for LLM tracing and span analysis. No Atropos integration, no skill-aware evaluation, no path to model fine-tuning.

**Confident AI / DeepEval** excels at LLM evaluation for compliance-sensitive teams. Covers governance and red teaming. Not built for self-hosted agent architectures with skill/memory systems.

**Braintrust** is the most technically sophisticated general-purpose competitor — genuine engineering quality. Excellent for LLM product teams. No concept of skill file evaluation, memory utilisation, or trajectory export for fine-tuning.

**Universal gap:** None of the existing tools ingest Atropos JSONL trajectories natively, evaluate skill files, score memory utilisation, or export filtered datasets for LoRA fine-tuning. BenchGen is the only platform that closes the full loop.

---

## Who BenchGen Is For

**Individual developers** who have been running an AI agent for a few weeks and are seeing inconsistent results. `benchgen scan` produces a quality report in under five minutes — no configuration required.

**Teams running internal automation** — document processing, research, ERP workflows. The weekly scan workflow catches regressions before users do.

**Enterprise teams in regulated industries** — Finance, Healthcare, Government, Manufacturing — who need verifiable evaluation records, auditability, and compliance-appropriate quality thresholds (90+).

**Organizations running Odoo or ERP-integrated agents.** BenchGen includes domain filtering to score ERP-specific workflows (invoice processing, CRM updates, field validation) separately from general agent performance.

**Enterprises deploying NemoClaw or IronClaw** on NVIDIA NIM infrastructure. The same evaluation framework applies with enterprise-grade thresholds appropriate for regulated operations.

---

## Market Opportunity

| Segment | Value |
|---|---|
| **TAM** — Total Addressable Market for agent infrastructure and evaluation | $28 Billion |
| **SAM** — Evaluation, simulation, and benchmarking solutions | $4.2 Billion |
| **SOM** — Initial target: Europe, Türkiye, GCC Region | $75 Million |

**Geographic focus:** Europe, Türkiye, GCC Region — markets where digital sovereignty, regulated AI deployment, and enterprise AI adoption are converging.

**Why now:**
- AI agents are moving from experimentation to production across enterprises
- Regulatory requirements for AI governance and auditability are increasing
- Falling LLM costs accelerate agent adoption; reliable benchmarking has become the bottleneck
- Synthetic data for evaluation is becoming a mainstream enterprise requirement

---

## Business Model

**SaaS Subscriptions** — Recurring platform access covering evaluation infrastructure, benchmarking tools, synthetic data generation, and reporting.

**Enterprise Licensing** — Custom deployments for on-premise or sovereign cloud environments with compliance requirements.

**Professional Services** — Implementation, integration, and agent optimization engagements.

**GPU Partner (DT Cloud)** — Fine-tuning on H100/H200 infrastructure on Turkish sovereign cloud, directly integrated with BenchGen's trajectory export workflow.

**Distribution Partner (UBOS)** — Enterprise relationships across Odoo/ERP deployments, providing direct access to organizations deploying AI agents in business operations.

---

## Team

**Andrii Bidochko — Co-Founder**
PhD in AI Systems. Founder of UBOS. 90+ software projects delivered across 13+ years in software products. Published research on long-horizon LLM agents in Elsevier's Journal of Computational Science.

**Tolga Dincer — Co-Founder**
Lifelong technologist specializing in AI-native cloud architecture. Focused on digital sovereignty. Experience across fintech, defense, and public-sector infrastructure.

**Ruslan Synytsky — Co-Founder**
Serial entrepreneur and Java Champion. Founded Jelastic PaaS, scaled across 100+ data centers. Acquired by Virtuozzo in 2021. Advisor on infrastructure strategy and cloud partnerships.

---

## Vision

AI is transitioning from systems that generate answers to systems that take actions.

This transition will redefine how software is built, deployed, and trusted. Agents will automate decisions, execute workflows, and operate systems on behalf of humans. But without the ability to evaluate agent behavior in realistic environments, progress will remain constrained by uncertainty.

The long-term goal of BenchGen is to become the **standard simulation and evaluation layer for the agent ecosystem** — the infrastructure that allows agents to learn before they act, improve through feedback, and demonstrate reliable performance before deployment.

Just as training infrastructure enabled the rise of large language models, and inference infrastructure enabled their deployment, the next generation of AI requires something new: **capability infrastructure** — the layer that measures, verifies, and compounds agent reliability over time.

BenchGen is building that layer.

---

## In One Sentence

**BenchGen is where AI agents are evaluated, measured, and improved — before they reach the real world.**

---

## Get Started

BenchGen is pre-launch, targeting Q3 2026.

```bash
pip install benchgen
benchgen scan
```

Join the waitlist and get early access at **[benchgen.com/hermes](https://benchgen.com/hermes)**

---

*For a deeper technical walkthrough, see the [Hermes Agent Evaluation Complete Guide](/blog/hermes-agent-evaluation-complete-guide) — an 11-chapter reference covering the full methodology from trajectory scoring to enterprise deployment.*