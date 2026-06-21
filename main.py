from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from typing import List
import database
import requests
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://precioventa-web.onrender.com"
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

def validar_numero(valor, campo, permite_cero=False):
    try:
        numero = float(str(valor).replace(',', '.'))
        if not permite_cero and numero <= 0:
            raise ValueError(campo)
        return numero
    except (ValueError, TypeError):
        raise ValueError(campo)

class Producto(BaseModel):
    nombreProducto: str = ""
    costoProducto: str = ""

class CalculoRequest(BaseModel):
    productos: List[Producto]
    tasaBcv: str = Field(...)
    tasaUsdt: str = Field(...)
    ganancia: str = Field(...)
    costoEnvio: str = Field(...)
    comisionTarjeta: str = Field(...)

    @field_validator("tasaBcv")
    def validar_bcv(cls, v):
        return str(validar_numero(v, "tasaBcv"))

    @field_validator("tasaUsdt")
    def validar_usdt(cls, v):
        return str(validar_numero(v, "tasaUsdt"))

    @field_validator("ganancia")
    def validar_ganancia(cls, v):
        return str(validar_numero(v, "ganancia"))

    @field_validator("costoEnvio")
    def validar_envio(cls, v):
        if not v or not v.strip():
            return "0"
        return str(validar_numero(v, "costoEnvio", permite_cero=True))

    @field_validator("comisionTarjeta")
    def validar_tarjeta(cls, v):
        if not v or not v.strip():
            return "0"
        return str(validar_numero(v, "comisionTarjeta", permite_cero=True))

ERRORES = {
    "tasaBcv":          {"codigo": 1001, "mensaje": "El campo tasaBcv no es válido"},
    "tasaUsdt":         {"codigo": 1002, "mensaje": "El campo tasaUsdt no es válido"},
    "ganancia":         {"codigo": 1003, "mensaje": "El campo ganancia no es válido"},
    "costoEnvio":       {"codigo": 1004, "mensaje": "El campo costoEnvio no es válido"},
    "comisionTarjeta":  {"codigo": 1005, "mensaje": "El campo comisionTarjeta no es válido"},
    "nombreProducto":   {"codigo": 1101, "mensaje": "El campo nombreProducto no es válido"},
    "costoProducto":    {"codigo": 1102, "mensaje": "El campo costoProducto no es válido"},
}

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    for error in exc.errors():
        campo = str(error.get("msg", "")).replace("Value error, ", "")
        if campo in ERRORES:
            return JSONResponse(
                status_code=422,
                content={"error": ERRORES[campo]}
            )
        campo = error["loc"][-1]
        if campo in ERRORES:
            return JSONResponse(
                status_code=422,
                content={"error": ERRORES[campo]}
            )
    return JSONResponse(
        status_code=422,
        content={"error": {"codigo": 1000, "mensaje": "Solicitud inválida"}}
    )

@app.get("/")
@app.head("/")
def inicio():
    return {"mensaje": "API funcionando correctamente"}

@app.get("/tasas")
def obtener_tasas():
    try:
        bcv_response = requests.get("https://rates.dolarvzla.com/bcv/current.json")
        bcv_data = bcv_response.json()

        usdt_key = database.obtener_config("usdt_api_key")
        usdt_response = requests.get(
            "https://api.dolarvzla.com/public/usdt/exchange-rate",
            headers={"x-dolarvzla-key": usdt_key}
        )
        usdt_data = usdt_response.json()

        return {
            "codigo": "0000",
            "tasaBcvUsd": bcv_data["current"]["usd"],
            "tasaBcvEur": bcv_data["current"]["eur"],
            "tasaUsdt": usdt_data["current"]["sell"]
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": {"codigo": 3001, "mensaje": str(e)}}
        )

@app.post("/calcular")
def calcular(data: CalculoRequest):
    def fmt(n):
        n = round(n, 2)
        return int(n) if n % 1 == 0 else n

    try:
        bcv = float(data.tasaBcv)
        usdt = float(data.tasaUsdt)
        ganancia = float(data.ganancia)
        tarjeta = float(data.comisionTarjeta)
        envio = float(data.costoEnvio)
    except (ValueError, TypeError):
        return JSONResponse(
            status_code=422,
            content={"error": {"codigo": 1000, "mensaje": "Datos generales inválidos"}}
        )

    productos_validos = []
    for producto in data.productos:
        nombre = producto.nombreProducto.strip() if producto.nombreProducto else ""
        if not nombre:
            continue
        try:
            costo = float(str(producto.costoProducto).replace(',', '.'))
            if costo <= 0:
                continue
        except (ValueError, TypeError):
            continue
        productos_validos.append((nombre, costo))

    if not productos_validos:
        return {"codigo": "0000", "resultados": []}

    envio_por_producto = envio / len(productos_validos)
    resultados = []

    for nombre, costo in productos_validos:
        dolares_objetivo = costo * (1 + ganancia / 100)
        precio_base = (dolares_objetivo * usdt) / bcv
        monto_tarjeta = precio_base * (tarjeta / 100)
        precio_unitario = precio_base + monto_tarjeta + envio_por_producto

        resultados.append({
            "nombreProducto": nombre,
            "precioUnitarioDolares": fmt(precio_unitario),
            "precioUnitarioBolivares": fmt(precio_unitario * bcv)
        })

    return {"codigo": "0000", "resultados": resultados}


class LoginRequest(BaseModel):
    usuario: str = Field(..., min_length=1)
    clave: str = Field(..., min_length=1)

@app.post("/login")
def login(data: LoginRequest):
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, usuario FROM usuarios WHERE usuario = %s AND clave = %s",
        (data.usuario, data.clave)
    )
    usuario = cursor.fetchone()
    cursor.close()
    conn.close()

    if not usuario:
        return JSONResponse(
            status_code=401,
            content={"error": {"codigo": 2001, "mensaje": "Usuario o clave incorrectos"}}
        )

    return {"codigo": "0000", "usuario": usuario[1], "usuarioId": usuario[0]}


class EstadoCalculadora(BaseModel):
    usuarioId: int
    datos: dict

@app.post("/estado-calculadora")
def guardar_estado(data: EstadoCalculadora):
    try:
        database.guardar_estado_calculadora(data.usuarioId, data.datos)
        return {"codigo": "0000"}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": {"codigo": 4001, "mensaje": "No se pudo guardar el estado"}}
        )

@app.get("/estado-calculadora/{usuario_id}")
def obtener_estado(usuario_id: int):
    try:
        datos = database.obtener_estado_calculadora(usuario_id)
        return {"codigo": "0000", "datos": datos}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": {"codigo": 4002, "mensaje": "No se pudo obtener el estado"}}
        )