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

def compress_image(uploaded_file: Any) -> Tuple[bytes, Image.Image]:
    raw = uploaded_file.read()
    img = Image.open(io.BytesIO(raw))
    if img.mode != "RGB":
        img = img.convert("RGB")
    img.thumbnail((1024, 1024))
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=75, optimize=True)
    return buffer.getvalue(), img

# Inicialização da página corrigida (Sem argumentos)
st.set_page_config(page_title=APP_TITLE, page_icon="🛡️", layout="centered")

st.title("🛡️ Sentinela Bravo")
st.subheader("Skill BO — Ocorrências Operacionais")

# Busca a chave nos Secrets
api_key = st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")

if not api_key:
    st.error("❌ ERRO: 'GEMINI_API_KEY' não encontrada nos Secrets do Streamlit.")
    st.stop()

genai.configure(api_key=api_key)

with st.form("bo_form"):
    local_exato = st.text_input("Local exato do fato")
    relato_bruto = st.text_area("Relato bruto da ocorrência")
    arquivos = st.file_uploader("Evidências Fotográficas", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
    submit = st.form_submit_button("🚀 Processar e Gerar BO")

if submit:
    if not relato_bruto.strip() or not local_exato.strip():
        st.warning("⚠️ Preencha os campos de local e relato.")
        st.stop()

    evidencias_pil = []
    for arq in arquivos or []:
        try:
            _, pil_img = compress_image(arq)
            evidencias_pil.append(pil_img)
        except Exception:
            st.error(f"Falha ao otimizar a imagem: {arq.name}")
            st.stop()

    payload = {
        "local": local_exato.strip(),
        "relato": relato_bruto.strip(),
        "data_sistema": datetime.now().strftime("%d/%m/%Y %H:%M")
    }

    prompt = (
        "Atue como um analista de segurança patrimonial. "
        "Formate os dados a seguir em um relatório técnico descritivo estrito, sem opiniões. "
        f"Retorne APENAS um formato JSON estruturado com as chaves 'analise' e 'bo_formatado'. Dados: {json.dumps(payload, ensure_ascii=False)}"
    )
    
    parts = [prompt] + evidencias_pil

    with st.spinner("Conectando ao servidor..."):
        try:
            model = genai.GenerativeModel("gemini-2.0-flash")
            response = model.generate_content(parts)
            
            if response and hasattr(response, "text"):
                parsed = parse_json_response(response.text)
                if parsed:
                    st.success("✅ Boletim estruturado com sucesso!")
                    st.json(parsed)
                else:
                    st.error("❌ Erro no formato do relatório gerado.")
                    st.text(response.text)
            else:
                st.error("❌ Resposta vazia recebida do servidor.")
                
        except Exception as e:
            error_msg = str(e)
            if "ResourceExhausted" in error_msg or "429" in error_msg:
                st.error("🚨 Limite de Cota Atingido pela API Gratuita.")
            else:
                st.error(f"❌ Falha na API: {error_msg}")
