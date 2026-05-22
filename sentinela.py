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
    st.error("⚠️ Chave de API não localizada. Configure GOOGLE_API_KEY nos Secrets do Streamlit.")
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

# ─── Upload de Evidências ──────────────────────────────────────────────────────
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
            img.thumbnail((1024, 1024))
            buffer = io.BytesIO()
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            img.save(buffer, format="JPEG", quality=72, optimize=True)
            buffer.seek(0)
            imagens_processadas.append(Image.open(buffer))
        except Exception:
            pass
    if imagens_processadas:
        st.success(f"✅ {len(imagens_processadas)} imagem(ns) comprimida(s) localmente.")

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
#  MOTOR DE PRÉ-AUDITORIA PYTHON — TRIAGEM COMPLETA SEM CONSUMO DE API
#  Objetivo: bloquear relatos incompletos ANTES de acionar o Gemini.
#  O Gemini só é chamado quando TODOS os critérios abaixo forem atendidos.
# ══════════════════════════════════════════════════════════════════════════════
def executar_auditoria_local(texto: str, local: str) -> list[dict]:
    """
    Analisa o relato bruto contra as regras obrigatórias do BO Stellantis.
    Retorna lista de pendências, cada uma com 'campo' e 'mensagem'.
    """
    pendencias = []
    t = texto.lower()

    # ── 1. LOCAL DO FATO ──────────────────────────────────────────────────────
    if not local or len(local.strip()) < 5:
        pendencias.append({
            "campo": "Local Exato",
            "mensagem": "Campo 'Local Exato' não preenchido ou muito genérico. "
                        "Informe galpão, portaria, coluna ou área específica."
        })

    # ── 2. IDENTIFICAÇÃO DO ENVOLVIDO (nome + RE/matrícula) ───────────────────
    tem_re = bool(re.search(
        r'\b(re|reg\.?|registro|matrícula|matricula|cnh|cpf|rg|n[°º])\s*[:\-]?\s*\d{3,}',
        t
    ))
    tem_nome_proprio = bool(re.search(
        r'\b(sr\.|sra\.|senhor|senhora)\s+[a-záàâãéêíóôõúüç]',
        t
    ))
    if not tem_re:
        pendencias.append({
            "campo": "Identificação do Envolvido",
            "mensagem": "Ausência de número de RE, Matrícula, CNH, RG ou CPF do envolvido. "
                        "Inclua o registro funcional ou documento de identificação."
        })
    if not tem_nome_proprio:
        pendencias.append({
            "campo": "Nome do Envolvido",
            "mensagem": "Nenhum nome próprio identificado (Sr./Sra. + nome). "
                        "Identifique os envolvidos pelo nome completo."
        })

    # ── 3. CONTATO TELEFÔNICO ─────────────────────────────────────────────────
    tem_tel = bool(re.search(
        r'(\(?\d{2}\)?\s*\d{4,5}[\s\-]?\d{4}|\btel\.?|\bfone|\bcelular|\bwhatsapp)',
        t
    ))
    if not tem_tel:
        pendencias.append({
            "campo": "Telefone de Contato",
            "mensagem": "Ausência de número de telefone ou celular do envolvido. "
                        "Inclua o contato no formato (DDD) XXXXX-XXXX."
        })

    # ── 4. LIDERANÇA CIENTE ───────────────────────────────────────────────────
    tem_lider = bool(re.search(
        r'\b(lider|líder|liderança|supervisor|supervisora|gerente|inspetor|inspetora'
        r'|técnico de segurança|tst|team leader|coordenador)\b',
        t
    ))
    if not tem_lider:
        pendencias.append({
            "campo": "Liderança Ciente",
            "mensagem": "Nenhuma menção a Líder, Supervisor, Gerente ou Inspetor ciente. "
                        "O BO exige identificação da liderança responsável (nome + RE)."
        })

    # ── 5. ALEGAÇÃO DO ENVOLVIDO ("disse que") ────────────────────────────────
    tem_alegacao = bool(re.search(
        r'\b(disse que|alegou|declarou|informou que|relatou que|afirmou que|mencionou que)\b',
        t
    ))
    if not tem_alegacao:
        pendencias.append({
            "campo": "Alegação do Envolvido",
            "mensagem": "Ausência de alegação do envolvido. "
                        "O BO exige registrar o que o envolvido disse "
                        "(ex: 'O Sr. X disse que...')."
        })

    # ── 6. DESFECHO / RESOLUÇÃO ───────────────────────────────────────────────
    palavras_desfecho = [
        "encaminhado", "liberado", "recolhido", "orientado", "retirado",
        "acionado", "notificado", "saiu", "retornou", "foi para",
        "cso", "alfândega", "galpão", "portaria", "gerado", "registrado",
        "solicitado", "providenciado", "regularizado", "removido", "trancado"
    ]
    tem_desfecho = any(p in t for p in palavras_desfecho)
    if not tem_desfecho:
        pendencias.append({
            "campo": "Desfecho / Resolução",
            "mensagem": "Ausência de desfecho ou providência adotada. "
                        "Informe como a ocorrência foi resolvida "
                        "(encaminhamento, orientação, remoção, acionamento de equipe etc.)."
        })

    # ── 7. TERMO PROIBIDO: 'DANIFICADO' ──────────────────────────────────────
    if "danificado" in t or "danificada" in t:
        pendencias.append({
            "campo": "Terminologia Técnica",
            "mensagem": "Uso do termo genérico 'danificado/danificada'. "
                        "Substitua por: AMASSADO, RISCADO, QUEBRADO, ARRANHADO, "
                        "EMPENADO, TRINCADO, DEFORMADO, ESTOURADO, FURADO, SOLTO."
        })

    # ── 8. TAMANHO MÍNIMO DO RELATO ───────────────────────────────────────────
    palavras = len(texto.split())
    if palavras < 30:
        pendencias.append({
            "campo": "Extensão do Relato",
            "mensagem": f"Relato muito curto ({palavras} palavras). "
                        "Um BO completo exige no mínimo 30 palavras. "
                        "Inclua todos os detalhes da ocorrência."
        })

    return pendencias


