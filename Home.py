import streamlit as st
import pandas as pd
import os
from datetime import datetime

# 1. Configuração inicial da página
st.set_page_config(
    page_title="Home",
    page_icon="📊",
    layout="wide"
)

# 2. Carregamento e Cache dos Dados
@st.cache_data
def carregar_dados():
    # Lê a primeira aba da planilha (onde ficam os dados dos diários)
    df_diarios = pd.read_excel("Diarios_Organizados_Final.xlsx", sheet_name=0)
    
    # Lê especificamente a aba de "Docentes"
    df_docentes = pd.read_excel("Diarios_Organizados_Final.xlsx", sheet_name="Docentes")
    
    return df_diarios, df_docentes

df, df_docentes = carregar_dados()

# 3. Configuração do Sidebar (Barra Lateral) - Filtros Iniciais
st.sidebar.title("Filtros")

# Filtro global de Progressão Parcial
incluir_pp = st.sidebar.checkbox("Incluir Aulas de Progressão Parcial", value=False)

if not incluir_pp:
    # Se não estiver marcado, removemos as linhas indicadas com 'Sim'
    df = df[df['Progressão Parcial'].astype(str).str.strip().str.upper() != 'SIM']

# Filtro de Ano (garantindo que não haja valores nulos e ordenando de forma decrescente)
anos = sorted(df['Ano Letivo'].dropna().unique(), reverse=True)
ano_selecionado = st.sidebar.selectbox("Ano Letivo", anos)

# Filtro de Período
periodos = sorted(df['Período Letivo'].dropna().unique(), reverse=True)
periodo_selecionado = st.sidebar.selectbox("Período Letivo", periodos)

# 4. Lógica de Filtragem (Aba Principal)

# Regra 1: Técnico integrado conta para os dois semestres.
mascara = (df['Ano Letivo'] == ano_selecionado) & (
    (df['Período Letivo'] == periodo_selecionado) | 
    (df['Modalidade'] == 'Técnico Integrado')
)
df_filtrado = df[mascara].copy()

# Regra 2: Dividir a carga horária se houver mais de um docente.
colunas_docentes = ['Docente 1', 'Docente 2', 'Docente 3', 'Docente 4', 'Docente 5', 'Docente 6']

df_filtrado['Qtd Docentes'] = df_filtrado[colunas_docentes].notna().sum(axis=1)
df_filtrado = df_filtrado[df_filtrado['Qtd Docentes'] > 0]
df_filtrado['Aulas Proporcionais'] = df_filtrado['Quantidade de Aulas Semanal'] / df_filtrado['Qtd Docentes']

# Transforma as colunas de docentes em linhas
df_melt = df_filtrado.melt(
    id_vars=['Componente Curricular', 'Aulas Proporcionais'], 
    value_vars=colunas_docentes, 
    value_name='Professor'
)
df_melt = df_melt.dropna(subset=['Professor'])

# 5. Agrupamento e Cruzamento de Dados com a aba "Docentes"

# Passo A: Agrupa e soma a carga horária
df_resultado = df_melt.groupby('Professor', as_index=False)['Aulas Proporcionais'].sum()
df_resultado.rename(columns={'Aulas Proporcionais': 'Quantidade de Aula Semanal Total'}, inplace=True)

# Passo B: Preparar os dados da aba "Docentes"
coluna_nome_aba_docentes = 'Nome do Docente' 

try:
    # Seleciona apenas as colunas que importam da aba Docentes e remove duplicados
    df_info_docentes = df_docentes[[coluna_nome_aba_docentes, 'Campus do mapa', 'Setor atual do docente', 'Lotação']].drop_duplicates(subset=[coluna_nome_aba_docentes])
    
    # Passo C: Faz o "PROCV" (.merge) ligando 'Professor' com o nome na aba 'Docentes'
    df_resultado = df_resultado.merge(
        df_info_docentes, 
        left_on='Professor', 
        right_on=coluna_nome_aba_docentes, 
        how='left'
    )
    
except KeyError as e:
    st.error(f"Erro ao cruzar os dados: A coluna {e} não foi encontrada na aba 'Docentes'.")

# Ordena os professores em ordem alfabética
df_resultado = df_resultado.sort_values(by='Professor', ascending=True)

