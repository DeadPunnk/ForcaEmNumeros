import streamlit as st
import duckdb
import altair as alt
import pandas as pd
import urllib.request
import os

# 1. Configurações Iniciais
duckdb.execute("SET memory_limit = '600MB';")

st.set_page_config(
    page_title="Força em Números",
    page_icon="img/agacho-icon.jpeg",
    layout="wide"
)

@st.cache_resource(show_spinner="Conectando ao Google Cloud e preparando base de dados... (Isso ocorre apenas uma vez)")
def preparar_banco_dados():
    os.makedirs("data", exist_ok=True)
    caminho_local = "data/openpowerlifting.parquet"
    
    url_ = os.getenv("URL_DADOS")
    
    # Baixa o arquivo apenas se ele não existir no disco do servidor
    
    return True

col_icone, col_titulo = st.columns([1, 20])

with col_icone:
    # Ajuste o width para ficar do tamanho ideal da fonte do título
    st.image("img/agacho-icon.jpeg", width=45) 

with col_titulo:
    st.title("Estatísticas de peso")
    st.info(
    "**Fonte dos Dados:** Esta página utiliza dados do projeto [OpenPowerlifting](https://www.openpowerlifting.org). "
    "Você pode baixar uma cópia dos dados originais em [gitlab.com/openpowerlifting/opl-data](https://gitlab.com/openpowerlifting/opl-data)."
)

    st.markdown("""
        ## O objetivo do projeto é a visualização e exploração dos dados de Powerlifters que foram cadastrados no OpenPowerlifting
        Para feedback responda esse formulário: :point_right: [Formulário para FeedBack](https://docs.google.com/forms/d/e/1FAIpQLSfUupaye1Iqo9Ck4Kboc9sjt7zwY_cGpIMAT_n2FPGpAIYi4Q/viewform?usp=header) :point_left:

        """)

# ==========================================
# 2. FILTROS GLOBAIS
# ==========================================
col_filtro1, col_filtro2 = st.columns(2)

with col_filtro1:
    modalidade = st.selectbox(
        "Modalidade",
        ["Raw", "Wraps", "Single-ply", "Multi-ply", "Straps"],
        index=0
    )

with col_filtro2:
    sexo_display = st.selectbox(
        "Sexo",
        ["Masculino", "Feminino"],
        index=0
    )
    mapa_sexo = {"Masculino": "M", "Feminino": "F"}
    sexo_filtro = mapa_sexo[sexo_display]

st.divider()

# ==========================================
# 3. FUNÇÕES DE RENDERIZAÇÃO ISOLADAS
# ==========================================