# ─── Botão Principal ──────────────────────────────────────────────────────────
if st.button("🛡️ Auditar e Gerar Boletim", type="primary"):

    if not relato_bruto.strip():
        st.warning("⚠️ O campo de Relato Bruto não pode estar vazio.")
        st.stop()

    # ── PASSO 1: Python audita localmente (zero custo de API) ─────────────────
    pendencias = executar_auditoria_local(relato_bruto, local_detalhado)
    st.session_state.pendencias_cache = pendencias

    if pendencias:
        # Bloqueia e exibe os desvios encontrados — Gemini NÃO é acionado
        st.error(f"⛔ **PRÉ-AUDITORIA: {len(pendencias)} pendência(s) encontrada(s)**")
        st.markdown(
            "Corrija os itens abaixo antes de gerar o boletim. "
            "O Gemini só será acionado após a aprovação completa:"
        )
        for p in pendencias:
            st.markdown(
                f"<div class='pendencia-box'>❌ <strong>{p['campo']}</strong><br>"
                f"{p['mensagem']}</div>",
                unsafe_allow_html=True
            )
        st.info(
            "💡 **Dica:** Cada pendência corrigida aqui evita um consumo de cota da API. "
            "O Python faz o trabalho bruto; o Gemini apenas formata o texto aprovado."
        )

    else:
        # ── PASSO 2: Relato aprovado — aciona o Gemini para formatação ────────
        with st.spinner("✅ Pré-auditoria aprovada! Formatando o boletim..."):
            try:
                modelo = genai.GenerativeModel("gemini-2.0-flash")

                prompt = f"""Você é o Boletinista Técnico da Gestão de Segurança Patrimonial da Stellantis Betim.
Sua função é receber informações de campo já validadas e estruturá-las em um Boletim de Ocorrência Interno formal, seguindo rigorosamente o padrão da empresa.

DADOS LOGÍSTICOS:
- Data: {data_fato.strftime('%d/%m/%Y')}
- Hora: {hora_fato}
- Local: {local_detalhado if local_detalhado.strip() else 'Declarado no histórico'}

RELATO BRUTO APROVADO:
\"\"\"
{relato_bruto}
\"\"\"

REGRAS DE ESCRITA (OBRIGATÓRIAS):
1. Identifique a natureza técnica da ocorrência no título (ex: CAMINHÃO COM DEFEITO, ESTACIONAMENTO IRREGULAR, ABALROAMENTO, OVERTIME etc.).
2. Linguagem técnica, factual, sem adjetivos subjetivos. Terceira pessoa do plural (Registramos / Notificamos).
3. Preserve EXATAMENTE: números de RE, matrículas, placas, MVMs, chassis, telefones, nomes próprios.
4. Alegações dos envolvidos introduzidas por: "O Sr. [nome] disse que..."
5. NUNCA use o termo "danificado". Use: amassado, riscado, quebrado, arranhado, empenado, trincado, deformado.
6. O boletim deve ter início, meio e fim — incluindo o desfecho (como foi resolvido).
7. Se houver imagens, corrobore os danos descritos com o que for visível nelas.

ESTRUTURA OBRIGATÓRIA DE SAÍDA (use exatamente estes marcadores):

[TÍTULO DA OCORRÊNCIA EM MAIÚSCULAS]

[Parágrafo 1 — Identificação: quem solicitou/relatou, envolvidos, veículos, local exato]

[Parágrafo 2 — Narrativa: o que aconteceu, cronologia do fato]

[Parágrafo 3 em diante — Alegações das partes e providências adotadas]

[Parágrafo final — Desfecho: encaminhamentos, orientações, regularizações]

Dados Complementares (se disponíveis):
- Filiação: [se informado]
- Endereço: [se informado]  
- Telefone: [número]

Anexo: [Fotos / Documentação — conforme disponível]

Relator: Vigilante [nome se informado]
----------------------------------------------------------------------
Emissão: {datetime.datetime.now().strftime('%d/%m/%Y às %H:%M')}
"""

                # Monta requisição com ou sem imagens
                conteudo = [prompt]
                if imagens_processadas:
                    conteudo.append(
                        "\n[Evidências visuais anexadas — analise e corrobore com o texto:]"
                    )
                    conteudo.extend(imagens_processadas)

                # Tentativas com backoff em caso de instabilidade
                resposta = None
                for tentativa in range(3):
                    try:
                        resposta = modelo.generate_content(conteudo)
                        if resposta and hasattr(resposta, "text") and resposta.text:
                            break
                    except Exception as e:
                        if "429" in str(e) and tentativa < 2:
                            time.sleep(15)
                        else:
                            raise e

                if resposta and resposta.text:
                    st.session_state.documento_final = resposta.text
                    st.session_state.nome_arquivo = (
                        f"BO_{data_fato.strftime('%Y%m%d')}_{hora_fato.replace(':', '')}.txt"
                    )
                else:
                    st.error("❌ A IA retornou resposta vazia. Tente novamente.")

            except Exception as e:
                st.error(f"❌ Erro no motor de IA: {str(e)}")
                if "429" in str(e):
                    st.warning(
                        "⚠️ Cota da API atingida. Aguarde alguns minutos e tente novamente. "
                        "Verifique o plano em: https://ai.dev/rate-limit"
                    )

# ─── Exibição do Resultado ────────────────────────────────────────────────────
if st.session_state.documento_final:
    st.success("✅ Boletim gerado e pronto para uso!")
    st.markdown("### 📄 Boletim Técnico Formatado")

    st.text_area(
        label="",
        value=st.session_state.documento_final,
        height=550,
        key="visualizador_bo"
    )

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
