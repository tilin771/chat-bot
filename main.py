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
    "pdv_validos" : set([
    "17","45","70","71","76","90","91","98","99",
    "A1","A2","A3","A4","A5",
    "Bg","Bm",
    "Ce","Cm","Cs",
    "D5",
    "Eh","Em","Eu",
    "Fc","Ff","Fg","Fm","Ft",
    "Gb","Gc","Gf","Gm","Gv",
    "H3","H5","H6","H7","Hb","Hl","Hm","Hn","Hz",
    "Ie",
    "Jb","Je","Jg","Jm","Jp","Jr","Js","Ju",
    "Ka","Kb","Kc","Kh","Km","Ko","Kr","Kt","Ku",
    "Lb","Lc","Lm","Lu",
    "Mc","Mi",
    "Nb","Nh","Np",
    "Oc","Od","Og","Oj","Ok","Op","Oq","Or","Os",
    "Pa","Pb","Pf","Pg","Ph","Pm","Po","Pp","Pq","Pr","Pv",
    "Qh","Qm","Qp","Qx",
    "Ra","Rb","Rc","Rd","Re","Rf","Rg","Ri","Rk","Rl","Rm","Rn","Rp","Rr","Rs","Rt","Ru","Rv","Rx",
    "Sl","Sx",
    "Ti","Tj","To","Tr","Tt",
    "Ub","Um","Uv",
    "V1","V2","Vb","Vc","Vg","Vh","Vm","Vp","Vs","Vt","Vv",
    "Xc","Xe","Xm",
    "Yc",
    "Zv","Zx"
]),
    "incompatibilidades": [
        {"linea": "ZZCAMPREC", "cuentas_prohibidas_prefijo": "I"}
    ]
}

def validar_mensaje(texto):
    errores = []

    # WIP
    for match in re.findall(r"\bWIP\s+(\d+)\b", texto, re.IGNORECASE):
        try:
            n = int(match)
            if not (GLOSARIO["wip"]["min"] <= n <= GLOSARIO["wip"]["max"]):
                errores.append(f"WIP {n} fuera de rango (10001-65535)")
        except ValueError:
            errores.append(f"WIP {match} no es un número válido")

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
    for pdv_match in re.findall(r"\b(?:pdv|punto de venta)\s+([A-Za-z0-9]+)\b", texto, re.IGNORECASE):
        print (f"PUNTO DE VENTA ENCONTRADO {pdv_match}")
        if pdv_match not in GLOSARIO["pdv_validos"]:
            errores.append(f"Punto de venta {pdv_match} no válido")
        pdvs.append(pdv_match)
        print(pdvs)

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
    # --- Mostrar mensaje del usuario siempre ---
    st.session_state["messages"].append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # --- Validación antes de llamar al agente ---
    errores = validar_mensaje(user_input)
    if errores:
        # Concatenar todos los errores en un solo mensaje
        mensaje_errores = ("⚠️ Se encontraron los siguientes errores en tu mensaje:\n\n" +"\n".join(f"- {e}" for e in errores))
        with st.chat_message("assistant"):
            st.markdown(mensaje_errores)
        st.session_state["messages"].append({"role": "assistant", "content": mensaje_errores})
    else:
        # Todo correcto → llamar al agente
        with st.chat_message("assistant"):
            with st.spinner("Pensando..."):
                try:
                    response = call_bedrock_agent(user_input, st.session_state["session_id"])
                    st.markdown(response)
                    st.session_state["messages"].append({"role": "assistant", "content": response})
                except Exception as e:
                    st.error(f"Error: {str(e)}")



