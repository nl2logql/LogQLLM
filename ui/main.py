from fastapi import FastAPI, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
from openai import OpenAI
from supabase import create_client, Client

from models import *

import re
import os
from os.path import join, dirname
import logging


dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

supabase_client: Client = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_SERVICE_ROLE_KEY"))
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

MODEL_PARAMS = {
    "messages": [
        {
        "role": "system",
        "content": [
            {
            "text": "You are LogQLLM, a specialized language model trained to convert natural language queries into LogQL (Log Query Language) queries. Your primary function is to interpret user requests expressed in plain English and translate them into valid LogQL syntax.",
            "type": "text"
            }
        ]
        }
    ],
    "temperature": 0.2,
    "max_tokens": 2048,
    "top_p": 1,
    "frequency_penalty": 0,
    "presence_penalty": 0,
    "response_format": {
        "type": "text"
    }
}

MODEL_REQ_TEMPLATES = {
    "gemma-2-logql": {
        "model": "gemma-2-logql",
        **MODEL_PARAMS
    },
    "llama-3.1-logql ": {
        "model": "llama-3.1-logql",
        **MODEL_PARAMS
    }
}

SUPPORTED_MODELS = list(MODEL_REQ_TEMPLATES.keys())

MODEL_API_ROUTES = {
    "gemma-2-logql": "",
    "llama-3.1-logql ": ""
}

def sanitize_name(name: str) -> str:
    sanitized = re.sub(r'[^a-zA-Z0-9 ]', '', name).strip()
    return sanitized if sanitized else None

async def get_user(request: Request):
    user_id = request.cookies.get("user_id")
    if not user_id:
        return None
    try:
        user = supabase_client.table("users").select("*").eq("id", user_id).single().execute()
    except:
        return None

    if not user.data:
        logger.error("Empty User Object Received")
        return None
    
    return user.data


def parse_chats(chats_dict):
    chats = []  
    for chat in chats_dict:
        if len(chat['messages']) < 1:
            continue
        newc = {}
        newc['title'] = chat['messages'][0]['content']
        newc['data'] = chat
        chats.append(newc)
    return chats

# Routes
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    user = await get_user(request)
    if not user:
        return templates.TemplateResponse("index.html", {"request": request, "ask_name": True})

    try:
        existing_chat_response = supabase_client.table("chats").select("*")\
            .eq('user_id', user['id'])\
            .eq('messages', {})\
            .order('created_at', desc=True)\
            .limit(1)\
            .execute()

        if existing_chat_response.data:
            chat_id = existing_chat_response.data[0]['id']
        else:
            chat_response = supabase_client.table("chats").insert({
                "user_id": user['id'],
                "messages": []
            }).execute()
            
            if not chat_response.data:
                logger.error("Failed to create new chat.")
                raise HTTPException(status_code=500, detail="Failed to create new chat.")
            
            chat_id = chat_response.data[0]['id']
    except Exception as e:
        logger.exception("Error creating new chat.")
        raise HTTPException(status_code=500, detail="Failed to create new chat.")
    
    all_chats = supabase_client.table("chats").select("*").eq('user_id', user['id']).order('created_at', desc=True).execute()
    chats = parse_chats(all_chats.data)
    
    response = templates.TemplateResponse("index.html", {
        "request": request,
        "user": user,
        "chats": chats,
        "ask_name": False,
        "models": SUPPORTED_MODELS,
    })
    response.set_cookie(key="chat_id", value=chat_id, httponly=False, max_age=60*60*24*1)  # 1 day
    return response

