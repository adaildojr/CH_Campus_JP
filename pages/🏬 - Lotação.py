import os
from datetime import datetime
import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Configuração da página
st.set_page_config(
    page_title="Lotação",
    page_icon="🏬",
    layout="wide"
)

@st.cache_data
def carregar_dados():
    # Lê as abas do arquivo Excel
    df_diarios = pd.read_excel("Diarios_Organizados_Final.xlsx", sheet_name="Diários Filtrados")
    df_docentes = pd.read_excel("Diarios_Organizados_Final.xlsx", sheet_name="Docentes")
    
    # Tratamento da Carga Horária Dividida
    docentes_cols = ['Docente 1', 'Docente 2', 'Docente 3', 'Docente 4', 'Docente 5', 'Docente 6']
    df_diarios['Num_Docentes'] = df_diarios[docentes_cols].notna().sum(axis=1)
    df_diarios['Num_Docentes'] = df_diarios['Num_Docentes'].replace(0, 1)
    
    # Divide a carga horária pela quantidade de docentes
    df_diarios['Aulas_Semanal_Ajustada'] = df_diarios['Quantidade de Aulas Semanal'] / df_diarios['Num_Docentes']
    
    # "Derrete" (Melt) as colunas de docentes
    df_melted = df_diarios.melt(
        id_vars=['ID', 'Modalidade', 'Curso', 'Ano Letivo', 'Período Letivo', 'Progressão Parcial', 'Aulas_Semanal_Ajustada'], 
        value_vars=docentes_cols, 
        value_name='Nome do Docente'
    ).dropna(subset=['Nome do Docente'])
    
    # Mescla os diários com as informações da aba Docentes
    df_merged = pd.merge(df_melted, df_docentes, on='Nome do Docente', how='inner')
    
    return df_merged

# Carrega os dados
df = carregar_dados()

st.title("📊 Análise por Lotação")

# 2. BARRA LATERAL (SIDEBAR)
st.sidebar.header("Filtros")

# Caixa de seleção para considerar Progressão Parcial
considerar_pp = st.sidebar.checkbox("Incluir Aulas de Progressão Parcial", value=False)

# Seleção de ANO e PERIODO
anos = sorted(df['Ano Letivo'].dropna().unique(), reverse=True)
ano_selecionado = st.sidebar.selectbox("Ano letivo", anos)

periodos = sorted(df['Período Letivo'].dropna().unique(), reverse=True)
periodo_selecionado = st.sidebar.selectbox("Período letivo", periodos)

# 3. Lógica de Filtro Base (Ano, Semestre e Técnico Integrado)
filtro_base = (df['Ano Letivo'] == ano_selecionado) & (
    (df['Período Letivo'] == periodo_selecionado) | 
    (df['Modalidade'].str.contains('Técnico Integrado', case=False, na=False))
)

df_filtrado = df[filtro_base].copy()

if not considerar_pp:
    df_filtrado = df_filtrado[df_filtrado['Progressão Parcial'] != 'Sim']

st.markdown("---")

# 4. Filtros em Cascata (Lotação -> Setor -> Campus) 
lotacoes = sorted(df_filtrado['Lotação'].dropna().unique())
lotacao_selecionada = st.multiselect("Lotação:", options=lotacoes, default=lotacoes)

if lotacao_selecionada:
    df_filtrado = df_filtrado[df_filtrado['Lotação'].isin(lotacao_selecionada)]

setores = sorted(df_filtrado['Setor atual do docente'].dropna().unique())
setor_selecionado = st.multiselect("Setor atual:", options=setores, default=setores)

if setor_selecionado:
    df_filtrado = df_filtrado[df_filtrado['Setor atual do docente'].isin(setor_selecionado)]

campus = sorted(df_filtrado['Campus do mapa'].dropna().unique())
campus_selecionado = st.multiselect("Campus:", options=campus, default=campus)

if campus_selecionado:
    df_filtrado = df_filtrado[df_filtrado['Campus do mapa'].isin(campus_selecionado)]

st.markdown("---")

# ==========================================
# TABELA INTERATIVA (COM CHECKBOX)
# ==========================================
if df_filtrado.empty:
    st.warning("Nenhum dado encontrado para as combinações de filtros selecionadas.")
