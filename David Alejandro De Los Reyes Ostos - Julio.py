import pandas as pd
import numpy as np
from collections import defaultdict
import os

def normalizar_texto(texto):
    """Normaliza texto para comparaciones más robustas"""
    if pd.isna(texto):
        return ""
    return str(texto).lower().strip()

def cargar_y_combinar_datos(archivos):
    """Carga y combina todos los archivos Excel en un solo DataFrame"""
    dfs = []
    for archivo in archivos:
        if os.path.exists(archivo):
            df = pd.read_excel(archivo)
            dfs.append(df)
        else:
            print(f"Advertencia: No se encontró el archivo {archivo}")

    if not dfs:
        raise Exception("No se pudieron cargar ninguno de los archivos")

    return pd.concat(dfs, ignore_index=True)

def identificar_medicamentos(medicamento_str):
    """Identifica a qué grupos pertenece un medicamento"""
    medicamento = normalizar_texto(medicamento_str)

    grupos = {
        # MEDICAMENTOS DE INTERÉS PRINCIPAL
        'metoprolol': ['metoprolol'],
        'propranolol': ['propranolol', 'propanolol'],
        'hidroclorotiazida': ['hidroclorotiazida'],

        # GRUPOS EXCLUIDOS
        'ARA_II': ['irbesartan', 'valsartan', 'olmesartan', 'telmisartan', 'losartan'],
        'IECA': ['enalapril', 'captopril', 'perindopril'],
        'calcioantagonistas': ['amlodipino', 'nifedipino', 'verapamilo'],
        'diureticos_otros': ['espironolactona', 'furosemida', 'indapamida', 'clortalidona'],
        'beta_bloqueadores_otros': ['bisoprolol', 'carvedilol', 'nebivolol'],
        'otros_antihipertensivos': ['minoxidil', 'prazosina', 'clonidina']
    }

    medicamentos_identificados = []
    for grupo, palabras_clave in grupos.items():
        for palabra in palabras_clave:
            if palabra in medicamento:
                medicamentos_identificados.append(grupo)
                break

    return medicamentos_identificados

def procesar_pacientes(df):
    """Procesa el DataFrame para identificar medicamentos por paciente"""
    # Agrupar por documento del paciente
    pacientes_medicamentos = defaultdict(set)
    pacientes_info = {}

    for _, fila in df.iterrows():
        documento = fila['Documento']
        medicamento = fila['Medicamento']

        # Guardar información del paciente (usamos la primera aparición)
        if documento not in pacientes_info:
            pacientes_info[documento] = {
                'nombres': f"{fila.get('Nom1PAc', '')} {fila.get('Nom2Pac', '')}".strip(),
                'apellidos': f"{fila.get('Apell1Pac', '')} {fila.get('Apell2Pac', '')}".strip(),
                'fecha_nacimiento': fila.get('Fechnac', ''),
                'sexo': fila.get('Sexo', '')
            }

        # Identificar medicamentos
        grupos_medicamento = identificar_medicamentos(medicamento)
        for grupo in grupos_medicamento:
            pacientes_medicamentos[documento].add(grupo)

    return pacientes_medicamentos, pacientes_info

