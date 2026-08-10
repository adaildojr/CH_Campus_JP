import streamlit as st
import pandas as pd
import os
from datetime import datetime

# 1. Configuração da página (deve ser o primeiro comando)
st.set_page_config(page_title="Outra Página", page_icon="📈", layout="wide")

# 2. VERIFICAÇÃO DE SEGURANÇA (Bloqueio)
if "autenticado" not in st.session_state or not st.session_state["autenticado"]:
    st.warning("🔒 Acesso negado. Por favor, faça o login na página Home.")
    # Interrompe a execução do restante do código nesta página
    #st.stop() 
    
    # Alternativa: se quiser forçar o usuário a voltar para a página inicial automaticamente, 
    # comente o st.stop() acima e descomente a linha abaixo (use o nome exato do seu arquivo principal):
    st.switch_page("Home.py")

st.set_page_config(
    page_title="Docente",
    page_icon="👨‍🏫",
    layout="wide"
)

@st.cache_data
def carregar_dados():
    df = pd.read_excel("Diarios_Organizados_Final.xlsx")
    
    # Tenta carregar a aba "Docentes", caso ela não exista não quebra o app
    try:
        df_docentes = pd.read_excel("Diarios_Organizados_Final.xlsx", sheet_name="Docentes")
    except Exception:
        df_docentes = pd.DataFrame()
        
    return df, df_docentes

df, df_docentes = carregar_dados()

# Define as colunas que contêm os docentes
colunas_docentes = ['Docente 1', 'Docente 2', 'Docente 3', 'Docente 4', 'Docente 5', 'Docente 6']

# Conta quantos professores não são nulos naquela disciplina
df['Qtd Docentes'] = df[colunas_docentes].notna().sum(axis=1)

# Remove linhas que não tenham nenhum professor associado
df_valido = df[df['Qtd Docentes'] > 0].copy()

# Calcula a carga horária proporcional (aulas semanais divididas pela quantidade de docentes)
df_valido['Aulas Proporcionais'] = df_valido['Quantidade de Aulas Semanal'] / df_valido['Qtd Docentes']

# Transforma as colunas de docentes em linhas (Melt)
# Como id_vars pega todas as outras colunas, 'Matrícula', 'Campus do mapa' e 'Setor atual' vêm junto!
id_vars = [col for col in df_valido.columns if col not in colunas_docentes]
df_melt = df_valido.melt(
    id_vars=id_vars, 
    value_vars=colunas_docentes, 
    value_name='Professor'
)

# Remove as linhas geradas vazias (onde não havia professor preenchido)
df_melt = df_melt.dropna(subset=['Professor'])

st.sidebar.title("Filtros")

# Filtro para incluir ou não a carga horária de Progressão Parcial
incluir_pp = st.sidebar.checkbox("Incluir Aulas de Progressão Parcial", value=False)

if not incluir_pp:
    # Se não estiver marcado, removemos as linhas onde Progressão Parcial indica 'Sim'
    df_melt = df_melt[df_melt['Progressão Parcial'].astype(str).str.strip().str.upper() != 'SIM']

# Remove espaços extras do início e fim dos nomes para evitar falhas na ordenação
df_melt['Professor'] = df_melt['Professor'].astype(str).str.strip()

# Lista unificada e em ordem alfabética real (ignorando diferenças de maiúsculas/minúsculas)
professores = sorted(df_melt['Professor'].unique(), key=lambda x: x.lower())
prof_selecionado = st.sidebar.selectbox("Selecione o Docente", professores)

anos = sorted(df_melt['Ano Letivo'].dropna().unique(), reverse=True)
ano_selecionado = st.sidebar.selectbox("Ano Letivo", anos)

periodos = sorted(df_melt['Período Letivo'].dropna().unique(),  reverse=True)
periodo_selecionado = st.sidebar.selectbox("Período Letivo", periodos)


# Filtra os dados apenas para o professor selecionado
df_prof = df_melt[df_melt['Professor'] == prof_selecionado]

