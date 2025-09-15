import streamlit as st
import boto3
import json
import uuid
import os
import re

# -----------------------------
# Glosario y validación
# -----------------------------
GLOSARIO = {
    "wip": {"min": 10001, "max": 65535},
    "lineas_validas": set(["ZZCAMPREC", "ZZVENTA", "ZZCOMPRA"]),
    "cuentas_validas": set(["I741351", "E123456"]),
    "pdv_validos": set(["Pa","Pb","Z1"]),
    "incompatibilidades": [
        {"linea": "ZZCAMPREC", "cuentas_prohibidas_prefijo": "I"}
    ]
}

def validar_mensaje(texto):
    errores = []

    # WIP
    for wip in re.findall(r"\b\d{5,8}\b", texto):
        try:
            n = int(wip)
            if not (GLOSARIO["wip"]["min"] <= n <= GLOSARIO["wip"]["max"]):
                errores.append(f"WIP {n} fuera de rango (10001-65535)")
        except ValueError:
            errores.append(f"WIP {wip} no es un número válido")

    # Cuentas
    cuentas = re.findall(r"\b[IE]\d{6}\b", texto)
    for cuenta in cuentas:
        if cuenta not in GLOSARIO["cuentas_validas"]:
            errores.append(f"Cuenta {cuenta} no válida")

    # Líneas
    lineas = []
    for linea in re.findall(r"\bZZ[A-Z0-9]+\b", texto, re.IGNORECASE):
        linea_upper = linea.upper()
        if linea_upper not in GLOSARIO["lineas_validas"]:
            errores.append(f"Línea {linea} no reconocida")
        lineas.append(linea_upper)

    # PdV
    pdvs = []
    for pdv_match in re.findall(r"\b[Pp]d[Vv]\s+([A-Za-z0-9]+)\b", texto):
        if pdv_match not in GLOSARIO["pdv_validos"]:
            errores.append(f"Punto de venta {pdv_match} no válido")
        pdvs.append(pdv_match)

    # Compatibilidades
    for regla in GLOSARIO["incompatibilidades"]:
        if regla["linea"] in lineas:
            for c in cuentas:
                if c.startswith(regla["cuentas_prohibidas_prefijo"]):
                    errores.append(f"Línea {regla['linea']} incompatible con cuenta {c}")

    return errores

# -----------------------------
# Configuración Bedrock
# -----------------------------
REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
AGENT_ARN = "arn:aws:bedrock:us-east-1:699541216231:agent/UT8RWCB5UB"
AGENT_ALIAS_ARN = "arn:aws:bedrock:us-east-1:699541216231:agent-alias/LK9JA0YTKV"

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

# -----------------------------
# Interfaz Streamlit
# -----------------------------
st.title("🤖 Chatbot soporte Autoline con IA")

if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "session_id" not in st.session_state:
    st.session_state["session_id"] = str(uuid.uuid4())

for message in st.session_state["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if user_input := st.chat_input("Escribe tu consulta..."):
    # --- Validación antes de llamar al agente ---
    errores = validar_mensaje(user_input)
    if errores:
        st.error("Se encontraron errores en tu mensaje:")
        for e in errores:
            st.warning(f"- {e}")
        # También lo agregamos a la conversación como asistente
        st.session_state["messages"].append({"role": "assistant", "content": "Se detectaron errores en los datos: " + ", ".join(errores)})
    else:
        # Todo correcto → llamar al agente
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
