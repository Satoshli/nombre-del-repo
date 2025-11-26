"""
Configuración de conexión a SQLite (plug and play).
"""

import sqlite3
import logging
from contextlib import contextmanager
from typing import Optional, Dict, Any
from pathlib import Path
import os

logger = logging.getLogger(__name__)


class DatabaseConfig:
    """Configuración centralizada de la base de datos SQLite."""
    
    def __init__(self):
        # Base de datos en el mismo directorio del proyecto
        self.db_path = os.getenv('DB_PATH', 'data/monitoreo_ambiental.db')
        
        # Crear directorio si no existe
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Base de datos SQLite: {self.db_path}")


class DatabaseConnection:
    """Manejador de conexiones SQLite con retry logic."""
    
    def __init__(self, config: Optional[DatabaseConfig] = None):
        self.config = config or DatabaseConfig()
        self.db_path = self.config.db_path
        
    @contextmanager
    def get_connection(self):
        """
        Context manager para obtener una conexión.
        
        Uso:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM table")
        """
        connection = None
        
        try:
            connection = sqlite3.connect(self.db_path)
            # Habilitar foreign keys (deshabilitado por defecto en SQLite)
            connection.execute("PRAGMA foreign_keys = ON")
            logger.debug("Conexión a SQLite establecida")
            yield connection
            connection.commit()
            
        except sqlite3.Error as e:
            logger.error(f"Error de conexión SQLite: {e}")
            if connection:
                connection.rollback()
            raise
            
        finally:
            if connection:
                connection.close()
                logger.debug("Conexión cerrada")
    
    @contextmanager
    def get_transaction(self):
        """
        Context manager para transacciones con rollback automático en errores.
        
        Uso:
            with db.get_transaction() as (conn, cursor):
                cursor.execute("INSERT ...")
                cursor.execute("UPDATE ...")
                # Auto commit si todo OK, rollback si hay excepción
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                yield conn, cursor
                conn.commit()
                logger.debug("Transacción confirmada (commit)")
                
            except Exception as e:
                conn.rollback()
                logger.error(f"Transacción revertida (rollback): {e}")
                raise
                
            finally:
                cursor.close()
    
    def test_connection(self) -> bool:
        """Prueba la conexión a la base de datos."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                return result[0] == 1
        except Exception as e:
            logger.error(f"Test de conexión fallido: {e}")
            return False
    
    def initialize_database(self, schema_file: str = None):
        """
        Inicializa la base de datos ejecutando el script de schema.
        
        Args:
            schema_file: Ruta al archivo SQL de schema
        """
        if schema_file is None:
            # Buscar schema en carpeta sql/
            base_dir = Path(__file__).parent.parent
            schema_file = base_dir / 'sql' / '01_create_schema_sqlite.sql'
        
        if not Path(schema_file).exists():
            logger.warning(f"Archivo de schema no encontrado: {schema_file}")
            return False
        
        try:
            with open(schema_file, 'r', encoding='utf-8') as f:
                schema_sql = f.read()
            
            with self.get_connection() as conn:
                # Ejecutar script completo
                conn.executescript(schema_sql)
                logger.info("Base de datos inicializada exitosamente")
                return True
                
        except Exception as e:
            logger.error(f"Error inicializando base de datos: {e}")
            return False
    
    def execute_query(self, query: str, params: tuple = None) -> list:
        """
        Ejecuta una query de lectura y retorna los resultados.
        
        Args:
            query: Query SQL
            params: Parámetros para la query (opcional)
            
        Returns:
            Lista de tuplas con los resultados
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.fetchall()
    
    def execute_non_query(self, query: str, params: tuple = None) -> int:
        """
        Ejecuta una query de modificación (INSERT, UPDATE, DELETE).
        
        Args:
            query: Query SQL
            params: Parámetros para la query (opcional)
            
        Returns:
            Número de filas afectadas
        """
        with self.get_transaction() as (conn, cursor):
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.rowcount
    
    def get_or_create_centro(self, codigo: str, nombre: str = None, 
                            es_censurado: bool = False) -> int:
        """
        Obtiene el ID de un centro o lo crea si no existe.
        
        Args:
            codigo: Código del centro
            nombre: Nombre del centro (opcional)
            es_censurado: Si los datos están censurados
            
        Returns:
            centro_id
        """
        # Intentar obtener centro existente
        query_select = "SELECT centro_id FROM centros WHERE codigo_centro = ?"
        result = self.execute_query(query_select, (codigo,))
        
        if result:
            return result[0][0]
        
        # Crear nuevo centro
        nombre_final = nombre or 'CENTRO_SIN_NOMBRE'
        
        query_insert = """
        INSERT INTO centros (codigo_centro, nombre_centro, es_censurado)
        VALUES (?, ?, ?)
        """
        
        with self.get_transaction() as (conn, cursor):
            cursor.execute(query_insert, (codigo, nombre_final, 1 if es_censurado else 0))
            centro_id = cursor.lastrowid
            
        logger.info(f"Centro creado: {codigo} (ID: {centro_id}, censurado: {es_censurado})")
        return centro_id
    
    def insert_with_identity(self, table: str, data: Dict[str, Any]) -> int:
        """
        Inserta un registro y retorna el ID generado.
        
        Args:
            table: Nombre de la tabla
            data: Diccionario con los datos {columna: valor}
            
        Returns:
            ID del registro insertado
        """
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data])
        values = tuple(data.values())
        
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        
        with self.get_transaction() as (conn, cursor):
            cursor.execute(query, values)
            return cursor.lastrowid
    
    def get_table_count(self, table: str) -> int:
        """Retorna el número de registros en una tabla."""
        result = self.execute_query(f"SELECT COUNT(*) FROM {table}")
        return result[0][0] if result else 0
    
    def get_all_tables(self) -> list:
        """Retorna lista de todas las tablas en la BD."""
        query = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        results = self.execute_query(query)
        return [row[0] for row in results]
    
    def vacuum(self):
        """Optimiza la base de datos (compacta y reorganiza)."""
        try:
            with self.get_connection() as conn:
                conn.execute("VACUUM")
            logger.info("Base de datos optimizada (VACUUM)")
        except Exception as e:
            logger.error(f"Error en VACUUM: {e}")


# Instancia global para uso en otros módulos
db = DatabaseConnection()
