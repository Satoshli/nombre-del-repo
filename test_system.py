"""
Script de pruebas automatizadas del sistema.
Ejecutar: python test_system.py
"""

import sys
from pathlib import Path
from config.database import db
from config.settings import INPUT_DIR
from utils.pdf_parser import PDFParser
from extractors.sedimento_extractor import SedimentoExtractor

def test_database_connection():
    """Test 1: Conexión a base de datos SQLite."""
    print("\n" + "="*60)
    print("TEST 1: Conexión a Base de Datos SQLite")
    print("="*60)
    
    try:
        if db.test_connection():
            print(f"✅ Conexión exitosa")
            print(f"   Base de datos: {db.db_path}")
            
            # Ver si la BD tiene tablas
            tables = db.get_all_tables()
            if tables:
                print(f"   Tablas encontradas: {len(tables)}")
            else:
                print("   ⚠️ BD vacía. Ejecutar: python main.py --init-db")
            return True
        else:
            print("❌ Conexión fallida")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_database_tables():
    """Test 2: Verificar que las tablas existen."""
    print("\n" + "="*60)
    print("TEST 2: Verificación de Tablas")
    print("="*60)
    
    expected_tables = [
        'centros', 'ordenes_trabajo', 
        'sedimento_estaciones', 'sedimento_materia_organica', 'sedimento_ph_redox',
        'oxigeno_perfiles', 'oxigeno_mediciones',
        'registro_visual_transectas', 'registro_visual_abundancia',
        'auditoria_extraccion', 'log_procesamiento', 'config_valores_default'
    ]
    
    try:
        query = """
        SELECT TABLE_NAME 
        FROM INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_SCHEMA = 'dbo' AND TABLE_TYPE = 'BASE TABLE'
        """
        results = db.execute_query(query)
        existing_tables = [row[0] for row in results]
        
        missing = set(expected_tables) - set(existing_tables)
        
        if missing:
            print(f"❌ Faltan tablas: {missing}")
            return False
        else:
            print(f"✅ Todas las tablas existen ({len(existing_tables)} tablas)")
            return True
            
    except Exception as e:
        print(f"❌ Error verificando tablas: {e}")
        return False


def test_pdf_parsing():
    """Test 3: Parsing de PDF."""
    print("\n" + "="*60)
    print("TEST 3: Parsing de PDF")
    print("="*60)
    
    # Buscar un PDF de prueba
    pdf_files = list(Path(INPUT_DIR).glob('*.pdf'))
    
    if not pdf_files:
        print(f"⚠️ No se encontraron PDFs en {INPUT_DIR}")
        return False
    
    test_pdf = pdf_files[0]
    print(f"Probando con: {test_pdf.name}")
    
    try:
        parser = PDFParser(str(test_pdf))
        
        # Extraer texto
        text = parser.extract_text(max_pages=2)
        if len(text) < 100:
            print("❌ Texto extraído muy corto")
            return False
        print(f"✅ Texto extraído: {len(text)} caracteres")
        
        # Extraer tablas
        tables = parser.extract_tables()
        if not tables:
            print("⚠️ No se extrajeron tablas (puede ser normal si PDF está mal formateado)")
        else:
            print(f"✅ Tablas extraídas: {len(tables)}")
        
        # Extraer OT
        ot_code = parser.extract_ot_code()
        if ot_code:
            print(f"✅ Código OT: {ot_code}")
        else:
            print("⚠️ No se pudo extraer código OT")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en parsing: {e}")
        return False


