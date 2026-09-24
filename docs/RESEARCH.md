# Research

## Research Problem

Multi-agent AI systems used for cybersecurity analysis can produce unreliable results when individual agent outputs are incorrect, conflicting, or misleading, and are trusted equally regardless of actual reliability.

## Research Questions

1. Can a simple, trust-aware weighting mechanism improve the reliability of a multi-agent cybersecurity analysis system compared to treating all agent outputs equally?
2. What, if anything, changes in agent output quality and system reliability when a base LLM is replaced with a fine-tuned, cybersecurity-oriented LLM?
3. Can a small set of understandable, checkable signals (historical accuracy, verification result, peer agreement) meaningfully distinguish reliable from unreliable agent outputs in this context?

## Objectives

- Build a working Phase 1 (base LLM) multi-agent baseline.
- Build a working Phase 2 (fine-tuned LLM) extension of the same system.
- Compare the two phases on a small number of measurable dimensions.
- Document what was actually learned, including negative or inconclusive results.

## Background

**Multi-agent AI:** Multi-agent systems (MAS) built on large language models have become a significant area of research, where multiple specialized LLM-based agents collaborate to solve tasks that a single agent would struggle with. Key architectural patterns include supervisor models (a central agent delegating to specialists), hierarchical models (layered structures), and network models (peer-to-peer communication). Recent surveys such as "Large Language Model Based Multi-agents: A Survey of Progress and Challenges" (IJCAI, 2024) provide an in-depth discussion of LLM-based multi-agent systems, covering agent profiling, communication methods, and application domains. For cybersecurity specifically, centralized multi-agent orchestration has been shown to yield significantly stronger performance than single-agent approaches.

**Cybersecurity AI:** Machine learning and LLM-based approaches to cybersecurity span intrusion detection, phishing detection, malware analysis, and log analysis. Traditional ML approaches (Random Forest, XGBoost, LSTM) have been applied to network intrusion detection using benchmark datasets such as CIC-IDS2017 and UNSW-NB15. More recently, researchers have adapted pre-trained LLMs for network traffic analysis — for example, transforming numerical network flow statistics into token sequences for processing by encoder-decoder models. LLMs have also been applied to generate natural language explanations for detected threats, improving the interpretability of detection decisions. Current academic consensus suggests LLMs work best as complementary systems to traditional ensemble-based IDS rather than complete replacements, due to computational overhead.

**LLMs and fine-tuning:** Parameter-efficient fine-tuning (PEFT) methods allow adaptation of large pre-trained models without updating all parameters. LoRA (Low-Rank Adaptation) freezes the original model weights and injects trainable low-rank decomposition matrices into transformer layers, typically reducing trainable parameters to 0.5%–5% of the original model size while maintaining performance comparable to full fine-tuning. QLoRA extends LoRA by quantizing the frozen base model to 4-bit precision (using NormalFloat or NF4 data types), allowing fine-tuning of much larger models (e.g., 65B parameters) on consumer-grade hardware. These techniques are well-supported by the Hugging Face PEFT library and have been successfully applied to cybersecurity-specific LLM fine-tuning tasks.

**Trust-aware AI / verification / uncertainty:** Trust modeling in multi-agent systems is an active research area. Key challenges include hallucination propagation (where errors from one agent are incorporated by downstream agents), state synchronization failures, and the "verifier reliability" problem (a verifier agent can itself be a point of failure). Research distinguishes between reputation-based trust and "actual trust" — an agent's objective capacity to deliver tasks. Formal methods such as model checking and temporal reasoning are being adapted for multi-agent trust verification. For LLM-specific trust, emerging frameworks use semantic uncertainty and entropy measures to quantify trust at the response meaning level, enabling adaptive orchestration such as selective re-prompting when uncertainty is high. The TrustAgent framework categorizes agent trustworthiness into intrinsic factors (brain, memory, tools) and extrinsic factors (user, environment).

## Related Work

- **Multi-agent LLM orchestration:** Supervisor-based architectures where a central coordinator dispatches tasks to specialized agents and aggregates results are a common pattern in recent multi-agent LLM research, and directly inform this project's Coordinator design.
- **CyberLLM:** A multi-agent framework for automotive cybersecurity combining deterministic layers with LLM-based refinement to detect vulnerabilities — demonstrates the viability of specialized agents for cybersecurity analysis.
- **LLM-based intrusion detection:** Research using adapted pre-trained LLMs (e.g., T5, LLaMA) for network traffic classification on CIC-IDS-2017 and UNSW-NB15 datasets, achieving high detection accuracy with fine-tuning approaches including QLoRA.
- **TrustAgent framework:** A comprehensive taxonomy of agent trustworthiness covering intrinsic and extrinsic trust factors, relevant to this project's trust model design.
- **Semantic uncertainty for LLM trust:** Frameworks using semantic entropy to measure LLM output reliability, providing a theoretical foundation for trust-based agent weighting.

## Literature

