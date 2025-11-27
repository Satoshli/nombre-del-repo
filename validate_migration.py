"""
Script de validación post-migración.
Verifica que todos los componentes funcionen correctamente.
"""

import sys
from pathlib import Path
from typing import List, Tuple

def check_imports() -> Tuple[bool, List[str]]:
    """Verifica que todos los módulos se puedan importar."""
    print("\n" + "="*60)
    print("1️⃣  VERIFICANDO IMPORTS")
    print("="*60)
    
    errors = []
    modules = [
        ('config.patterns', 'Configuración de patrones'),
        ('config.database', 'Configuración de BD'),
        ('config.settings', 'Settings generales'),
        ('core.pdf_reader', 'Lector de PDF'),
        ('core.metadata', 'Extractor de metadatos'),
        ('extractors.sedimento', 'Extractor de sedimento'),
        ('loaders.database_loader', 'Cargador a BD'),
    ]
    
    for module_name, description in modules:
        try:
            __import__(module_name)
            print(f"✅ {description:30s} ({module_name})")
        except ImportError as e:
            error = f"❌ {description}: {e}"
            print(error)
            errors.append(error)
    
    return len(errors) == 0, errors


def check_file_structure() -> Tuple[bool, List[str]]:
    """Verifica que existan todos los archivos necesarios."""
    print("\n" + "="*60)
    print("2️⃣  VERIFICANDO ESTRUCTURA DE ARCHIVOS")
    print("="*60)
    
    errors = []
    required_files = [
        'config/patterns.py',
        'core/__init__.py',
        'core/pdf_reader.py',
        'core/metadata.py',
        'extractors/sedimento.py',
        'loaders/__init__.py',
        'loaders/database_loader.py',
        'main.py',
    ]
    
    obsolete_files = [
        'utils/pdf_parser.py',
        'utils/normalizadores.py',
        'utils/ocr_metadata_extractor.py',
        'utils/pdf_text_extractor.py',
        'config/extractor_config.py',
        'extractors/base_extractor.py',
    ]
    
    # Verificar archivos requeridos
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"✅ {file_path}")
        else:
            error = f"❌ Falta: {file_path}"
            print(error)
            errors.append(error)
    
    # Verificar archivos obsoletos (deben NO existir)
    print("\n⚠️  Verificando archivos obsoletos (deben estar eliminados):")
    for file_path in obsolete_files:
        if Path(file_path).exists():
            warning = f"⚠️  Todavía existe (debería eliminarse): {file_path}"
            print(warning)
            errors.append(warning)
        else:
            print(f"✅ Eliminado: {file_path}")
    
    return len(errors) == 0, errors


def check_database() -> Tuple[bool, List[str]]:
    """Verifica conexión y estructura de BD."""
    print("\n" + "="*60)
    print("3️⃣  VERIFICANDO BASE DE DATOS")
    print("="*60)
    
    errors = []
    
    try:
        from config.database import db
        
        # Test conexión
        if db.test_connection():
            print("✅ Conexión a BD exitosa")
            print(f"   Ubicación: {db.db_path}")
        else:
            error = "❌ No se pudo conectar a BD"
            print(error)
            errors.append(error)
            return False, errors
        
        # Verificar tablas
        tables = db.get_all_tables()
        expected_tables = [
            'centros',
            'ordenes_trabajo',
            'sedimento_estaciones',
            'sedimento_materia_organica',
            'sedimento_ph_redox',
        ]
        
        print(f"\n✅ Total de tablas: {len(tables)}")
        
        for table in expected_tables:
            if table in tables:
                count = db.get_table_count(table)
                print(f"   ✅ {table}: {count} registros")
            else:
                error = f"   ❌ Falta tabla: {table}"
                print(error)
                errors.append(error)
        
    except Exception as e:
        error = f"❌ Error verificando BD: {e}"
        print(error)
        errors.append(error)
    
    return len(errors) == 0, errors


def check_patterns_config() -> Tuple[bool, List[str]]:
    """Verifica que la configuración de patrones esté correcta."""
    print("\n" + "="*60)
    print("4️⃣  VERIFICANDO CONFIGURACIÓN DE PATRONES")
    print("="*60)
    
    errors = []
    
    try:
        from config import patterns
        
        # Verificar que existan las constantes principales
        required_attrs = [
            'METADATA_PATTERNS',
            'SAMPLE_CODE_PATTERNS',
            'REPORT_TYPE_KEYWORDS',
            'VALIDATION_RANGES',
            'REGULATORY_LIMITS',
        ]
        
        for attr in required_attrs:
            if hasattr(patterns, attr):
                value = getattr(patterns, attr)
                print(f"✅ {attr}: {len(value)} entradas")
            else:
                error = f"❌ Falta constante: {attr}"
                print(error)
                errors.append(error)
        
    except Exception as e:
        error = f"❌ Error verificando patrones: {e}"
        print(error)
        errors.append(error)
    
    return len(errors) == 0, errors


