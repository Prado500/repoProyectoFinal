import pandas as pd
import numpy as np
import os
import re


def normalizar_texto(texto):
    """Normaliza texto para comparaciones más robustas"""
    if pd.isna(texto):
        return ""
    return str(texto).lower().strip()


def cargar_y_combinar_datos(archivos):
    """Carga y combina todos los archivos CSV en un solo DataFrame"""
    dfs = []
    for archivo in archivos:
        if os.path.exists(archivo):
            encodings = ["latin-1", "ISO-8859-1", "utf-8"]
            separadores = [";", ","]

            cargado = False
            for encoding in encodings:
                if cargado:
                    break
                for sep in separadores:
                    try:
                        df = pd.read_csv(archivo, encoding=encoding, sep=sep)
                        if len(df.columns) > 1:
                            dfs.append(df)
                            print(
                                f"✓ {archivo} cargado con encoding {encoding} y separador '{sep}'"
                            )
                            cargado = True
                            break
                    except (UnicodeDecodeError, pd.errors.ParserError):
                        continue
            if not cargado:
                print(
                    f"✗ No se pudo cargar {archivo} con ninguna combinación de encoding/separador"
                )
        else:
            print(f"Advertencia: No se encontró el archivo {archivo}")

    if not dfs:
        raise Exception("No se pudieron cargar ninguno de los archivos")

    return pd.concat(dfs, ignore_index=True)


def identificar_columnas(df):
    """Identifica automáticamente los nombres de las columnas clave"""
    columnas = df.columns.tolist()
    print("Columnas disponibles:", columnas)

    doc_posibles = [
        "Documento",
        "documento",
        "DOCUMENTO",
        "NumeroDocumento",
        "NroDocumento",
    ]
    for doc in doc_posibles:
        if doc in columnas:
            doc_col = doc
            break
    else:
        for col in columnas:
            if "doc" in col.lower() or "id" in col.lower() or "numero" in col.lower():
                doc_col = col
                break
        else:
            doc_col = columnas[1] if len(columnas) > 1 else columnas[0]

    med_posibles = [
        "Medicamento",
        "medicamento",
        "MEDICAMENTO",
        "MedicamentoNombre",
        "NombreMedicamento",
    ]
    for med in med_posibles:
        if med in columnas:
            med_col = med
            break
    else:
        for col in columnas:
            if (
                "medic" in col.lower()
                or "drug" in col.lower()
                or "farma" in col.lower()
            ):
                med_col = col
                break
        else:
            med_col = columnas[4] if len(columnas) > 4 else columnas[2]

    print(f"Usando columna para documento: {doc_col}")
    print(f"Usando columna para medicamento: {med_col}")

    return doc_col, med_col


def buscar_medicamentos_exactos(texto_medicamento):
    """Busca EXACTAMENTE los medicamentos de interés en el texto, evitando falsos positivos"""
    texto = normalizar_texto(texto_medicamento)

    # Diccionario de medicamentos con sus nombres EXACTOS y grupos
    medicamentos_exactos = {
        # GRUPO ESPECIAL
        "metoprolol": "GE_metoprolol",
        "propranolol": "GE_metoprolol",
        "propanolol": "GE_metoprolol",
        "hidroclorotiazida": "GE_hidroclorotiazida",
        # ARA II
        "irbesartan": "ARA_II",
        "valsartan": "ARA_II",
        "olmesartan": "ARA_II",
        "telmisartan": "ARA_II",
        "losartan": "ARA_II",
        # IECA
        "enalapril": "IECA",
        "captopril": "IECA",
        "perindopril": "IECA",
        # Calcioantagonistas
        "amlodipino": "Calcioantagonistas",
        "nifedipino": "Calcioantagonistas",
        "verapamilo": "Calcioantagonistas",
        # Otros diuréticos
        "espironolactona": "Otros_diuréticos",
        "furosemida": "Otros_diuréticos",
        "indapamida": "Otros_diuréticos",
        "clortalidona": "Otros_diuréticos",
        # Otros Beta-Bloqueadores
        "bisoprolol": "Otros_Beta_Bloqueadores",
        "carvedilol": "Otros_Beta_Bloqueadores",
        "nebivolol": "Otros_Beta_Bloqueadores",
        # Otros antihipertensivos
        "minoxidil": "Otros_antihipertensivos",
        "prazosina": "Otros_antihipertensivos",
        "clonidina": "Otros_antihipertensivos",
    }

    grupos_encontrados = set()

    # Buscar cada medicamento EXACTAMENTE en el texto
    for medicamento, grupo in medicamentos_exactos.items():
        # Usar regex para buscar la palabra completa, evitando subcadenas
        if re.search(r"\b" + re.escape(medicamento) + r"\b", texto):
            grupos_encontrados.add(grupo)

    return list(grupos_encontrados)


