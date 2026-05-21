import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
import datetime

# ─── Configuração de Página ───────────────────────────────────────────────────
st.set_page_config(
    page_title="Sentinela Bravo — Auditor de BO",
    page_icon="🛡️",
    layout="centered"
)

# Estilização CSS para máxima legibilidade no celular
st.markdown("""
<style>
    .block-container { padding-top: 1rem; }
    h1 { font-size: 2rem !important; font-weight: 800 !important; color: #1e3d59; }
    .stTextArea textarea { font-family: 'Courier New', monospace; font-size: 0.9rem; }
    .stButton > button[kind="primary"] {
        background-color: #1e3d59;
        color: white;
        font-weight: 700;
        font-size: 1.05rem;
        border: none;
        padding: 0.75rem;
        border-radius: 6px;
    }
    .stButton > button[kind="primary"]:hover { background-color: #17b978; color: white; }
    div[data-testid="stAlert"] { border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

st.markdown("# 🛡️ Sentinela Bravo")
st.caption("Módulo Boletinista Auditor — Stellantis Betim")
st.markdown("---")

# Inicialização de variáveis na sessão para persistência absoluta
if "documento_completo" not in st.session_state:
    st.session_state.documento_completo = None
if "nome_arquivo" not in st.session_state:
    st.session_state.nome_arquivo = ""

# ─── Configuração da Conexão com API ──────────────────────────────────────────
api_key = st.secrets.get("GOOGLE_API_KEY") or st.secrets.get("GEMINI_API_KEY")

if api_key:
    genai.configure(api_key=api_key)
else:
    st.error("⚠️ Chave de API não configurada nos Secrets do Streamlit.")
    st.stop()

# ─── Painel de Entrada de Dados ───────────────────────────────────────────────
st.markdown("### 📝 Entrada de Dados Operacionais")

col1, col2 = st.columns(2)
with col1:
    data_fato = st.date_input("Data do Fato", value=datetime.date.today())
with col2:
    hora_fato = st.selectbox(
        "Hora do Fato",
        options=[f"{h:02d}:{m:02d}" for h in range(0, 24) for m in range(0, 60, 5)],
        index=144
    )

local_detalhado = st.text_input(
    "Local Exato do Fato",
    placeholder="Ex: Portaria 03 baia 02, Galpão 89 coluna 32AC..."
)

relato_whatsapp = st.text_area(
    "Insira o Relato Bruto (WhatsApp / Campo)",
    placeholder="Cole aqui as mensagens informais recebidas das equipes de campo...",
    height=180
)

# ─── Módulo Compressor de Imagem Nativo ───────────────────────────────────────
st.markdown("### 📷 Evidências Fotográficas")
fotos_carregadas = st.file_uploader(
    "Arraste ou selecione as fotos",
    type=["jpg", "jpeg", "png", "webp"],
    accept_multiple_files=True,
    label_visibility="collapsed"
)

imagens_processadas_api = []

if fotos_carregadas:
    for foto in fotos_carregadas:
        try:
            foto.seek(0)
            img = Image.open(io.BytesIO(foto.read()))
            img.thumbnail((1024, 1024)) # Redimensionamento leve ideal para redes móveis
            
            buffer = io.BytesIO()
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
                
            img.save(buffer, format="JPEG", quality=70, optimize=True)
            buffer.seek(0)
            imagens_processadas_api.append(Image.open(buffer))
        except Exception:
            pass # Ignora imagens corrompidas para não travar o fluxo
            
    if imagens_processadas_api:
        st.success(f"✅ {len(imagens_processadas_api)} imagem(ns) otimizada(s) para o celular!")

st.markdown("---")

# ─── Execução do Processamento ────────────────────────────────────────────────
disparar_analise = st.button("🛡️ Auditar e Confeccionar Boletim", use_container_width=True, type="primary")

if disparar_analise:
    if not relato_whatsapp.strip():
        st.warning("⚠️ Forneça o relato bruto antes de gerar.")
        st.stop()
        
    with st.spinner("🔄 Processando dados... Por favor, mantenha a página aberta."):
        try:
            modelo_boletinista = genai.GenerativeModel("gemini-2.0-flash")
            
            prompt = f"""Você é o Boletinista Auditor da Segurança Patrimonial da Stellantis Betim, MG.
Analise as informações fornecidas e gere um documento unificado contendo a AUDITORIA DE OMISSÕES e o BOLETIM DE OCORRÊNCIA FORMATADO.

DATA DO REGISTRO: {data_fato.strftime('%d/%m/%Y')}
HORA DO FATO: {hora_fato}
LOCAL INFORMADO: {local_detalhado if local_detalhado else 'Não especificado'}
RELATO ENVIADO:
\"\"\"
{relato_whatsapp}
\"\"\"

DIRETRIZES DE AUDITORIA:
1. Identifique omissões de dados de Funcionários (Nome, RE, Telefone, Superior válido - lembre que Team Leader não responde por BO).
2. Identifique omissões de dados de Terceiros/Motoristas/Atos Dolosos (RG/CNH, Empresa, Endereço Residencial, Telefone, Filiação).
3. Classifique a ocorrência em uma das naturezas oficiais (Ex: Excesso de Carga Horária, Estacionamento Irregular, Danos de Trânsito Interno - usando Choque/Colisão/Abalroamento conforme a regra técnica. Proibido usar 'danificado', use amassado, riscado, quebrado, etc.).

DIRETRIZES DE FORMATAÇÃO:
Gere um texto limpo, em linguagem culta, formal e simples. O layout deve ser perfeitamente alinhado para cópia no Bloco de Notas ou Word.

Estruture sua resposta estritamente neste formato de texto abaixo:

RELATÓRIO DE AUDITORIA OPERACIONAL
----------------------------------------------------------------------
[Liste aqui os dados que faltam para o encerramento do turno ou se há pendências de terceiros/líderes. Se estiver tudo OK, escreva 'NENHUMA OMISSÃO DETECTADA'].
Justificativa da Natureza: [Explique o motivo técnico da classificação].

BOLETIM DE OCORRÊNCIA INTERNO — STELLANTIS BETIM
----------------------------------------------------------------------
1. DADOS LOGÍSTICOS
- Data do Fato: {data_fato.strftime('%d/%m/%Y')}
- Hora do Fato: {hora_fato}
- Local Exato: {local_detalhado if local_detalhado else 'Informado no histórico'}
- Natureza da Ocorrência: [Classificação Técnica Exata]

2. QUALIFICAÇÃO DOS ENVOLVIDOS
[Separe por tópicos Funcionários e Terceiros com seus respectivos dados].

3. HISTÓRICO DOS FATOS (CRONOLOGIA)
[Texto claro, formal e impessoal narrando o início, meio e fim, incluindo as alegações de todos os envolvidos].

4. PROVIDÊNCIAS ADOTADAS
[Encaminhamentos, isolamentos, acionamentos de liderança ou recusas registradas].

5. REGISTRO
- Vigilante Relator: ___________________________ RE: ___________
- Inspetor de Plantão Ciente: ___________________________
- Data/Hora da Emissão: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}
----------------------------------------------------------------------
"""

            conteudo_requisicao = [prompt]
            if imagens_processadas_api:
                conteudo_requisicao.append("\n[Análise de Evidências Visuais]: Extraia dados das fotos anexadas abaixo:")
                conteudo_requisicao.extend(imagens_processadas_api)

            resposta = modelo_boletinista.generate_content(conteudo_requisicao)
            
            if resposta and hasattr(resposta, "text") and resposta.text:
                st.session_state.documento_completo = resposta.text
                st.session_state.nome_arquivo = f"BO_{data_fato.strftime('%Y%m%d')}_{hora_fato.replace(':', '')}.txt"
            else:
                st.error("❌ A central retornou um documento vazio. Tente novamente em um navegador comum.")
                
        except Exception as e:
            st.error(f"❌ Erro de processamento: {str(e)}")

# ─── Área de Exibição dos Resultados (Persistente) ────────────────────────────
if st.session_state.documento_completo:
    st.success("✅ Documento confeccionado com sucesso!")
    st.markdown("### 📋 Documento Pronto para Cópia / Envio")
    
    st.text_area(
        label="",
        value=st.session_state.documento_completo,
        height=500,
        key="visualizador_final"
    )
    
    st.download_button(
        label="⬇️ Baixar Arquivo para Bloco de Notas / Word (.txt)",
        data=st.session_state.documento_completo.encode("utf-8"),
        file_name=st.session_state.nome_arquivo,
        mime="text/plain",
        use_container_width=True
    )
