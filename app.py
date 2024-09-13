import os
import time
import logging
from dotenv import load_dotenv
import google.generativeai as genai
import chainlit as cl
from chainlit.logger import logger as l
import asyncio

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set Chainlit logger to ERROR level to suppress warnings
l.setLevel(logging.ERROR)

load_dotenv()
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
# flag = False

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
    logger.info("Chat started")
    cl.user_session.set("chat_session", model.start_chat(history=[]))
    await cl.Message(content="Welcome! Please upload an audit report (pdf) to begin.").send()


@cl.on_message
async def main(message: cl.Message):
    # global flag
    logger.info(f"Received message: {message.content}")
    chat_session = cl.user_session.get("chat_session")

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
                message.content # "Summarize the priority issues in this audit report and grade them by severity and order by which should be fixed first.",
            ])
        else:
            if not chat_session:
                await cl.Message(content="Please upload a PDF file to analyze first.").send()
                return

            logger.info("Sending message to Gemini")
            response = chat_session.send_message(message.content)

        logger.info(f"Received response from Gemini: {response.text}")
        await cl.Message(content=response.text).send()
            

    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        await cl.Message(content=f"An error occurred: {str(e)}").send()

    # Force an update to the UI
    await asyncio.sleep(0.1)

@cl.on_stop
def on_stop():
    logger.info("Chat stopped")
    