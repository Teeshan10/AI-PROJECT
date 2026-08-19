import streamlit as st
import requests
import json
from groq import Groq

# 1. SET UP THE WEB UI
st.title("🏨 AI Concierge & Travel Agent")
st.write("Ask me to find hotels, restaurants, or local attractions anywhere in the world!")

# 2. LOAD SECRET KEYS (Hidden safely from the public)
GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
FOURSQUARE_API_KEY = st.secrets["FOURSQUARE_API_KEY"]
client = Groq(api_key=GROQ_API_KEY)

# 3. CREATE THE FOURSQUARE DATA RETRIEVAL FUNCTION
def search_foursquare(query, near):
    url = "https://api.foursquare.com/v3/places/search"
    headers = {
        "Accept": "application/json",
        "Authorization": FOURSQUARE_API_KEY
    }
    params = {
        "query": query,
        "near": near,
        "limit": 3
    }
    
    # Fetches real-time places data from Foursquare's global database
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        venues = response.json().get('results', [])
        results = []
        for v in venues:
            results.append({
                "name": v.get("name"),
                "address": v.get("location", {}).get("formatted_address", "Address unavailable"),
                "categories": [c.get("name") for c in v.get("categories", [])]
            })
        return json.dumps(results)
    return "No results found or error fetching data."

# Tell Llama how and when to use the Foursquare function
tools = [
    {
        "type": "function",
        "function": {
            "name": "search_foursquare",
            "description": "Search for hotels, restaurants, and places using Foursquare.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "e.g., 'luxury hotel', 'italian restaurant'"},
                    "near": {"type": "string", "description": "e.g., 'Kolkata', 'New York City'"}
                },
                "required": ["query", "near"]
            }
        }
    }
]

# 4. MANAGE THE CHAT HISTORY
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": "You are a friendly travel concierge. Use the search_foursquare tool to find venue recommendations and present them nicely to the user."}
    ]

# Display past chat messages
for msg in st.session_state.messages:
    if msg["role"] not in ["system", "tool"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# 5. HANDLE CHAT INPUT & EXECUTION
user_input = st.chat_input("E.g., Find a great rooftop cafe in Kolkata")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)
        
    with st.chat_message("assistant"):
        # Send query to Llama
        response = client.chat.completions.create(
            model="llama3-8b-8192", # <--- CHANGE THIS LINE
            messages=st.session_state.messages,
            tools=tools,
            tool_choice="auto"
        )
        
        response_msg = response.choices[0].message
        
        # If Llama decides it needs real-time database results via Foursquare
        if response_msg.tool_calls:
            tool_call_record = {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments}
                    } for tc in response_msg.tool_calls
                ]
            }
            st.session_state.messages.append(tool_call_record)
            
            # Execute the Foursquare search call
            for tool_call in response_msg.tool_calls:
                args = json.loads(tool_call.function.arguments)
                func_response = search_foursquare(args.get("query"), args.get("near"))
                
                st.session_state.messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": "search_foursquare",
                    "content": func_response
                })
            
            # Llama reads the data returned from Foursquare and writes the final answer
            final_response = client.chat.completions.create(
                model="llama3-8b-8192", # <--- CHANGE THIS LINE TOO
                messages=st.session_state.messages
            )
            final_text = final_response.choices[0].message.content
            st.markdown(final_text)
            st.session_state.messages.append({"role": "assistant", "content": final_text})
            
        else:
            st.markdown(response_msg.content)
            st.session_state.messages.append({"role": "assistant", "content": response_msg.content})