def renderizar_visao_geral(mod, sex):
    """Renderiza os gráficos de barra e a dispersão geral (Top 100)."""
    
    # Busca os 100 melhores da modalidade/sexo
    query = """
        SELECT 
            Name, 
            MAX(Best3SquatKg) as MaiorAgacho, 
            MAX(Best3BenchKg) AS MaiorSupino, 
            MAX(Best3DeadliftKg) as MaiorTerra, 
            MAX(TotalKg) AS TotalKg,
            ANY_VALUE(BodyweightKg) AS BodyweightKg,
            MAX(Dots) AS Dots
        FROM 'data/openpowerlifting.parquet'
        WHERE Equipment = ? AND Sex = ?
        GROUP BY Name
        ORDER BY TotalKg DESC
        LIMIT 100
    """
    df_geral = duckdb.execute(query, [mod, sex]).df()
    
    if df_geral.empty:
        st.warning("Nenhum dado encontrado para estes filtros.")
        return

    # --- GRÁFICOS DE BARRA (TOP 10 FIXO) ---
    top_10 = df_geral.head(10)
    col_esq, col_dir = st.columns(2)
    
    with col_esq:
        st.markdown(f"**Top 10 Maiores Totais - {mod}**")
        chart_totais = alt.Chart(top_10).mark_bar().encode(
            x=alt.X("TotalKg:Q", title="Total (Kg)"),
            y=alt.Y("Name:N", sort="-x", title="Atleta"), 
            color=alt.value('#bd1e1e')
        ).properties(height=400)
        st.altair_chart(chart_totais, use_container_width=True)

    with col_dir:
        st.markdown(f"**Top 10 Maiores Levantamentos - {mod}**")
        df_melted = top_10.melt(
            id_vars=['Name'], 
            value_vars=['MaiorAgacho', 'MaiorSupino', 'MaiorTerra'], 
            var_name='Levantamento', 
            value_name='Carga'
        )
        df_melted['Carga'] = pd.to_numeric(df_melted['Carga'], errors='coerce').fillna(0)
        
        escala_cores = alt.Scale(domain=['MaiorAgacho', 'MaiorSupino', 'MaiorTerra'], range=['#bd1e1e', '#0892a5', '#314158'])
            
        barras = alt.Chart(df_melted).mark_bar(opacity=1).encode(
            x=alt.X("Carga:Q", title="Carga (Kg)", stack="zero"),
            y=alt.Y("Name:N", sort=None, title="Atleta"), 
            color=alt.Color("Levantamento:N", scale=escala_cores),
            order=alt.Order("Levantamento:N", sort="ascending") 
        )
        textos = alt.Chart(df_melted).mark_text(align='right', dx=-5, color='white', fontWeight='bold').encode(
            x=alt.X("Carga:Q", stack="zero"),
            y=alt.Y("Name:N", sort=None),
            text=alt.Text("Carga:Q", format=".1f"),
            detail='Levantamento:N', 
            order=alt.Order("Levantamento:N", sort="ascending") 
        )
        st.altair_chart((barras + textos).properties(height=400), use_container_width=True, theme=None)

    st.divider()

    # --- GRÁFICO DE DISPERSÃO GERAL ---
    st.markdown("**Dispersão de Eficiência Geral: Peso Corporal vs Total**")
    
    # Slider exclusivo
    limite_geral = st.slider("Quantidade de Atletas (Geral)", 10, 100, 50, 1, key="slider_geral")
    df_scatter_geral = df_geral.head(limite_geral)
    
    chart_disp_geral = alt.Chart(df_scatter_geral).mark_circle(opacity=0.85).encode(
        x=alt.X("BodyweightKg:Q", title="Peso Corporal (Kg)", scale=alt.Scale(zero=False)),
        y=alt.Y("TotalKg:Q", title="Total Levantado (Kg)", scale=alt.Scale(zero=False)),
        size=alt.Size("Dots:Q", title="Pontuação DOTS", scale=alt.Scale(range=[50, 350])),
        color=alt.Color("Dots:Q", title="DOTS", scale=alt.Scale(scheme="reds")),
        tooltip=['Name', 'BodyweightKg', 'TotalKg', alt.Tooltip('Dots:Q', format='.2f')]
    ).properties(height=500)
    
    st.altair_chart(chart_disp_geral, use_container_width=True, theme=None)


