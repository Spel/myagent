# Changelog: BenchGen Pre-Launch Alpha (v0.1.0)

**Date:** June 15, 2026  
**Author:** Andrii Bidochko & Ubraine Bot  

We are excited to announce the first official pre-launch alpha release of **BenchGen** (v0.1.0)! BenchGen is an evaluation and fine-tuning harness designed to help developers build production-ready, highly reliable AI agents by capturing and analyzing real decision trajectories.

---

## 🚀 Key Features in v0.1.0

### 1. Unified Trajectory Scoring (The 5 Dimensions)
We have introduced a deterministic scoring engine that rates agent behavior across five core dimensions of production quality:
* **Tool-Call Accuracy (Target ≥ 85%):** Catching malformed parameters, silent tool failures, and nested schemas.
* **Skill Coverage (Target ≥ 80%):** Validating whether agents utilize structured instructions (skills) or fall back on raw improvisation.
* **Goal Completion (Target ≥ 78%):** Verifying if the agent completed the full multi-step workflow without infinite loops or early halting.
* **Memory Utilisation (Target ≥ 75%):** Tracking long-term memory read/write cycles to prevent context bloating and factual drift.
* **Regression Stability (Target ±5 points max):** Creating historical quality baselines before and after model or skill switches.

### 2. Atropos JSONL Trajectory Ingestion
* Native parsing support for Atropos-format trajectory JSONL logs exported directly from **OpenClaw** and **NemoClaw** sessions.
* Instant, automated conversion of raw execution steps into state-action-reward loops.

### 3. Training-Data Export for LoRA Fine-Tuning
* Filter clean, high-scoring execution trajectories (e.g., above a customizable quality score threshold like 78/100).
* Export structured JSONL datasets ready to feed directly into open-weight model training harnesses (Llama 4, Qwen 3, Gemma 4):
  ```bash
  benchgen export --min-score 78 --output ./training-data/
  ```

---

## 🛠️ Performance & Setup

Install the pre-launch CLI client with:
```bash
pip install benchgen
```

Run a complete trajectory audit from your local history in under 5 minutes:
```bash
benchgen scan
```

---

## 🗓️ What’s Next?
Our roadmap toward our Q3 2026 public launch includes:
1. **Digital-Twin Environments:** Simulated business organizations (replicating ERP, CRM, and internal workflows) to test agents under safe, sandboxed conditions.
2. **Domain Filtering:** Domain-specific scoring layers for ERP-integrated agents (such as Odoo or SAP).
3. **DT Cloud & Sovereign GPU Integration:** Zero-click fine-tuning pipelines directly on sovereign cloud clusters.
