import io
import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import google.generativeai as genai
import streamlit as st
from PIL import Image

APP_TITLE = "Sentinela Bravo — Skill BO"

MODELS_TO_TRY = [
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-1.5-flash"
]

MAX_IMAGE_WIDTH = 1280
JPEG_QUALITY = 78

MODEL_HINTS = {
    "🔥 GERAR BOLETIM UNIVERSAL": "Use o modelo padrão para a situação descrita.",
    "📦 Carga Tombada / Danos em Racks": "Exigir dados de carga, transportadora, motorista, MVM e DANFE.",
    "❌ Recusa de Carga / Divergência Fiscal": "Exigir dados de transporte, placas, MVM e justificativas.",
    "🚨 Acidente de Trânsito / Colisão Interna": "Exigir veículos, placas, tipo de impacto e danos por lado.",
    "🛡️ Desvio de Segurança / Regra de Ouro": "Exigir relato objetivo, identificação e providências.",
}

def init_page() -> None:
    st.set_page_config(page_title=APP_TITLE, page_icon="🛡️", layout="centered")

def get_all_api_keys() -> List[str]:
    keys = []
    # Tratamento seguro usando .get() para evitar o erro KeyError caso o painel de Secrets esteja vazio
    for secret_name in ["GEMINI_API_KEY", "GEMINI_API_KEY_2", "GEMINI_API_KEY_3"]:
        try:
            key = st.secrets.get(secret_name)
        except Exception:
            key = None
            
        if not key:
            key = os.getenv(secret_name)
            
        if key:
            cleaned = key.strip().replace('"', '').replace("'", "")
            if cleaned and cleaned not in keys:
                keys.append(cleaned)
    return keys

def compress_image(uploaded_file: Any) -> Tuple[bytes, Image.Image]:
    raw = uploaded_file.read()
    img = Image.open(io.BytesIO(raw))
    if img.mode != "RGB":
        img = img.convert("RGB")
    img.thumbnail((MAX_IMAGE_WIDTH, MAX_IMAGE_WIDTH))
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    return buffer.getvalue(), img

def parse_json_response(text: str) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(text)
    except Exception:
        pass
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            return None
    return None

def main() -> None:
    init_page()
    api_keys = get_all_api_keys()
    
    st.title("🛡️ Sentinela Bravo")
    
    # Se não houver chaves configuradas, exibe um aviso amigável na tela do app em vez de quebrar o sistema
    if not api_keys:
        st.warning("⚠️ Atenção: Nenhuma chave de API encontrada nos Secrets do Streamlit.")
        st.info("Por favor, acesse as configurações do aplicativo (Settings > Secrets) e adicione a sua 'GEMINI_API_KEY' para ativar o sistema.")
        st.stop()

    st.caption("Skill BO operacional com redundância de chaves ativa.")

    with st.form("bo_form"):
        tipo_ocorrencia = st.selectbox("Modelo de Ocorrência", list(MODEL_HINTS.keys()))
        local_exato = st.text_input("Local exato")
        relato_bruto = st.text_area("Relato dos fatos")
        arquivos = st.file_uploader("Evidências (Fotos)", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
        submit = st.form_submit_button("🚀 Gerar Relatório")

    if submit:
        if not relato_bruto.strip() or not local_exato.strip():
            st.warning("Por favor, preencha o local e o relato.")
            st.stop()

        evidencias_pil = []
        for arq in arquivos or []:
            try:
                _, pil_img = compress_image(arq)
                evidencias_pil.append(pil_img)
            except Exception:
                st.error(f"Erro ao processar imagem: {arq.name}")
                st.stop()

        payload = {
            "tipo": tipo_ocorrencia,
            "local": local_exato.strip(),
            "relato": relato_bruto.strip(),
            "data_registro": datetime.now().strftime("%d/%m/%Y %H:%M")
        }

        prompt = f"Gere um boletim técnico em formato JSON puro baseado nestes dados: {json.dumps(payload, ensure_ascii=False)}"
        parts = [prompt] + evidencias_pil
        parsed_response = None

        for k in api_keys:
            if parsed_response:
                break
            try:
                genai.configure(api_key=k)
                for model_name in MODELS_TO_TRY:
                    try:
                        model = genai.GenerativeModel(model_name)
                        res = model.generate_content(parts)
                        if res and hasattr(res, "text"):
                            parsed_response = parse_json_response(res.text)
                            if parsed_response:
                                break
                    except Exception:
                        continue
            except Exception:
                continue

        if not parsed_response:
            st.error("Todas as chaves atingiram o limite da cota gratuita. Aguarde 60 segundos.")
            st.stop()

        st.success("Relatório processado com sucesso!")
        st.json(parsed_response)

if __name__ == "__main__":
    main()
