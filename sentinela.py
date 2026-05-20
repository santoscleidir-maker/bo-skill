import base64
import io
import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st
from openai import OpenAI
from PIL import Image

APP_TITLE = "Sentinela Bravo — Skill BO"

FREE_MODELS = [
    "google/gemini-2.0-flash-exp:free",
    "meta-llama/llama-4-scout:free",
    "mistralai/mistral-small-3.2-24b-instruct:free",
]

MAX_IMAGE_WIDTH = 1280
JPEG_QUALITY = 78

MODEL_HINTS = {
    "🔥 GERAR BOLETIM UNIVERSAL (Qualquer Modelo do Manual)": "Use o modelo mais aderente ao manual para a situação descrita.",
    "📦 Carga Tombada / Peças Molhadas / Danos em Racks": "Exigir dados de carga, transportadora, motorista, MVM, DANFE, rack e destino da avaliação.",
    "❌ Recusa de Carga / Divergência Fiscal / Excesso de Jornada": "Exigir dados de transporte, horários, placas, MVM e justificativas formais.",
    "Acidente de Trânsito / Colisão Interna (Choque ou Abalroamento)": "Exigir veículos, placas, chassi, tipo de impacto, danos por lado e desfecho.",
    "Desvio de Segurança / Quebra de Regra de Ouro (Falta Grave)": "Exigir relato objetivo, identificação completa, liderança responsável e providências.",
    "Controle de Acesso / Portaria (Notebooks / Instabilidade Ronda)": "Exigir portaria, item recolhido, documentação, guarda de objetos e providência.",
}


def init_page() -> None:
    st.set_page_config(page_title=APP_TITLE, page_icon="🛡️", layout="centered")
    st.markdown("""
    <style>
    .main { background-color: #0d1117; }
    h1, h2, h3 { color: #f97316; }
    .subtitle { color: #8b949e; text-align: center; font-size: 1.02rem; margin-bottom: 1.2rem; }
    .section-card { background-color: #161b22; padding: 16px; border-radius: 14px; border: 1px solid #30363d; margin-bottom: 14px; }
    .section-title { color: #f97316; font-size: 1.08rem; font-weight: 700; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)


def get_api_key() -> Optional[str]:
    try:
        key = st.secrets.get("OPENROUTER_API_KEY")
    except Exception:
        key = None
    if not key:
        key = os.getenv("OPENROUTER_API_KEY")
    if key:
        return key.strip().replace('"', '').replace("'", "")
    return None


def get_client(api_key: str) -> OpenAI:
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )


def compress_and_encode(uploaded_file: Any) -> Tuple[str, Image.Image]:
    raw = uploaded_file.read()
    img = Image.open(io.BytesIO(raw))
    if img.mode != "RGB":
        img = img.convert("RGB")
    img.thumbnail((MAX_IMAGE_WIDTH, MAX_IMAGE_WIDTH))
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return b64, img


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
            pass
    return None


def build_prompt(payload: Dict[str, Any]) -> str:
    return f"""
Você é a Skill BO Sentinela Bravo, sistema de registro de ocorrências de segurança patrimonial industrial.

Regras obrigatórias:
- Linguagem clara, objetiva, factual e sem opinião pessoal.
- Não invente dados. Use "NÃO INFORMADO" para dados ausentes.
- A hora deve ser a hora do fato, não do preenchimento.
- Em acidentes, mencione CSO, TST, ambulância SOMENTE se informado.
- Ao analisar imagens: extraia placas, documentos, telefones, códigos de rack e qualquer texto visível.

Tarefa:
1) Auditar conformidade com o manual de BO.
2) Extrair informações das imagens (placas, documentos, pessoas, danos).
3) Gerar boletim interno estruturado.
4) Indicar lacunas sem inventar dados.

