import streamlit as st
import boto3
import json
import uuid
import os

# Configuración
REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
AGENT_ARN = "arn:aws:bedrock:us-east-1:699541216231:agent/UT8RWCB5UB"
AGENT_ALIAS_ARN = "arn:aws:bedrock:us-east-1:699541216231:agent-alias/UFVLOHXRKM"

# Cliente Bedrock (lee credenciales de variables de entorno en Railway)
bedrock_agent_client = boto3.client("bedrock-agent-runtime", region_name=REGION)

def call_bedrock_agent(prompt, session_id):
    response_stream = bedrock_agent_client.invoke_agent(
        agentId=AGENT_ARN.split("/")[-1],
        agentAliasId=AGENT_ALIAS_ARN.split("/")[-1],
        sessionId=session_id,
        inputText=prompt
    )
    
    final_response = ""
    for event in response_stream['completion']:
        if 'chunk' in event:
            data = event['chunk']['bytes']
            text_piece = data.decode('utf-8')
            final_response += text_piece
    return final_response

# Interfaz Streamlit
st.title("🤖 Chatbot soporte Autoline con IA")

if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "session_id" not in st.session_state:
    st.session_state["session_id"] = str(uuid.uuid4())

for message in st.session_state["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if user_input := st.chat_input("Escribe tu consulta..."):
    st.session_state["messages"].append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Pensando..."):
            try:
                response = call_bedrock_agent(user_input, st.session_state["session_id"])
                st.markdown(response)
                st.session_state["messages"].append({"role": "assistant", "content": response})
            except Exception as e:
                st.error(f"Error: {str(e)}")


