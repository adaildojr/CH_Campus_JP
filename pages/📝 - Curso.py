import os
from datetime import datetime
import streamlit as st
import pandas as pd

# 1. Configuração da página (deve ser o primeiro comando)
st.set_page_config(page_title="Outra Página", page_icon="📈", layout="wide")

# 2. VERIFICAÇÃO DE SEGURANÇA (Bloqueio)
if "autenticado" not in st.session_state or not st.session_state["autenticado"]:
    st.warning("🔒 Acesso negado. Por favor, faça o login na página Home.")
    # Interrompe a execução do restante do código nesta página
    # st.stop() 
    
    # Alternativa: se quiser forçar o usuário a voltar para a página inicial automaticamente, 
    # comente o st.stop() acima e descomente a linha abaixo (use o nome exato do seu arquivo principal):
    st.switch_page("Home.py")

 
    st.sidebar.markdown("---")

# Configuração da página
st.set_page_config(
    page_title="Curso",
    page_icon="📒",
    layout="wide"
)


# 1. Carregamento e Processamento Inicial dos Dados
@st.cache_data
def carregar_dados():
    # Lê o arquivo Excel. Usa o ExcelFile para pegar as abas por índice, 
    # evitando erros caso o nome da aba não seja exatamente 'Aba 1'
    xls = pd.ExcelFile("Diarios_Organizados_Final.xlsx")
    nomes_abas = xls.sheet_names
    
    # Assume que a primeira aba é a de Diários e a segunda a de Docentes
    df_diarios = pd.read_excel(xls, sheet_name=nomes_abas[0])
    df_docentes = pd.read_excel(xls, sheet_name=nomes_abas[1])
    
    return df_diarios, df_docentes

try:
    df_diarios_raw, df_docentes = carregar_dados()
except FileNotFoundError:
    st.error("Arquivo 'Diarios_Organizados_Final.xlsx' não encontrado. Verifique se ele está no mesmo diretório do script.")
    st.stop()

# 2. Configuração da Sidebar (Barra Lateral)
st.sidebar.title("Filtros Gerais")

incluir_pp = st.sidebar.checkbox("Incluir disciplinas com Progressão Parcial", value=False)

# Coletando os anos e semestres disponíveis
anos_disponiveis = sorted(df_diarios_raw['Ano Letivo'].dropna().unique(),reverse=True)
semestres_disponiveis = sorted(df_diarios_raw['Período Letivo'].dropna().unique(),reverse=True)

ano_letivo = st.sidebar.selectbox("Ano Letivo", anos_disponiveis)
semestre_letivo = st.sidebar.selectbox("Semestre Letivo", semestres_disponiveis)

# Filtro de Ano
mask_ano = df_diarios_raw['Ano Letivo'] == ano_letivo

# Filtro de Semestre com a regra do "Técnico Integrado" (conta para ambos os semestres)
# Identifica se a modalidade contém a palavra "Integrado"
is_integrado = df_diarios_raw['Modalidade'].astype(str).str.contains('Integrado', case=False, na=False)
mask_semestre = (df_diarios_raw['Período Letivo'] == semestre_letivo) | is_integrado

df_diarios = df_diarios_raw[mask_ano & mask_semestre].copy()

# Filtro de Progressão Parcial
if not incluir_pp:
    # Se desmarcado, removemos o que for "Sim" (ou valor similar dependendo de como está preenchido)
    df_diarios = df_diarios[~df_diarios['Progressão Parcial'].astype(str).str.contains('Sim', case=False, na=False)]

# Identificando as colunas de docentes
colunas_docentes = ['Docente 1', 'Docente 2', 'Docente 3', 'Docente 4', 'Docente 5', 'Docente 6']

# Conta quantos docentes de fato existem preenchidos naquela disciplina
df_diarios['Qtd_Docentes_Disciplina'] = df_diarios[colunas_docentes].notna().sum(axis=1)

# "Explodindo" as colunas de docentes para que cada docente tenha sua própria linha na tabela
colunas_id = [col for col in df_diarios.columns if col not in colunas_docentes]
df_melt = df_diarios.melt(
    id_vars=colunas_id,
    value_vars=colunas_docentes,
    var_name='Posicao_Docente',
    value_name='Professor'
)

# Remove as linhas vazias geradas por docentes que não existiam (ex: disciplina só tinha 1 docente, os outros 5 viraram NaN)
df_melt = df_melt.dropna(subset=['Professor'])

# Dividindo a Carga Horária / Aulas Semanais pela quantidade de docentes daquela disciplina
df_melt['Quantidade de Aulas Semanal'] = df_melt['Quantidade de Aulas Semanal'] / df_melt['Qtd_Docentes_Disciplina']

# Trazendo as informações da Aba 2 (Docentes)
# Fazemos um left join usando o nome do professor
df_completo = pd.merge(
    df_melt, 
    df_docentes[['Nome do Docente', 'Matrícula', 'Campus do mapa', 'Setor atual do docente', 'Lotação']], 
    left_on='Professor', 
    right_on='Nome do Docente', 
    how='left'
)

