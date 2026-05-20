import io
import json
import os
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import google.generativeai as genai
import streamlit as st
from PIL import Image

APP_TITLE = "Sentinela Bravo — Skill BO"

# Lista de modelos em ordem de prioridade para a estratégia de Fallback
MODELS_TO_TRY = [
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-2.0-flash-lite"
]

MAX_IMAGES = 5
MAX_IMAGE_WIDTH = 1280
JPEG_QUALITY = 78

MODEL_HINTS = {
    "🔥 GERAR BOLETIM UNIVERSAL (Qualquer Modelo do Manual)": "Use o modelo mais aderente ao manual para a situação descrita.",
    "📦 Carga Tombada / Peças Molhadas / Danos em Racks": "Exigir dados de carga, transportadora, motorista, MVM, DANFE, rack e destino da avaliação.",
    "❌ Recusa de Carga / Divergência Fiscal / Excesso de Jornada": "Exigir dados de transporte, horários, placas, MVM e justificativas formais.",
    "Acidente de Trânsito / Colisão Interna (Choque ou Abalroamento)": "Exigir veículos, placas, chassi, tipo de impacto, danos por lado e desfecho com CSO/TST/ambulância se houver.",
    "Desvio de Segurança / Quebra de Regra de Ouro (Falta Grave)": "Exigir relato objective, identificação completa, liderança responsável e providências.",
    "Controle de Acesso / Portaria (Notebooks / Instabilidade Ronda)": "Exigir portaria, item recolhido, documentação, guarda de objetos e providência tomada.",
}

def init_page() -> None:
    st.set_page_config(page_title=APP_TITLE, page_icon="🛡️", layout="centered")
    st.markdown(
        """
        <style>
        .main { background-color: #0d1117; }
        h1, h2, h3 { color: #f97316; }
        .subtitle {
            color: #8b949e;
            text-align: center;
            font-size: 1.02rem;
            margin-bottom: 1.2rem;
        }
        .section-card {
            background-color: #161b22;
            padding: 16px;
            border-radius: 14px;
            border: 1px solid #30363d;
            margin-bottom: 14px;
        }
        .section-title {
            color: #f97316;
            font-size: 1.08rem;
            font-weight: 700;
            margin-bottom: 10px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

def get_api_key() -> Optional[str]:
    key = None
    try:
        key = st.secrets.get("GEMINI_API_KEY")
    except Exception:
        key = None
    if not key:
        key = os.getenv("GEMINI_API_KEY")
        
    if key:
        key = key.strip().replace('"', '').replace("'", "")
    return key

def compress_image(uploaded_file: Any) -> Tuple[bytes, Image.Image]:
    raw = uploaded_file.read()
    img = Image.open(io.BytesIO(raw))
    if img.mode != "RGB":
        img = img.convert("RGB")
    img.thumbnail((MAX_IMAGE_WIDTH, MAX_IMAGE_WIDTH))
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    return buffer.getvalue(), img

def safe_date_str(dt: datetime) -> str:
    return dt.strftime("%d/%m/%Y %H:%M")

def parse_json_response(text: str) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(text)
    except Exception:
        pass
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except Exception:
        return None

def build_prompt(payload: Dict[str, Any]) -> str:
    return f"""
Você é a Skill BO Sentinela Bravo.

Regras obrigatórias do manual:
- Linguagem clara, objetiva, factual e sem opinião pessoal.
- Não invente dados.
- Quando um dado não for informado, escreva exatamente "NÃO INFORMADO".
- A hora deve ser a hora do fato, não a hora do preenchimento.

Tarefa:
1) Fazer auditoria de conformidade com o manual.
2) Gerar o boletim interno estruturado.

Formato de saída obrigatório (JSON puro):
{{
  "audit": {{
    "modelo_identificado": "",
    "conformidade": "",
    "dados_criticos_localizados": [],
    "lacunas": []
  }},
  "bo": {{
    "data_hora_fato": "",
    "local_exato": "",
    "acionamento": "",
    "envolvidos": [],
    "ativos_veiculos_documentos": [],
    "dinamica": "",
    "alegacao": "",
    "providencias": [],
    "status": "",
    "anexos_recomendados": []
  }}
}}