def segregar_pacientes(pacientes_medicamentos):
    """Segrega pacientes según los criterios especificados"""

    # 1. Pacientes que toman SOLO Metoprolol/Propranolol/Hidroclorotiazida sin otros antihipertensivos
    grupos_excluidos = {
        'ARA_II', 'IECA', 'calcioantagonistas', 'diureticos_otros',
        'beta_bloqueadores_otros', 'otros_antihipertensivos'
    }

    pacientes_exclusivos_interes = []
    pacientes_combinados_interes = []

    for doc, medicamentos in pacientes_medicamentos.items():
        tiene_interes = any(m in medicamentos for m in ['metoprolol', 'propranolol', 'hidroclorotiazida'])
        tiene_excluidos = any(m in medicamentos for m in grupos_excluidos)

        if tiene_interes:
            if not tiene_excluidos:
                pacientes_exclusivos_interes.append(doc)
            else:
                pacientes_combinados_interes.append(doc)

    # 2. Pacientes por grupo exclusivo
    grupos_medicamentos = {
        'ARA_II': ['ARA_II'],
        'IECA': ['IECA'],
        'calcioantagonistas': ['calcioantagonistas'],
        'diureticos_otros': ['diureticos_otros'],
        'beta_bloqueadores_otros': ['beta_bloqueadores_otros'],
        'otros_antihipertensivos': ['otros_antihipertensivos']
    }

    pacientes_por_grupo_exclusivo = {}
    pacientes_por_grupo_combinado = {}

    for nombre_grupo, grupos in grupos_medicamentos.items():
        exclusivos = []
        combinados = []

        for doc, medicamentos in pacientes_medicamentos.items():
            tiene_grupo = any(g in medicamentos for g in grupos)
            otros_medicamentos = medicamentos - set(grupos)

            if tiene_grupo:
                if len(otros_medicamentos) == 0:
                    exclusivos.append(doc)
                else:
                    combinados.append(doc)

        pacientes_por_grupo_exclusivo[nombre_grupo] = exclusivos
        pacientes_por_grupo_combinado[nombre_grupo] = combinados

    return {
        'exclusivos_interes': pacientes_exclusivos_interes,
        'combinados_interes': pacientes_combinados_interes,
        'por_grupo_exclusivo': pacientes_por_grupo_exclusivo,
        'por_grupo_combinado': pacientes_por_grupo_combinado,
        'todos_pacientes': pacientes_medicamentos
    }