# 3. Configuração da Página Principal com Preservação de Estado (Session State)
st.title("Carga Horária e Disciplinas")

# Criação das colunas para os filtros hierárquicos
col1, col2, col3 = st.columns([1,1,1], gap="large", vertical_alignment="bottom",width="stretch")

with col1:
    modalidades = sorted(df_completo['Modalidade'].dropna().unique())
    # Preservar o índice da última seleção se existir
    mod_idx = modalidades.index(st.session_state.mod_selecionada) if 'mod_selecionada' in st.session_state and st.session_state.mod_selecionada in modalidades else 0
        
    if modalidades:
        mod_selecionada = st.selectbox("Selecione a Modalidade", modalidades, index=mod_idx)
        st.session_state.mod_selecionada = mod_selecionada
        df_filtrado = df_completo[df_completo['Modalidade'] == mod_selecionada].copy()
    else:
        df_filtrado = df_completo.copy()

with col2:
    cursos = sorted(df_filtrado['Curso'].dropna().unique())
    curso_idx = cursos.index(st.session_state.curso_selecionado) if 'curso_selecionado' in st.session_state and st.session_state.curso_selecionado in cursos else 0
        
    if cursos:
        curso_selecionado = st.selectbox("Selecione o Curso", cursos, index=curso_idx)
        st.session_state.curso_selecionado = curso_selecionado
        df_filtrado = df_filtrado[df_filtrado['Curso'] == curso_selecionado].copy()

with col3:
    turnos = sorted(df_filtrado['Turno'].dropna().unique())
    turno_idx = turnos.index(st.session_state.turno_selecionado) if 'turno_selecionado' in st.session_state and st.session_state.turno_selecionado in turnos else 0

    if len(turnos) > 1:
        turno_selecionado = st.selectbox("Selecione o Turno", turnos, index=turno_idx)
        st.session_state.turno_selecionado = turno_selecionado
        df_filtrado = df_filtrado[df_filtrado['Turno'] == turno_selecionado].copy()
    elif len(turnos) == 1:
        st.info(f"Turno único: {turnos[0]}")
        st.session_state.turno_selecionado = turnos[0]
        df_filtrado = df_filtrado[df_filtrado['Turno'] == turnos[0]].copy()

st.markdown("---")

st.subheader("Disciplinas e Docentes")
st.write("Marque ou desmarque as disciplinas na coluna **'Calcular'** para atualizar o resumo de métricas.")

# Seleção e ordenação de colunas da tabela interativa
colunas_exibicao = [
    'Período', 
    'Componente Curricular', 
    'Professor',
    'Matrícula', 
    'Campus do mapa', 
    'Setor atual do docente', 
    'Lotação', 
    'Quantidade de Aulas Semanal', 
    'Quantidade de Alunos',
    'ID' # ID oculto na view, mas necessário para não duplicar média de alunos
]

df_tabela = df_filtrado[colunas_exibicao].copy()

# ================= ORDENAÇÃO NUMÉRICA DO PERÍODO =================
# Cria uma coluna temporária extraindo os números da coluna 'Período'
# Isso garante que "10º" seja lido como o número 10 e não como texto.
df_tabela['Ordem_Periodo'] = df_tabela['Período'].astype(str).str.extract(r'(\d+)').astype(float)
# Preenche valores vazios com 999 para jogá-los para o final da lista (caso haja "Optativa", etc)
df_tabela['Ordem_Periodo'] = df_tabela['Ordem_Periodo'].fillna(999)

# Ordena pela chave numérica temporária e, em seguida, por Componente Curricular
df_tabela = df_tabela.sort_values(by=['Ordem_Periodo', 'Componente Curricular'])

# Remove a coluna temporária para não exibi-la na tela final
df_tabela = df_tabela.drop(columns=['Ordem_Periodo'])
# =================================================================

# Ordenar por Período e depois Componente Curricular
#df_tabela = df_tabela.sort_values(by=['Período', 'Componente Curricular'])

# Inserindo o checkbox no início
df_tabela.insert(0, "Calcular", True)

df_editado = st.data_editor(
    df_tabela,
    column_config={
        "Calcular": st.column_config.CheckboxColumn(
            "Calcular?",
            help="Selecione para incluir no cálculo das métricas abaixo",
            default=True,
        ),
        "ID": None # Oculta a coluna ID visualmente
    },
    disabled=colunas_exibicao, # Apenas a coluna "Calcular" pode ser editada
    hide_index=True,
    width='content'
)

st.markdown("---")

df_calculo = df_editado[df_editado["Calcular"] == True].copy()

