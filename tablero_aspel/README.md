# Tablero Aspel SAE (datos anonimizados)

App en Streamlit que lee las tablas de Aspel SAE cargadas en Neon
(esquema `aspel_demo`) y muestra: resumen de ventas, clientes (Pareto,
recencia y frecuencia, nuevos contra recurrentes), ciclo pedido → factura,
inventario (ABC, bajo mínimo, sin movimiento), compras y descarga de datos.

## Estructura
- `app.py`: página principal y pestañas.
- `modulos/conexion.py`: conexión a Neon y lectura de tablas permitidas.
- `modulos/datos.py`: limpieza y unión de tablas (lo mismo que hace Power Query).
- `modulos/graficas.py`: gráficas y formatos.
- `sql/crear_usuario_lector.sql`: usuario de solo lectura para la app y los alumnos.

## Despliegue en Streamlit Community Cloud
1. Sube esta carpeta a un repositorio nuevo de GitHub (app.py en la raíz).
2. En share.streamlit.io: Create app › elige el repositorio › archivo `app.py`.
3. En Advanced settings › Secrets pega el contenido de
   `.streamlit/secrets.toml.example` con tu usuario y contraseña reales.