def renderizar_visao_categoria(mod, sex):
    """Renderiza a dispersão e os levantamentos focados numa categoria de peso específica."""
    st.divider()
    st.markdown("**Análise por Categoria de Peso**")
    
    col_cat1, col_cat2 = st.columns(2)
    with col_cat1:
        categoria_peso = st.selectbox(
            "Selecione a Categoria de Peso (Kg)",
            ["52", "56", "60", "67.5", "75", "82.5", "90", "100", "110", "125", "140", "140+"],
            index=1 # Mantém os 56kg selecionados por padrão
        )
    with col_cat2:
        # Slider para controlar a dispersão
        limite_categoria = st.slider("Quantidade de Atletas (Dispersão Categoria)", 10, 100, 50, 1, key="slider_categoria")
    
    # Adicionámos as colunas dos 3 levantamentos à query
    query = """
        SELECT 
            Name, 
            MAX(Best3SquatKg) as MaiorAgacho, 
            MAX(Best3BenchKg) AS MaiorSupino, 
            MAX(Best3DeadliftKg) as MaiorTerra, 
            MAX(TotalKg) AS TotalKg,
            ANY_VALUE(BodyweightKg) AS BodyweightKg,
            ANY_VALUE(Age) AS Age,
            MAX(Dots) AS Dots
        FROM 'data/openpowerlifting.parquet'
        WHERE Equipment = ? AND Sex = ? AND WeightClassKg = ?
        GROUP BY Name
        ORDER BY TotalKg DESC
        LIMIT 100
    """
    df_cat = duckdb.execute(query, [mod, sex, categoria_peso]).df()
    
    if df_cat.empty:
        st.warning("Nenhum dado encontrado para esta categoria.")
        return
        
    # --- Divide a tela em duas colunas para os gráficos da categoria ---
    col_esq_cat, col_dir_cat = st.columns(2)
    
    with col_esq_cat:
        st.markdown(f"**Corte de Peso vs Total (Top {limite_categoria})**")
        df_scatter_cat = df_cat.head(limite_categoria)
        
        chart_disp_cat = alt.Chart(df_scatter_cat).mark_circle(opacity=0.85, size=90).encode(
            x=alt.X("BodyweightKg:Q", title="Peso Corporal no Dia (Kg)", scale=alt.Scale(zero=False)),
            y=alt.Y("TotalKg:Q", title="Total Levantado (Kg)", scale=alt.Scale(zero=False)),
            color=alt.Color("Dots:Q", title="DOTS", scale=alt.Scale(scheme="reds")),
            tooltip=['Name', 'Age', 'BodyweightKg', 'TotalKg', alt.Tooltip('Dots:Q', format='.2f')]
        ).properties(height=500)
        
        st.altair_chart(chart_disp_cat, use_container_width=True, theme=None)

    with col_dir_cat:
        st.markdown(f"**Composição do Total (Top 10 - {categoria_peso}kg)**")
        
        # Filtra estritamente os top 10 da categoria selecionada para o gráfico de barras
        top_10_cat = df_cat.head(10)
        
        df_melted_cat = top_10_cat.melt(
            id_vars=['Name'], 
            value_vars=['MaiorAgacho', 'MaiorSupino', 'MaiorTerra'], 
            var_name='Levantamento', 
            value_name='Carga'
        )
        df_melted_cat['Carga'] = pd.to_numeric(df_melted_cat['Carga'], errors='coerce').fillna(0)
        
        escala_cores = alt.Scale(domain=['MaiorAgacho', 'MaiorSupino', 'MaiorTerra'], range=['#bd1e1e', '#0892a5', '#314158'])
            
        barras_cat = alt.Chart(df_melted_cat).mark_bar(opacity=1).encode(
            x=alt.X("Carga:Q", title="Carga (Kg)", stack="zero"),
            y=alt.Y("Name:N", sort=None, title="Atleta"), 
            color=alt.Color("Levantamento:N", scale=escala_cores),
            order=alt.Order("Levantamento:N", sort="ascending") 
        )
        
        textos_cat = alt.Chart(df_melted_cat).mark_text(align='right', dx=-5, color='white', fontWeight='bold').encode(
            x=alt.X("Carga:Q", stack="zero"),
            y=alt.Y("Name:N", sort=None),
            text=alt.Text("Carga:Q", format=".1f"),
            detail='Levantamento:N', 
            order=alt.Order("Levantamento:N", sort="ascending") 
        )
        
        # Ajustei a altura (height=500) para ficar perfeitamente alinhado com o gráfico de dispersão ao lado
        chart_lifts_cat = (barras_cat + textos_cat).properties(height=500)
        st.altair_chart(chart_lifts_cat, use_container_width=True, theme=None)