@app.post("/set_name")
async def set_name(request: Request, name: str = Form(...)):
    sanitized_name = sanitize_name(name)
    if not sanitized_name:
        raise HTTPException(status_code=400, detail="Invalid name.")
    try:
        response = supabase_client.table("users").insert({"name": sanitized_name}).execute()
        if not response.data:
            logger.error(f"Supabase Insert Error: {response.error}")
            raise HTTPException(status_code=500, detail="Failed to create user.")
        user = response.data
        if not user:
            raise HTTPException(status_code=500, detail="User creation failed.")
        user_id = user[0]['id']
    except Exception as e:
        logger.exception("Exception while inserting user into Supabase")
        print(e)
        raise HTTPException(status_code=500, detail="Internal server error.")
    response_redirect = RedirectResponse(url="/", status_code=303)
    response_redirect.set_cookie(key="user_id", value=user_id, httponly=False, max_age=60*60*24*30)  # 30 days
    return response_redirect

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, user_request: Request):
    logger.info(f"Received chat request with model: {request.model}")

    user = await get_user(user_request)
    if not user:
        logger.warning("Unauthenticated access attempt.")
        raise HTTPException(status_code=401, detail="User not authenticated.")
    user_id = user['id']

    chat_id = user_request.cookies.get("chat_id")
    if not chat_id:
        logger.warning("No chat_id found in cookies.")
        raise HTTPException(status_code=400, detail="No active chat found.")

    # Retrieve the specific chat
    try:
        chat_response = supabase_client.table("chats").select("*")\
            .eq("id", chat_id)\
            .execute()

        if not chat_response.data:
            logger.error("Chat not found.")
            raise HTTPException(status_code=400, detail="Chat not found.")

        chat = chat_response.data[0]
        existing_messages = chat.get('messages', [])
    except RuntimeError as err:
        logger.error(f"Supabase API Error: {err}")
        raise HTTPException(status_code=500, detail="Database query failed.")
    except Exception as e:
        logger.exception("Unexpected error while retrieving chat.")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")

    # Append the new user message
    updated_messages = request.messages

    # Update the chat with new user message
    try:
        update_response = supabase_client.table("chats")\
            .update({"messages": updated_messages})\
            .eq("id", chat_id)\
            .execute()

        if not update_response.data:
            logger.error("Failed to update chat messages.")
            raise HTTPException(status_code=500, detail="Failed to update chat messages.")
    except RuntimeError as err:
        logger.error(f"Supabase API Error: {err}")
        raise HTTPException(status_code=500, detail="Failed to update chat messages.")
    except Exception as e:
        logger.exception("Unexpected error while updating chat.")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")

    if request.model not in SUPPORTED_MODELS:
        logger.error(f"Unsupported model: {request.model}")
        raise HTTPException(status_code=400, detail="Unsupported model.")

    try:
        #TODO: Replace with custom inference client
        api_req = MODEL_REQ_TEMPLATES[request.model]
        api_req['messages'].append(request.messages[-1])
        print(api_req)
        response = client.chat.completions.create(
            model="ft:gpt-4o-2024-08-06:epoch-0:logqllm-0:AEZ5l6x0",
            messages=[
                {
                "role": "system",
                "content": [
                    {
                    "text": "You are LogQLLM, a specialized language model trained to convert natural language queries into LogQL (Log Query Language) queries. Your primary function is to interpret user requests expressed in plain English and translate them into valid LogQL syntax.",
                    "type": "text"
                    }
                ]
                },
                request.messages[-1]
            ],
            temperature=0.2,
            max_tokens=2048,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
            response_format={
                "type": "text"
            }
        )
        # response = client.chat.completions.create(
        #     model=request.model,
        #     messages=[request.messages[-1]]
        # )
        reply = response.choices[0].message.content
        updated_messages.append({"role": "assistant", "content": reply})
        supabase_client.table("chats")\
            .update({"messages": updated_messages})\
            .eq("id", chat_id)\
            .execute()

        logger.info("Successfully got a response from OpenAI API.")
        return ChatResponse(reply=reply)
    except Exception as e:
        logger.exception("Error communicating with OpenAI API.")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/get_chat/{chat_id}")
async def get_chat(chat_id: str, request: Request):
    user = await get_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="User not authenticated.")
    chat = supabase_client.table("chats").select("*").eq("id", chat_id).execute()
    if not chat.data:
        raise HTTPException(status_code=404, detail="Chat not found.")
    return {"messages": chat.data[0]['messages']}


@app.post("/feedback")
async def feedback(feedback: FeedbackRequest):
    feedback_bool = feedback.feedback_type == "positive"
    
    response = supabase_client.table("feedback").insert({
        "feedback_type": feedback_bool,
        "chat_id": feedback.chat_id,
        "user_id": feedback.user_id,
        "message_idx": feedback.message_idx
    }).execute()
    
    if not response.data:
        raise HTTPException(status_code=500, detail="Error inserting feedback.")
    
    return {"status": "Feedback submitted successfully"}


@app.get("/health")
async def health():
    return {"status": "ok"}