Dados do formulário:
{json.dumps(payload, ensure_ascii=False, indent=2)}
""".strip()

def render_kv(label: str, value: Any) -> None:
    st.markdown(f"**{label}:** {value}")

def main() -> None:
    init_page()

    api_key = get_api_key()
    if not api_key:
        st.error("Configure `GEMINI_API_KEY` nos Secrets do Streamlit.")
        st.stop()

    # Inicializa a configuração global da API
    genai.configure(api_key=api_key)

    col1, col2 = st.columns([1, 4])
    with col1:
        try:
            logo = Image.open("sentinela bravo.jpg")
            st.image(logo, width=96)
        except Exception:
            st.write("🛡️")
    with col2:
        st.title("Sentinela Bravo")
        st.markdown(
            "<p class='subtitle'>Skill BO • Boletim de Ocorrência Eletrônico Inteligente para planta industrial</p>",
            unsafe_allow_html=True,
        )

    # Exibe o indicador visual do modelo ativo no topo para controle do turno
    st.info(f"🔄 Modo de Redundância Ativo (Modelos suportados: {', '.join(MODELS_TO_TRY)})")

    with st.form("bo_form", clear_on_submit=False):
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">🚨 Classificação da ocorrência</div>', unsafe_allow_html=True)

        tipo_ocorrencia = st.selectbox("Modelo principal", list(MODEL_HINTS.keys()))
        st.caption(MODEL_HINTS[tipo_ocorrencia])

        data_fato = st.date_input("Data da ocorrência")
        hora_fato = st.time_input("Hora da ocorrência")
        local_exato = st.text_input("Local exato do fato", placeholder="Ex.: Portaria 03, baia 02...")
        vigilante_relator = st.text_input("Vigilante relator / registro")
        lider_responsavel = st.text_input("Líder / Supervisor / Gerente responsável")
        lider_contato = st.text_input("Contato do líder / supervisor / gerente")
        acionamento = st.text_area("Acionamento / providência imediata", height=90)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">📝 Relato bruto</div>', unsafe_allow_html=True)
        relato_bruto = st.text_area("Descreva os fatos", height=180)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">📎 Dados complementares por tipo</div>', unsafe_allow_html=True)
        
        dados_complementares: Dict[str, Any] = {}
        if "Carga Tombada" in tipo_ocorrencia:
            dados_complementares.update({
                "placa_veiculo": st.text_input("Placa do veículo"),
                "mvm": st.text_input("MVM"),
                "danfe": st.text_input("DANFE"),
                "transportadora": st.text_input("Transportadora"),
                "motorista": st.text_input("Nome do motorista"),
                "descricao_peças": st.text_area("Peças / avarias", height=80),
            })
        elif "Colisão" in tipo_ocorrencia or "Choque" in tipo_ocorrencia or "Abalroamento" in tipo_ocorrencia:
            dados_complementares.update({
                "veiculo_1": st.text_input("Veículo 1"),
                "veiculo_2": st.text_input("Veículo 2"),
                "danos_veiculo_1": st.text_area("Danos veículo 1", height=70),
                "danos_veiculo_2": st.text_area("Danos veículo 2", height=70),
                "houve_vitima": st.radio("Houve vítima?", ["Não", "Sim"], horizontal=True),
            })
        else:
            dados_complementares.update({
                "envolvidos": st.text_area("Envolvidos e dados já levantados", height=90),
                "veiculos_documentos": st.text_area("Veículos / documentos", height=90),
            })
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">📸 Evidências</div>', unsafe_allow_html=True)
        arquivos = st.file_uploader("Anexe até 5 imagens", type=["png", "jpg", "jpeg", "webp"], accept_multiple_files=True)
        st.markdown('</div>', unsafe_allow_html=True)

        submit = st.form_submit_button("🚀 Gerar BO")

    if not submit:
        return

    if not relato_bruto.strip() or not local_exato.strip():
        st.warning("Preencha o relato e o local exato antes de prosseguir.")
        st.stop()

    evidencias_pil: List[Image.Image] = []
    for arquivo in arquivos or []:
        try:
            _, pil_img = compress_image(arquivo)
            evidencias_pil.append(pil_img)
        except Exception as exc:
            st.error(f"Erro no processamento da imagem {arquivo.name}: {exc}")
            st.stop()

    payload = {
        "tipo_ocorrencia": tipo_ocorrencia,
        "data_ocorrencia": data_fato.isoformat(),
        "hora_ocorrencia": hora_fato.strftime("%H:%M"),
        "local_exato": local_exato.strip(),
        "vigilante_relator": vigilante_relator.strip(),
        "relato_bruto": relato_bruto.strip(),
        "dados_complementares": dados_complementares,
        "timestamp_geracao": safe_date_str(datetime.now()),
    }

    prompt = build_prompt(payload)
    parts: List[Any] = [prompt] + evidencias_pil

    texto = ""
    parsed = None
    ultimo_erro = ""

    # Execução inteligente com Fallback entre modelos para mitigar o erro 429 (Resource Exhausted)
    with st.spinner("Processando o relato com a Skill BO (Verificando cot
