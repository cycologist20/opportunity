# setup2.ps1
# Safe, no-here-strings file populater + deps installer for ok-mvp

param(
  [string]$ProjectRoot = (Get-Location).Path
)

function Ensure-Folder {
  param([string]$Path)
  if (-not (Test-Path -LiteralPath $Path)) {
    New-Item -Path $Path -ItemType Directory -Force | Out-Null
  }
}

function Write-Lines {
  param([string]$Path, [string[]]$Lines)
  Ensure-Folder ([System.IO.Path]::GetDirectoryName($Path))
  [System.IO.File]::WriteAllLines($Path, $Lines)
  Write-Host "Wrote: $Path"
}

# Ensure folders
Ensure-Folder $ProjectRoot
Ensure-Folder "$ProjectRoot\ok_mvp"
Ensure-Folder "$ProjectRoot\output"

# README.md
Write-Lines "$ProjectRoot\README.md" @(
  '# OpportunityKnocks.ai - Wizards Toolkit (MVP)',
  '',
  'Internal CLI to generate structured Opportunity Brief research from YouTube and arXiv.',
  '',
  'Requirements:',
  '- Python 3.11+',
  '- Poetry (see https://python-poetry.org/docs/#installation)',
  '',
  'Setup:',
  '1) poetry install',
  '2) Copy .env.example to .env and add your API keys',
  '',
  'Run:',
  'poetry run python ok_mvp/main.py --topic "AI in preventative healthcare"',
  'poetry run python ok_mvp/main.py --topic "wearable tech for seniors" --source youtube',
  '',
  'Outputs:',
  '- output/<topic>_youtube.json',
  '- output/<topic>_arxiv.json'
)

# .env.example
Write-Lines "$ProjectRoot\.env.example" @(
  '# API Keys',
  'OPENAI_API_KEY=your_api_key_here'
)

# .gitignore
Write-Lines "$ProjectRoot\.gitignore" @(
  '__pycache__/',
  '*.pyc',
  '.venv/',
  '.env',
  'output/',
  'poetry.lock'
)

# ok_mvp/__init__.py
Write-Lines "$ProjectRoot\ok_mvp\__init__.py" @(
  '"""Wizards Toolkit MVP package initialization."""'
)

# ok_mvp/logger.py
Write-Lines "$ProjectRoot\ok_mvp\logger.py" @(
  'import logging',
  '',
  'def get_logger():',
  '    logger = logging.getLogger("wizard_toolkit")',
  '    if not logger.handlers:',
  '        handler = logging.StreamHandler()',
  '        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")',
  '        handler.setFormatter(formatter)',
  '        logger.addHandler(handler)',
  '        logger.setLevel(logging.INFO)',
  '    return logger'
)

# ok_mvp/config.py
Write-Lines "$ProjectRoot\ok_mvp\config.py" @(
  '# Central configuration',
  'TOP_N_YOUTUBE_VIDEOS = 10',
  'TOP_N_ARXIV_PAPERS = 5',
  'LLM_MODEL = "gpt-4-turbo"'
)

# ok_mvp/llm_utils.py
Write-Lines "$ProjectRoot\ok_mvp\llm_utils.py" @(
  'from .logger import get_logger',
  '',
  'logger = get_logger()',
  '',
  'def synthesize_with_llm(text_chunks, model):',
  '    """Placeholder synthesis; implement OpenAI calls and chunking here."""',
  '    logger.info(f"Synthesizing {len(text_chunks)} chunks with model {model}")',
  '    return "Placeholder synthesis result"'
)