def generar_reportes(resultados, pacientes_info, archivo_salida="reporte_pacientes.xlsx"):
    """Genera reportes en Excel con los resultados"""

    with pd.ExcelWriter(archivo_salida, engine='openpyxl') as writer:

        # 1. Pacientes exclusivos de interés
        datos = []
        for doc in resultados['exclusivos_interes']:
            info = pacientes_info.get(doc, {})
            datos.append({
                'Documento': doc,
                'Nombres': info.get('nombres', ''),
                'Apellidos': info.get('apellidos', ''),
                'Fecha_Nacimiento': info.get('fecha_nacimiento', ''),
                'Sexo': info.get('sexo', ''),
                'Grupo': 'Metoprolol/Propranolol/Hidroclorotiazida EXCLUSIVO'
            })

        df_exclusivos = pd.DataFrame(datos)
        if not df_exclusivos.empty:
            df_exclusivos.to_excel(writer, sheet_name='Exclusivos_Interes', index=False)

        # 2. Pacientes combinados de interés
        datos = []
        for doc in resultados['combinados_interes']:
            info = pacientes_info.get(doc, {})
            medicamentos = resultados['todos_pacientes'].get(doc, set())
            datos.append({
                'Documento': doc,
                'Nombres': info.get('nombres', ''),
                'Apellidos': info.get('apellidos', ''),
                'Fecha_Nacimiento': info.get('fecha_nacimiento', ''),
                'Sexo': info.get('sexo', ''),
                'Medicamentos': ', '.join(medicamentos)
            })

        df_combinados = pd.DataFrame(datos)
        if not df_combinados.empty:
            df_combinados.to_excel(writer, sheet_name='Combinados_Interes', index=False)

        # 3. Pacientes por grupo exclusivo
        for grupo, documentos in resultados['por_grupo_exclusivo'].items():
            datos = []
            for doc in documentos:
                info = pacientes_info.get(doc, {})
                datos.append({
                    'Documento': doc,
                    'Nombres': info.get('nombres', ''),
                    'Apellidos': info.get('apellidos', ''),
                    'Fecha_Nacimiento': info.get('fecha_nacimiento', ''),
                    'Sexo': info.get('sexo', ''),
                    'Grupo': f'{grupo} EXCLUSIVO'
                })

            df_grupo = pd.DataFrame(datos)
            if not df_grupo.empty:
                # Limitar nombre de hoja a 31 caracteres
                nombre_hoja = f"Excl_{grupo}"[:31]
                df_grupo.to_excel(writer, sheet_name=nombre_hoja, index=False)

        # 4. Pacientes por grupo combinado
        for grupo, documentos in resultados['por_grupo_combinado'].items():
            datos = []
            for doc in documentos:
                info = pacientes_info.get(doc, {})
                medicamentos = resultados['todos_pacientes'].get(doc, set())
                datos.append({
                    'Documento': doc,
                    'Nombres': info.get('nombres', ''),
                    'Apellidos': info.get('apellidos', ''),
                    'Fecha_Nacimiento': info.get('fecha_nacimiento', ''),
                    'Sexo': info.get('sexo', ''),
                    'Medicamentos': ', '.join(medicamentos)
                })

            df_grupo = pd.DataFrame(datos)
            if not df_grupo.empty:
                # Limitar nombre de hoja a 31 caracteres
                nombre_hoja = f"Comb_{grupo}"[:31]
                df_grupo.to_excel(writer, sheet_name=nombre_hoja, index=False)

        # 5. Resumen general
        resumen_datos = []
        total_pacientes = len(resultados['todos_pacientes'])

        resumen_datos.append({
            'Categoría': 'Total pacientes únicos',
            'Cantidad': total_pacientes
        })

        resumen_datos.append({
            'Categoría': 'Pacientes Metoprolol/Propranolol/Hidroclorotiazida EXCLUSIVO',
            'Cantidad': len(resultados['exclusivos_interes'])
        })

        resumen_datos.append({
            'Categoría': 'Pacientes Metoprolol/Propranolol/Hidroclorotiazida COMBINADO',
            'Cantidad': len(resultados['combinados_interes'])
        })

        for grupo in resultados['por_grupo_exclusivo']:
            resumen_datos.append({
                'Categoría': f'Pacientes {grupo} EXCLUSIVO',
                'Cantidad': len(resultados['por_grupo_exclusivo'][grupo])
            })

        for grupo in resultados['por_grupo_combinado']:
            resumen_datos.append({
                'Categoría': f'Pacientes {grupo} COMBINADO',
                'Cantidad': len(resultados['por_grupo_combinado'][grupo])
            })

        df_resumen = pd.DataFrame(resumen_datos)
        df_resumen.to_excel(writer, sheet_name='Resumen_General', index=False)

    print(f"Reporte generado exitosamente: {archivo_salida}")

def main():
    """Función principal"""
    # Lista de archivos a procesar
    archivos = [
        "Antihipertensivos1_shrinked.xlsx",
        "Antihipertensivos2_shrinked.xlsx",
        "OtrosMedicamentos_shrinked.xlsx"
    ]

    try:
        print("Cargando y combinando datos...")
        df_completo = cargar_y_combinar_datos(archivos)

        print("Procesando pacientes y medicamentos...")
        pacientes_medicamentos, pacientes_info = procesar_pacientes(df_completo)

        print("Segregando pacientes según criterios...")
        resultados = segregar_pacientes(pacientes_medicamentos)

        print("Generando reportes...")
        generar_reportes(resultados, pacientes_info)

        print("\n=== RESUMEN EJECUTADO CON ÉXITO ===")
        print(f"Total pacientes procesados: {len(pacientes_medicamentos)}")
        print(f"Pacientes con Metoprolol/Propranolol/Hidroclorotiazida exclusivo: {len(resultados['exclusivos_interes'])}")
        print(f"Pacientes con Metoprolol/Propranolol/Hidroclorotiazida combinado: {len(resultados['combinados_interes'])}")

    except Exception as e:
        print(f"Error durante la ejecución: {str(e)}")
        raise

if __name__ == "__main__":
    main()