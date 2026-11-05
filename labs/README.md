# Labs

Seven hands-on labs that build, break, and verify Atlas. Each has a
README with objectives, steps, the complete code (`lab.py`), the
commands, the expected output from a recorded run, verification,
common errors, a production checklist, and challenges.

| Lab | Topic | Chapters | Time | Needs |
|---|---|---|---|---|
| [1](lab01-rag/) | Build a production RAG application | 13–18 | 45–60 min | Python |
| [2](lab02-model-gateway/) | Build a model gateway | 9, 24, 46 | 30–45 min | Python |
| [3](lab03-evaluation/) | Build an AI evaluation pipeline | 33–38 | 45 min | Python |
| [4](lab04-agent-security/) | Secure an AI agent | 19, 26–29, 39–43 | 45–60 min | Python; Docker optional |
| [5](lab05-deployment/) | Deploy an AI application | 44, 47, 48 | 30 min | Docker |
| [6](lab06-observability/) | Implement AI observability | 32, 37, 45, 46 | 30–45 min | Python |
| [7](lab07-production-readiness/) | Production readiness review | 44–47, 51, 53 | 20 min | Python |

Run any lab from the repository root:

```bash
python labs/lab01-rag/lab.py
```

`make labs` runs the six offline labs in order. No lab calls a paid
API; every model call goes to the deterministic mock provider.
