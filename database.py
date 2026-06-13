import psycopg2

def get_connection():
    return psycopg2.connect(
        host="localhost",
        database="precioventa_db",
        user="postgres",
        password="248710"
    )