# --- INÍCIO DO NOVO BLOCO: Extração de Matrícula, Campus e Setor ---
# Função auxiliar para pegar o valor único consultando a aba Docentes
def obter_info_docente(coluna):
    if not df_docentes.empty and 'Nome do Docente' in df_docentes.columns and coluna in df_docentes.columns:
        # Encontra a linha correspondente ao professor selecionado (ignorando diferenças de maiúsculas/minúsculas)
        match_docente = df_docentes[df_docentes['Nome do Docente'].astype(str).str.strip().str.lower() == prof_selecionado.lower()]
        
        if not match_docente.empty:
            valor = match_docente[coluna].dropna()
            if not valor.empty:
                v = valor.iloc[0]
                # Corrige visualização caso venha interpretada como float (ex: 12345.0)
                if isinstance(v, float) and v.is_integer():
                    return str(int(v))
                return str(v)
    return "Não informado"

matricula = obter_info_docente('Matrícula')
campus = obter_info_docente('Campus do mapa')
setor = obter_info_docente('Setor atual do docente')
lotacao = obter_info_docente('Lotação')
                             
#st.header("👨‍🏫 Docente")
st.title(f"{prof_selecionado} ({matricula}) - {ano_selecionado}.{periodo_selecionado}")

#st.markdown(f"<div style='text-align: right; font-size: 22px;'><b>Lotação: {campus}</b></div>",unsafe_allow_html=True)
#st.markdown(f"<div style='text-align: right; font-size: 22px;'><b>Setor: {setor}</b></div>",unsafe_allow_html=True)
#st.markdown(f"**Lotação: {campus}**")
#st.markdown(f"**Setor: {setor}**")


      
# --- FIM DO NOVO BLOCO ---

# Aplica a regra de Técnico Integrado para o semestre atual
mascara_semestre = (df_prof['Ano Letivo'] == ano_selecionado) & (
    (df_prof['Período Letivo'] == periodo_selecionado) | 
    (df_prof['Modalidade'] == 'Técnico Integrado')
)
df_prof_semestre = df_prof[mascara_semestre].copy()

if df_prof_semestre.empty:
    st.warning("Nenhum dado encontrado para o docente no Ano e Período selecionados.")
else:
    # Métricas Totais
    total_aulas_semestre = df_prof_semestre['Aulas Proporcionais'].sum()
    cursos_atuacao = df_prof_semestre['Curso'].dropna().unique()
    cursos_formatados = ", ".join(sorted(cursos_atuacao))

    #st.metric(f"Total de Aulas Semanais {ano_selecionado}.{periodo_selecionado}", f"{total_aulas_semestre:.2f}",delta=(total_aulas_semestre-12), border=True, width="content")

    col_info1, col_info2 = st.columns([.8, .15], gap="large", vertical_alignment="bottom",width="stretch")
    with col_info2:
        st.metric(f"Total de Aulas Semanais {ano_selecionado}.{periodo_selecionado}", f"{total_aulas_semestre:.2f}",delta=(total_aulas_semestre-12), border=True, width="content")
        
    with col_info1:
        st.markdown(f"<div style='text-align: right; font-size: 22px;'><b>{campus} / Setor Atual: {setor}</b></div>",unsafe_allow_html=True)
        st.markdown(f"<div style='text-align: right; font-size: 22px;'><b>Lotação: {lotacao}</b></div>",unsafe_allow_html=True)
 
        #st.info(f"**Curso(s) que Atua:**\n{cursos_formatados}")
        st.markdown(f"<div style='text-align: left; font-size: 22px;'><b>Curso(s) que Atua:</b></div>",unsafe_allow_html=True)
        #st.markdown(f"<div style='text-align: center; font-size: 22px;'><b>{cursos_formatados}</b></div>",unsafe_allow_html=True)
        st.info(f"{cursos_formatados}")
      
    
    st.markdown(f"### 📋 Disciplinas {ano_selecionado}.{periodo_selecionado}")
    
    # Prepara a tabela solicitada
    tabela_detalhe = df_prof_semestre[['Modalidade', 'Curso', 'Componente Curricular', 'Aulas Proporcionais']].copy()
    tabela_detalhe.rename(columns={'Aulas Proporcionais': 'Quantidade de Aula Semanal'}, inplace=True)
    
    # Adiciona a linha de total
    linha_total = pd.DataFrame([{
        'Modalidade': 'TOTAL', 
        'Curso': '-', 
        'Componente Curricular': '-', 
        'Quantidade de Aula Semanal': total_aulas_semestre
    }])
    tabela_final = pd.concat([tabela_detalhe, linha_total], ignore_index=True)
    
    # Exibe a tabela no Streamlit
    st.dataframe(
        tabela_final,
       width='stretch',
        hide_index=True,
        column_config={
            "Quantidade de Aula Semanal": st.column_config.NumberColumn(
                "Quantidade de Aula Semanal",
                format="%.2f"
            )
        }
    )