| Source | Key Finding | Relevance |
|---|---|---|
| Guo et al., "Large Language Model Based Multi-agents: A Survey of Progress and Challenges" (IJCAI, 2024) | Comprehensive survey of LLM-based multi-agent systems covering profiling, communication, and application domains | Foundational reference for multi-agent architecture design |
| Hu et al., "LoRA: Low-Rank Adaptation of Large Language Models" (ICLR, 2022) | Introduced LoRA — injecting trainable low-rank matrices into frozen pre-trained models reduces trainable parameters to ~0.5–5% with comparable performance | Core technique for Phase 2 fine-tuning |
| Dettmers et al., "QLoRA: Efficient Finetuning of Quantized LLMs" (NeurIPS, 2023) | Extended LoRA with 4-bit quantization (NF4), enabling fine-tuning of 65B-parameter models on consumer GPUs | Enables Phase 2 fine-tuning on student hardware |
| Moustafa & Slay, "UNSW-NB15: A Comprehensive Dataset for Network Intrusion Detection" (MilCIS, 2015) | Standard network intrusion detection benchmark with modern attack categories (Fuzzers, Backdoors, DoS, Exploits, etc.) | Candidate dataset for Detection Agent evaluation |
| Sharafaldin et al., "Toward Generating a New Intrusion Detection Dataset and Intrusion Traffic Characterization" (ICISSP, 2018) | Created CIC-IDS2017 benchmark dataset covering common modern attacks (DDoS, Botnets, Brute Force) | Candidate dataset for Detection Agent training/evaluation |
| "A Survey on LoRA of Large Language Models" (arXiv, 2024) | Structured review of LoRA variants, theoretical foundations, and downstream adaptation approaches | Guides selection of specific LoRA configuration for Phase 2 |
| TrustAgent framework (arXiv, 2024) | Categorizes agent trustworthiness into intrinsic (brain, memory, tools) and extrinsic (user, environment) factors | Informs trust model design and limitation analysis |

## Dataset Considerations

No dataset has been finalized. Candidates to evaluate (not commitments):

- **CIC-IDS2017** — Canadian Institute for Cybersecurity intrusion detection dataset with labeled network flows covering DDoS, Botnets, Brute Force, and other attack types. Widely used academic benchmark, freely available for research.
- **UNSW-NB15** — University of New South Wales network intrusion dataset with nine modern attack categories. More complex and representative than older datasets like KDD Cup 99.
- **Phishing email datasets** — Publicly available labeled phishing/legitimate email corpora for testing email-based threat detection.
- **Synthetic IOC data** — Locally constructed indicators of compromise (IP addresses, domains, file hashes) for the Intelligence Agent, clearly labeled as synthetic.
- **Synthetic behavioral baselines** — Constructed user/host activity profiles for the Behavioral Analysis Agent, clearly labeled as synthetic.

Any dataset used must be appropriately licensed for academic use, and any synthetic data must be clearly labeled as synthetic in the final report. See `docs/DATASET.md` for detailed dataset documentation.

## Phase 1 Methodology

Build the four logical agents using a base/normal LLM with role-specific prompting. Implement verification and trust as plain code. Test on a small, chosen scenario set. Record baseline behavior and any issues encountered.

## Phase 2 Methodology

Fine-tune an open-source LLM (approach: LoRA/QLoRA, to be investigated) on cybersecurity-related data. **Which agent(s) receive the fine-tuned model is not yet decided** (see `docs/DECISIONS.md`, D-010) — the choice depends on dataset availability, hardware, training feasibility, time, student skill level, experimental design, and educational value. Integrate the fine-tuned model into the same architecture used in Phase 1, changing only the model, not the surrounding system. See `docs/LLM_FINE_TUNING.md` for fine-tuning methodology details.

## Evaluation Methodology

Compare Phase 1 and Phase 2 using a small number of concrete, measurable dimensions selected by the team (e.g., accuracy on a labeled test set, handling of a deliberately conflicting/misleading test case, whether trust-weighting changed the final outcome). Exact metrics are **TO BE DECIDED** — this document intentionally does not pre-select final metrics or claim expected results. See `docs/EXPERIMENTS.md` for experiment design and tracking.

## Limitations

- Small team, limited time, and limited compute constrain both the fine-tuning scope and the size/rigor of any evaluation.
- Any accuracy or reliability figures produced will be based on a small, non-industrial-scale test set and should be reported as such.
- Literature review is based on publicly available sources reviewed at the time of writing; the team should continue to track relevant new publications.

## Research Gaps

- Which agent(s) will be fine-tuned in Phase 2 is unresolved.
- No baseline experiments have been run.
- No dataset has been finalized (candidates identified — see Dataset Considerations above and `docs/DATASET.md`).
- Optimal trust model weights and thresholds require empirical tuning once the system is operational.

## References

1. Guo, T., et al. "Large Language Model Based Multi-agents: A Survey of Progress and Challenges." IJCAI, 2024.
2. Hu, E. J., et al. "LoRA: Low-Rank Adaptation of Large Language Models." ICLR, 2022.
3. Dettmers, T., et al. "QLoRA: Efficient Finetuning of Quantized LLMs." NeurIPS, 2023.
4. Moustafa, N. & Slay, J. "UNSW-NB15: A Comprehensive Data Set for Network Intrusion Detection Systems." MilCIS, 2015.
5. Sharafaldin, I., et al. "Toward Generating a New Intrusion Detection Dataset and Intrusion Traffic Characterization." ICISSP, 2018.
6. Wang, Z., et al. "A Survey on LoRA of Large Language Models." arXiv preprint, 2024.
7. TrustAgent: Trustworthiness framework for LLM-based agents. arXiv preprint, 2024.
