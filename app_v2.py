import os
import json
import time
import logging
from dotenv import load_dotenv
import google.generativeai as genai
import chainlit as cl
from chainlit.logger import logger as l
from chainlit.types import ThreadDict
import asyncio
import uuid

chat_sessions = {}

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set Chainlit logger to ERROR level to suppress warnings
l.setLevel(logging.ERROR)

load_dotenv()
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
# flag = False


def convert_history_to_serializable(history):
    serializable_history = []
    for item in history:
        serializable_item = {
            'role': item['role'] if isinstance(item, dict) else item.role,
            'parts': []
        }
        parts = item['parts'] if isinstance(item, dict) else item.parts
        for part in parts:
            if isinstance(part, dict):
                serializable_item['parts'].append(part.get('text', str(part)))
            else:
                serializable_item['parts'].append(str(part))
        serializable_history.append(serializable_item)
    return serializable_history


def save_conversation_history(session_id, history):
    folder = 'chat_histories'
    if not os.path.exists(folder):
        os.makedirs(folder)  # Create folder if it doesn't exist
    file_path = os.path.join(folder, f'conversation_{session_id}.json')
    serializable_history = convert_history_to_serializable(history)
    with open(file_path, 'w') as file:
        json.dump(serializable_history, file)
    return file_path


def load_conversation_history(session_id):
    file_path = os.path.join(
        'chat_histories', f'conversation_{session_id}.json')
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            return json.load(file)
    return []


async def append_to_history(session_id, user_message, model_response):
    history = load_conversation_history(session_id)
    history.append({'role': 'user', 'parts': [user_message]})
    history.append({'role': 'model', 'parts': [model_response]})
    save_conversation_history(session_id, history)


async def initialize_chat(session_id):
    history = load_conversation_history(session_id)
    converted_history = []
    for item in history:
        converted_item = genai.types.ContentDict(
            role=item['role'],
            parts=[part if isinstance(part, str) else part['text']
                   for part in item['parts']]
        )
        converted_history.append(converted_item)
    return model.start_chat(history=converted_history)


def list_previous_chats():
    folder = 'chat_histories'
    if os.path.exists(folder):
        return [f.split('_')[1].split('.')[0] for f in os.listdir(folder) if f.endswith('.json')]
    return []


def upload_to_gemini(path, mime_type=None):
    try:
        file = genai.upload_file(path, mime_type=mime_type)
        logger.info(f"Uploaded file '{file.display_name}' as: {file.uri}")
        return file
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        raise


def wait_for_files_active(files):
    logger.info("Waiting for file processing...")
    for name in (file.name for file in files):
        file = genai.get_file(name)
        while file.state.name == "PROCESSING":
            logger.info(".", end="", flush=True)
            time.sleep(1)
            file = genai.get_file(name)
        if file.state.name != "ACTIVE":
            raise Exception(f"File {file.name} failed to process")
    logger.info("...all files ready")


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
    system_instruction='''
    You’re a highly skilled cybersecurity analyst with a deep understanding of unstructured data analysis and natural language processing. You have been working in the field for over 15 years, specializing in interpreting and synthesizing complex cybersecurity audit reports into clear, actionable insights. Your expertise allows you to facilitate effective communication on cybersecurity issues through intuitive, chat-based interaction.

    Your task is to analyze unstructured cybersecurity audit reports attached and provide chat-based responses to decision-related questions. Here are the details you need to keep in mind:  
    - Unstructured audit report content
    - Specific questions or decision points to address
    - Key metrics or insights to highlight
    - Audience for the chat-based output

    Remember, your goal is to leverage machine learning algorithms and NLP capabilities to not only interpret the reports but also to summarize findings and present actionable insights that streamline the decision-making process efficiently. Always remember to format the text in the type requested by the user like: Bulletted List, Table or Tabular, csv, json, etc.
    
    Take a deep breath and answer the query, thinking it through step-by-step.
    ''',
    tools='code_execution',
)


@cl.on_chat_start
async def start():
    session_id = str(uuid.uuid4())
    chat_session = await initialize_chat(session_id)
    chat_sessions[session_id] = chat_session
    logger.info(f"Chat started with session id as: {session_id}")

    cl.user_session.set("session_id", session_id)
    cl.user_session.set("chat_session", chat_session)

    # Load and display previous messages
    history = load_conversation_history(session_id)
    for item in history:
        if item['role'] == 'user':
            await cl.Message(content=item['parts'][0], author="Human").send()
        elif item['role'] == 'model':
            await cl.Message(content=item['parts'][0]).send()

    await cl.Message(content="Welcome! Please upload an audit report (pdf) to begin.").send()


@cl.on_message
async def main(message: cl.Message):
    session_id = cl.user_session.get("session_id")
    chat_session = chat_sessions.get(session_id)
    logger.info(f"Continuing conversation with session id: {session_id}")

    logger.info(f"Received message: {message.content}")

    try:
        if message.elements:
            files = []
            for element in message.elements:
                if isinstance(element, cl.File) and element.mime == "application/pdf":
                    files.append(upload_to_gemini(element.path, element.mime))

            if not files:
                await cl.Message(content="No valid PDF files were uploaded. Please upload a PDF file.").send()
                return

            wait_for_files_active(files)

            logger.info("Sending message to Gemini with uploaded file")
            response = chat_session.send_message([
                files[0],
                message.content  # "Summarize the priority issues in this audit report and grade them by severity and order by which should be fixed first.",
            ])
        else:
            if not chat_session:
                await cl.Message(content="Please upload a PDF file to analyze first.").send()
                return

            logger.info("Sending message to Gemini")
            response = chat_session.send_message(message.content)

        logger.info(f"Received response from Gemini: {response.text}")
        await cl.Message(content=response.text).send()

        # Save the conversation history
        await append_to_history(session_id, message.content, response.text)

    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        await cl.Message(content=f"An error occurred: {str(e)}").send()

    # Force an update to the UI
    await asyncio.sleep(0.1)


@cl.on_chat_end
def on_chat_end():
    session_id = cl.user_session.get("session_id")
    if session_id in chat_sessions:
        # Save the final state of the conversation
        history = load_conversation_history(
            session_id)  # Load existing history
        save_conversation_history(session_id, history)
        del chat_sessions[session_id]
    logger.info(f"Chat ended for session {session_id}")


@cl.on_chat_resume
async def on_chat_resume(thread: ThreadDict):
    session_id = thread.get("session_id")
    if session_id not in chat_sessions:
        chat_session = await initialize_chat(session_id)
        chat_sessions[session_id] = chat_session
    cl.user_session.set("session_id", session_id)
    cl.user_session.set("chat_session", chat_sessions[session_id])
    logger.info(f"Chat resumed for session {session_id}")

    # Load and display previous messages
    history = load_conversation_history(session_id)
    for message in history:
        if 'user' in message:
            await cl.Message(content=message['user'], author="Human").send()
        if 'model' in message:
            await cl.Message(content=message['model']).send()


@cl.on_stop
def on_stop():
    session_id = cl.user_session.get("session_id")
    logger.info(f"Chat stopped for session {session_id}")