def tiene_medicamento_x(texto_medicamento, grupos_encontrados):
    """Determina si hay medicamentos X adicionales de manera más inteligente"""
    texto = normalizar_texto(texto_medicamento)

    # Lista de palabras comunes en descripciones de medicamentos (NO son medicamentos X)
    palabras_no_x = {
        "mg", "mcg", "g", "ml", "l", "cc", "tableta", "tabletas", "comprimido", "comprimidos",
        "capsula", "capsulas", "cápsula", "cápsulas", "gragea", "grageas", "inyección", "ampolla",
        "frasco", "sobre", "suspension", "suspensión", "jarabe", "crema", "pomada", "supositorio",
        "spray", "inhalador", "parche", "ungüento", "oral", "intramuscular", "intravenoso",
        "subcutaneo", "subcutáneo", "topico", "tópico", "rectal", "vaginal", "oftalmico", "oftálmico",
        "otico", "ótico", "nasal", "cada", "horas", "día", "dias", "semana", "semanas", "mes", "meses",
        "año", "años", "dosis", "frecuencia", "tratamiento", "tomar", "aplicar", "uso", "adultos",
        "niños", "pacientes", "administrar", "via", "cad", "diaria", "semanal", "mensual", "anual",
        "continuo", "alternos", "mg", "mcg", "g", "ml", "l", "cc", "ui", "unidad", "unidades",
        "por", "con", "sin", "de", "la", "el", "y", "o", "para", "entre", "hasta", "desde", "sobre",
        "bajo", "tras", "durante", "antes", "después", "al", "del", "se", "es", "en", "a", "u", "un",
        "una", "unos", "unas", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve",
        "diez", "cien", "mil", "medio", "media", "cuarto", "cuarta", "primera", "segunda", "tercera",
        "tartrato", "bloqueadores", "antihipertensivos", "diuréticos", "bloqueador", "antihipertensivo",
        "diurético", "calcioantagonistas", "calcioantagonista", "hidroclorotiazida", "clorhidrato",
        "maleato", "succinato", "besilato", "valsartan", "irbesartan", "telmisartan", "olmesartan",
        "losartan", "enalapril", "captopril", "perindopril", "amlodipino", "nifedipino", "verapamilo",
        "espironolactona", "furosemida", "indapamida", "clortalidona", "bisoprolol", "carvedilol",
        "nebivolol", "minoxidil", "prazosina", "clonidina", "metoprolol", "propranolol", "propanolol",
    }

    # Remover los medicamentos encontrados
    texto_limpio = texto
    for grupo in grupos_encontrados:
        medicamentos_grupo = {
            "GE_metoprolol": ["metoprolol", "propranolol", "propanolol"],
            "GE_hidroclorotiazida": ["hidroclorotiazida"],
            "ARA_II": ["irbesartan", "valsartan", "olmesartan", "telmisartan", "losartan"],
            "IECA": ["enalapril", "captopril", "perindopril"],
            "Calcioantagonistas": ["amlodipino", "nifedipino", "verapamilo"],
            "Otros_diuréticos": ["espironolactona", "furosemida", "indapamida", "clortalidona"],
            "Otros_Beta_Bloqueadores": ["bisoprolol", "carvedilol", "nebivolol"],
            "Otros_antihipertensivos": ["minoxidil", "prazosina", "clonidina"],
        }

        if grupo in medicamentos_grupo:
            for med in medicamentos_grupo[grupo]:
                texto_limpio = re.sub(r"\b" + re.escape(med) + r"\b", "", texto_limpio)

    # Remover palabras no-X y números, buscar palabras de 4+ letras
    palabras = re.findall(r"[a-zA-Z]{4,}", texto_limpio)  # Solo palabras de 4+ letras
    palabras_filtradas = [p for p in palabras if p not in palabras_no_x]

    # También verificar si hay signos de múltiples medicamentos (+, &, "y", "con")
    tiene_multiples = bool(re.search(r"\+|\&| y | con |/\s*[a-zA-Z]", texto))

    return len(palabras_filtradas) > 0 or tiene_multiples