def test_sedimento_extraction():
    """Test 4: Extracción completa de sedimento."""
    print("\n" + "="*60)
    print("TEST 4: Extracción de Datos de Sedimento")
    print("="*60)
    
    # Buscar PDF de sedimento
    pdf_files = list(Path(INPUT_DIR).glob('*SEDIMENTO*.pdf'))
    
    if not pdf_files:
        pdf_files = list(Path(INPUT_DIR).glob('*.pdf'))
    
    if not pdf_files:
        print(f"⚠️ No se encontraron PDFs en {INPUT_DIR}")
        return False
    
    test_pdf = pdf_files[0]
    print(f"Probando con: {test_pdf.name}")
    
    try:
        extractor = SedimentoExtractor(str(test_pdf))
        data = extractor.extract()
        
        # Verificar metadata
        if not data.get('metadata'):
            print("❌ No se extrajo metadata")
            return False
        print(f"✅ Metadata extraída")
        print(f"   - Código OT: {data['metadata'].get('codigo_ot')}")
        print(f"   - Tipo monitoreo: {data['metadata'].get('tipo_monitoreo')}")
        print(f"   - Condición: {data['metadata'].get('condicion_centro')}")
        
        # Verificar ubicaciones
        if data.get('ubicacion'):
            print(f"✅ Ubicaciones: {len(data['ubicacion'])} estaciones")
        else:
            print("⚠️ No se extrajo ubicación")
        
        # Verificar MOT
        if data.get('materia_organica'):
            print(f"✅ MOT: {len(data['materia_organica'])} mediciones")
            
            # Mostrar estadísticas
            mot_values = [m['mot_porcentaje'] for m in data['materia_organica']]
            avg_mot = sum(mot_values) / len(mot_values)
            print(f"   - MOT promedio: {avg_mot:.2f}%")
            print(f"   - MOT mín: {min(mot_values):.2f}%")
            print(f"   - MOT máx: {max(mot_values):.2f}%")
        else:
            print("❌ No se extrajo MOT")
            return False
        
        # Verificar pH/Redox
        if data.get('ph_redox'):
            print(f"✅ pH/Redox: {len(data['ph_redox'])} mediciones")
        else:
            print("⚠️ No se extrajo pH/Redox")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en extracción: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_data_validation():
    """Test 5: Validación de datos extraídos."""
    print("\n" + "="*60)
    print("TEST 5: Validación de Datos")
    print("="*60)
    
    pdf_files = list(Path(INPUT_DIR).glob('*SEDIMENTO*.pdf'))
    if not pdf_files:
        pdf_files = list(Path(INPUT_DIR).glob('*.pdf'))
    
    if not pdf_files:
        print(f"⚠️ No se encontraron PDFs")
        return False
    
    test_pdf = pdf_files[0]
    
    try:
        extractor = SedimentoExtractor(str(test_pdf))
        data = extractor.extract()
        
        issues = []
        
        # Validar MOT
        for mot in data.get('materia_organica', []):
            mot_val = mot.get('mot_porcentaje')
            
            if mot_val is None:
                issues.append(f"MOT NULL en {mot.get('codigo_muestra')}")
            elif mot_val < 0 or mot_val > 100:
                issues.append(f"MOT fuera de rango (0-100): {mot_val}% en {mot.get('codigo_muestra')}")
            elif mot_val > 50:
                issues.append(f"⚠️ MOT muy alto: {mot_val}% en {mot.get('codigo_muestra')}")
        
        # Validar pH
        for pr in data.get('ph_redox', []):
            ph_val = pr.get('ph')
            
            if ph_val is None:
                issues.append(f"pH NULL en {pr.get('codigo_muestra')}")
            elif ph_val < 0 or ph_val > 14:
                issues.append(f"pH fuera de rango (0-14): {ph_val} en {pr.get('codigo_muestra')}")
        
        if issues:
            print(f"⚠️ Se encontraron {len(issues)} problemas:")
            for issue in issues[:10]:  # Mostrar máximo 10
                print(f"   - {issue}")
            if len(issues) > 10:
                print(f"   ... y {len(issues)-10} más")
        else:
            print("✅ Todos los datos están en rangos válidos")
        
        return len([i for i in issues if not i.startswith('⚠️')]) == 0
        
    except Exception as e:
        print(f"❌ Error en validación: {e}")
        return False


def test_database_insert():
    """Test 6: Inserción en base de datos (crear y eliminar)."""
    print("\n" + "="*60)
    print("TEST 6: Inserción en Base de Datos (Test)")
    print("="*60)
    
    try:
        # Crear centro de prueba
        test_codigo = f"TEST_{int(Path(__file__).stat().st_mtime)}"
        
        centro_id = db.get_or_create_centro(
            codigo=test_codigo,
            nombre="Centro de Prueba",
            es_censurado=False
        )
        print(f"✅ Centro de prueba creado: ID {centro_id}")
        
        # Verificar que existe
        result = db.execute_query(
            "SELECT nombre_centro FROM centros WHERE centro_id = ?",
            (centro_id,)
        )
        
        if result and result[0][0] == "Centro de Prueba":
            print("✅ Centro verificado en BD")
        else:
            print("❌ Centro no encontrado en BD")
            return False
        
        # Eliminar centro de prueba
        db.execute_non_query(
            "DELETE FROM centros WHERE centro_id = ?",
            (centro_id,)
        )
        print("✅ Centro de prueba eliminado")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en inserción: {e}")
        return False


def run_all_tests():
    """Ejecuta todos los tests."""
    print("\n" + "🧪 " + "="*58)
    print("   SUITE DE PRUEBAS DEL SISTEMA")
    print("   " + "="*58)
    
    tests = [
        ("Conexión a BD", test_database_connection),
        ("Tablas de BD", test_database_tables),
        ("Parsing de PDF", test_pdf_parsing),
        ("Extracción Sedimento", test_sedimento_extraction),
        ("Validación de Datos", test_data_validation),
        ("Inserción en BD", test_database_insert),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"\n❌ Test '{test_name}' falló con excepción: {e}")
            results[test_name] = False
    
    # Resumen final
    print("\n" + "="*60)
    print("RESUMEN DE PRUEBAS")
    print("="*60)
    
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print("-"*60)
    print(f"Total: {passed}/{total} pruebas pasadas ({passed/total*100:.1f}%)")
    print("="*60)
    
    if passed == total:
        print("\n🎉 ¡Todos los tests pasaron! Sistema listo para usar.")
        return 0
    else:
        print(f"\n⚠️ {total-passed} test(s) fallaron. Revisar errores arriba.")
        return 1


if __name__ == '__main__':
    sys.exit(run_all_tests())
