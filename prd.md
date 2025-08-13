Product Requirements Document: podcast\_module.py
Project Name: opportunityknocks.ai - Wizard's Toolkit

Component: podcast\_module.py

Version: 1.0

Date: August 10, 2025

Author: Lead Architect

## 1\. Overview \& Goals

1.1. Problem Statement
Aspiring entrepreneurs need a reliable source of high-quality, long-form content to analyze for new business ideas.

1.2. Proposed Solution
An internal Python module that integrates with the Taddy Podcast API to search for relevant podcast episodes, retrieve their full transcripts, and synthesize the content into actionable opportunities. This module will serve as the new, primary data source for the "Opportunity Brief," replacing the deprecated YouTube module.

1.3. Strategic Goals
De-risk the MVP: Replace an unreliable data source (YouTube scraping) with a stable, legitimate API to ensure consistent product delivery.

Enable Manual Fulfillment: Equip the "Wizard" with a functional tool to generate the podcast-based section of the Opportunity Brief.

Maintain Consistency: Ensure the output of this module matches the established enriched JSON format for seamless integration into the Wizard's workflow.

## 2\. Scope

2.1. In Scope for MVP ✅
A Python module (podcast\_module.py) that integrates with the main CLI script.

Integration with the Taddy Podcast API for searching episodes and retrieving transcripts.

An LLM integration for synthesizing the transcript content.

Output of enriched, structured JSON data, including source metadata, to a local file.

2.2. Out of Scope for MVP ❌
Integration with any other podcast API.

Processing of podcast audio files.

A user-facing UI for interacting with the module.

## 3\. User Persona \& Use Case

Persona: "The Wizard" (the Founder, Jim).

Key Use Case:

The Wizard runs the toolkit with a specific topic and the --source podcast flag.

The script calls the podcast\_module, which interacts with the Taddy API to fetch and analyze relevant episodes.

The script generates an enriched JSON output file (e.g., \[topic]\_podcast.json).

The Wizard uses this file to craft the podcast-based evidence for the final Opportunity Brief.

## 4\. Functional Requirements

FR-1: API Integration \& Configuration
1.1. The module must securely load the TADDY\_API\_KEY and TADDY\_USER\_ID from the .env file.
1.2. All API calls to Taddy must include the required authentication headers as per their documentation.

FR-2: Episode Search \& Transcript Retrieval
2.1. The module must have a function to search for podcast episodes by topic using the Taddy API's searchForTerm endpoint.
2.2. The module must have a function to retrieve an episode's transcript. This function must:

* First, check if a transcript is immediately available.
* If not, call the getEpisodeTranscriptOnDemand endpoint to request AI generation.
* Poll the transcript status endpoint until the status is COMPLETED.
* Return the full, completed transcript text.

FR-3: Main Module Function
3.1. A main async function (e.g., fetch\_and\_analyze\_podcasts) must orchestrate the entire process.
3.2. This function must first search for the Top N (configurable) episodes.
3.3. It must then asynchronously retrieve the transcript for each of those episodes.
3.4. It must perform the two-step synthesis (summarize, then synthesize) and parsing logic to generate opportunities linked to their source evidence.
3.5. It must save its output as a structured JSON file that precisely matches the established enriched data structure (see below).

FR-4: Output Data Structure
The JSON output must follow our standard enriched structure:

JSON

{
"search\_topic": "AI for solopreneurs",
"synthesized\_opportunities": \[
{
"idea": "A synthesized business idea from a podcast...",
"description": "...",
"supporting\_evidence\_indices": \[0]
}
],
"source\_evidence": \[
{
"index": 0,
"source\_type": "Podcast",
"title": "Episode Title",
"author": "Podcast Show Name",
"url": "URL to the episode page.",
"key\_quote": "A key quote from the transcript..."
}
]
}

## 5\. Non-Functional Requirements

NFR-1 (Configurability): Key parameters like TOP\_N\_PODCAST\_EPISODES must be in the config.py file.

NFR-2 (API Rate Limiting): The module must be mindful of the Taddy API's rate limits for our tier. Implement a small asyncio.sleep() between requests in loops if needed.

NFR-3 (Error Handling): The module must gracefully handle common API errors from Taddy (e.g., 401, 404, 429) and transcript generation timeouts.

## 6\. Data Flow

CLI Command -> Podcast Module -> Taddy API (Search \& Transcribe) -> LLM API -> Enriched JSON -> Wizard

## 7\. Success Criteria \& Timeline

Success Criteria: The Wizard can run python -m ok\_mvp.main --topic "..." --source podcast and receive a correctly formatted, enriched JSON file.

Timeline: This module should be implemented in a 2-Day Development Sprint.

