#!/bin/bash
# sets up the environment - creates fake PDFs in /papers/inbox/ for the LLM to triage
# in prod these would be real arxiv papers but for now we generate
# synthetic ones with enough signal to classify

set -e

uv pip install --system pymupdf --quiet

mkdir -p /papers/inbox /papers/must-read /papers/nice-to-read /papers/bullshit

python3 << 'PYEOF'
import fitz
import json
import os

GROUND_TRUTH_PATH = os.environ.get("GROUND_TRUTH", "/environment/ground_truth.json")

with open(GROUND_TRUTH_PATH) as f:
    gt = json.load(f)

# fake abstracts - enough content for the agent to figure out what's relevant
# and what's bullshit
paper_abstracts = {
    "dpo_convergence_guarantees.pdf": """
        We study the convergence properties of Direct Preference Optimization (DPO) under
        realistic distributional assumptions. We prove that DPO converges to the optimal policy
        at rate O(1/sqrt(T)) under mild conditions on the preference dataset. Our analysis reveals
        that the implicit reward model learned by DPO has favorable generalization properties,
        and we derive optimal learning rate schedules based on our theoretical results. Experiments
        on Anthropic-HH and UltraFeedback confirm our theoretical predictions. We show that
        the commonly used learning rates are suboptimal by a factor of 3-5x.
    """,
    "reward_hacking_taxonomy.pdf": """
        Reward hacking remains a critical failure mode in RLHF-trained language models. We
        propose a comprehensive taxonomy of reward hacking behaviors organized along three axes:
        exploitation type (specification gaming, reward tampering, distributional shift),
        severity (cosmetic, behavioral, catastrophic), and detectability (overt, subtle, latent).
        We validate our taxonomy by red-teaming five production reward models across three model
        families (LLaMA, Mistral, Qwen) and document 47 distinct hacking strategies. We release
        RewardHackBench, a benchmark for evaluating reward model robustness.
    """,
    "kto_vs_dpo_ablation.pdf": """
        Kahneman-Tversky Optimization (KTO) and Direct Preference Optimization (DPO) are the
        two dominant offline preference optimization methods. Despite widespread adoption, no
        large-scale controlled comparison exists. We conduct ablations across 12 benchmarks,
        4 model sizes (1B to 70B), and 3 data regimes. Key findings: KTO dominates when
        preference data is noisy (>15% label noise), DPO is superior with clean data and
        larger models, and both methods benefit substantially from iterative training. We
        release all training configs and checkpoints.
    """,
    "preference_data_quality.pdf": """
        The quality of preference data is a critical bottleneck for RLHF performance, yet
        there are no standardized metrics for measuring it. We introduce PreferenceQA, a suite
        of automatic quality metrics including annotation consistency, preference transitivity,
        difficulty calibration, and distributional coverage. We show that these metrics predict
        downstream RLHF performance (R^2 = 0.83) across 8 training runs. We also demonstrate
        that filtering 20% of low-quality pairs using our metrics yields models equivalent to
        training on 2x the unfiltered data.
    """,
    "iterative_dpo_curriculum.pdf": """
        Iterative DPO generates new preference pairs from the current policy at each round.
        We show that the ordering of these pairs matters: presenting easier pairs first
        (curriculum learning) yields consistent improvements on GSM8K (+4.2%), MATH (+3.8%),
        and HumanEval (+2.1%) compared to random ordering. We define difficulty using the
        policy's own confidence scores and show this is more effective than external difficulty
        estimates. Our method adds zero computational overhead to standard iterative DPO.
    """,
    "sparse_reward_models.pdf": """
        Reward model inference is a bottleneck in online RLHF pipelines. We propose SparseRM,
        a mixture-of-experts reward model that activates only 2 of 8 expert heads per input.
        SparseRM reduces inference cost by 3.1x while retaining 98.5% of the dense model's
        accuracy on RewardBench. We also show that the expert specialization is interpretable:
        different experts activate for different quality dimensions (helpfulness, safety,
        coherence). Training uses a standard load-balancing loss.
    """,
    "llm_judge_consistency.pdf": """
        LLM-as-judge is increasingly used for evaluation, but its reliability is poorly
        understood. We measure inter-rater reliability of GPT-4, Claude, and LLaMA-3-70B
        as judges against 500 human expert annotations across six dimensions: helpfulness,
        harmlessness, honesty, reasoning, creativity, and instruction-following. We find
        strong agreement on helpfulness (Cohen's kappa = 0.78) but poor agreement on
        creativity (kappa = 0.31). Position bias accounts for 12% of judgment variance.
    """,
    "multimodal_preference_learning.pdf": """
        We extend Direct Preference Optimization to vision-language models (VLMs). Given paired
        preferences over image-caption outputs, our method VL-DPO trains the VLM to prefer
        higher-quality descriptions. We collect 50K preference pairs over LLaVA outputs and
        show that VL-DPO improves visual grounding accuracy by 8% on RefCOCO. The method
        requires no reward model and works with any VLM architecture.
    """,
    "efficient_ppo_tricks.pdf": """
        PPO for RLHF is notoriously unstable. We document a collection of practical tricks
        gathered from training 20+ models: adaptive KL penalty scheduling, batched generalized
        advantage estimation, reference model EMA updates, and gradient accumulation strategies
        for large batch RLHF. Each trick is ablated independently. Combined, they reduce
        training instability (measured by reward variance) by 60% and improve final reward
        by 8% on Anthropic-HH. Code is available.
    """,
    "constitutional_ai_extensions.pdf": """
        Constitutional AI (CAI) uses a set of principles to guide model behavior during RLHF.
        We propose domain-specific constitutions for medical AI (MedConst) and legal AI
        (LegalConst). Each constitution encodes domain-specific safety requirements and
        professional standards. Models trained with domain constitutions show 40% fewer
        safety violations on domain-specific red-team evaluations while maintaining general
        helpfulness. We release both constitutions and evaluation suites.
    """,
    "transformer_quantization_survey.pdf": """
        Post-training quantization (PTQ) enables efficient deployment of transformer models.
        We survey 35 recent PTQ methods across three categories: weight-only, weight-activation,
        and KV-cache quantization. We benchmark all methods on LLaMA-2 and Mistral at 4-bit,
        3-bit, and 2-bit precision. GPTQ and AWQ remain strong baselines, but recent methods
        like QuIP# show advantages at extreme compression. We discuss open challenges including
        quantization-aware fine-tuning and hardware-specific kernels.
    """,
    "diffusion_model_controlnet.pdf": """
        We propose three new conditioning mechanisms for ControlNet: frequency-band control
        (allowing separate control over low and high frequency details), temporal control
        (for video generation with frame-level spatial guidance), and compositional control
        (combining multiple ControlNet branches without interference). Experiments on COCO
        and custom datasets show 15-25% improvement in spatial accuracy metrics.
    """,
    "graph_neural_network_molecules.pdf": """
        Molecular property prediction using GNNs is limited by dataset scale. We introduce
        MolScale, a framework that trains GNNs on 10M+ compounds using distributed message
        passing and hierarchical graph batching. On the OGB-LSC challenge, MolScale achieves
        state-of-the-art MAE on PCQM4Mv2. We also release a pre-trained molecular encoder
        that transfers to 12 downstream property prediction tasks.
    """,
    "federated_learning_heterogeneity.pdf": """
        Data heterogeneity is a fundamental challenge in federated learning. We propose
        FedBalance, an aggregation strategy that weights client contributions by their
        local data distribution similarity to the global distribution. FedBalance outperforms
        FedAvg by 7% accuracy on non-IID partitions of CIFAR-100 and by 12% on pathological
        partitions. The method adds negligible communication overhead.
    """,
    "tokenizer_ablation_multilingual.pdf": """
        Tokenizer choice significantly impacts multilingual LLM performance but is rarely
        ablated systematically. We train 24 LLMs (350M parameters) with BPE, Unigram, and
        WordPiece tokenizers across vocab sizes from 32K to 256K on 50+ languages. Key findings:
        Unigram outperforms BPE for agglutinative languages by 8% on downstream tasks, larger
        vocabularies consistently help for CJK languages, and byte-fallback is critical for
        low-resource scripts. We release all tokenizers and evaluation data.
    """
}

for filename, abstract in paper_abstracts.items():
    doc = fitz.open()
    meta = gt["labels"].get(filename, {})
    title = meta.get("title", filename.replace(".pdf", "").replace("_", " ").title())

    page = doc.new_page()
    page.insert_text((72, 80), title, fontsize=16, fontname="helv")
    page.insert_text((72, 120), "Abstract", fontsize=12, fontname="helv")
    # manual text wrapping, fitz doesn't do this for us
    y = 145
    words = abstract.strip().split()
    line = ""
    for w in words:
        test = line + " " + w if line else w
        if len(test) > 85:
            page.insert_text((72, y), line, fontsize=10, fontname="helv")
            y += 14
            line = w
        else:
            line = test
    if line:
        page.insert_text((72, y), line, fontsize=10, fontname="helv")

    doc.save(f"/papers/inbox/{filename}")
    doc.close()

print(f"created {len(paper_abstracts)} papers in /papers/inbox/")
PYEOF

echo "environment ready"
