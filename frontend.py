import chainlit as cl
import markdown
# from rich.console import Console
from rich.markdown import Markdown
from ai import *
import re

def sanitize_filename(filename):
    # Remove any character that isn't lowercase alphanumeric or dash
    sanitized = re.sub(r'[^a-z0-9-]', '', filename.lower())
    # Remove leading and trailing dashes
    sanitized = sanitized.strip('-')
    # Ensure the filename isn't empty after sanitization
    return sanitized if sanitized else 'report'


def get_markdown(text):
    # Convert markdown to HTML
    html = markdown.markdown(text)
    
    # Create a Markdown object
    md = Markdown(html)
    
    return md

chat_session = None

@cl.on_chat_start
async def start():
    files = await cl.AskFileMessage(
        content="Please upload a document to analyze",
        accept=["text/plain", "application/pdf"]
    ).send()
    if files:
        file = files[0]
        sanitized_name = sanitize_filename(file.name.split('.')[0])
        file.name = sanitized_name + '.pdf'
    wait_for_files_active(files)
    global chat_session
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


    

@cl.on_message
async def main(message: str):
    # Handle user messages
    global chat_session
    response = chat_session.send_message(message)
    await cl.Message(content=get_markdown(response)).send()