def check_pdf_reader() -> Tuple[bool, List[str]]:
    """Verifica que el PDFReader funcione."""
    print("\n" + "="*60)
    print("5️⃣  VERIFICANDO PDF READER")
    print("="*60)
    
    errors = []
    
    try:
        from core.pdf_reader import PDFReader
        
        # Buscar un PDF de prueba
        pdf_files = list(Path('data/pdfs').glob('*.pdf'))
        
        if not pdf_files:
            error = "⚠️  No hay PDFs de prueba en data/pdfs"
            print(error)
            errors.append(error)
            return False, errors
        
        test_pdf = str(pdf_files[0])
        print(f"📄 Probando con: {Path(test_pdf).name}")
        
        reader = PDFReader(test_pdf)
        
        # Test número de páginas
        num_pages = reader.get_page_count()
        print(f"   ✅ Páginas detectadas: {num_pages}")
        
        # Test extracción de texto
        textos = reader.extract_all_pages_text()
        print(f"   ✅ Páginas con texto: {len([t for t in textos if t])}")
        
        if not textos or not any(textos):
            error = "   ⚠️  No se extrajo texto"
            print(error)
            errors.append(error)
        
    except Exception as e:
        error = f"❌ Error en PDFReader: {e}"
        print(error)
        errors.append(error)
    
    return len(errors) == 0, errors


def check_metadata_extractor() -> Tuple[bool, List[str]]:
    """Verifica que el MetadataExtractor funcione."""
    print("\n" + "="*60)
    print("6️⃣  VERIFICANDO METADATA EXTRACTOR")
    print("="*60)
    
    errors = []
    
    try:
        from core.pdf_reader import PDFReader
        from core.metadata import MetadataExtractor
        
        pdf_files = list(Path('data/pdfs').glob('*.pdf'))
        
        if not pdf_files:
            return False, ["No hay PDFs de prueba"]
        
        test_pdf = str(pdf_files[0])
        print(f"📄 Probando con: {Path(test_pdf).name}")
        
        reader = PDFReader(test_pdf)
        textos = reader.extract_all_pages_text()
        
        metadatos = MetadataExtractor.extract_all(test_pdf, textos, debug=False)
        
        # Verificar campos extraídos
        campos_esperados = ['codigo_ot', 'tipo_monitoreo', 'condicion_centro']
        
        for campo in campos_esperados:
            valor = metadatos.get(campo)
            if valor:
                print(f"   ✅ {campo}: {valor}")
            else:
                warning = f"   ⚠️  {campo} no extraído"
                print(warning)
        
    except Exception as e:
        error = f"❌ Error en MetadataExtractor: {e}"
        print(error)
        errors.append(error)
    
    return len(errors) == 0, errors


def run_full_validation():
    """Ejecuta todas las validaciones."""
    print("\n" + "🔍 " + "="*58)
    print("   VALIDACIÓN POST-MIGRACIÓN")
    print("   " + "="*58)
    
    all_results = []
    
    # Ejecutar todas las verificaciones
    checks = [
        check_imports,
        check_file_structure,
        check_database,
        check_patterns_config,
        check_pdf_reader,
        check_metadata_extractor,
    ]
    
    for check in checks:
        success, errors = check()
        all_results.append((check.__name__, success, errors))
    
    # Resumen final
    print("\n" + "="*60)
    print("📊 RESUMEN DE VALIDACIÓN")
    print("="*60)
    
    total_checks = len(all_results)
    passed_checks = sum(1 for _, success, _ in all_results if success)
    
    for check_name, success, errors in all_results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {check_name.replace('check_', '').replace('_', ' ').title()}")
        
        if errors:
            for error in errors[:3]:  # Mostrar máximo 3 errores
                print(f"      {error}")
            if len(errors) > 3:
                print(f"      ... y {len(errors)-3} errores más")
    
    print("-" * 60)
    print(f"Total: {passed_checks}/{total_checks} verificaciones pasadas")
    print("=" * 60)
    
    if passed_checks == total_checks:
        print("\n🎉 ¡MIGRACIÓN EXITOSA! Sistema listo para usar.")
        return 0
    else:
        print(f"\n⚠️  {total_checks - passed_checks} verificación(es) fallaron.")
        print("   Revisa los errores arriba y corrígelos.")
        return 1


if __name__ == '__main__':
    sys.exit(run_full_validation())