def determinar_categorizacion_por_registro(medicamento_str):
    """Determina la categorización INDIVIDUAL para CADA REGISTRO - VERSIÓN MEJORADA"""
    # Buscar grupos de medicamentos EXACTOS
    grupos = buscar_medicamentos_exactos(medicamento_str)

    # Si no hay medicamentos de interés, no procesar
    if not grupos:
        return "NO_APLICA"

    # Determinar si hay medicamento X
    hay_x = tiene_medicamento_x(medicamento_str, grupos)

    # Mapeo de nombres internos a nombres de categorización
    mapeo_categorias = {
        "GE_metoprolol": "GE metoprolol",
        "GE_hidroclorotiazida": "GE Hidroclorotiazida",
        "ARA_II": "ARA II",
        "IECA": "IECA",
        "Calcioantagonistas": "Calcioantagonistas",
        "Otros_diuréticos": "Otros diuréticos",
        "Otros_Beta_Bloqueadores": "Otros Beta-Bloqueadores",
        "Otros_antihipertensivos": "Otros Anti-Hipertensivos",
    }

    # Convertir grupos internos a nombres de categoría
    grupos_categoria = [mapeo_categorias[grupo] for grupo in grupos]

    # ORDEN JERÁRQUICO DE GRUPOS
    orden_jerarquico = [
        "GE metoprolol",
        "GE Hidroclorotiazida", 
        "ARA II",
        "IECA",
        "Calcioantagonistas",
        "Otros diuréticos",
        "Otros Beta-Bloqueadores",
        "Otros Anti-Hipertensivos"
    ]

    # Separar grupos especiales y ordenar todos los grupos por jerarquía
    grupos_especiales = [g for g in grupos_categoria if g.startswith("GE ")]
    grupos_no_especiales = [g for g in grupos_categoria if not g.startswith("GE ")]
    
    # Ordenar grupos por jerarquía
    grupos_ordenados = []
    for grupo in orden_jerarquico:
        if grupo in grupos_especiales or grupo in grupos_no_especiales:
            grupos_ordenados.append(grupo)

    # REGLAS DE CATEGORIZACIÓN MEJORADAS PARA MÚLTIPLES MEDICAMENTOS

    # Caso 1: Solo un grupo de interés
    if len(grupos_ordenados) == 1:
        if hay_x:
            return f"{grupos_ordenados[0]}-X univ"
        else:
            return f"{grupos_ordenados[0]} univ"

    # Caso 2: Múltiples grupos de interés
    else:
        # Construir etiqueta base uniendo grupos ordenados
        etiqueta_base = " && ".join(grupos_ordenados)
        
        # Manejar grupos especiales en múltiples combinaciones
        if any(g.startswith("GE ") for g in grupos_ordenados):
            # Si hay GE, verificar combinaciones específicas
            tiene_ge_metoprolol = "GE metoprolol" in grupos_ordenados
            tiene_ge_hidro = "GE Hidroclorotiazida" in grupos_ordenados
            
            # Remover "GE " de los nombres para construcción especial
            grupos_sin_ge = [g.replace("GE ", "") for g in grupos_ordenados if g.startswith("GE ")]
            grupos_no_ge = [g for g in grupos_ordenados if not g.startswith("GE ")]
            
            if tiene_ge_metoprolol and tiene_ge_hidro:
                # Caso GE Hidro-Meto con otros grupos
                if grupos_no_ge:
                    etiqueta_base = f"GE Hidro-Meto && {' && '.join(grupos_no_ge)}"
                else:
                    etiqueta_base = "GE Hidro-Meto"
            elif tiene_ge_metoprolol:
                # Caso GE Meto con otros grupos
                if grupos_no_ge:
                    etiqueta_base = f"GE Meto && {' && '.join(grupos_no_ge)}"
                else:
                    etiqueta_base = "GE Meto"
            elif tiene_ge_hidro:
                # Caso GE Hidro con otros grupos
                if grupos_no_ge:
                    etiqueta_base = f"GE Hidro && {' && '.join(grupos_no_ge)}"
                else:
                    etiqueta_base = "GE Hidro"

        # Añadir X si existe
        if hay_x:
            return f"{etiqueta_base} - X"
        else:
            return etiqueta_base