# ==========================================
# NOVO: FILTROS DINÂMICOS DE LOTAÇÃO (Campus, Setor, Lotação)
# ==========================================
st.sidebar.markdown("---")
st.sidebar.markdown("### Filtros de Lotação")

# Filtro de Campus
campi_disponiveis = sorted(df_resultado['Campus do mapa'].dropna().astype(str).unique().tolist())
campus_selecionado = st.sidebar.multiselect("Campus", campi_disponiveis, placeholder="Todos os campi",default="CAMPUS-JP")
if campus_selecionado:
    df_resultado_Filtrado = df_resultado[df_resultado['Campus do mapa'].isin(campus_selecionado)]

# Filtro de Setor (Atualiza com base no Campus selecionado)
setores_disponiveis = sorted(df_resultado['Setor atual do docente'].dropna().astype(str).unique().tolist())
setor_selecionado = st.sidebar.multiselect("Setor Atual", setores_disponiveis, placeholder="Todos os setores")
if setor_selecionado:
    df_resultado_Filtrado = df_resultado[df_resultado['Setor atual do docente'].isin(setor_selecionado)]

# Filtro de Lotação (Atualiza com base no Campus e Setor selecionados)
lotacoes_disponiveis = sorted(df_resultado['Lotação'].dropna().astype(str).unique().tolist())
lotacao_selecionada = st.sidebar.multiselect("Lotação", lotacoes_disponiveis, placeholder="Todas as lotações")
if lotacao_selecionada:
    df_resultado_Filtrado = df_resultado[df_resultado['Lotação'].isin(lotacao_selecionada)]

# ==========================================
# 6. Construção da Interface Principal
# ==========================================
st.title("📊 Lista Carga Horária Docente")
st.markdown("---")

if df_resultado.empty:
    st.warning("Nenhum dado encontrado para a combinação de filtros selecionada.")