Formato de saída — JSON puro, sem markdown, sem texto fora das chaves:
{{
  "audit": {{
    "modelo_identificado": "",
    "conformidade": "",
    "dados_criticos_localizados": [],
    "dados_extraidos_imagens": [],
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


def chamar_api(client: OpenAI, prompt: str, imagens_b64: List[str]) -> Optional[str]:
    content: List[Any] = [{"type": "text", "text": prompt}]
    for b64 in imagens_b64:
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
        })
    for idx, model_name in enumerate(FREE_MODELS):
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": content}],
                max_tokens=4096,
            )
            texto = response.choices[0].message.content or ""
            if texto.strip():
                st.caption(f"✅ Modelo: `{model_name}`")
                return texto
        except Exception as e:
            if idx < len(FREE_MODELS) - 1:
                st.warning(f"⚠️ Modelo `{model_name}` indisponível. Tentando próximo...")
            else:
                st.error(f"❌ Todos os modelos falharam. Erro: {str(e)}")
    return None


def render_kv(label: str, value: Any) -> None:
    st.markdown(f"**{label}:** {value}")


def main() -> None:
    init_page()

    api_key = get_api_key()
    if not api_key:
        st.error("Configure OPENROUTER_API_KEY nos Secrets do Streamlit.")
        st.info("Crie sua chave gratuita em: https://openrouter.ai/keys")
        st.stop()

    client = get_client(api_key)
    st.caption("✅ OpenRouter conectado — 100% gratuito, sem limite de cota")

    col1, col2 = st.columns([1, 4])
    with col1:
        try:
            logo = Image.open("sentinela bravo.jpg")
            st.image(logo, width=96)
        except Exception:
            st.write("🛡️")
    with col2:
        st.title("Sentinela Bravo")
        st.markdown("<p class='subtitle'>Skill BO • Boletim de Ocorrência com IA — 100% Gratuito</p>",
                    unsafe_allow_html=True)

    with st.form("bo_form", clear_on_submit=False):
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">🚨 Classificação da ocorrência</div>', unsafe_allow_html=True)

        tipo_ocorrencia = st.selectbox("Modelo principal", list(MODEL_HINTS.keys()))
        st.caption(MODEL_HINTS[tipo_ocorrencia])

        data_fato = st.date_input("Data da ocorrência")
        hora_fato = st.time_input("Hora da ocorrência")
        local_exato = st.text_input("Local exato do fato", placeholder="Ex.: Galpão 89, coluna 32AC")
        vigilante_relator = st.text_input("Vigilante relator / registro")
        lider_responsavel = st.text_input("Líder / Supervisor / Gerente responsável")
        lider_contato = st.text_input("Contato do líder", placeholder="Telefone ou ramal")
        acionamento = st.text_area("Acionamento / providência imediata", height=90)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">📝 Relato bruto</div>', unsafe_allow_html=True)
        relato_bruto = st.text_area("Descreva os fatos", height=180,
                                    placeholder="Relato objetivo com o máximo de detalhes.")
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
        st.markdown('<div class="section-title">📸 Evidências (placa, documento, dano)</div>',
                    unsafe_allow_html=True)
        arquivos = st.file_uploader("Anexe até 5 imagens — a IA extrai texto automaticamente",
                                    type=["png", "jpg", "jpeg", "webp"],
                                    accept_multiple_files=True)
        st.markdown('</div>', unsafe_allow_html=True)

        submit = st.form_submit_button("🚀 Gerar BO")

    if not submit:
        return

    if not relato_bruto.strip():
        st.warning("Preencha o relato bruto.")
        st.stop()
    if not local_exato.strip():
        st.warning("O local exato é obrigatório.")
        st.stop()
    if len(arquivos or []) > 5:
        st.warning("Máximo 5 imagens.")
        st.stop()

    imagens_b64: List[str] = []
    for arquivo in arquivos or []:
        try:
            b64, _ = compress_and_encode(arquivo)
            imagens_b64.append(b64)
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
        "qtd_imagens_anexadas": len(imagens_b64),
        "observacao": "NÃO INFORMADO para dados ausentes. Extrair texto de imagens.",
        "timestamp_geracao": datetime.now().strftime("%d/%m/%Y %H:%M"),
    }

    prompt_text = build_prompt(payload)

    with st.spinner("Analisando relato e imagens com IA gratuita..."):
        texto = chamar_api(client, prompt_text, imagens_b64)

    if not texto:
        st.stop()

    parsed = parse_json_response(texto)
    if not parsed:
        st.warning("Resposta bruta (JSON inválido):")
        st.code(texto)
        st.stop()

    audit = parsed.get("audit", {})
    bo = parsed.get("bo", {})

    st.success("✅ Boletim gerado com sucesso.")

    st.subheader("Auditoria de conformidade")
    render_kv("Modelo identificado", audit.get("modelo_identificado", "NÃO INFORMADO"))
    render_kv("Conformidade", audit.get("conformidade", "NÃO INFORMADO"))

    extraidos = audit.get("dados_extraidos_imagens", [])
    if extraidos:
        st.markdown("**🔍 Dados extraídos das imagens**")
        for item in extraidos:
            st.write(f"- {item}")

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
