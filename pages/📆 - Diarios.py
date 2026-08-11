import streamlit as st
import pandas as pd
import os
from datetime import datetime

# 1. Configuração da página
st.set_page_config(page_title="Identificação de Diários", page_icon="📆", layout="wide")

# 2. VERIFICAÇÃO DE SEGURANÇA (Bloqueio)
if "autenticado" not in st.session_state or not st.session_state["autenticado"]:
    st.warning("🔒 Acesso negado. Por favor, faça o login na página Home.")
    # st.stop() 
    st.switch_page("Home.py") # Descomente para forçar o redirecionamento automático

@st.cache_data
def carregar_dados_diarios():
    df = pd.read_excel("Diarios_Organizados_Final.xlsx")
    
    # Define as colunas que contêm os docentes
    colunas_docentes = ['Docente 1', 'Docente 2', 'Docente 3', 'Docente 4', 'Docente 5', 'Docente 6']
    
    # 1. Conta quantos docentes estão vinculados a este diário
    df['Qtd Docentes'] = df[colunas_docentes].notna().sum(axis=1)
    
    # 2. Cria uma única coluna juntando o nome de todos os docentes daquele diário
    def juntar_docentes(row):
        docs = [str(row[c]).strip() for c in colunas_docentes if pd.notna(row[c]) and str(row[c]).strip() != ""]
        return ", ".join(docs) if docs else "SEM PROFESSOR"
        
    df['Docentes'] = df.apply(juntar_docentes, axis=1)
    
    # 3. Trata alunos nulos como 0 para facilitar as contagens nos indicadores
    if 'Quantidade de Alunos' in df.columns:
        df['Quantidade de Alunos'] = pd.to_numeric(df['Quantidade de Alunos'], errors='coerce').fillna(0)
    
    return df

df = carregar_dados_diarios()


# BARRA LATERAL (SIDEBAR) - FILTROS GERAIS

st.sidebar.title("Filtros Globais")

# Filtro de Progressão Parcial
incluir_pp = st.sidebar.checkbox("Incluir Aulas de Progressão Parcial", value=False)

if not incluir_pp:
    df = df[df['Progressão Parcial'].astype(str).str.strip().str.upper() != 'SIM']

# Filtro de Ano e Período
anos = sorted(df['Ano Letivo'].dropna().unique(), reverse=True)
ano_selecionado = st.sidebar.selectbox("Ano Letivo", anos)

periodos = sorted(df['Período Letivo'].dropna().unique(), reverse=True)
periodo_selecionado = st.sidebar.selectbox("Semestre Letivo", periodos)

# Regra do Técnico Integrado: deve aparecer no semestre 1 e 2.
mascara_semestre = (df['Ano Letivo'] == ano_selecionado) & (
    (df['Período Letivo'] == periodo_selecionado) | 
    (df['Modalidade'] == 'Técnico Integrado')
)
df_semestre = df[mascara_semestre].copy()


# PÁGINA PRINCIPAL

st.title(f"Diários - {ano_selecionado}.{periodo_selecionado}")
st.markdown("---")

# Filtros da Página Principal (Modalidade e Curso)
st.markdown("#### Filtros Específicos")
col_mod, col_curso = st.columns(2)

with col_mod:
    modalidades = ["Todas"] + sorted(df_semestre['Modalidade'].dropna().unique())
    modalidade_selecionada = st.selectbox("Selecione a Modalidade", modalidades)

# Filtra a base pela modalidade para atualizar a lista de cursos dinamicamente
if modalidade_selecionada != "Todas":
    df_filtrado_mod = df_semestre[df_semestre['Modalidade'] == modalidade_selecionada]
else:
    df_filtrado_mod = df_semestre

with col_curso:
    cursos = ["Todos"] + sorted(df_filtrado_mod['Curso'].dropna().unique())
    curso_selecionado = st.selectbox("Selecione o Curso", cursos)

# Filtra a base final pelo curso escolhido
if curso_selecionado != "Todos":
    df_final = df_filtrado_mod[df_filtrado_mod['Curso'] == curso_selecionado]
else:
    df_final = df_filtrado_mod


# INDICADORES (KPIs)

st.markdown("### 📊 Indicadores de Turmas")

qtd_0_alunos = len(df_final[df_final['Quantidade de Alunos'] == 0])
qtd_1_aluno = len(df_final[df_final['Quantidade de Alunos'] == 1])
qtd_sem_prof = len(df_final[df_final['Qtd Docentes'] == 0])
qtd_mais_1_prof = len(df_final[df_final['Qtd Docentes'] > 1])

# Mostra os indicadores lado a lado usando st.columns
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("Diários com 0 Alunos", qtd_0_alunos)
kpi2.metric("Diários com 1 Aluno", qtd_1_aluno)
kpi3.metric("Diários SEM Professor", qtd_sem_prof)
kpi4.metric("Diários com > 1 Professor", qtd_mais_1_prof)

# ==========================================
# TABELA DE DADOS
# ==========================================
st.markdown("### 📋 Relação de Diários (Disciplinas)")

if df_final.empty:
    st.info("Nenhum diário encontrado com os filtros selecionados.")
else:
    # Seleciona as colunas solicitadas para exibir (Adicionada 'Quantidade de Aulas Semanal')
    colunas_exibir = [
        'Modalidade', 
        'Curso', 
        'Componente Curricular', 
        'Docentes', 
        'Quantidade de Alunos', 
        'Carga Horária (h)',
        'Quantidade de Aulas Semanal'
    ]
    
    # Verifica quais dessas colunas de fato existem no dataset para não quebrar
    colunas_presentes = [col for col in colunas_exibir if col in df_final.columns]
    
    df_tabela = df_final[colunas_presentes].copy()
    
    # Renomeia colunas para ficar mais amigável na tela
    df_tabela.rename(columns={
        'Docentes': 'Docente(s)',
        'Carga Horária (h)': 'Carga Horária Total',
        'Quantidade de Aulas Semanal': 'Aulas Semanais'
    }, inplace=True)
    
    # Exibe a tabela interativa
    st.dataframe(
        df_tabela,
        width='stretch',
        hide_index=True,
        column_config={
            "Quantidade de Alunos": st.column_config.NumberColumn("Qtd Alunos", format="%d"),
            "Aulas Semanais": st.column_config.NumberColumn("Aulas Semanais", format="%.2f")
        }
    )

# ==========================================
# RODAPÉ (DATA DE ATUALIZAÇÃO)
# ==========================================
try:
    timestamp_atualizacao = os.path.getctime("Diarios_Organizados_Final.xlsx")
    data_obj = datetime.fromtimestamp(timestamp_atualizacao)
    data_formatada = data_obj.strftime("%d/%m/%Y às %H:%M")
    mensagem = f"📅 Dados atualizados em: {data_formatada}"
except FileNotFoundError:
    mensagem = "⚠️ Arquivo de dados não encontrado."

st.sidebar.markdown("---")
st.sidebar.caption(mensagem)