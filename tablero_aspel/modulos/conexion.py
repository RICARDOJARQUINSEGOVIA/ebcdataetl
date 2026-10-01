"""
Conexión a la base de datos (Neon / PostgreSQL) y lectura de tablas.

La dirección de la base y el esquema se leen de los secretos de Streamlit:
    [database]
    url     = "postgresql+psycopg2://usuario:clave@host/neondb?sslmode=require"
    esquema = "aspel_demo"
"""
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text

# Solo estas tablas pueden leerse desde la app (evita consultas arbitrarias).
TABLAS = [
    "clie02", "prov02", "inve02", "mult02",
    "factf02", "par_factf02", "factp02", "par_factp02",
    "compc02", "par_compc02",
]


@st.cache_resource(show_spinner=False)
def obtener_motor():
    """Crea una sola conexión reutilizable para toda la app."""
    url = st.secrets["database"]["url"]
    # pool_pre_ping revisa que la conexión siga viva: Neon "duerme"
    # la base tras unos minutos sin uso y corta las conexiones viejas.
    return create_engine(url, pool_pre_ping=True, pool_recycle=240)


def esquema() -> str:
    return st.secrets["database"].get("esquema", "aspel_demo")


def leer_tabla(nombre: str) -> pd.DataFrame:
    """Lee una tabla completa y deja los nombres de columna en minúsculas."""
    if nombre not in TABLAS:
        raise ValueError(f"Tabla no permitida: {nombre}")
    prefijo = f"{esquema()}." if esquema() else ""
    with obtener_motor().connect() as con:
        df = pd.read_sql(text(f"SELECT * FROM {prefijo}{nombre}"), con)
    df.columns = [c.lower() for c in df.columns]
    return df
