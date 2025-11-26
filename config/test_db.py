from database import db

print("Probando conexión a SQL Server...")

if db.test_connection():
    print("✅ Conexión exitosa a SQL Server")
else:
    print("❌ Falló la conexión")
