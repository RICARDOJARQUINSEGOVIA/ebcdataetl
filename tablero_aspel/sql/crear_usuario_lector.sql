-- Ejecutar en Neon (proyecto ebcexample) con el usuario neondb_owner.
-- Crea un usuario que SOLO puede leer el esquema aspel_demo.
-- Ejecuta cada instrucción por separado (clic dentro y Ctrl + Enter).
CREATE ROLE alumno_lector WITH LOGIN PASSWORD 'cambia-esta-clave';
GRANT CONNECT ON DATABASE neondb TO alumno_lector;
GRANT USAGE ON SCHEMA aspel_demo TO alumno_lector;
GRANT SELECT ON ALL TABLES IN SCHEMA aspel_demo TO alumno_lector;
ALTER DEFAULT PRIVILEGES IN SCHEMA aspel_demo GRANT SELECT ON TABLES TO alumno_lector;