def es_registro_de_interes(medicamento_str):
    """Determina si un registro contiene al menos un medicamento de interés"""
    grupos = buscar_medicamentos_exactos(medicamento_str)
    return len(grupos) > 0


def procesar_csv_por_registro(df, doc_col, med_col):
    """Procesa CADA REGISTRO individualmente y genera el CSV de salida"""
    registros_procesados = []

    print(f"Procesando {len(df)} registros individualmente...")
    registros_con_interes = 0

    for indice, fila in df.iterrows():
        medicamento = fila[med_col]

        # SOLO procesar si el registro tiene medicamentos de interés
        if es_registro_de_interes(medicamento):
            registros_con_interes += 1

            # Crear copia del registro
            registro_procesado = fila.to_dict()

            # Asignar categorización INDIVIDUAL para este registro
            categoria = determinar_categorizacion_por_registro(medicamento)
            registro_procesado["Categorización"] = categoria

            registros_procesados.append(registro_procesado)

    print(f"Registros con medicamentos de interés: {registros_con_interes}")
    return registros_procesados


def main():
    """Función principal"""
    archivos = [
        "full_size/Antihipertensivos1.csv",
        "full_size/Antihipertensivos2.csv",
        "full_size/OtrosMedicamentos.csv",
    ]

    try:
        print("Cargando y combinando datos desde CSV...")
        df_completo = cargar_y_combinar_datos(archivos)

        print("\nIdentificando columnas...")
        doc_col, med_col = identificar_columnas(df_completo)

        print("Procesando registros INDIVIDUALMENTE...")
        registros_finales = procesar_csv_por_registro(df_completo, doc_col, med_col)

        # Crear DataFrame final
        if registros_finales:
            df_final = pd.DataFrame(registros_finales)

            # Reordenar columnas para que 'Categorización' esté al final
            if "Categorización" in df_final.columns:
                columnas = [
                    col for col in df_final.columns if col != "Categorización"
                ] + ["Categorización"]
                df_final = df_final[columnas]

            # Guardar el archivo final
            archivo_salida = "registros_clasificados_por_medicamento_final.csv"
            df_final.to_csv(archivo_salida, index=False, encoding="utf-8-sig", sep=";")

            print(f"\n=== PROCESO COMPLETADO CON ÉXITO ===")
            print(f"Archivo generado: {archivo_salida}")
            print(f"Total de registros procesados: {len(df_final)}")

            # Mostrar resumen de categorizaciones
            print(f"\nResumen de categorizaciones POR REGISTRO:")
            categorias_count = df_final["Categorización"].value_counts()
            for categoria, count in categorias_count.items():
                print(f"  {categoria}: {count} registros")

            print(f"\nTotal de categorías únicas: {len(categorias_count)}")

        else:
            print("No se encontraron registros con medicamentos de interés")

    except Exception as e:
        print(f"Error durante la ejecución: {str(e)}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()