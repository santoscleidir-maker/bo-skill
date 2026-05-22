import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
import datetime
import time
import re

# ─── Configuração de Página ────────────────────────────────────────────────────
st.set_page_config(
    page_title="Sentinela Bravo — Boletinista",
    page_icon="🛡️",
    layout="centered"
)

st.markdown("""
<style>
    .block-container { padding-top: 1rem; }
    h1 { font-size: 1.9rem !important; font-weight: 800 !important; color: #1e3d59; }
    h3 { color: #1e3d59; font-size: 1.05rem !important; }
    .stTextArea textarea { font-family: 'Courier New', monospace; font-size: 0.9rem; }
    .stButton > button[kind="primary"] {
        background-color: #1e3d59; color: white;
        font-weight: 700; font-size: 1rem;
        border: none; padding: 0.75rem;
        border-radius: 6px; width: 100%;
    }
    .stButton > button[kind="primary"]:hover { background-color: #17b978; }
    .pendencia-box {
        background: #fff3cd; border-left: 4px solid #e0a800;
        padding: 0.8rem 1rem; border-radius: 4px;
        margin: 0.3rem 0; font-size: 0.92rem;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("# 🛡️ Sentinela Bravo")
st.caption("Boletinista Técnico — Stellantis Betim | Grupo Souza Lima")
st.markdown("---")

# ─── Estado de Sessão ─────────────────────────────────────────────────────────
for chave in ["documento_final", "nome_arquivo", "pendencias_cache"]:
    if chave not in st.session_state:
        st.session_state[chave] = None if chave != "pendencias_cache" else []

# ─── Autenticação API ─────────────────────────────────────────────────────────
api_key = st.secrets.get("GOOGLE_API_KEY") or st.secrets.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
else:
    st.error("⚠️ Chave de API não localizada. Configure GOOGLE_API_KEY nos Secrets.")
    st.stop()

# ─── Formulário de Dados Logísticos ───────────────────────────────────────────
st.markdown("### 📋 Dados da Ocorrência")

col1, col2 = st.columns(2)
with col1:
    data_fato = st.date_input("Data do Fato", value=datetime.date.today())
with col2:
    hora_fato = st.selectbox(
        "Hora do Fato (24h)",
        options=[f"{h:02d}:{m:02d}" for h in range(0, 24) for m in range(0, 60, 5)],
        index=144
    )

local_detalhado = st.text_input(
    "Local Exato",
    placeholder="Ex: Galpão 04, colunas 26AB / Portaria 03, baia 02..."
)

relato_bruto = st.text_area(
    "Relato Bruto do Plantão",
    placeholder=(
        "Cole aqui o texto do WhatsApp ou anotações de campo.\n\n"
        "OBRIGATÓRIO conter:\n"
        "• Nome, RE/Matrícula e telefone do(s) envolvido(s)\n"
        "• Nome e RE do Líder/Supervisor/Gerente ciente\n"
        "• O que o(s) envolvido(s) DISSE(ARAM) (alegação)\n"
        "• Como a situação foi RESOLVIDA (desfecho)"
    ),
    height=220
)

# ─── Upload de Evidências (Otimização Extrema de Memória) ─────────────────────
st.markdown("### 📷 Evidências Visuais (opcional)")
fotos_carregadas = st.file_uploader(
    "Anexe fotos da ocorrência",
    type=["jpg", "jpeg", "png", "webp"],
    accept_multiple_files=True,
    label_visibility="collapsed"
)

imagens_processadas = []
if fotos_carregadas:
    for foto in fotos_carregadas:
        try:
            foto.seek(0)
            img = Image.open(io.BytesIO(foto.read()))
            
            # Super compactação para não estourar tráfego por minuto
            img.thumbnail((600, 600)) 
            buffer = io.BytesIO()
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            
            img.save(buffer, format="JPEG", quality=40, optimize=True)
            buffer.seek(0)
            imagens_processadas.append(Image.open(buffer))
        except Exception:
            pass
    if imagens_processadas:
        st.info(f"📸 {len(imagens_processadas)} imagem(ns) carregada(s) e compactada(s).")

st.markdown("---")

# ─── MOTOR DE PRÉ-AUDITORIA PYTHON ────────────────────────────────────────────
def executar_auditoria_local(texto: str, local: str) -> list[dict]:
    pendencias = []
    t = texto.lower()

    # 1. Localização
    local_no_campo = local and len(local.strip()) >= 5
    local_no_texto = bool(re.search(
        r'\b(galpão|galpao|portaria|coluna|sala|pátio|patio|baia|baía'
        r'|portão|portao|recebimento|almoxarifado|área|area'
        r'|refeitório|refeitorio|estacionamento|pátio central'
        r'|cso|cku|ckd|oficina|restaurante|guarita|cancela'
        r'|p1|p2|p3|p4|p5|p6|p7|p8)\b',
        t
    ))
    if not local_no_campo and not local_no_texto:
        pendencias.append({
            "campo": "Local Exato",
            "mensagem": "Nenhuma referência de localização encontrada no campo nem no relato."
        })

    # 2. Identificação
    tem_re = bool(re.search(r'\b(re|reg\.?|registro|matrícula|matricula|cnh|cpf|rg|n[°º]|re\s*\d+)\s*[:\-]?\s*\d{3,}', t))
    tem_nome_proprio = bool(re.search(r'\b(sr\.|sra\.|senhor|senhora|vigilante|motorista|líder|lider|tean|team|fiscal)\s+[a-záàâãéêíóôõúüç]', t)) or len(t) > 40
    
    if not tem_re:
        pendencias.append({
            "campo": "Identificação do Envolvido",
            "mensagem": "Ausência de número de RE, Matrícula ou documento de identificação."
        })
    if not tem_nome_proprio:
        pendencias.append({
            "campo": "Nome do Envolvido",
            "mensagem": "Identifique os envolvidos pelo nome no relato."
        })

    # 3. Contato
    tem_tel = bool(re.search(r'(\(?\d{2}\)?\s*\d{4,5}[\s\-]?\d{4}|\btel\.?|\bfone|\bcelular|\bwhatsapp|\b319|\b31\s*9)', t))
    if not tem_tel:
        pendencias.append({
            "campo": "Telefone de Contato",
            "mensagem": "Ausência de número de telefone ou celular de contato."
        })

    # 4. Liderança
    tem_lider = bool(re.search(r'\b(lider|líder|liderança|supervisor|supervisora|gerente|inspetor|inspetora|técnico de segurança|tst|team leader|coordenador|lopes)\b', t))
    if not tem_lider:
        pendencias.append({
            "campo": "Liderança Ciente",
            "mensagem": "O BO exige identificação da liderança responsável ciente."
        })

    # 5. Alegação
    tem_alegacao = bool(re.search(r'\b(disse que|alegou|declarou|informou que|relatou que|afirmou que|mencionou que|solicitado|chegada|encaminhados)\b', t))
    if not tem_alegacao:
        pendencias.append({
            "campo": "Alegação do Envolvido",
            "mensagem": "O BO exige registrar o histórico descritivo ou alegação."
        })

    # 6. Desfecho
    palavras_desfecho = [
        "encaminhado", "liberado", "recolhido", "orientado", "retirado",
        "acionado", "notificado", "saiu", "retornou", "foi para", "reparação",
        "cso", "alfândega", "galpão", "portaria", "gerado", "registrado",
        "solicitado", "providenciado", "regularizado", "removido", "trancado", "pátio"
    ]
    tem_desfecho = any(p in t for p in palavras_desfecho)
    if not tem_desfecho:
        pendencias.append({
            "campo": "Desfecho / Resolução",
            "mensagem": "Informe como a ocorrência foi resolvida ou direcionada."
        })

    # 7. Termo Proibido
    if "danificado" in t or "danificada" in t:
        pendencias.append({
            "campo": "Terminologia Técnica",
            "mensagem": "Uso do termo genérico 'danificado'. Substitua por termos descritivos (amassado, riscado, quebrado)."
        })

    return pendencias

# ─── Processamento Combinado ──────────────────────────────────────────────────
if st.button("🛡️ Auditar e Gerar Boletim", type="primary"):

    if not relato_bruto.strip():
        st.warning("⚠️ O campo de Relato Bruto não pode estar vazio.")
        st.stop()

    pendencias = executar_auditoria_local(relato_bruto, local_detalhado)
    st.session_state.pendencias_cache = pendencias

    if pendencias:
        st.error(f"⛔ **PRÉ-AUDITORIA: {len(pendencias)} pendência(s) encontrada(s)**")
        for p in pendencias:
            st.markdown(f"<div class='pendencia-box'>❌ <strong>{p['campo']}</strong><br>{p['mensagem']}</div>", unsafe_allow_html=True)
    else:
        with st.spinner("⚡ Formatando documento oficial..."):
            
            analise_visual_texto = "Nenhuma evidência fotográfica anexada."
            
            # PASSO 2A: Tenta analisar imagens isoladamente se houver
            if imagens_processadas:
                try:
                    modelo_visao = genai.GenerativeModel("gemini-1.5-flash")
                    prompt_visao = "Descreva de forma extremamente resumida e em tópicos técnicos as avarias, placas ou irregularidades visíveis nesta imagem para um relatório de segurança."
                    
                    conteudo_visao = [prompt_visao] + imagens_processadas
                    resposta_visao = modelo_visao.generate_content(conteudo_visao)
                    
                    if resposta_visao and resposta_visao.text:
                        analise_visual_texto = resposta_visao.text
                except Exception as erro_midia:
                    # Se estourar a cota de imagem, o sistema avisa mas NÃO trava o BO
                    analise_visual_texto = "Evidências anexadas (Análise automatizada indisponível devido ao limite de tráfego por minuto da API)."

            # PASSO 2B: Geração do BO usando o motor robusto de Texto puro
            try:
                modelo_texto = genai.GenerativeModel("gemini-2.0-flash")

                prompt_final = f"""Você é o Boletinista Técnico da Gestão de Segurança Patrimonial da Stellantis Betim.
Sua função é estruturar as informações validadas em um Boletim de Ocorrência Interno formal.

DADOS LOGÍSTICOS:
- Data: {data_fato.strftime('%d/%m/%Y')}
- Hora: {hora_fato}
- Local: {local_detalhado if local_detalhado.strip() else 'Declarado no histórico'}

RELATO BRUTO APROVADO:
\"\"\"
{relato_bruto}
\"\"\"

ANÁLISE DE EVIDÊNCIAS VISUAIS DA OCORRÊNCIA:
{analise_visual_texto}

REGRAS DE ESCRITA:
1. Identifique a natureza técnica da ocorrência no título (Maiúsculas).
2. Linguagem técnica, factual, na terceira pessoa do plural (Registramos).
3. Preserve EXATAMENTE: números de RE, placas, chassis e telefones.
4. NUNCA use o termo "danificado". Use termos específicos (amassado, riscado, quebrado).

ESTRUTURA OBRIGATÓRIA:
[TÍTULO DA OCORRÊNCIA]
1. DADOS LOGÍSTICOS E CLASSIFICAÇÃO
2. QUALIFICAÇÃO DOS ENVOLVIDOS
3. HISTÓRICO DOS FATOS
4. PROVIDÊNCIAS ADOTADAS
----------------------------------------------------------------------
Emissão: {datetime.datetime.now().strftime('%d/%m/%Y às %H:%M')}
"""

                resposta = modelo_texto.generate_content(
                    prompt_final,
                    generation_config={"max_output_tokens": 1000, "temperature": 0.1}
                )

                if resposta and resposta.text:
                    st.session_state.documento_final = resposta.text
                    st.session_state.nome_arquivo = f"BO_{data_fato.strftime('%Y%m%d')}_{hora_fato.replace(':', '')}.txt"
                else:
                    st.error("❌ O servidor retornou uma resposta em branco. Clique novamente.")

            except Exception as e:
                st.error(f"❌ Falha no processador de texto: {str(e)}")

# ─── Exibição do Resultado ────────────────────────────────────────────────────
if st.session_state.documento_final:
    st.success("✅ Boletim gerado com sucesso!")
    st.text_area(label="", value=st.session_state.documento_final, height=500, key="visualizador_bo")

    col_a, col_b = st.columns(2)
    with col_a:
        st.download_button(
            label="⬇️ Baixar (.txt)",
            data=st.session_state.documento_final.encode("utf-8"),
            file_name=st.session_state.nome_arquivo,
            mime="text/plain",
            use_container_width=True
        )
    with col_b:
        if st.button("🔄 Novo Boletim", use_container_width=True):
            st.session_state.documento_final = None
            st.session_state.nome_arquivo = None
            st.rerun()
