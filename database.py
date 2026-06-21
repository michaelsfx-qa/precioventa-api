import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        sslmode="require"
    )

def obtener_config(nombre):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT valor FROM config_api WHERE nombre = %s", (nombre,))
    resultado = cursor.fetchone()
    cursor.close()
    conn.close()
    return resultado[0] if resultado else None

def guardar_estado_calculadora(usuario_id, datos):
    import json
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO calculadora_estado (usuario_id, datos, actualizado_en)
        VALUES (%s, %s, NOW())
        ON CONFLICT (usuario_id)
        DO UPDATE SET datos = %s, actualizado_en = NOW()
        """,
        (usuario_id, json.dumps(datos), json.dumps(datos))
    )
    conn.commit()
    cursor.close()
    conn.close()

def obtener_estado_calculadora(usuario_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT datos FROM calculadora_estado WHERE usuario_id = %s",
        (usuario_id,)
    )
    resultado = cursor.fetchone()
    cursor.close()
    conn.close()
    return resultado[0] if resultado else None