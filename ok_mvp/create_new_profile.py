# ok_mvp/create_new_profile.py
"""
Finds a specific submission in a Tally.so CSV export from the 'input' folder,
transforms it to JSON, and saves it in a new directory inside the 'output' folder.
"""
import pandas as pd
import json
import os

def process_submission(submission_id_to_find, csv_file_name):
    """
    Finds a specific submission in a Tally.so CSV export from the 'input' folder,
    transforms it to JSON, and saves it in a new directory inside the 'output' folder.
    """
    try:
        # Get the directory where the script is located
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # Get the project root directory (one level up)
        project_root = os.path.dirname(script_dir)

        # Construct the full path to the input CSV file
        csv_file_path = os.path.join(project_root, 'input', csv_file_name)

        # Read the CSV file
        df = pd.read_csv(csv_file_path)

        # Find the row with the matching Submission ID
        target_row = df[df['Submission ID'] == submission_id_to_find]

        if not target_row.empty:
            profile_series = target_row.iloc[0]

            # Define the exact column names from the CSV
            col_map = {
                'first_name': 'Enter first name',
                'last_name': 'Last Name',
                'catalyst': "Think about what's happening in your life, career, or the world right now. Why is this the moment you've chosen to build something new?\n",
                'mission': "If your business succeeds beyond your wildest dreams, what positive change will exist in the world because of it? This is the core impact you want to make.\n",
                'purple_cow_insight': "e.g., 'The onboarding process for new software is always so generic and boring,' or 'Local service businesses are terrible at online marketing.",
                'unfair_advantage': "What is the unique knowledge or skill you've gained from your specific life and career path? This could be a technical skill, a deep industry network, or a lesson learned from a past failure.\n\n",
                'tribe': "Describe the specific group of people you want to help. Think about their jobs, their challenges, and their goals. The more specific you are, the better. Consider if there's an underserved community whose needs are being ignored.\n\n"
            }

            # Create the JSON object
            founder_profile = {
                "name": f"{profile_series[col_map['first_name']]} {profile_series[col_map['last_name']]}",
                "catalyst": profile_series[col_map['catalyst']],
                "mission": profile_series[col_map['mission']],
                "purple_cow_insight": profile_series[col_map['purple_cow_insight']],
                "unfair_advantage": profile_series[col_map['unfair_advantage']],
                "tribe": profile_series[col_map['tribe']]
            }

            # Construct the output directory path within the project's 'output' folder
            output_dir = os.path.join(project_root, 'output', submission_id_to_find)
            os.makedirs(output_dir, exist_ok=True)

            # Define the output file path
            output_file_path = os.path.join(output_dir, 'founder_profile.json')

            # Save the JSON data to the file
            with open(output_file_path, 'w') as json_file:
                json.dump(founder_profile, json_file, indent=2)

            print(f"Successfully created directory: '{output_dir}'")
            print(f"Successfully saved founder profile to: '{output_file_path}'")
            print("\n--- File Content ---")
            print(json.dumps(founder_profile, indent=2))

        else:
            print(f"Error: Submission ID '{submission_id_to_find}' not found in the CSV file.")

    except FileNotFoundError:
        print(f"Error: The file '{csv_file_path}' was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == '__main__':
    # Define the target Submission ID and the name of the input file
    submission_id = 'ODBbJqp'
    csv_filename = 'Founder_s_Discovery_Engine_Submissions_2025-08-13.csv'
    process_submission(submission_id, csv_filename)