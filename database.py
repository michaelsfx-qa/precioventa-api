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