else:
    st.subheader("Carga Horária Semanal por Docente e Cursos")
    st.markdown("*Dica: Desmarque as caixas na coluna **Selecionar** para remover docentes específicos do cálculo das métricas e do gráfico abaixo.*")
    
    # Cria a Tabela Dinâmica base
    tabela = pd.pivot_table(
        df_filtrado, 
        values='Aulas_Semanal_Ajustada', 
        index=['Nome do Docente', 'Setor atual do docente', 'Lotação'], 
        columns='Curso', 
        aggfunc='sum', 
        fill_value=0
    )
    
    tabela['Somatório (Total)'] = tabela.sum(axis=1)
    tabela = tabela.sort_index(level=0)

    tabela = tabela.reset_index(level=['Setor atual do docente', 'Lotação'])
    tabela.columns.name = None
    
    # 6. INSERE A COLUNA DE CHECKBOX NA PRIMEIRA POSIÇÃO (Índice 0)
    tabela.insert(1, 'Selecionar', True)
    
    # Lista de colunas que não podem ser editadas (todas, exceto 'Selecionar')
    colunas_desabilitadas = tabela.columns.drop('Selecionar').tolist()

    # ==========================================
    # LÓGICA DE CORES
    # ==========================================
    def colorir_maior_que_zero(valor):
        # Verifica se o valor é numérico (int/float), não é o booleano do checkbox, e é > 0
        if isinstance(valor, (int, float)) and not isinstance(valor, bool) and valor > 0:
            return 'background-color: #d4edda; color: #155724;' # Fundo verde claro e texto verde escuro
        return ''

    # Aplica o estilo na tabela
    if hasattr(tabela.style, 'map'):
        tabela_estilizada = tabela.style.map(colorir_maior_que_zero)
    else:
        tabela_estilizada = tabela.style.applymap(colorir_maior_que_zero)

    # Exibe o st.data_editor passando a tabela_estilizada
    tabela_editada = st.data_editor(
        tabela_estilizada, 
        width='content', 
        hide_index=False,
        column_config={
            "Selecionar": st.column_config.CheckboxColumn(
                "Selecionar",
                help="Marque/Desmarque para incluir/excluir dos cálculos",
                default=True,
            )
        },
        disabled=colunas_desabilitadas # Bloqueia as outras colunas para edição
    )
    
    # ==========================================
    # CÁLCULO DAS MÉTRICAS COM BASE NA SELEÇÃO
    # ==========================================
    # Filtra apenas as linhas onde o checkbox 'Selecionar' é True
    tabela_final = tabela_editada[tabela_editada['Selecionar'] == True]
    
    st.markdown("---")
    st.subheader("Indicadores Gerais")
    
    if tabela_final.empty:
        st.info("Nenhum docente selecionado na tabela acima.")
    else:
        # Calcula as métricas usando a tabela final filtrada pelos checkboxes
        media_aulas = tabela_final['Somatório (Total)'].mean()
        menor_aulas = tabela_final['Somatório (Total)'].min()
        maior_aulas = tabela_final['Somatório (Total)'].max()
        total_docentes = len(tabela_final)
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Docentes Selecionados", total_docentes)
        col2.metric("Média de Aulas / Semanal", round(media_aulas, 2))
        col3.metric("Menor Carga de Aulas", round(menor_aulas, 2))
        col4.metric("Maior Carga de Aulas", round(maior_aulas, 2))
        
        # ==========================================
        # GRÁFICO (COM BASE NA SELEÇÃO)
        # ==========================================
        st.subheader("Gráfico Geral de Aulas Semanais")

        
        #Como 'Nome do Docente' virou índice, precisamos dar um reset temporário para que o Plotly Express consiga ler o nome no eixo X corretamente.
        tabela_grafico = tabela_final.reset_index()

        fig = px.bar(
            tabela_grafico, 
            x='Nome do Docente', 
            y='Somatório (Total)', 
            labels={'Somatório (Total)': 'Total de Aulas Semanais', 'Nome do Docente': 'Docente'},
            title='Carga Semanal Total por Professor Selecionado'
        )
        
        fig.add_hline(y=media_aulas, line_dash="dash", line_color="orange", annotation_text=f"Média ({media_aulas:.1f})", annotation_position="top left")
        fig.add_hline(y=12, line_dash="solid", line_color="red", annotation_text="Referência (12)", annotation_position="top right")

        st.plotly_chart(fig, width='stretch')

# Informar data dos dados atualizados
try:
    # Obtém o timestamp da última modificação do arquivo
    timestamp_atualizacao = os.path.getmtime("Diarios_Organizados_Final.xlsx")
    
    # Converte o timestamp para uma data legível
    data_obj = datetime.fromtimestamp(timestamp_atualizacao)
    
    # Formata a data no padrão Brasileiro: DD/MM/AAAA às HH:MM
    data_formatada = data_obj.strftime("%d/%m/%Y às %H:%M")
    
    mensagem = f"📅 Arquivo atualizado em: {data_formatada}"

except FileNotFoundError:
    mensagem = "⚠️ Arquivo de dados não encontrado."

st.sidebar.markdown("---") # Cria uma linha divisória para separar o conteúdo principal do rodapé
st.sidebar.caption(mensagem) # Coloca a mensagem com uma fonte menor (caption) na parte inferior da barra lateral