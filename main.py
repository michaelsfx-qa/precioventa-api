from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from typing import List

app = FastAPI()

def validar_numero(valor, campo, permite_cero=False):
    try:
        numero = float(valor)
        if not permite_cero and numero <= 0:
            raise ValueError(campo)
        return numero
    except (ValueError, TypeError):
        raise ValueError(campo)

class Producto(BaseModel):
    nombreProducto: str = Field(...)
    costoProducto: str = Field(...)
    cantidadProducto: str = Field(...)

    @field_validator("nombreProducto")
    def validar_nombre(cls, v):
        if not v or not v.strip():
            raise ValueError("nombreProducto")
        return v.strip()

    @field_validator("costoProducto")
    def validar_costo(cls, v):
        return str(validar_numero(v, "costoProducto"))

    @field_validator("cantidadProducto")
    def validar_cantidad(cls, v):
        return str(validar_numero(v, "cantidadProducto"))

class CalculoRequest(BaseModel):
    productos: List[Producto]
    tasaBcv: str = Field(...)
    tasaParalelo: str = Field(...)
    ganancia: str = Field(...)
    costoEnvio: str = Field(...)
    comisionTarjeta: str = Field(...)

    @field_validator("tasaBcv")
    def validar_bcv(cls, v):
        return str(validar_numero(v, "tasaBcv"))

    @field_validator("tasaParalelo")
    def validar_paralelo(cls, v):
        return str(validar_numero(v, "tasaParalelo"))

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
    "tasaParalelo":     {"codigo": 1002, "mensaje": "El campo tasaParalelo no es válido"},
    "ganancia":         {"codigo": 1003, "mensaje": "El campo ganancia no es válido"},
    "costoEnvio":       {"codigo": 1004, "mensaje": "El campo costoEnvio no es válido"},
    "comisionTarjeta":  {"codigo": 1005, "mensaje": "El campo comisionTarjeta no es válido"},
    "nombreProducto":   {"codigo": 1101, "mensaje": "El campo nombreProducto no es válido"},
    "costoProducto":    {"codigo": 1102, "mensaje": "El campo costoProducto no es válido"},
    "cantidadProducto": {"codigo": 1103, "mensaje": "El campo cantidadProducto no es válido"},
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
def inicio():
    return {"mensaje": "API funcionando correctamente"}

@app.post("/calcular")
def calcular(data: CalculoRequest):
    envio_por_producto = float(data.costoEnvio) / len(data.productos)
    resultados = []

    for producto in data.productos:
        costo = float(producto.costoProducto)
        cantidad = float(producto.cantidadProducto)
        bcv = float(data.tasaBcv)
        paralelo = float(data.tasaParalelo)
        ganancia = float(data.ganancia)
        tarjeta = float(data.comisionTarjeta)

        dolares_objetivo = costo * (1 + ganancia / 100)
        precio_base = (dolares_objetivo * paralelo) / bcv
        monto_tarjeta = precio_base * (tarjeta / 100)
        precio_unitario = precio_base + monto_tarjeta + envio_por_producto
        precio_total = precio_unitario * cantidad

        resultados.append({
            "nombreProducto": producto.nombreProducto,
            "precioUnitario": round(precio_unitario, 2)
        })

    return {"resultados": resultados}

    //test