st.markdown("### 📈 Histórico de Carga Horária")

# Prepara todas as combinações de ano e período existentes na base geral
combinacoes = df_melt[['Ano Letivo', 'Período Letivo']].dropna().drop_duplicates().sort_values(by=['Ano Letivo', 'Período Letivo'])

historico = []

for _, row in combinacoes.iterrows():
    ano_h = row['Ano Letivo']
    per_h = row['Período Letivo']
    
    # Aplica a regra de negócio para cada semestre histórico do professor
    masc_hist = (df_prof['Ano Letivo'] == ano_h) & (
        (df_prof['Período Letivo'] == per_h) | 
        (df_prof['Modalidade'] == 'Técnico Integrado')
    )
    carga = df_prof[masc_hist]['Aulas Proporcionais'].sum()
    
    if carga > 0:  # Salva apenas os semestres com atividade para exibir no gráfico
        historico.append({
            'Semestre': f"{int(ano_h)}.{int(per_h)}",
            'Carga Horária': carga
        })
        
df_historico = pd.DataFrame(historico)

if not df_historico.empty:
    df_historico = df_historico.set_index('Semestre')
    # Renderiza o gráfico de colunas
    st.bar_chart(df_historico['Carga Horária'])
else:
    st.info("Sem histórico de aulas para exibir para este docente.")

st.markdown("### Lista de Disciplinas Lecionadas (Todos os Semestres)")

df_todas = df_prof[["Ano Letivo", "Período Letivo", "Modalidade", "Curso", "Componente Curricular"]].drop_duplicates().reset_index(drop=True)
df_todas.sort_values(by=["Ano Letivo", "Período Letivo", "Componente Curricular"], ascending=[False, False, True], inplace=True)
st.dataframe(df_todas, hide_index=True, width='stretch')


# Informar data dos dados atualizados
try:
    # Obtém o timestamp da última modificação do arquivo
    timestamp_atualizacao = os.path.getctime("Diarios_Organizados_Final.xlsx")
    
    # Data de CRIAÇÃO do arquivo no Windows, use:
    #timestamp_atualizacao = os.path.getctime("Diarios_Organizados_Final.xlsx")
    
    # Converte o timestamp para uma data legível
    data_obj = datetime.fromtimestamp(timestamp_atualizacao)
    
    # Formata a data no padrão Brasileiro: DD/MM/AAAA às HH:MM
    data_formatada = data_obj.strftime("%d/%m/%Y às %H:%M")
    
    mensagem = f"📅 Arquivo atualizado em: {data_formatada}"

except FileNotFoundError:
    mensagem = "⚠️ Arquivo de dados não encontrado."


st.sidebar.markdown("---") # Cria uma linha divisória para separar o conteúdo principal do rodapé
st.sidebar.caption(mensagem) # Coloca a mensagem com uma fonte menor (caption) na parte de ba