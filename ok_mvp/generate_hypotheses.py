"""
Loads a founder_profile.json for a specific submission, sends it to an LLM
with a structured prompt to generate three opportunity hypotheses, and saves
the result as hypotheses.json in the same submission folder.
"""
import json
import os
from openai import OpenAI
from dotenv import load_dotenv

def get_prompt_text(founder_profile_content):
    """Constructs the full prompt with embedded founder profile data."""
    
    # This is the detailed prompt we designed earlier.
    prompt = f"""
# ROLE
You are an expert business strategist and startup incubator analyst. Your specialty is identifying high-potential, niche business opportunities based on a founder's unique profile and "earned secrets." You excel at translating personal insights and frustrations into concrete, viable business concepts.

# TASK
Analyze the following founder profile and generate three distinct, specific, and viable 'Opportunity Hypotheses.' These hypotheses will be used to guide deep research into market trends, existing solutions, and technical feasibility.

# CONTEXT
The founder profile data is gathered from a multi-step intake form designed to uncover the founder's core motivations and unique perspective.

# INSTRUCTIONS
1. Carefully analyze the provided `## FOUNDER PROFILE DATA`.
2. Generate three **distinct** hypotheses. Consider different business models for each (e.g., a niche SaaS tool, a tech-enabled service, a data product).
3. For each hypothesis, use the following framework as a guide:
    > "For **[Tribe]**, who are frustrated by **[Purple Cow Insight]**, we can build a **[Product/Service]** that uses **[Unfair Advantage/Technology]** to deliver **[Key Delight/Value Prop]**."
4. Return ONLY a valid JSON array with exactly 3 objects. No explanatory text, no markdown formatting, no additional content.

# FOUNDER PROFILE DATA
{json.dumps(founder_profile_content, indent=2)}

You must respond with a JSON array containing exactly 3 hypothesis objects. Each object must have these exact fields:
- hypothesis_name (string)
- hypothesis_description (string) 
- business_model (string)
- target_customer (string)
"""
    return prompt

def generate_hypotheses(submission_id):
    """
    Main function to generate hypotheses for a given submission ID.
    """
    try:
        # --- 1. Define Paths ---
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        submission_dir = os.path.join(project_root, 'output', submission_id)
        profile_path = os.path.join(submission_dir, 'founder_profile.json')
        hypotheses_path = os.path.join(submission_dir, 'hypotheses.json')
        dotenv_path = os.path.join(project_root, '.env')

        # --- 2. Load Inputs ---
        print(f"Loading founder profile from: {profile_path}")
        with open(profile_path, 'r') as f:
            founder_profile = json.load(f)

        print(f"Loading API key from: {dotenv_path}")
        load_dotenv(dotenv_path=dotenv_path)
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in .env file")

        # --- 3. Call AI ---
        client = OpenAI(api_key=api_key)
        prompt = get_prompt_text(founder_profile)

        print("Sending request to OpenAI API...")
        response = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[
                {"role": "system", "content": "You are an expert business strategist. Return only valid JSON arrays with no additional text."},
                {"role": "user", "content": prompt}
            ]
        )
        
        response_content = response.choices[0].message.content
        print("Received response from API.")
        print(f"Raw response content: {response_content[:500]}...")  # Debug output
        
        # --- 4. Save Output ---
        # The API is instructed to return a JSON object, so we parse the string.
        # Sometimes the response might include markdown ```json ... ``` tags, so we clean it.
        if "```json" in response_content:
            json_string = response_content.split("```json\n")[1].split("\n```")[0]
        else:
            json_string = response_content
            
        try:
            hypotheses_data = json.loads(json_string)
            # Ensure it's a list of hypotheses
            if not isinstance(hypotheses_data, list):
                raise ValueError("Response should be a JSON array")
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            print(f"Attempted to parse: {json_string}")
            raise

        print(f"Saving hypotheses to: {hypotheses_path}")
        with open(hypotheses_path, 'w') as f:
            json.dump(hypotheses_data, f, indent=2)
            
        print("Successfully generated and saved hypotheses.")
        print("\n--- File Content ---")
        print(json.dumps(hypotheses_data, indent=2))

    except FileNotFoundError as e:
        print(f"Error: Could not find a required file. {e}")
    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == '__main__':
    # Define the target Submission ID for this run
    submission_id_to_process = 'ODBbJqp'
    generate_hypotheses(submission_id_to_process)