else:
    # --- MÉTRICAS E TABELA GERAL ---
    media_carga = df_resultado['Quantidade de Aula Semanal Total'].mean()
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="Média de Carga Horária", value=f"{media_carga:.2f} aulas", border=True, width="content")
    with col2:
        st.metric(label="Total de Professores", value=f"{len(df_resultado)}", border=True, width="content")
        
    st.markdown("### 📋 Listagem Geral de Professores")
    
    st.dataframe(
        df_resultado,
        width='stretch',
        hide_index=True,
        column_order=[
            "Professor", 
            "Campus do mapa", 
            "Setor atual do docente", 
            "Lotação", 
            "Quantidade de Aula Semanal Total"
        ],
        column_config={
            "Professor": st.column_config.TextColumn("Nome do Professor"),
            "Campus do mapa": st.column_config.TextColumn("Campus"),
            "Setor atual do docente": st.column_config.TextColumn("Setor"),
            "Lotação": st.column_config.TextColumn("Lotação"),
            "Quantidade de Aula Semanal Total": st.column_config.ProgressColumn(
                "Carga Semanal Total",
                format="%.2f",
                min_value=0,
                max_value=20,
            )
        }
    )

    st.markdown("---")
    
  
    # 7. SEÇÃO: ANÁLISE DE OCIOSIDADE
   
    st.markdown("### 🔍 Filtro Por Lotação")
    
    # Identifica o valor mínimo e máximo de aulas para configurar o slider
    min_aulas = float(df_resultado['Quantidade de Aula Semanal Total'].min())
    max_aulas = float(df_resultado['Quantidade de Aula Semanal Total'].max())
    
    if min_aulas == max_aulas:
        st.info("Todos os docentes filtrados possuem exatamente a mesma carga horária.")
        val_min, val_max = min_aulas, max_aulas
    else:
        # Cria o slider com duas pontas para selecionar um intervalo (mínimo e máximo)
        val_min, val_max = st.slider(
            "Selecione o intervalo de Quantidade de Aula Semanal Total:",
            min_value=min_aulas,
            max_value=max_aulas,
            value=(min_aulas, max_aulas),
            step=0.5
        )
    
    # Filtra o dataframe com base nos valores do slider
    df_ociosidade =  df_resultado_Filtrado [
        (df_resultado_Filtrado['Quantidade de Aula Semanal Total'] >= val_min) &
        (df_resultado_Filtrado['Quantidade de Aula Semanal Total'] <= val_max)
    ].copy()
    
    # Executa as regras matemáticas solicitadas para ociosidade
    df_ociosidade['Ociosidade (12h)'] = df_ociosidade['Quantidade de Aula Semanal Total'] - 12
    df_ociosidade['Ociosidade (20h)'] = df_ociosidade['Quantidade de Aula Semanal Total'] - 20
    
    # Exibe os resultados (Totais da filtragem)


   
    
    col_oci1, col_oci2, col_oci3= st.columns(3,gap="large", vertical_alignment="center",width="stretch")
    with col_oci1:
        varicao_per= (((len(df_ociosidade))/len(df_resultado))*100)
        st.metric(f"**Total de Docentes Selecionado:**", f"{len(df_ociosidade)}",delta=f"{varicao_per:.2f}%" , border=True, width="content")
        varicao_per=(df_ociosidade['Quantidade de Aula Semanal Total'].mean())-12
        st.metric("Média de Carga Horária (Docentes Filtrados)", f"{df_ociosidade['Quantidade de Aula Semanal Total'].mean():.2f} aulas", delta=f"{varicao_per:.2f} aulas", border=True, width="content")
    with col_oci2:
        varicao_per=(df_ociosidade['Ociosidade (12h)'].sum())/(len(df_ociosidade))
        st.metric("Total Ociosidade (Base 12h)", f"{df_ociosidade['Ociosidade (12h)'].sum():.2f} aulas", delta=f"{varicao_per:.2f} aulas",  border=True, width="content")
        varicao_per=(df_ociosidade['Ociosidade (20h)'].sum())/(len(df_ociosidade))
        st.metric("Total Ociosidade (Base 20h)", f"{df_ociosidade['Ociosidade (20h)'].sum():.2f} aulas", delta=f"{varicao_per:.2f} aulas", border=True, width="content")
    with col_oci3:
        st.metric("Quantidade de Disciplinas com 2 horas semanis", f"{-(df_ociosidade['Ociosidade (12h)'].sum())/2:.2f} Disciplinas", border=True, width="content")
        st.metric("Quantidade de Disciplinas com 4 horas semanis", f"{-(df_ociosidade['Ociosidade (12h)'].sum())/4:.2f} Disciplinas", border=True, width="content")
        st.metric("Quantidade de Disciplinas com 6 horas semanis", f"{-(df_ociosidade['Ociosidade (12h)'].sum())/6:.2f} Disciplinas", border=True, width="content")

    # Exibe a tabela filtrada final com as novas colunas
    st.markdown("#### Detalhamento da Ociosidade")
    st.dataframe(
        df_ociosidade,
        width='stretch',
        hide_index=True,
        column_order=[
            "Professor", 
            "Campus do mapa", 
            "Setor atual do docente", 
            "Lotação", 
            "Quantidade de Aula Semanal Total",
            "Ociosidade (12h)",
            "Ociosidade (20h)"
        ],
        column_config={
            "Professor": st.column_config.TextColumn("Nome do Professor"),
            "Campus do mapa": st.column_config.TextColumn("Campus"),
            "Setor atual do docente": st.column_config.TextColumn("Setor"),
            "Lotação": st.column_config.TextColumn("Lotação"),
            "Quantidade de Aula Semanal Total": st.column_config.NumberColumn(
                "Carga Semanal Total", format="%.2f"
            ),
            "Ociosidade (12h)": st.column_config.NumberColumn(
                "Ociosidade (-12h)", format="%.2f"
            ),
            "Ociosidade (20h)": st.column_config.NumberColumn(
                "Ociosidade (-20h)", format="%.2f"
            )
        }
    )

# Informar data dos dados atualizados no rodapé
try:
    timestamp_atualizacao = os.path.getmtime("Diarios_Organizados_Final.xlsx")
    data_obj = datetime.fromtimestamp(timestamp_atualizacao)
    data_formatada = data_obj.strftime("%d/%m/%Y às %H:%M")
    mensagem = f"📅 Arquivo atualizado em: {data_formatada}"
except FileNotFoundError:
    mensagem = "⚠️ Arquivo de dados não encontrado."

st.sidebar.markdown("---")
st.sidebar.caption(mensagem)