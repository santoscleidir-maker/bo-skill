import io
import json
import os
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from google import genai
from google.genai import types
import streamlit as st
from PIL import Image


APP_TITLE = "Sentinela Bravo — Skill BO"
MODEL_NAME = "gemini-2.0-flash"  # fixo — sem probe, sem cota desperdiçada

MAX_IMAGES = 5
MAX_IMAGE_WIDTH = 1280
JPEG_QUALITY = 78

MODEL_HINTS = {
    "🔥 GERAR BOLETIM UNIVERSAL (Qualquer Modelo do Manual)": "Use o modelo mais aderente ao manual para a situação descrita.",
    "📦 Carga Tombada / Peças Molhadas / Danos em Racks": "Exigir dados de carga, transportadora, motorista, MVM, DANFE, rack e destino da avaliação.",
    "❌ Recusa de Carga / Divergência Fiscal / Excesso de Jornada": "Exigir dados de transporte, horários, placas, MVM e justificativas formais.",
    "Acidente de Trânsito / Colisão Interna (Choque ou Abalroamento)": "Exigir veículos, placas, chassi, tipo de impacto, danos por lado e desfecho com CSO/TST/ambulância se houver.",
    "Desvio de Segurança / Quebra de Regra de Ouro (Falta Grave)": "Exigir relato objetivo, identificação completa, liderança responsável e providências.",
    "Controle de Acesso / Portaria (Notebooks / Instabilidade Ronda)": "Exigir portaria, item recolhido, documentação, guarda de objetos e providência tomada.",
}


def init_page() -> None:
    st.set_page_config(page_title=APP_TITLE, page_icon="🛡️", layout="centered")
    st.markdown(
        """
        <style>
        .main { background-color: #0d1117; }
        h1, h2, h3 { color: #f97316; }
        .subtitle { color: #8b949e; text-align: center; font-size: 1.02rem; margin-bottom: 1.2rem; }
        .section-card { background-color: #161b22; padding: 16px; border-radius: 14px; border: 1px solid #30363d; margin-bottom: 14px; }
        .section-title { color: #f97316; font-size: 1.08rem; font-weight: 700; margin-bottom: 10px; }
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


# CORREÇÃO PRINCIPAL: sem probe — não consome cota na inicialização
def get_client(api_key: str) -> genai.Client:
    return genai.Client(api_key=api_key)


def compress_image(uploaded_file: Any) -> Tuple[bytes, Image.Image]:
    raw = uploaded_file.read()
    img = Image.open(io.BytesIO(raw))
    if img.mode != "RGB":
        img = img.convert("RGB")
    img.thumbnail((MAX_IMAGE_WIDTH, MAX_IMAGE_WIDTH))
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    return buffer.getvalue(), img


def pil_to_part(img: Image.Image) -> types.Part:
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return types.Part.from_bytes(data=buf.getvalue(), mime_type="image/jpeg")


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


def safe_extract_text(response: Any) -> str:
    try:
        return response.text or ""
    except Exception:
        try:
            parts = response.candidates[0].content.parts
            return " ".join(p.text for p in parts if hasattr(p, "text"))
        except Exception:
            return ""


def build_prompt(payload: Dict[str, Any]) -> str:
    return f"""
Você é a Skill BO Sentinela Bravo.

Regras obrigatórias do manual:
- Linguagem clara, objetiva, factual e sem opinião pessoal.
- Não invente dados.
- Quando um dado não for informado, escreva exatamente "NÃO INFORMADO".
- A hora deve ser a hora do fato, não a hora do preenchimento.
- Para pessoas sem vínculo com a Stellantis, use documento de identificação; para motoristas de transportadora, inclua endereço e filiação.
- Em acidentes, inclua CSO, TST, ambulância e desfecho somente se essas informações existirem no relato.

Tarefa:
1) Fazer auditoria de conformidade com o manual.
2) Gerar o boletim interno estruturado.
3) Indicar lacunas de coleta sem inventar dados.

