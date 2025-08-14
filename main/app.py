import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import plotly.express as px
import folium
from streamlit_folium import st_folium
from folium.plugins import HeatMap
import boto3
import json

st.markdown("""
<style>
    /* Fundo geral claro */
    body, .main { 
        background-color: #F5F6FA; 
        font-family: 'Arial', sans-serif; 
        color: #2C3E50 !important; /* Texto escuro padrão para boa legibilidade */
    }

    /* Força cor escura para TUDO */
    *, *::before, *::after {
        color: #2C3E50 !important;
    }

    /* HERO roxo que engloba título, descrição e métricas (altura automática, sem cortes) */
    .hero {
        background: linear-gradient(135deg, #1D345B 0%, #2C5282 100%);
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 16px;
        box-shadow: 0 4px 12px rgba(29, 52, 91, 0.2);
    }
    .hero .header-title {
        color: #FFFFFF !important;
        font-size: 1.8rem;
        font-weight: 800;
        margin: 4px 0 6px 0;
        text-shadow: 0 2px 4px rgba(0,0,0,0.3);
    }
    .hero .header-desc {
        color: #E2E8F0 !important; /* Cor mais clara para melhor contraste */
        font-size: 1rem;
        margin-bottom: 18px;
        max-width: 1200px;
        line-height: 1.35;
        text-shadow: 0 1px 2px rgba(0,0,0,0.2);
    }
    .hero .metrics {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
        gap: 12px;
    }
    .metric-card {
        background-color: #FFFFFF;
        padding: 16px;
        border-radius: 12px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.06);
        text-align: center;
        border: 1px solid #E2E8F0;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    .metric-card h3 {
        font-size: 1rem;
        color: #4A5568 !important; /* Cor mais escura para melhor legibilidade */
        margin-bottom: 6px;
        font-weight: 700;
    }
    .metric-card p {
        font-size: 1.4rem;
        font-weight: 800;
        margin: 0;
        color: #1A202C !important; /* Cor bem escura para números */
    }

    /* Caixas brancas da página */
    .content-box {
        background-color: #FFFFFF;
        padding: 16px;
        border-radius: 12px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.06);
        margin-bottom: 16px;
        border: 1px solid #E2E8F0;
        color: #2D3748 !important; /* Texto escuro para conteúdo */
    }

    /* Força cor escura para elementos dentro de content-box */
    .content-box * {
        color: #2D3748 !important;
    }

    /* Títulos e subtítulos */
    h1, h2, h3, h4, h5, h6 {
        color: #1A202C !important;
    }

    /* TODAS as labels - abordagem mais agressiva */
    label,
    .stSelectbox label,
    .stMultiSelect label,
    .stTextInput label,
    .stNumberInput label,
    .stDateInput label,
    .stTimeInput label,
    .stTextArea label,
    .stCheckbox label,
    .stRadio label,
    .stSlider label,
    [data-testid="stSelectbox"] label,
    [data-testid="stMultiSelect"] label,
    [data-testid="stTextInput"] label,
    [data-testid="stNumberInput"] label,
    [data-testid="stDateInput"] label,
    [data-testid="stTimeInput"] label,
    [data-testid="stTextArea"] label,
    [data-testid="stCheckbox"] label,
    [data-testid="stRadio"] label,
    [data-testid="stSlider"] label {
        color: #2D3748 !important;
        font-weight: 600 !important;
        font-size: 14px !important;
    }

    /* Streamlit widgets - seletores mais específicos */
    .stSelectbox > div > label,
    .stMultiSelect > div > label,
    .stSelectbox div label,
    .stMultiSelect div label {
        color: #2D3748 !important;
        font-weight: 600 !important;
    }

    /* Seletores baseados em classes CSS do Streamlit */
    .css-1cpxqw2,
    .css-1d391kg,
    .css-1y4p8pa,
    .css-1v0mbdj label {
        color: #2D3748 !important;
    }

    /* Tabs do Streamlit */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: #F7FAFC;
        color: #2D3748 !important;
        border-radius: 8px 8px 0 0;
        padding: 8px 16px;
        border: 1px solid #E2E8F0;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #FFFFFF !important;
        color: #1A202C !important;
        font-weight: 600;
    }

    /* Dataframes */
    .dataframe {
        color: #2D3748 !important;
    }

    /* Warnings e mensagens */
    .stAlert {
        color: #2D3748 !important;
    }

    /* Rodapé */
    .footer {
        text-align: center; 
        color: #718096 !important; /* Cor cinza mais escura para melhor legibilidade */
        margin-top: 40px;
        font-size: 0.9rem;
        padding: 16px;
        background-color: #F7FAFC;
        border-radius: 8px;
        border-top: 2px solid #E2E8F0;
    }

    /* Override final - força cor escura para tudo exceto hero */
    .main * {
        color: #2D3748 !important;
    }
    
    /* Exceções para o hero */
    .hero * {
        color: inherit !important;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_secret(secret_name, region_name="us-east-1"):
    """
    Retrieve secret from AWS Secrets Manager
    """
    try:
        # Create a Secrets Manager client
        session = boto3.session.Session()
        client = session.client(
            service_name='secretsmanager',
            region_name=region_name
        )
        
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
        
        # Parse the secret string
        secret_string = get_secret_value_response['SecretString']
        secret = json.loads(secret_string)
        
        return secret
        
    except json.JSONDecodeError as e:
        st.error(f"Erro ao fazer parse do JSON do secret: {e}")
        return None
    except Exception as e:
        st.error(f"Erro ao recuperar secret do AWS Secrets Manager: {e}")
        return None

@st.cache_resource
def init_connection():
    try:
        # Get database credentials from AWS Secrets Manager
        db_credentials = get_secret("rds-secret")
        
        if db_credentials is None:
            st.error("Não foi possível recuperar as credenciais do banco de dados do AWS Secrets Manager")
            return None
        
        # Check for required keys
        required_keys = ['username', 'password', 'host', 'db_name']
        missing_keys = [key for key in required_keys if key not in db_credentials]
        
        if missing_keys:
            st.error(f"Credenciais incompletas no banco de dados")
            return None
            
        # Build connection string using the actual secret structure
        connection_string = (f"postgresql+psycopg2://{db_credentials['username']}:{db_credentials['password']}@"
                             f"{db_credentials['host']}:{db_credentials.get('port', 5432)}/{db_credentials['db_name']}")
        
        engine = create_engine(connection_string)
        
        # Test the connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        return engine
        
    except KeyError as e:
        st.error(f"Configuração de banco de dados incompleta")
        return None
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

def footer():
    st.markdown(
        "<div class='footer'>Desenvolvido por Pedro e Mateus Lima para o Projeto de Análise de Dados | Fonte: DATASUS / AIH</div>",
        unsafe_allow_html=True
    )

engine = init_connection()

if engine:
    minha_query = 'SELECT * FROM public.sus_ride_df_aih;'
    df = run_query(minha_query, engine)

    if df is not None and not df.empty:

        if 'latitude' in df.columns and 'longitude' in df.columns:
            df = df.rename(columns={'latitude': 'lat', 'longitude': 'lon'})

        valor_total_fmt = f"{df['vl_total'].sum():,.2f}"
        qtd_total_fmt = f"{df['qtd_total'].sum():,.0f}"
        n_reg_fmt = f"{len(df):,}"

        st.markdown(f"""
        <div class="hero">
            <div class="header-title">🏥 Análise de Internações (AIH) na RIDE-DF</div>
            <div class="header-desc">
                Este painel apresenta análises interativas com dados de Autorizações de Internação Hospitalar do DATASUS.
                É possível filtrar por UF, município, ano e mês para personalizar a análise.
            </div>
            <div class="metrics">
                <div class="metric-card">
                    <h3>Valor Total (R$)</h3>
                    <p>{valor_total_fmt}</p>
                </div>
                <div class="metric-card">
                    <h3>Quantidade Total</h3>
                    <p>{qtd_total_fmt}</p>
                </div>
                <div class="metric-card">
                    <h3>Nº de Registros</h3>
                    <p>{n_reg_fmt}</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        col_filtros, col_conteudo = st.columns([1, 3])
        df_filtrado = df.copy()

        with col_filtros:
            st.markdown("<div class='content-box'>", unsafe_allow_html=True)
            st.header("Filtros")

            ufs_disponiveis = sorted(df['uf_nome'].unique())
            ufs_selecionadas = st.multiselect('UF(s):', ufs_disponiveis)
            if ufs_selecionadas:
                df_filtrado = df_filtrado[df_filtrado['uf_nome'].isin(ufs_selecionadas)]

            municipios_disponiveis = sorted(df_filtrado['nome_municipio'].unique())
            municipios_selecionados = st.multiselect('Município(s):', municipios_disponiveis)
            if municipios_selecionados:
                df_filtrado = df_filtrado[df_filtrado['nome_municipio'].isin(municipios_selecionados)]

            anos_disponiveis = sorted(df_filtrado['ano_aih'].unique(), reverse=True)
            anos_selecionados = st.multiselect('Ano(s):', anos_disponiveis)
            if anos_selecionados:
                df_filtrado = df_filtrado[df_filtrado['ano_aih'].isin(anos_selecionados)]

            meses_disponiveis = sorted(df_filtrado['mes_aih'].unique())
            meses_selecionados = st.multiselect('Mês(es):', meses_disponiveis)
            if meses_selecionados:
                df_filtrado = df_filtrado[df_filtrado['mes_aih'].isin(meses_selecionados)]
            st.markdown("</div>", unsafe_allow_html=True)

        with col_conteudo:
            st.markdown("<div class='content-box'>", unsafe_allow_html=True)
            if df_filtrado.empty:
                st.warning("Nenhum registro encontrado para a combinação de filtros selecionada.")
            else:
                abas = st.tabs(["Visão Geral", "Por Região", "Análise Temporal", "Mapa Geográfico", "Dados Brutos", "Gráfico de Pizza"])

                with abas[0]:
                    st.subheader("Ranking por Município")
                    soma_por_municipio = df_filtrado.groupby('nome_municipio')['vl_total'].sum().sort_values(ascending=False)
                    st.bar_chart(soma_por_municipio)

                    if 'numero_habitantes' in df_filtrado.columns and df_filtrado['numero_habitantes'].sum() > 0:
                        st.subheader("Top 15 Municípios por Valor Gasto por Habitante (R$)")
                        df_per_capita = df_filtrado.groupby('nome_municipio').agg(
                            vl_total_sum=('vl_total', 'sum'),
                            populacao_sum=('numero_habitantes', 'first')
                        ).dropna()
                        df_per_capita['valor_por_habitante'] = df_per_capita['vl_total_sum'] / df_per_capita['populacao_sum']
                        st.bar_chart(df_per_capita['valor_por_habitante'].sort_values(ascending=False).head(15), color="#D13F42")

                with abas[1]:
                    st.subheader("Ranking por Região")
                    if 'regiao_nome' in df_filtrado.columns:
                        soma_por_regiao = df_filtrado.groupby('regiao_nome')['vl_total'].sum().sort_values(ascending=False)
                        st.bar_chart(soma_por_regiao)
                        qtd_por_regiao = df_filtrado.groupby('regiao_nome')['qtd_total'].sum().sort_values(ascending=False)
                        st.bar_chart(qtd_por_regiao, color="#D13F42")

                with abas[2]:
                    st.subheader("Evolução Mensal do Valor Total")
                    df_temporal = df_filtrado.copy()
                    df_temporal['data'] = pd.to_datetime(df_filtrado['ano_aih'].astype(str) + '-' + df_filtrado['mes_aih'].astype(str))
                    soma_mensal = df_temporal.groupby('data')['vl_total'].sum().sort_index()
                    st.line_chart(soma_mensal)

                with abas[3]:
                    st.subheader("Mapa de Calor")
                    if 'lat' in df_filtrado.columns:
                        df_mapa = df_filtrado.dropna(subset=['lat', 'lon', 'vl_total'])
                        if not df_mapa.empty:
                            mapa_calor = folium.Map(location=[df_mapa['lat'].mean(), df_mapa['lon'].mean()],
                                                    zoom_start=8, tiles="cartodbdark_matter")
                            HeatMap(df_mapa[['lat', 'lon', 'vl_total']].values.tolist(), radius=15).add_to(mapa_calor)
                            st_folium(mapa_calor, use_container_width=True, height=500)
                        else:
                            st.warning("Não há dados geográficos para exibir.")
                    else:
                        st.warning("Colunas de latitude e longitude não encontradas.")

                with abas[4]:
                    st.subheader("Amostra dos Dados")
                    st.dataframe(df_filtrado.head(100))
                
                with abas[5]:
                    st.subheader("Análise por Tipo de Procedimento")

                    # Mapeamento dos nomes das colunas para nomes legíveis
                    mapeamento_grupos = {
                        'vl_02': 'Diagnósticos',
                        'vl_03': 'Clínicos',
                        'vl_04': 'Cirúrgicos',
                        'vl_05': 'Transplantes',
                        'vl_06': 'Medicamentos',
                        'vl_07': 'Órteses e Próteses',
                        'vl_08': 'Ações Complementares'
                    }
                    colunas_grupos = list(mapeamento_grupos.keys())
                    soma_grupos = df_filtrado[colunas_grupos].sum().rename(index=mapeamento_grupos).sort_values(ascending=False)
                    soma_grupos = soma_grupos[soma_grupos > 0]

                    if not soma_grupos.empty:
                        st.markdown("##### Proporção de Gasto por Grupo de Procedimento")
                        fig_pizza = px.pie(soma_grupos, values=soma_grupos.values, names=soma_grupos.index, hole=0.4)
                        st.plotly_chart(fig_pizza, use_container_width=True)
                    
                    st.markdown("---")

                    mapeamento_cirurgias = {
                        'vl_0401': 'Pele e Mucosa', 'vl_0403': 'Sistema Nervoso', 'vl_0404': 'Cabeça e Pescoço',
                        'vl_0405': 'Visão', 'vl_0406': 'Aparelho Circulatório', 'vl_0407': 'Aparelho Digestivo',
                        'vl_0408': 'Osteomuscular', 'vl_0409': 'Geniturinário', 'vl_0411': 'Obstétrica',
                        'vl_0416': 'Oncologia'
                    }
                    colunas_cirurgias = list(mapeamento_cirurgias.keys())
                    soma_cirurgias = df_filtrado[colunas_cirurgias].sum().rename(index=mapeamento_cirurgias).sort_values(ascending=False)
                    soma_cirurgias = soma_cirurgias[soma_cirurgias > 0]

                    if not soma_cirurgias.empty:
                        st.markdown("##### Valor Gasto nos Principais Tipos de Cirurgia (R$)")
                        st.bar_chart(soma_cirurgias)
                
            st.markdown("</div>", unsafe_allow_html=True)
            footer()

    else:
        st.warning("A consulta não retornou dados.")
else:
    st.error("A conexão com o banco de dados falhou.")