if not df_calculo.empty:
    # Métricas Principais
    qtd_docentes = df_calculo['Professor'].nunique()
    qtd_disciplinas = df_calculo['Componente Curricular'].nunique()
    
    # Para alunos, removemos duplicidade do ID para que alunos de uma turma
    # com 3 professores não sejam contados 3 vezes na média do curso
    df_unicos = df_calculo.drop_duplicates(subset=['ID'])
    media_alunos_curso = df_unicos['Quantidade de Alunos'].mean()

    # Cálculo da Aulas
    total_aulas_semana = df_calculo['Quantidade de Aulas Semanal'].sum()
    media_aulas_docente = total_aulas_semana / qtd_docentes if qtd_docentes > 0 else 0

    st.subheader("Resumo do Curso")
    
    c1, c2, c3 = st.columns([1,1,2], gap="large", vertical_alignment="center",width="stretch")

    with c1:
        st.metric("Quantidade de Docentes", qtd_docentes)
        st.metric("Quantidade de Disciplinas", qtd_disciplinas)
        

    with c2:
        st.metric("Total de Aulas por Semana", f"{total_aulas_semana:.1f}")
        st.metric("Média de Aulas por Docente", f"{media_aulas_docente:.1f}")
        if pd.isna(media_alunos_curso):
            st.metric("Média de Alunos no Curso", "0.0")
        else:
            st.metric("Média de Alunos no Curso", f"{media_alunos_curso:.1f}")
       
    with c3:
        st.subheader("Quantidade Média de Alunos por Período")
    
        # Usa o df_unicos para a média por período
        df_resumo_periodo = df_unicos.groupby('Período')['Quantidade de Alunos'].mean().reset_index()
    
        # Adiciona a ordem aqui novamente também para exibir o resumo ordenado
        df_resumo_periodo['Ordem_Periodo'] = df_resumo_periodo['Período'].astype(str).str.extract(r'(\d+)').astype(float)
        df_resumo_periodo = df_resumo_periodo.sort_values(by='Ordem_Periodo').drop(columns=['Ordem_Periodo'])

        df_resumo_periodo.rename(columns={'Quantidade de Alunos': 'Média de Alunos'}, inplace=True)
        df_resumo_periodo['Média de Alunos'] = df_resumo_periodo['Média de Alunos'].round(1)
    
        st.dataframe(df_resumo_periodo, hide_index=True, width='stretch')

    st.markdown("<br>", unsafe_allow_html=True)

# NOVO CÓDIGO: TABELA DE RESUMO POR PROFESSOR
    # =========================================================================
    st.markdown("---")
    st.subheader("Detalhamento por Docente")
    
    # 1. Agrupar os dados do curso selecionado (df_calculo)
    df_prof_curso = df_calculo.groupby(['Professor', 'Lotação']).agg(
        Disciplinas=('Componente Curricular', lambda x: ', '.join(x.unique())),
        CH_Curso=('Quantidade de Aulas Semanal', 'sum')
    ).reset_index()

    # 2. Calcular a Carga Horária TOTAL no semestre para os professores 
    # Usamos o df_completo pois ele não tem o filtro de Modalidade/Curso/Turno aplicado
    df_ch_total = df_completo.groupby('Professor')['Quantidade de Aulas Semanal'].sum().reset_index()
    df_ch_total = df_ch_total.rename(columns={'Quantidade de Aulas Semanal': 'CH_Total_Semestre'})

    # 3. Cruzar as informações (Left join para manter apenas os professores do curso atual)
    df_resumo_prof = pd.merge(df_prof_curso, df_ch_total, on='Professor', how='left')

    # 4. Renomear e formatar as colunas
    df_resumo_prof = df_resumo_prof.rename(columns={
        'Professor': 'Docente',
        'Disciplinas': 'Disciplinas no Curso',
        'CH_Curso': 'C.H. no Curso',
        'CH_Total_Semestre': 'C.H. Total (Semestre)'
    })
    
    # Arredondar os valores numéricos para 1 casa decimal
    df_resumo_prof['C.H. no Curso'] = df_resumo_prof['C.H. no Curso'].round(1)
    df_resumo_prof['C.H. Total (Semestre)'] = df_resumo_prof['C.H. Total (Semestre)'].round(1)
    
    # Ordenar alfabeticamente pelo nome do professor
    df_resumo_prof = df_resumo_prof.sort_values(by='Docente')

    # 5. Exibir a tabela na tela
    st.dataframe(df_resumo_prof, hide_index=True, width='stretch')





else:
    st.warning("Nenhuma disciplina encontrada ou selecionada para os filtros atuais.")




# Informar data dos dados atualizados
try:
    # Obtém o timestamp da última modificação do arquivo
    #timestamp_atualizacao = os.path.getmtime("Diarios_Organizados_Final.xlsx")
    
    # Data de CRIAÇÃO do arquivo no Windows, use:
    timestamp_atualizacao = os.path.getctime("Diarios_Organizados_Final.xlsx")
    
    # Converte o timestamp para uma data legível
    data_obj = datetime.fromtimestamp(timestamp_atualizacao)
    
    # Formata a data no padrão Brasileiro: DD/MM/AAAA às HH:MM
    data_formatada = data_obj.strftime("%d/%m/%Y às %H:%M")
    
    mensagem = f"📅 Arquivo atualizado em: {data_formatada}"

except FileNotFoundError:
    mensagem = "⚠️ Arquivo de dados não encontrado."


st.sidebar.markdown("---") # Cria uma linha divisória para separar o conteúdo principal do rodapé
st.sidebar.caption(mensagem) # Coloca a mensagem com uma fonte menor (caption) na parte de ba


