"""
Install the Google AI Python SDK

$ pip install google-generativeai
"""

import os
import time
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
genai.configure(api_key=os.environ["GEMINI_API_KEY"])

def upload_to_gemini(path, mime_type=None):
  """Uploads the given file to Gemini.

  See https://ai.google.dev/gemini-api/docs/prompting_with_media
  """
  file = genai.upload_file(path, mime_type=mime_type)
  print(f"Uploaded file '{file.display_name}' as: {file.uri}")
  return file

def wait_for_files_active(files):
  """Waits for the given files to be active.

  Some files uploaded to the Gemini API need to be processed before they can be
  used as prompt inputs. The status can be seen by querying the file's "state"
  field.

  This implementation uses a simple blocking polling loop. Production code
  should probably employ a more sophisticated approach.
  """
  print("Waiting for file processing...")
  for name in (file.name for file in files):
    file = genai.get_file(name)
    while file.state.name == "PROCESSING":
      print(".", end="", flush=True)
      time.sleep(10)
      file = genai.get_file(name)
    if file.state.name != "ACTIVE":
      raise Exception(f"File {file.name} failed to process")
  print("...all files ready")
  print()

# Create the model
generation_config = {
  "temperature": 0.1,
  "top_p": 0.95,
  "top_k": 64,
  "max_output_tokens": 100000,
  "response_mime_type": "text/plain",
}

model = genai.GenerativeModel(
  model_name="gemini-1.5-pro-exp-0827",
  generation_config=generation_config,
  # safety_settings = Adjust safety settings
  # See https://ai.google.dev/gemini-api/docs/safety-settings
  system_instruction="You’re a highly skilled cybersecurity analyst with a deep understanding of unstructured data analysis and natural language processing. You have been working in the field for over 15 years, specializing in interpreting and synthesizing complex cybersecurity audit reports into clear, actionable insights. Your expertise allows you to facilitate effective communication on cybersecurity issues through intuitive, chat-based interaction.\n\nYour task is to analyze unstructured cybersecurity audit reports attached and provide chat-based responses to decision-related questions. Here are the details you need to keep in mind:  \n- Unstructured audit report content\n- Specific questions or decision points to address\n- Key metrics or insights to highlight\n- Audience for the chat-based output\n\nRemember, your goal is to leverage machine learning algorithms and NLP capabilities to not only interpret the reports but also to summarize findings and present actionable insights that streamline the decision-making process efficiently.",
  tools='code_execution',
)

# TODO Make these files available on the local file system
# You may need to update the file paths
files = [
  upload_to_gemini("/Users/ssircar/Documents/Cybersecurity Audit AI/report.pdf", mime_type="application/pdf"),
]

# Some files have a processing delay. Wait for them to be ready.
wait_for_files_active(files)

chat_session = model.start_chat(
  history=[
    {
      "role": "user",
      "parts": [
        files[0],
        "Summarize the priority 2 issues and grade them by severity and order by which should be fixed first.",
      ],
    },
    {
      "role": "model",
      "parts": [
        "Here's a summary of the Priority 2 issues from the Croydon Cyber Security Audit Report, graded by severity and ordered by priority for fixing:\n\n**Issue 1: Insufficient Resources Dedicated to Cyber Security**\n\n* **Description:** The Council has only one dedicated member of staff for cyber security, compared to peers who have 3-4.\n* **Severity:** High. This significantly limits the Council's ability to proactively manage cyber risks and increases the likelihood of successful attacks.\n* **Rationale:**  Limited resources lead to a reactive, \"best endeavors\" approach, rather than a proactive and robust security posture.\n* **Fix Priority:**  **Highest**. Addressing the resource deficit is fundamental to improving the overall security posture.\n\n**Issue 2:  Inadequate Cyber Security Awareness Training and Communication**\n\n* **Description:** Cyber security awareness reminders are unstructured, infrequent, and not part of a formal training program.\n* **Severity:**  Medium.  Lack of awareness increases the risk of employees falling victim to phishing and other social engineering attacks.\n* **Rationale:**  Employees are often the \"weak link\" in an organization's security. Regular, structured training is crucial to build a strong security culture.\n* **Fix Priority:** **High**. Implementing a formal training program and regular, targeted communication will significantly reduce human error as a risk factor.\n\n**Issue 3: Lack of \"Phishing\" Exercises**\n\n* **Description:** The Council does not conduct regular simulated phishing exercises to test employee awareness and resilience.\n* **Severity:** Medium.  Without testing, the effectiveness of awareness training and the Council's overall vulnerability to phishing attacks is unknown.\n* **Rationale:** Phishing is a highly common and successful attack vector. Regular simulations are essential to identify weaknesses and improve employee responses.\n* **Fix Priority:** **Medium**. While important, implementing phishing exercises can be done after establishing a baseline level of awareness through training.\n\n**Issue 4: Reliance on Capita for Cyber Security Management and Lack of Control Visibility**\n\n* **Description:** The Council relies heavily on Capita, a third-party IT provider, for cyber security but lacks visibility into some of Capita's controls.\n* **Severity:** Medium.  This creates a dependency and potential blind spot in the Council's security posture.\n* **Rationale:**  While using third-party providers is common, maintaining oversight and ensuring adequate controls are in place is crucial.\n* **Fix Priority:** **Medium**.  Working with Capita to improve control visibility and potentially incorporating audit rights into contracts is important for risk management.\n\n**Issue 5: Infrequent Reviews of Privileged/Administrator Accounts**\n\n* **Description:** Reviews of privileged accounts are not formally scheduled or conducted regularly enough.\n* **Severity:** Medium.  Infrequent reviews increase the risk of unauthorized access and misuse of powerful accounts.\n* **Rationale:** Privileged accounts are high-value targets for attackers. Regular reviews are essential to ensure only authorized users have access and that dormant accounts are disabled.\n* **Fix Priority:** **Medium**. Implementing a formal schedule and process for reviewing privileged accounts will reduce the risk of insider threats and account compromise.\n\n**Issue 6:  Lack of Timeframe for Disabling/Removing Unnecessary Firewall Rules**\n\n* **Description:** No policy or documentation defines a timeframe for disabling or removing firewall rules that are no longer needed.\n* **Severity:** Low.  While not an immediate threat, outdated firewall rules can create unnecessary complexity and potential security gaps.\n* **Rationale:**  Regularly reviewing and removing unnecessary rules improves firewall performance and reduces the attack surface.\n* **Fix Priority:** **Lowest**.  Establishing a process and timeframe for firewall rule review is a good practice but can be addressed after higher-priority issues. \n",
      ],
    },
  ]
)

response = chat_session.send_message("Summarize the issues in the Audit Report of Fort Worth and grade them by severity and order by which should be fixed first.")

print(response.text)