import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Dashboard Dengue", layout="wide")

DATA_FILE = "dengue_data.xlsx"

COVE = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#6250d6', '#e34948']
MUTED = '#898781'


@st.cache_data
def load_data(path):
    df = pd.read_excel(path)
    return df


def normalizar_criterio(v):
    v = str(v).strip().lower()
    if v in ('1', '1.0', 'laboratorial'):
        return 'Laboratorial'
    if v in ('2', '2.0', 'clinico epidemiologico', 'clínico epidemiológico', 'clínico-epidemiológico'):
        return 'Clínico-Epidemiológico'
    if v in ('3', '3.0', 'em investigacao', 'em investigação'):
        return 'Em investigação'
    if v in ('ignorado', 'nan', 'none'):
        return 'Ignorado'
    return v.title()


def normalizar_evolucao(v):
    v = str(v).strip().lower()
    if v in ('1', '1.0', 'cura'):
        return 'Cura'
    if 'obito' in v or 'óbito' in v:
        if 'outra' in v:
            return 'Óbito por outras causas'
        if 'investig' in v:
            return 'Óbito em investigação'
        return 'Óbito por dengue'
    if v in ('ignorado', 'nan', 'none'):
        return 'Ignorado'
    return v.title()


def normalizar_classi(v):
    v = str(v).strip().lower()
    if v.startswith('descartado'):
        return 'Descartado'
    if v.startswith('dengue grave'):
        return 'Dengue grave'
    if 'sinais de alarme' in v:
        return 'Dengue com sinais de alarme'
    if v == 'dengue':
        return 'Dengue'
    if 'inconclus' in v:
        return 'Inconclusivo'
    return v.title()


def normalizar_raca(v):
    mapa = {1: 'Branca', 2: 'Preta', 3: 'Amarela', 4: 'Parda', 5: 'Indígena', 9: 'Ignorado'}
    try:
        return mapa.get(int(v), 'Ignorado')
    except (ValueError, TypeError):
        return str(v).title() if pd.notna(v) else 'Ignorado'


def normalizar_sexo(v):
    return {'F': 'Feminino', 'M': 'Masculino'}.get(str(v).strip().upper(), 'Ignorado')


def faixa_etaria(idade):
    if pd.isna(idade):
        return 'Ignorado'
    if idade < 1:
        return '<1 ano'
    if idade < 5:
        return '1-4'
    if idade < 10:
        return '5-9'
    if idade < 15:
        return '10-14'
    if idade < 20:
        return '15-19'
    if idade < 30:
        return '20-29'
    if idade < 40:
        return '30-39'
    if idade < 50:
        return '40-49'
    if idade < 60:
        return '50-59'
    if idade < 70:
        return '60-69'
    if idade < 80:
        return '70-79'
    return '80+'


ORDEM_FAIXA = ['<1 ano', '1-4', '5-9', '10-14', '15-19', '20-29', '30-39',
               '40-49', '50-59', '60-69', '70-79', '80+', 'Ignorado']


def preparar(df):
    df = df.copy()
    df['DT_NOTIFIC'] = pd.to_datetime(df['DT_NOTIFIC'], errors='coerce')
    df['DT_NASC'] = pd.to_datetime(df['DT_NASC'], errors='coerce')
    df['mes'] = df['DT_NOTIFIC'].dt.to_period('M').astype(str)
    df['idade'] = (df['DT_NOTIFIC'] - df['DT_NASC']).dt.days / 365.25
    df['faixa_etaria'] = df['idade'].apply(faixa_etaria)
    df['sexo_norm'] = df['CS_SEXO'].apply(normalizar_sexo)
    df['raca_norm'] = df['CS_RACA'].apply(normalizar_raca)
    df['classi_norm'] = df['CLASSI_FIN'].apply(normalizar_classi)
    df['criterio_norm'] = df['CRITERIO'].apply(normalizar_criterio)
    df['evolucao_norm'] = df['EVOLUCAO'].apply(normalizar_evolucao)
    return df


def bar_chart(labels, values, orientation='v', color=COVE[0], highlight_last_muted=False):
    colors = [color] * len(values)
    if highlight_last_muted:
        colors[-1] = MUTED
    if orientation == 'v':
        fig = go.Figure(go.Bar(x=labels, y=values, marker_color=colors))
    else:
        fig = go.Figure(go.Bar(x=values, y=labels, orientation='h', marker_color=colors))
        fig.update_yaxes(autorange='reversed')
    fig.update_layout(
        margin=dict(l=10, r=10, t=10, b=10),
        height=340,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        showlegend=False,
    )
    return fig


