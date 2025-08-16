# ok_mvp/run_toolkit_research.py
import json
import os
import argparse
import asyncio
from openai import OpenAI
from dotenv import load_dotenv

from ok_mvp import podcast_module
from ok_mvp import arxiv_module
from ok_mvp import youtube_module
# from ok_mvp import cache_utils # Caching is handled within each module

def load_config():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    dotenv_path = os.path.join(project_root, '.env')
    load_dotenv(dotenv_path=dotenv_path)
    config = {
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
        "TADDY_API_KEY": os.getenv("TADDY_API_KEY"),
        "MAX_RESULTS_PER_SOURCE": 3
    }
    if not all([config["OPENAI_API_KEY"], config["TADDY_API_KEY"]]):
        raise ValueError("API keys for Taddy and OpenAI must be set in the .env file")
    return config

def synthesize_content(client, content_blobs, hypothesis, search_terms):
    print("  Synthesizing content with OpenAI...")
    full_text = "\n\n---\n\n".join(content_blobs)
    prompt = f"""
# ROLE
You are a research analyst. Your task is to analyze a collection of raw text from podcasts and academic papers and synthesize the key business opportunities relevant to a specific hypothesis.

# CONTEXT
The user is exploring the following business hypothesis: "{hypothesis['hypothesis_description']}"
You have been provided with raw text from several sources related to this topic.

# INSTRUCTIONS
1. Read through all the provided raw text.
2. Identify 3-5 distinct business ideas, market needs, or strategic insights that are directly relevant to the user's hypothesis.
3. For each idea, write a concise `idea` title and a `description`.
4. The output must be a JSON object containing a single key "synthesized_opportunities" which is an array of objects. Do not include any text outside the JSON object.

# RAW TEXT
---
{full_text[:12000]}
---
"""
    response = client.chat.completions.create(
        model="gpt-5-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    return json.loads(response.choices[0].message.content)

async def run_research_for_hypothesis(submission_id, hypothesis_num, config, sources_to_run):
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    submission_dir = os.path.join(project_root, 'output', submission_id)
    search_terms_path = os.path.join(submission_dir, f'hypothesis_{hypothesis_num}_search_terms.json')
    results_path = os.path.join(submission_dir, f'hypothesis_{hypothesis_num}_research_results.json')
    print(f"\n--- Processing Hypothesis {hypothesis_num} for Submission ID: {submission_id} ---")
    
    with open(search_terms_path, 'r') as f:
        search_terms = json.load(f).get('search_terms', [])
    
    hypotheses_path = os.path.join(submission_dir, 'hypotheses.json')
    with open(hypotheses_path, 'r') as f:
        current_hypothesis = json.load(f)[hypothesis_num - 1]

    all_source_evidence, all_content_for_synthesis = [], []

    if 'podcast' in sources_to_run:
        podcast_sources, podcast_content = await podcast_module.research(search_terms, config)
        all_source_evidence.extend(podcast_sources)
        all_content_for_synthesis.extend(podcast_content)
    if 'arxiv' in sources_to_run:
        arxiv_sources, arxiv_content = await arxiv_module.research(search_terms, config)
        all_source_evidence.extend(arxiv_sources)
        all_content_for_synthesis.extend(arxiv_content)
    if 'youtube' in sources_to_run:
        youtube_sources, youtube_content = await youtube_module.research(search_terms, config)
        all_source_evidence.extend(youtube_sources)
        all_content_for_synthesis.extend(youtube_content)

    print(f"  Aggregated {len(all_source_evidence)} sources for synthesis.")
    
    for i, source in enumerate(all_source_evidence):
        source['index'] = i
    
    if all_content_for_synthesis:
        openai_client = OpenAI(api_key=config["OPENAI_API_KEY"])
        synthesis_result = synthesize_content(openai_client, all_content_for_synthesis, current_hypothesis, search_terms)
        final_output = {**synthesis_result, "source_evidence": all_source_evidence}
    else:
        final_output = {"search_topic": search_terms[0] if search_terms else "N/A", "synthesized_opportunities": [], "source_evidence": all_source_evidence}

    with open(results_path, 'w') as f:
        json.dump(final_output, f, indent=2)
    print(f"Successfully saved final research results to: {results_path}")
    print(f"--- Finished Hypothesis {hypothesis_num} ---")

async def main():
    parser = argparse.ArgumentParser(description="Run the research toolkit for a given submission.")
    parser.add_argument("submission_id", help="The submission ID to process.")
    parser.add_argument("--sources", nargs='+', default=['podcast', 'arxiv', 'youtube'], 
                        choices=['podcast', 'arxiv', 'youtube'], 
                        help="Specify which sources to run. Default is all.")
    args = parser.parse_args()
    
    try:
        configuration = load_config()
        tasks = [run_research_for_hypothesis(args.submission_id, i, configuration, args.sources) for i in range(1, 4)]
        await asyncio.gather(*tasks)
    except ValueError as e:
        print(f"Configuration Error: {e}")

if __name__ == '__main__':
    asyncio.run(main())