from dotenv import load_dotenv
from openai import OpenAI
import json
import os
import requests
from PyPDF2 import PdfReader
import gradio as gr

load_dotenv(override=True)

def push(text):
    requests.post(
        "https://api.pushover.net/1/messages.json",
        data = {
            "user": os.getenv("PUSHOVER_USER"),
            "token" : os.getenv("PUSHOVER_TOKEN"),
            "message": text
        }
    )

def record_user_details(email, name="Name not provided", notes = "not provided"):
    push(f"Recording interest from {name} with email {email} and notes {notes}")
    return {"recorded": "ok"}


def record_unknown_question(question):
    push(f"Recording {question} asked that I could not answer")
    return {"recorded": "ok"}


record_user_details_json = {
    "name": "record_user_details",
    "description": "Use this tool to record a user's interest in being in touch and provided an email address",
    "parameters": {
        "type": "object",
        "properties": {
            "email": {
                "type": "string",
                "description": "the email address of this user"
            },
            "name": {
                "type": "string",
                "description": "the user's name, if they provided it"
            },
            "notes": {
                "type": "string",
                "description": "Any additional information about the conversation that's worth recording to give context"
            }            
        },
        "required": ["email"],
        "additionalProperties": False
    }
}


record_unknown_question_json = {
    "name": "record_unknown_question",
    "description": "Always use this tool to record any question that couldn't be answered as you didn't know the answer",
    "parameters": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "The question that couldn't be answered"
            },
        },
        "required": ["question"],
        "additionalProperties": False 
    }
}


tools = [{"type": "function", "function": record_user_details_json },
        {"type": "function", "function": record_unknown_question_json }]


class Me:


    def __init__(self):
        self.openai = OpenAI()
        self.name = "Kausthab"
        reader = PdfReader("data_files/me.pdf")
        self.linkedin = ""
        for page in reader.pages:
            text = page.extract_text()
            if text:
                self.linkedin = self.linkedin + text 

        with open("data_files/profile.txt","r") as f:
            self.summary = f.read()

    def handle_tool_calls(self, tool_calls):
        results = []
        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
            print(f"Tool called: {tool_name}", flush = True)
            tool = globals().get(tool_name)
            result = tool(**arguments) if tool else {}
            results.append({"role": "tool", "content": json.dumps(result), "tool_call_id": tool_call.id})
        return results

    def system_prompt(self):
        system_prompt = f"""You are acting as {self.name}. You are answering questions on behalf of {self.name} on {self.name}'s career website. People will visit their website and \
        interact with you and you will answer all questions truthfully and in an egaging manner. Be courteous and empathetic. If you do not know the answer to any \
        question or the user asks you question that is out of your context, use the record_unknown_question tool to record question even if that question is not related to {self.name}'s career. \
        Also, if a user is engaging in a discussion, try to steer them towards getting in touch vis email; ask for their email and record their response using your record_user_details tool. In order \
        to better equip you, you will be given context of {self.name}'s LinkedIn and a snapshot of their resume/profile, so that you can engage with potential recruiters \
        or clinets in a professional and engaging manner"""

        system_prompt += f"""\n\n Summary:\n{self.summary}\n\n## LinkedIn Profile: \n{self.linkedin}\n\n"""
        system_prompt += f"with this context, please chat with the user, always staying in character as {self.name}."

        return system_prompt

    def chat(self, message, history):
        messages = [{"role": "system", "content": self.system_prompt()}] + history + [{"role": "user", "content": message}]
        done = False 
        while not done:
            response = self.openai.chat.completions.create(model = "gpt-4o-mini", messages=messages, tools=tools)
            if response.choices[0].finish_reason == "tool_calls":
                message = response.choices[0].message
                tool_calls = message.tool_calls #take out the tool call
                results = self.handle_tool_calls(tool_calls) #function is called
                messages.append(message)
                messages.extend(results)
            else:
                done = True 
        return response.choices[0].message.content


if __name__ == "__main__":
    me = Me()
    gr.ChatInterface(me.chat, type = "messages").launch()