def donut_chart(labels, values, colors=None):
    fig = go.Figure(go.Pie(labels=labels, values=values, hole=0.55,
                            marker=dict(colors=colors) if colors else None))
    fig.update_layout(
        margin=dict(l=10, r=10, t=10, b=10),
        height=320,
        legend=dict(orientation='h', y=-0.1),
    )
    return fig


st.title("Notificações de dengue - 2026")

raw = load_data(DATA_FILE)
df = preparar(raw)

st.caption(f"Base: {DATA_FILE} · {len(df)} registros individuais (SINAN)")

# ---- Filtros ----
with st.sidebar:
    st.header("Filtros")
    meses = sorted(df['mes'].dropna().unique())
    meses_sel = st.multiselect("Mês da notificação", meses, default=meses)
    bairros = sorted(df['NM_BAIRRO'].dropna().unique())
    bairros_sel = st.multiselect("Bairro", bairros, default=[])

df_f = df[df['mes'].isin(meses_sel)]
if bairros_sel:
    df_f = df_f[df_f['NM_BAIRRO'].isin(bairros_sel)]

# ---- Métricas ----
classi_counts = df_f['classi_norm'].value_counts()
total = len(df_f)
confirmados = (classi_counts.get('Dengue', 0) + classi_counts.get('Dengue grave', 0)
               + classi_counts.get('Dengue com sinais de alarme', 0))
descartados = classi_counts.get('Descartado', 0)
alarme = classi_counts.get('Dengue com sinais de alarme', 0)
grave = classi_counts.get('Dengue grave', 0)
inconclusivo = classi_counts.get('Inconclusivo', 0)
obitos = df_f['evolucao_norm'].value_counts().get('Óbito por dengue', 0)

c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
c1.metric("Total de notificações", total)
c2.metric("Confirmados (todos)", confirmados)
c3.metric("Descartados", descartados)
c4.metric("Dengue c/ sinais de alarme", alarme)
c5.metric("Dengue grave", grave)
c6.metric("Inconclusivo", inconclusivo)
c7.metric("Óbitos por dengue", obitos)

st.divider()

# ---- 1. Data da notificação ----
st.subheader("Notificações por mês")
por_mes = df_f['mes'].value_counts().sort_index()
st.plotly_chart(bar_chart(list(por_mes.index), list(por_mes.values)), width='stretch')

col_a, col_b = st.columns(2)

# ---- 2. Faixa etária ----
with col_a:
    st.subheader("Faixa etária")
    fe = df_f['faixa_etaria'].value_counts().reindex(ORDEM_FAIXA).fillna(0).astype(int)
    st.plotly_chart(bar_chart(list(fe.index), list(fe.values), orientation='h'), width='stretch')

# ---- 5. Bairro ----
with col_b:
    st.subheader("Casos por bairro (top 10)")
    bairro_counts = df_f['NM_BAIRRO'].dropna().value_counts()
    top10 = bairro_counts.head(10)
    nao_inf = df_f['NM_BAIRRO'].isna().sum()
    labels = list(top10.index) + ['Não informado']
    values = list(top10.values) + [nao_inf]
    st.plotly_chart(bar_chart(labels, values, orientation='h', highlight_last_muted=True), width='stretch')

col_c, col_d = st.columns(2)

# ---- 3. Sexo ----
with col_c:
    st.subheader("Sexo")
    sexo = df_f['sexo_norm'].value_counts()
    st.plotly_chart(donut_chart(list(sexo.index), list(sexo.values), colors=[COVE[4], COVE[0]]),
                     width='stretch')

# ---- 4. Raça/cor ----
with col_d:
    st.subheader("Raça/cor")
    raca = df_f['raca_norm'].value_counts()
    st.plotly_chart(donut_chart(list(raca.index), list(raca.values)), width='stretch')

col_e, col_f = st.columns(2)

# ---- 7. Critério ----
with col_e:
    st.subheader("Critério de confirmação")
    crit = df_f['criterio_norm'].value_counts()
    st.plotly_chart(donut_chart(list(crit.index), list(crit.values)), width='stretch')

# ---- 8. Evolução ----
with col_f:
    st.subheader("Evolução do caso")
    evo = df_f['evolucao_norm'].value_counts()
    st.plotly_chart(donut_chart(list(evo.index), list(evo.values)), width='stretch')

# ---- 6. Classificação final ----
st.subheader("Classificação final")
classi = df_f['classi_norm'].value_counts()
st.plotly_chart(bar_chart(list(classi.index), list(classi.values), orientation='h'), width='stretch')
