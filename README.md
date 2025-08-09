# OpportunityKnocks.ai - Wizards Toolkit (MVP)

Internal CLI to generate structured Opportunity Brief research from YouTube and arXiv.

Requirements:
- Python 3.11+
- Poetry (see https://python-poetry.org/docs/#installation)

Setup:
1) poetry install
2) Copy .env.example to .env and add your API keys

Run:
poetry run python ok_mvp/main.py --topic "AI in preventative healthcare"
poetry run python ok_mvp/main.py --topic "wearable tech for seniors" --source youtube

Outputs:
- output/<topic>_youtube.json
- output/<topic>_arxiv.json
