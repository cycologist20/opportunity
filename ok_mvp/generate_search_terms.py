"""
Loads the hypotheses.json file for a specific submission, loops through
each hypothesis, and calls an LLM to generate a list of search terms
for each one. Saves each list of terms to a separate JSON file.
"""
import json
import os
from openai import OpenAI
from dotenv import load_dotenv

def get_prompt_text(hypothesis_object):
    """Constructs the full prompt with an embedded hypothesis object."""
    
    # This is the detailed prompt we designed for search term derivation.
    prompt = f"""
# ROLE
You are an expert market researcher and data strategist. Your skill is deconstructing a business concept into a comprehensive set of search queries designed to uncover technical documentation, market analysis, and competitor intelligence.

# TASK
Analyze the following 'Opportunity Hypothesis' and generate a diverse list of search terms. These terms will be used to find relevant podcasts, academic papers, and articles to validate the business idea.

# CONTEXT
The search terms should cover multiple facets of the hypothesis to ensure a well-rounded research output. The goal is to gather information on the 'how' (technical), the 'why' (strategy), the 'who' (market), and the 'what else' (competitors).

# INSTRUCTIONS
1. Carefully analyze the provided `## OPPORTUNITY HYPOTHESIS`.
2. Generate a list of at least 10-15 distinct search terms.
3. Ensure the list includes a mix of the following categories:
    * Technical/Implementation Terms: Specific APIs, algorithms, or technologies needed to build the product.
    * Business/Strategy Terms: Business models, market segments, or strategic challenges related to the idea.
    * Market/Customer Terms: The target customer's pain points or relevant industry trends.
    * Competitor Terms: Queries designed to find existing players or alternative solutions.
4. Return ONLY a valid JSON object with a "search_terms" array. No explanatory text, no markdown formatting, no additional content.

# OPPORTUNITY HYPOTHESIS
{json.dumps(hypothesis_object, indent=2)}

You must respond with a JSON object containing a "search_terms" array with 10-15 search term strings.
"""
    return prompt

def generate_terms_for_hypotheses(submission_id):
    """
    Main function to generate search terms for all hypotheses of a given submission ID.
    """
    try:
        # --- 1. Define Paths ---
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        submission_dir = os.path.join(project_root, 'output', submission_id)
        hypotheses_path = os.path.join(submission_dir, 'hypotheses.json')
        dotenv_path = os.path.join(project_root, '.env')

        # --- 2. Load Inputs ---
        print(f"Loading hypotheses from: {hypotheses_path}")
        with open(hypotheses_path, 'r') as f:
            hypotheses = json.load(f)

        print(f"Loading API key from: {dotenv_path}")
        load_dotenv(dotenv_path=dotenv_path)
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in .env file")
        
        client = OpenAI(api_key=api_key)

        # --- 3. Loop Through Hypotheses and Call AI ---
        for i, hypothesis in enumerate(hypotheses):
            hypothesis_name = hypothesis.get("hypothesis_name", f"Hypothesis_{i+1}")
            print(f"\n--- Generating search terms for: '{hypothesis_name}' ---")
            
            prompt = get_prompt_text(hypothesis)

            print("Sending request to OpenAI API...")
            response = client.chat.completions.create(
                model="gpt-5-mini",
                messages=[
                    {"role": "system", "content": "You are an expert market researcher. Return only valid JSON objects with no additional text."},
                    {"role": "user", "content": prompt}
                ]
            )
            
            response_content = response.choices[0].message.content
            print("Received response from API.")
            print(f"Raw response content: {response_content[:200]}...")  # Debug output
            
            # --- 4. Save Output ---
            try:
                search_terms_data = json.loads(response_content)
                # Ensure it has the expected structure
                if not isinstance(search_terms_data.get("search_terms"), list):
                    raise ValueError("Response should contain a 'search_terms' array")
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}")
                print(f"Attempted to parse: {response_content}")
                raise
            
            # Sanitize hypothesis name for use in filename
            filename_safe_name = f"hypothesis_{i+1}_search_terms.json"
            output_path = os.path.join(submission_dir, filename_safe_name)

            print(f"Saving search terms to: {output_path}")
            with open(output_path, 'w') as f:
                json.dump(search_terms_data, f, indent=2)
            
            print(f"Successfully generated and saved {len(search_terms_data.get('search_terms', []))} search terms for Hypothesis {i+1}.")
            print(f"Generated {len(search_terms_data.get('search_terms', []))} search terms.")

    except FileNotFoundError as e:
        print(f"Error: Could not find a required file. {e}")
    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == '__main__':
    # Define the target Submission ID for this run
    submission_id_to_process = 'ODBbJqp'
    generate_terms_for_hypotheses(submission_id_to_process)
