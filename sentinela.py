import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
import datetime

# ─── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Sentinela Bravo — Skill BO",
    page_icon="🛡️",
    layout="centered"
)

st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; }
    h1 { font-size: 2.2rem !important; font-weight: 800 !important; }
    .stTextArea textarea { font-family: monospace; font-size: 0.85rem; }
    .stButton > button[kind="primary"] {
        background-color: #c0392b;
        color: white;
        font-weight: 700;
        font-size: 1rem;
        border: none;
        padding: 0.6rem;
    }
    .stButton > button[kind="primary"]:hover { background-color: #a93226; }
    div[data-testid="stAlert"] { border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# ─── Cabeçalho ─────────────────────────────────────────────────────────────────
st.markdown("# 🛡️ Sentinela Bravo")
st.caption("Skill BO • Boletim de Ocorrência Inteligente — Stellantis Betim")
st.markdown("---")

# ─── Inicialização do Estado de Sessão (Evita sumir o texto ao baixar) ──────────
if "bo_texto" not in st.session_state:
    st.session_state.bo_texto = None
if "nome_arquivo" not in st.session_state:
    st.session_state.nome_arquivo = ""

# ─── Configuração da API ────────────────────────────────────────────────────────
# Busca flexível para evitar quebras por nomenclatura de chave
api_key = st.secrets.get("GOOGLE_API_KEY") or st.secrets.get("GEMINI_API_KEY")

if api_key:
    genai.configure(api_key=api_key)
    st.success("✅ Google Gemini AI Studio — conectado com sucesso")
else:
    st.error("⚠️ Chave de API não encontrada nos Secrets.")
    st.info(
        "**Como obter sua chave gratuita:**\n"
        "1. Acesse [aistudio.google.com/apikey](https://aistudio.google.com/apikey)\n"
        "2. Clique em **Create API key**\n"
        "3. No Streamlit → Settings → Secrets → adicione:\n"
        "```toml\nGOOGLE_API_KEY = \"sua-chave-aqui\"\n```"
    )
    st.stop()

# ─── Formulário ────────────────────────────────────────────────────────────────
st.markdown("### 🚨 Identificação da Ocorrência")

col1, col2 = st.columns(2)
with col1:
    data_oco = st.date_input("Data da ocorrência", value=datetime.date.today())
with col2:
    hora_oco = st.selectbox(
        "Hora da ocorrência (hora do fato)",
        options=[f"{h:02d}:{m:02d}" for h in range(0, 24) for m in range(0, 60, 10)],
        index=74  # 12:20 como padrão
    )

local_exato = st.text_input(
    "Local exato do fato",
    placeholder="Ex: Galpão 89 coluna 32AC, Portaria 03 baia 01, Pátio externo"
)

tipo_ref = st.text_input(
    "Referência / tipo (opcional — a IA identifica automaticamente)",
    placeholder="Ex: Acidente com empilhadeira, Furto, Avaria de carga, Acesso indevido"
)

relato_bruto = st.text_area(
    "Relato bruto da ocorrência",
    placeholder=(
        "Descreva livremente o que aconteceu. Exemplo:\n"
        "segurança para registrar carga tombada devida o operador de empilhadeira "
        "Hyster envolvida EPG1887 transportando rack elevado acima da torre, "
        "rack vindo ao solo por volta das 22h30, foram acionados líderes Elysio Richard "
        "para averiguação matrícula 997765 teen líder stellantis logis..."
    ),
    height=170
)

# ─── Upload de Fotos ───────────────────────────────────────────────────────────
st.markdown("### 📷 Evidências Fotográficas")
st.caption("A IA extrai automaticamente: placas, matrículas, documentos, equipamentos e outras informações visíveis.")

fotos = st.file_uploader(
    "Adicione fotos da ocorrência",
    type=["jpg", "jpeg", "png", "webp"],
    accept_multiple_files=True,
    label_visibility="collapsed"
)

if fotos:
    cols = st.columns(min(len(fotos), 3))
    for i, foto in enumerate(fotos[:3]):
        with cols[i]:
            st.image(foto, use_container_width=True, caption=f"Foto {i+1}")
    if len(fotos) > 3:
        st.caption(f"+ {len(fotos) - 3} foto(s) adicional(is) carregada(s).")

st.markdown("---")

# ─── Botão Gerar ──────────────────────────────────────────────────────────────
gerar = st.button("🚀 Gerar Boletim de Ocorrência", use_container_width=True, type="primary")

if gerar:
    if not relato_bruto.strip():
        st.warning("⚠️ Preencha o relato da ocorrência antes de gerar o BO.")
        st.stop()

    with st.spinner("🔄 Processando com Google Gemini... aguarde."):
        try:
            model = genai.GenerativeModel("gemini-2.0-flash")

            prompt = f"""Você é especialista em segurança patrimonial da Stellantis Betim, MG.
Gere um Boletim de Ocorrência (BO) formal, completo e profissional em português brasileiro.

═══════════════════════════════════════════
DADOS FORNECIDOS PELO VIGILANTE:
═══════════════════════════════════════════
Data do fato:      {data_oco.strftime('%d/%m/%Y')}
Hora do fato:      {hora_oco}
Local exato:       {local_exato or 'Não informado'}
Tipo/Referência:   {tipo_ref or 'Identificar automaticamente pelo relato'}
Relato bruto:      {relato_bruto}
═══════════════════════════════════════════

REGRAS OBRIGATÓRIAS:
1. Use linguagem formal e técnica de vigilância patrimonial.
2. Atribua corretamente as ações às pessoas mencionadas no relato (operador, líder, colaborador, etc.).
   Não atribua as ações ao vigilante que escreve, salvo quando ele for o agente direto.
3. Corrija erros de digitação e gramática do relato bruto — preserve os dados (nomes, matrículas, placas).
4. Estruture o BO com as seguintes seções:
   ────────────────────────────────────────
   BOLETIM DE OCORRÊNCIA — STELLANTIS BETIM
   ────────────────────────────────────────
   1. IDENTIFICAÇÃO DA OCORRÊNCIA
   2. DESCRIÇÃO DOS FATOS
   3. ANÁLISE DAS EVIDÊNCIAS (se houver fotos, descreva o que foi identificado)
   4. PROVIDÊNCIAS TOMADAS
   5. CONCLUSÃO
   ────────────────────────────────────────
   Vigilante Responsável: _______________
   Matrícula: ___________________________
   Data/Hora do Registro: _______________
   Assinatura: __________________________
   ────────────────────────────────────────
5. Se não houver fotos, omita a seção ANÁLISE DAS EVIDÊNCIAS.
6. O BO deve ter entre 300 e 600 palavras, objetivo e completo.

Gere o BO agora:"""

            content = [prompt]

            # Otimização Inteligente de Imagens para ambiente de produção (Reduz consumo e acelera a API)
            if fotos:
                content.append(
                    "A seguir estão as fotos de evidências. Para cada imagem, identifique e liste: "
                    "placas de veículos, códigos de empilhadeira/equipamento, números de matrícula visíveis, "
                    "documentos, avarias, posição dos objetos e qualquer detalhe relevante para o BO."
                )
                for foto in fotos:
                    foto.seek(0)
                    img = Image.open(io.BytesIO(foto.read()))
                    
                    # Redimensiona mantendo a proporção para não sobrecarregar a rede móvel da portaria
                    img.thumbnail((1024, 1024))
                    buffer = io.BytesIO()
                    img.save(buffer, format="JPEG", quality=78, optimize=True)
                    
                    content.append(Image.open(buffer))

            response = model.generate_content(content)
            
            # Salvando o resultado no Estado da Sessão
            st.session_state.bo_texto = response.text
            st.session_state.nome_arquivo = (
                f"BO_Stellantis_{data_oco.strftime('%Y%m%d')}"
                f"_{hora_oco.replace(':', '')}.txt"
            )

        except Exception as e:
            err = str(e)
            st.error(f"❌ Erro ao processar: {err}")
            if "quota" in err.lower() or "429" in err:
                st.info("Limite de cota temporário do plano gratuito. Aguarde alguns segundos.")

# ─── Área de Exibição Persistente (Impedem o desaparecimento dos dados) ───────
if st.session_state.bo_texto:
    st.success("✅ Boletim gerado com sucesso!")
    st.markdown("---")
    st.markdown("## 📋 Boletim de Ocorrência")

    # Exibir BO
    st.text_area(
        label="",
        value=st.session_state.bo_texto,
        height=600,
        label_visibility="collapsed",
        key="bo_output"
    )

    # Botão de download funcional e testado
    st.download_button(
        label="⬇️ Baixar BO (.txt)",
        data=st.session_state.bo_texto.encode("utf-8"),
        file_name=st.session_state.nome_arquivo,
        mime="text/plain",
        use_container_width=True
    )
