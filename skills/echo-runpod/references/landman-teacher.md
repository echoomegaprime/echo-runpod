# Landman teacher example (isolation fixture)

Not a generic default. Do not hard-code this workload into generic RunPod logic.

| Field | Value |
|---|---|
| workload_id | landman-teacher-v4-exp1 |
| project | landman |
| dataset | E:\tmp\echo-landman-teacher-v4\forge_exp1_corpus_20260816T180000Z\experimental_corpus.jsonl |
| rows | 5800 (4000 teacher + 1800 title-math) |
| sha256 | 3f6b93e80818e670402e75463ec2a5898104af03f4b616e1b8b6dfd8e6766a81 |
| model | Qwen/Qwen2.5-32B-Instruct |
| GPU class | RTX 6000 Ada (live-confirm) |
| budget | $1.50/hr · $40 total · 8h |
| eval | frozen, never mixed into training |

Prometheus 27B work is a different project. Cross-use is rejected.

```text
python -m echo_runpod.operator landman-example
```
