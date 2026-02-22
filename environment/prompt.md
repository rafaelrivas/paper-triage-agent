# Paper Triage Task

You are an AI/ML research engineer specializing in reinforcement learning from human feedback (RLHF) and preference-based training. You have a backlog of recently published papers dumped into `/papers/inbox/`.

## Your task

1. **Read every PDF** in `/papers/inbox/`.
2. **Classify each paper** by moving it into exactly one of these folders:
   - `/papers/must-read/` — Papers that introduce novel methods, significant improvements, or foundational ideas directly relevant to RLHF, reward modeling, preference optimization (DPO, KTO, etc.), or LLM alignment. The stuff that actually matters. New important paper that a RL AI Engineer should read.
   - `/papers/nice-to-read/` — Papers that are tangentially related, incremental improvements, or useful background but not critical for an RL engineer working on preference-based training. Maybe things related to technology of model deployments.
   - `/papers/bullshit/` — Papers that are off-topic, irrelevant to your work, or a waste of your time. nothing that helps you ship a better reward model.
3. **Create a reading order** file at `/papers/reading_order.txt`. This file must contain one line per must-read paper, ordered from highest to lowest priority. Each line must follow this exact format:
   ```
   <rank>. <filename> | <one-line justification>
   ```
   Example:
   ```
   1. dpo_convergence.pdf | Proves convergence guarantees for DPO that impact hyperparameter selection
   2. reward_hacking_survey.pdf | Comprehensive taxonomy of reward hacking failure modes
   ```
4. **Create a triage report** at `/papers/triage_report.json`. The JSON must be an array of objects, one per paper, each with these exact fields:
   ```json
   {
     "filename": "paper_name.pdf",
     "title": "Extracted paper title",
     "classification": "must-read" | "nice-to-read" | "bullshit",
     "domain_tags": ["rlhf", "reward-modeling", ...],
     "key_contribution": "One sentence describing the main contribution",
     "relevance_score": 0.0 to 1.0
   }
   ```

## Constraints

- You must classify ALL papers. Every PDF in `/papers/inbox/` must end up in exactly one output folder.
- No paper can appear in more than one folder.
- The `/papers/inbox/` folder should be empty when you are done.
- `reading_order.txt` must only contain must-read papers and must list ALL of them.
- `triage_report.json` must be valid JSON and contain an entry for every paper.

## Tools available

You have access to a command line. You can read files, write files, run Python scripts, and install packages.