# ok_mvp/youtube_module.py
Write-Lines "$ProjectRoot\ok_mvp\youtube_module.py" @(
  'import json',
  'from pathlib import Path',
  'from .logger import get_logger',
  'from .config import TOP_N_YOUTUBE_VIDEOS, LLM_MODEL',
  'from .llm_utils import synthesize_with_llm',
  '',
  'logger = get_logger()',
  '',
  'def fetch_and_analyze_youtube(topic: str):',
  '    logger.info(f"[YouTube] Topic: {topic} | TopN={TOP_N_YOUTUBE_VIDEOS} | Model={LLM_MODEL}")',
  '    # TODO: search videos, fetch transcripts, chunk + synthesize',
  '    output_path = Path("output") / f"{topic.replace('' '', ''_'')}_youtube.json"',
  '    with open(output_path, "w", encoding="utf-8") as f:',
  '        json.dump(',
  '            {',
  '                "topic": topic,',
  '                "source": "youtube",',
  '                "top_n": TOP_N_YOUTUBE_VIDEOS,',
  '                "model": LLM_MODEL,',
  '                "data": [],',
  '                "summary": synthesize_with_llm([], LLM_MODEL),',
  '            },',
  '            f,',
  '            indent=2,',
  '        )',
  '    logger.info(f"[YouTube] Wrote {output_path}")'
)

# ok_mvp/arxiv_module.py
Write-Lines "$ProjectRoot\ok_mvp\arxiv_module.py" @(
  'import json',
  'from pathlib import Path',
  'from .logger import get_logger',
  'from .config import TOP_N_ARXIV_PAPERS, LLM_MODEL',
  'from .llm_utils import synthesize_with_llm',
  '',
  'logger = get_logger()',
  '',
  'def fetch_and_analyze_arxiv(topic: str):',
  '    logger.info(f"[arXiv] Topic: {topic} | TopN={TOP_N_ARXIV_PAPERS} | Model={LLM_MODEL}")',
  '    # TODO: search arXiv, download PDFs, extract text, per-paper summaries, final synthesis',
  '    output_path = Path("output") / f"{topic.replace('' '', ''_'')}_arxiv.json"',
  '    with open(output_path, "w", encoding="utf-8") as f:',
  '        json.dump(',
  '            {',
  '                "topic": topic,',
  '                "source": "arxiv",',
  '                "top_n": TOP_N_ARXIV_PAPERS,',
  '                "model": LLM_MODEL,',
  '                "papers": [],',
  '                "synthesis": synthesize_with_llm([], LLM_MODEL),',
  '            },',
  '            f,',
  '            indent=2,',
  '        )',
  '    logger.info(f"[arXiv] Wrote {output_path}")'
)

# ok_mvp/main.py
Write-Lines "$ProjectRoot\ok_mvp\main.py" @(
  'import argparse',
  'from . import youtube_module, arxiv_module',
  'from .logger import get_logger',
  '',
  'logger = get_logger()',
  '',
  'def main():',
  '    parser = argparse.ArgumentParser(description="Wizards Toolkit - Opportunity Brief Generator")',
  '    parser.add_argument("--topic", required=True, help="Research topic")',
  '    parser.add_argument(',
  '        "--source",',
  '        choices=["youtube", "arxiv", "both"],',
  '        default="both",',
  '        help="Data source to use",',
  '    )',
  '    args = parser.parse_args()',
  '',
  '    logger.info(f"Starting research for topic: {args.topic}")',
  '',
  '    if args.source in ("youtube", "both"):',
  '        youtube_module.fetch_and_analyze_youtube(args.topic)',
  '',
  '    if args.source in ("arxiv", "both"):',
  '        arxiv_module.fetch_and_analyze_arxiv(args.topic)',
  '',
  'if __name__ == "__main__":',
  '    main()'
)

# Dependencies via Poetry (optional but per PRD)
Push-Location $ProjectRoot
if (Get-Command poetry -ErrorAction SilentlyContinue) {
  if (-not (Test-Path "$ProjectRoot\pyproject.toml")) {
    poetry init -n --name "ok-mvp" --description "Wizards Toolkit MVP (CLI)" --license "MIT" --readme "README.md" | Out-Null
  }
  poetry add youtube-transcript-api arxiv pypdf openai python-dotenv argparse | Out-Null
  poetry add --dev black ruff | Out-Null
  poetry export -f requirements.txt -o requirements.txt --without-hashes | Out-Null
  Write-Host 'Dependencies installed and requirements.txt exported.'
} else {
  Write-Warning 'Poetry not found; skipping dependency install.'
}
Pop-Location

Write-Host 'setup2 complete.'