def renderizar_pesquisa_atleta():
    """Renderiza a área de pesquisa individual de atletas e a sua evolução no tempo."""
    st.divider()
    st.markdown("## 🔍 Pesquisa de Atleta")
    st.markdown("Analise o histórico e a evolução temporal de um atleta específico.")
    
    # Campo de texto para buscar o nome
    nome_pesquisa = st.text_input(
        "Digite o nome exato do atleta da maneira como foi cadastrado no OpenPowerlifting:", 
        placeholder="Insira o nome e pressione Enter..."
    )
    
    # Só executa a pesquisa se o utilizador tiver digitado algo
    if nome_pesquisa:
        # A query usa ILIKE para ignorar maiúsculas/minúsculas e busca o histórico cronológico
        query_hist = """
            SELECT 
                CAST(Date AS DATE) AS Data_Competicao,
                MAX(Best3SquatKg) as Agachamento,
                MAX(Best3BenchKg) as Supino,
                MAX(Best3DeadliftKg) as Terra,
                MAX(TotalKg) as Total,
                MAX(Dots) as Dots
            FROM 'data/openpowerlifting.parquet'
            WHERE Name ILIKE ? AND Date IS NOT NULL
            GROUP BY Data_Competicao
            ORDER BY Data_Competicao ASC
        """
        
        # O DuckDB faz a busca instantânea pelo nome no disco
        df_hist = duckdb.execute(query_hist, [nome_pesquisa]).df()
        
        if df_hist.empty:
            st.warning(f"Nenhum atleta encontrado com o nome '{nome_pesquisa}'. Verifique a ortografia (o OpenPowerlifting costuma usar nomes completos ou abreviações específicas).")
            return
            
        st.success(f"Histórico carregado para: **{nome_pesquisa.title()}** ({len(df_hist)} competições registadas)")
        
        # --- CARDS COM OS RECORDES PESSOAIS (ALL-TIME BESTS) ---
        # Pega o maior valor de cada coluna em toda a história do atleta
        melhor_agacho = df_hist['Agachamento'].max()
        melhor_supino = df_hist['Supino'].max()
        melhor_terra = df_hist['Terra'].max()
        melhor_total = df_hist['Total'].max()
        
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        col_m1.metric("Maior Agachamento", f"{melhor_agacho} kg" if pd.notna(melhor_agacho) else "-")
        col_m2.metric("Maior Supino", f"{melhor_supino} kg" if pd.notna(melhor_supino) else "-")
        col_m3.metric("Maior Terra", f"{melhor_terra} kg" if pd.notna(melhor_terra) else "-")
        col_m4.metric("Maior Total", f"{melhor_total} kg" if pd.notna(melhor_total) else "-")
        
        st.write("") # Espaçamento
        
        # --- GRÁFICOS DE SÉRIES TEMPORAIS ---
        col_graf1, col_graf2 = st.columns(2)
        
        with col_graf1:
            st.markdown("**Evolução: Total Levantado vs Eficiência (DOTS)**")
            
            # Gráfico base com o eixo X sendo a Data (Temporal)
            base = alt.Chart(df_hist).encode(
                x=alt.X('Data_Competicao:T', title='Data da Competição')
            )
            
            # Linha do Total (Azul Escuro)
            linha_total = base.mark_line(point=True, color='#0892a5', strokeWidth=3).encode(
                y=alt.Y('Total:Q', title='Total (Kg)', scale=alt.Scale(zero=False)),
                tooltip=[alt.Tooltip('Data_Competicao:T', title='Data'), alt.Tooltip('Total:Q', title='Total (Kg)')]
            )
            
            # Linha do DOTS (Vermelho)
            linha_dots = base.mark_line(point=True, color='#bd1e1e', strokeWidth=3).encode(
                y=alt.Y('Dots:Q', title='Pontuação DOTS', scale=alt.Scale(zero=False)),
                tooltip=[alt.Tooltip('Data_Competicao:T', title='Data'), alt.Tooltip('Dots:Q', title='DOTS', format='.2f')]
            )
            
            # Camadas com eixos Y independentes (resolve_scale) para mostrar Kg e Pontos no mesmo quadro
            chart_evolucao = alt.layer(linha_total, linha_dots).resolve_scale(
                y='independent'
            ).properties(height=400)
            
            st.altair_chart(chart_evolucao, use_container_width=True, theme=None)
            
        with col_graf2:
            st.markdown("**Progressão por Levantamento**")
            
            # Derrete o dataframe para ter os 3 levantamentos numa única coluna categórica
            df_hist_melted = df_hist.melt(
                id_vars=['Data_Competicao'],
                value_vars=['Agachamento', 'Supino', 'Terra'],
                var_name='Levantamento',
                value_name='Carga'
            ).dropna(subset=['Carga']) # Ignora competições onde ele não fez um dos lifts (ex: campeonato só de supino)
            
            escala_cores = alt.Scale(domain=['Agachamento', 'Supino', 'Terra'], range=['#bd1e1e', '#0892a5', '#314158'])
            
            chart_lifts_tempo = alt.Chart(df_hist_melted).mark_line(point=True, strokeWidth=2.5).encode(
                x=alt.X('Data_Competicao:T', title='Data da Competição'),
                y=alt.Y('Carga:Q', title='Carga (Kg)', scale=alt.Scale(zero=False)),
                color=alt.Color('Levantamento:N', scale=escala_cores),
                tooltip=[
                    alt.Tooltip('Data_Competicao:T', title='Data'),
                    alt.Tooltip('Levantamento:N', title='Movimento'),
                    alt.Tooltip('Carga:Q', title='Carga (Kg)')
                ]
            ).properties(height=400)
            
            st.altair_chart(chart_lifts_tempo, use_container_width=True, theme=None)


# ==========================================
# 4. EXECUÇÃO DO APLICATIVO
# ==========================================
if modalidade and sexo_filtro:
    renderizar_visao_geral(modalidade, sexo_filtro)
    renderizar_visao_categoria(modalidade, sexo_filtro)

renderizar_pesquisa_atleta()