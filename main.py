import re
import json

# -----------------------------
# Glosario optimizado
# -----------------------------
GLOSARIO = {
    "wip": {"min": 10001, "max": 65535},
    "lineas_validas": set(["ZZCAMPREC", "ZZVENTA", "ZZCOMPRA"]),
    "cuentas_validas": set(["I741351", "E123456"]),
    "pdv_validos": set(["Pa","Pb","W1"]),
    "incompatibilidades": [
        {"linea": "ZZCAMPREC", "cuentas_prohibidas_prefijo": "I"}
    ]
}

# -----------------------------
# Función de validación bulletproof
# -----------------------------
def validar_mensaje(texto):
    errores = []

    texto_lower = texto.lower()

    # --- WIP ---
    wips = []
    for wip in re.findall(r"\b\d{5,8}\b", texto):
        try:
            n = int(wip)
            if not (GLOSARIO["wip"]["min"] <= n <= GLOSARIO["wip"]["max"]):
                errores.append(f"WIP {n} fuera de rango (10001-65535)")
            wips.append(n)
        except ValueError:
            errores.append(f"WIP {wip} no es un número válido")

    # --- Cuentas ---
    cuentas = []
    for cuenta in re.findall(r"\b[IE]\d{6}\b", texto):
        if cuenta not in GLOSARIO["cuentas_validas"]:
            errores.append(f"Cuenta {cuenta} no válida")
        cuentas.append(cuenta)

    # --- Líneas ---
    lineas = []
    for linea in re.findall(r"\bZZ[A-Z0-9]+\b", texto, re.IGNORECASE):
        linea_upper = linea.upper()
        if linea_upper not in GLOSARIO["lineas_validas"]:
            errores.append(f"Línea {linea} no reconocida")
        lineas.append(linea_upper)

    # --- PdV ---
    pdvs = []
    # Detecta todos los PdV siguiendo "PdV" en el texto
    for pdv_match in re.findall(r"\b[Pp]d[Vv]\s+([A-Za-z0-9]+)\b", texto):
        if pdv_match not in GLOSARIO["pdv_validos"]:
            errores.append(f"Punto de venta {pdv_match} no válido")
        pdvs.append(pdv_match)

    # --- Compatibilidades ---
    for regla in GLOSARIO["incompatibilidades"]:
        if regla["linea"] in lineas:
            for c in cuentas:
                if c.startswith(regla["cuentas_prohibidas_prefijo"]):
                    errores.append(f"Línea {regla['linea']} incompatible con cuenta {c}")

    return errores

# -----------------------------
# Función principal
# -----------------------------
def procesar_mensaje(texto):
    errores = validar_mensaje(texto)
    if errores:
        return {"status": "error", "errores": errores}
    else:
        return {"status": "ok", "mensaje": texto}

# -----------------------------
# Lambda handler
# -----------------------------
def lambda_handler(event, context):
    texto = event.get("input", "")
    return procesar_mensaje(texto)

# -----------------------------
# Prueba rápida
# -----------------------------
if __name__ == "__main__":
    mensaje_usuario = (
        "Quiero facturar la línea ZZCAMPREC contra la cuenta E123456 "
        "de la WIP 12589 en PdV Pa y también la línea ZZVENTA "
        "contra en PdV W1"
    )
    resultado = procesar_mensaje(mensaje_usuario)
    print(json.dumps(resultado, indent=2))
