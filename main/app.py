import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import plotly.express as px

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Dashboard AIH - RIDE", layout="wide")

# --- CSS CUSTOMIZADO PARA O ESTILO ---
st.markdown("""
<style>
    /* Remove o padding do topo da página */
    .block-container {
        padding-top: 2rem !important;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Estilo do Header Principal */
    .header-container {
        background-color: #1D355B; /* Azul Principal */
        padding: 2rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 2rem;
    }
    
    /* Estilo das caixas de métrica (KPIs) */
    .kpi-card {
        background-color: rgba(255, 255, 255, 0.1);
        padding: 1.5rem;
        border-radius: 10px;
        text-align: center;
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    .kpi-card .stMetricValue {
        color: white;
        font-size: 2em;
    }
    .kpi-card .stMetricLabel {
        color: rgba(255, 255, 255, 0.7);
        margin-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# --- FUNÇÕES DE BANCO DE DADOS E CARREGAMENTO DE DADOS ---
@st.cache_resource
def init_connection():
    try:
        db_credentials = st.secrets["postgres"]
        connection_string = (f"postgresql+psycopg2://{db_credentials['user']}:{db_credentials['password']}@{db_credentials['host']}:{db_credentials['port']}/{db_credentials['database']}")
        return create_engine(connection_string)
    except Exception as e:
        st.error(f"Não foi possível conectar ao banco de dados: {e}")
        return None

@st.cache_data(ttl=600)
def run_query(query, _engine):
    try:
        with _engine.connect() as connection:
            df = pd.read_sql(text(query), connection)
        return df
    except Exception as e:
        st.error(f"Erro ao executar a consulta: {e}")
        return None

# --- INÍCIO DA APLICAÇÃO ---
engine = init_connection()

if engine:
    minha_query = 'SELECT * FROM public.sus_ride_df_aih;'
    df = run_query(minha_query, engine)

    if df is not None and not df.empty:
        
        # --- HEADER COM TÍTULO E KPIs ---
        with st.container():
            st.markdown('<div class="header-container">', unsafe_allow_html=True)
            st.title("🏥 Análise de Internações (AIH) na RIDE-DF")
            st.markdown("Dashboard interativo para exploração de dados de Autorizações de Internação Hospitalar do DATASUS.")
            st.markdown("---")
            
            # KPIs Dinâmicos baseados no dataframe completo
            kpi1, kpi2, kpi3 = st.columns(3)
            with kpi1:
                st.markdown('<div class="kpi-card">', unsafe_allow_html=True)
                st.metric("Valor Total (R$)", f"{df['vl_total'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                st.markdown('</div>', unsafe_allow_html=True)
            with kpi2:
                st.markdown('<div class="kpi-card">', unsafe_allow_html=True)
                st.metric("Quantidade Total", f"{df['qtd_total'].sum():,.0f}")
                st.markdown('</div>', unsafe_allow_html=True)
            with kpi3:
                st.markdown('<div class="kpi-card">', unsafe_allow_html=True)
                st.metric("Nº de Registros", f"{len(df):,}")
                st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('</div>', unsafe_allow_html=True)

        col_filtros, col_conteudo = st.columns([1, 3])

        df_filtrado = df

        with col_filtros:
            st.header("Filtros")
            
            ufs_disponiveis = sorted(df['uf_nome'].unique())
            ufs_disponiveis.insert(0, "Todas")
            uf_selecionada = st.selectbox('Selecione a UF:', ufs_disponiveis)
            if uf_selecionada != "Todas":
                df_filtrado = df_filtrado[df_filtrado['uf_nome'] == uf_selecionada]

            municipios_disponiveis = sorted(df_filtrado['nome_municipio'].unique())
            municipios_selecionados = st.multiselect('Selecione um ou mais municípios:', municipios_disponiveis)
            if municipios_selecionados != "Todas":
                df_filtrado = df_filtrado[df_filtrado['nome_municipio'].isin(municipios_selecionados)]

            anos_disponiveis = sorted(df_filtrado['ano_aih'].unique(), reverse=True)
            ano_selecionado = st.selectbox('Selecione o Ano:', anos_disponiveis)
            if ano_selecionado:
                df_filtrado = df_filtrado[df_filtrado['ano_aih'] == ano_selecionado]

            meses_disponiveis = sorted(df_filtrado['mes_aih'].unique())
            meses_disponiveis.insert(0, "Todos os meses")
            mes_selecionado = st.selectbox('Selecione o Mês:', meses_disponiveis)
            if mes_selecionado != "Todos os meses":
                df_filtrado = df_filtrado[df_filtrado['mes_aih'] == mes_selecionado]

        with col_conteudo:
            tab1, tab2, tab3 = st.tabs(["Visão Geral por Município", "Análise Temporal", "Dados Brutos"])

            with tab1:
                st.subheader("Análise de Ranking por Município")
                
                st.markdown("##### Valor Total (R$)")
                soma_por_municipio = df_filtrado.groupby('nome_municipio')['vl_total'].sum().sort_values(ascending=False).head(15)
                st.bar_chart(soma_por_municipio)

                st.markdown("##### Quantidade Total")
                qtd_por_municipio = df_filtrado.groupby('nome_municipio')['qtd_total'].sum().sort_values(ascending=False).head(15)
                st.bar_chart(qtd_por_municipio, color="#D13F42")
                
            with tab2:
                st.subheader("Evolução Mensal do Valor Total")
                
                df_temporal = df_filtrado.copy()
                if not df_temporal.empty:
                    df_temporal['data'] = pd.to_datetime(df_temporal['ano_aih'].astype(str) + '-' + df_temporal['mes_aih'].astype(str))
                    soma_mensal = df_temporal.groupby('data')['vl_total'].sum()
                    st.line_chart(soma_mensal)
                else:
                    st.warning("Não há dados para exibir com os filtros selecionados.")
            
            with tab3:
                st.subheader("Amostra dos Dados Filtrados")
                st.dataframe(df_filtrado.head(100))
    else:
        st.warning("A consulta não retornou dados.")
else:
    st.error("A conexão com o banco de dados falhou.")