Formato de saída obrigatório (JSON puro, sem markdown, sem texto fora das chaves):
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
        st.error("Configure `GEMINI_API_KEY` em `st.secrets` ou nas variáveis de ambiente.")
        st.stop()

    # Sem spinner de validação — não chama a API na inicialização
    client = get_client(api_key)
    st.caption(f"✅ Modelo: `{MODEL_NAME}`")

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

    with st.form("bo_form", clear_on_submit=False):
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">🚨 Classificação da ocorrência</div>', unsafe_allow_html=True)

        tipo_ocorrencia = st.selectbox("Modelo principal", list(MODEL_HINTS.keys()))
        st.caption(MODEL_HINTS[tipo_ocorrencia])

        data_fato = st.date_input("Data da ocorrência")
        hora_fato = st.time_input("Hora da ocorrência")
        local_exato = st.text_input("Local exato do fato", placeholder="Ex.: Portaria 03, baia 02, galpão 04, coluna L/D")
        vigilante_relator = st.text_input("Vigilante relator / registro", placeholder="Nome e registro do vigilante")
        lider_responsavel = st.text_input("Líder / Supervisor / Gerente responsável", placeholder="Nome e sobrenome")
        lider_contato = st.text_input("Contato do líder", placeholder="Telefone ou ramal")
        acionamento = st.text_area("Acionamento / providência imediata", placeholder="Ex.: Central 2400 acionada...", height=90)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">📝 Relato bruto</div>', unsafe_allow_html=True)
        relato_bruto = st.text_area("Descreva os fatos", height=180, placeholder="Escreva o relato com o máximo de detalhes objetivos.")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">📎 Dados complementares</div>', unsafe_allow_html=True)

        dados_complementares: Dict[str, Any] = {}

        if "Carga Tombada" in tipo_ocorrencia:
            dados_complementares.update({
                "placa_veiculo": st.text_input("Placa do veículo"),
                "mvm": st.text_input("MVM"),
                "danfe": st.text_input("DANFE"),
                "transportadora": st.text_input("Transportadora"),
                "fornecedor": st.text_input("Fornecedor"),
                "motorista": st.text_input("Nome do motorista"),
                "telefone_motorista": st.text_input("Telefone do motorista"),
                "rack_codigo": st.text_input("Código do rack / container"),
                "descricao_pecas": st.text_area("Peças / avarias / quantidade", height=80),
            })
        elif any(k in tipo_ocorrencia for k in ["Colisão", "Choque", "Abalroamento"]):
            dados_complementares.update({
                "veiculo_1": st.text_input("Veículo 1"),
                "veiculo_2": st.text_input("Veículo 2"),
                "danos_veiculo_1": st.text_area("Danos veículo 1", height=70),
                "danos_veiculo_2": st.text_area("Danos veículo 2", height=70),
                "houve_vitima": st.radio("Houve vítima?", ["Não", "Sim"], horizontal=True),
                "cso_tst_ambulancia": st.text_area("CSO / TST / ambulância / desfecho", height=90),
            })
        elif any(k in tipo_ocorrencia for k in ["Controle de Acesso", "Portaria"]):
            dados_complementares.update({
                "nome_colaborador": st.text_input("Nome do colaborador / visitante"),
                "matricula": st.text_input("Matrícula / registro"),
                "empresa_setor": st.text_input("Empresa / setor"),
                "objeto_recolhido": st.text_input("Objeto / equipamento / documento"),
                "documentacao": st.text_input("Documentação que acoberta a saída"),
                "guarda_objetos": st.text_input("Nº de guarda de objetos / alfândega"),
            })
        else:
            dados_complementares.update({
                "envolvidos": st.text_area("Envolvidos e dados levantados", height=90),
                "veiculos_documentos": st.text_area("Veículos / documentos / equipamentos", height=90),
            })

        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">📸 Evidências</div>', unsafe_allow_html=True)
        arquivos = st.file_uploader("Anexe até 5 imagens", type=["png", "jpg", "jpeg", "webp"], accept_multiple_files=True)
        st.markdown('</div>', unsafe_allow_html=True)

        submit = st.form_submit_button("🚀 Gerar BO")

    if not submit:
        return

    if not relato_bruto.strip():
        st.warning("Preencha o relato bruto antes de gerar o boletim.")
        st.stop()
    if not local_exato.strip():
        st.warning("O local exato do fato é obrigatório.")
        st.stop()
    if len(arquivos or []) > MAX_IMAGES:
        st.warning(f"Envie no máximo {MAX_IMAGES} imagens.")
        st.stop()

    image_parts: List[types.Part] = []
    evidencias_info: List[str] = []

    for arquivo in arquivos or []:
        try:
            _, pil_img = compress_image(arquivo)
            image_parts.append(pil_to_part(pil_img))
            evidencias_info.append(arquivo.name)
        except Exception as exc:
            st.error(f"Falha ao processar {arquivo.name}: {exc}")
            st.stop()

    payload = {
        "tipo_ocorrencia": tipo_ocorrencia,
        "data_ocorrencia": data_fato.isoformat(),
        "hora_ocorrencia": hora_fato.strftime("%H:%M"),
        "local_exato": local_exato.strip(),
        "vigilante_relator": vigilante_relator.strip(),
        "lider_responsavel": lider_responsavel.strip(),
        "lider_contato": lider_contato.strip(),
        "acionamento": acionamento.strip(),
        "relato_bruto": relato_bruto.strip(),
        "dados_complementares": dados_complementares,
        "evidencias": evidencias_info,
        "observacao": "Não inventar dados; usar NÃO INFORMADO quando faltar informação.",
        "timestamp_geracao": safe_date_str(datetime.now()),
    }

    prompt_text = build_prompt(payload)
    contents: List[Any] = [types.Part.from_text(text=prompt_text)] + image_parts

    with st.spinner("Processando o relato com a Skill BO..."):
        texto = ""
        parsed = None

        for tentativa in range(3):
            try:
                response = client.models.generate_content(
                    model=MODEL_NAME,
                    contents=contents,
                    config=types.GenerateContentConfig(max_output_tokens=4096),
                )
                texto = safe_extract_text(response)
                parsed = parse_json_response(texto)
                if parsed:
                    break
            except Exception as exc:
                erro_str = str(exc)
                if "429" in erro_str or "RESOURCE_EXHAUSTED" in erro_str:
                    st.error("⚠️ Cota da API Gemini esgotada. Aguarde alguns minutos e tente novamente.")
                    st.stop()
                elif tentativa < 2:
                    st.warning(f"⚠️ Tentativa {tentativa + 1} de 3... aguardando 2s.")
                    time.sleep(2)
                else:
                    st.error(f"❌ Erro definitivo: {exc}")
                    st.stop()

    if not parsed:
        st.warning("O modelo não retornou JSON válido. Resposta bruta:")
        st.code(texto)
        st.stop()

    audit = parsed.get("audit", {})
    bo = parsed.get("bo", {})

    st.success(f"✅ Boletim gerado com sucesso.")

    st.subheader("Auditoria de conformidade")
    render_kv("Modelo identificado", audit.get("modelo_identificado", "NÃO INFORMADO"))
    render_kv("Conformidade", audit.get("conformidade", "NÃO INFORMADO"))
    st.markdown("**Dados críticos localizados**")
    for item in audit.get("dados_criticos_localizados", []):
        st.write(f"- {item}")
    st.markdown("**Lacunas**")
    for item in audit.get("lacunas", []):
        st.write(f"- {item}")

    st.subheader("Boletim estruturado")
    render_kv("Data/hora do fato", bo.get("data_hora_fato", "NÃO INFORMADO"))
    render_kv("Local exato", bo.get("local_exato", "NÃO INFORMADO"))
    render_kv("Acionamento", bo.get("acionamento", "NÃO INFORMADO"))
    render_kv("Dinâmica", bo.get("dinamica", "NÃO INFORMADO"))
    render_kv("Alegação", bo.get("alegacao", "NÃO INFORMADO"))
    render_kv("Status", bo.get("status", "NÃO INFORMADO"))
    st.markdown("**Envolvidos**")
    for item in bo.get("envolvidos", []):
        st.write(f"- {item}")
    st.markdown("**Ativos / veículos / documentos**")
    for item in bo.get("ativos_veiculos_documentos", []):
        st.write(f"- {item}")
    st.markdown("**Providências**")
    for item in bo.get("providencias", []):
        st.write(f"- {item}")
    st.markdown("**Anexos recomendados**")
    for item in bo.get("anexos_recomendados", []):
        st.write(f"- {item}")


if __name__ == "__main__":
    main()
