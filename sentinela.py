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
        "• Nome e dados do envolvido (RE se funcionário, ou Placa/MVM se motorista externo)\n"
        "• Nome do Líder/Supervisor/Gerente ciente\n"
        "• Histórico ou alegação do condutor\n"
        "• Como a situação foi RESOLVIDA (desfecho)"
    ),
    height=220
)

# ─── Upload de Evidências (Otimizado e Inteligente) ───────────────────────────
st.markdown("### 📷 Evidências Visuais / Documentos (CNH, RG, MVM) - Opcional")
fotos_carregadas = st.file_uploader(
    "Anexe fotos ou documentos da ocorrência para extração de dados",
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
            
            # Redimensionamento para não estourar limite por minuto da API gratuita
            img.thumbnail((800, 800)) 
            buffer = io.BytesIO()
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            
            img.save(buffer, format="JPEG", quality=60, optimize=True)
            buffer.seek(0)
            imagens_processadas.append(Image.open(buffer))
        except Exception:
            pass
    if imagens_processadas:
        st.success(f"✅ {len(imagens_processadas)} imagem(ns) carregada(s) com sucesso.")

st.markdown("---")

# ─── MOTOR DE PRÉ-AUDITORIA PYTHON (INTELIGENTE PARA LOGÍSTICA/AGREGADOS) ──────
def executar_auditoria_local(texto: str, local: str, tem_fotos: bool) -> list[dict]:
    pendencias = []
    t = texto.lower()

    # 1. Localização
    local_no_campo = local and len(local.strip()) >= 5
    local_no_texto = bool(re.search(
        r'\b(galpão|galpao|portaria|coluna|sala|pátio|patio|baia|baía'
        r'|portão|portao|recebimento|almoxarifado|área|area'
        r'|refeitório|refeitorio|estacionamento|pátio central'
        r'|cso|cku|ckd|oficina|restaurante|guarita|cancela'
        r'|p1|p2|p3|p4|p5|p6|p7|p8|galpao\s*\d+|galpão\s*\d+)\b',
        t
    ))
    if not local_no_campo and not local_no_texto:
        pendencias.append({
            "campo": "Local Exato",
            "mensagem": "Nenhuma referência de localização encontrada no campo nem no relato."
        })

    # 2. Identificação Inteligente (Aceita RE para funcionário OU Placa/MVM/Transportadora para Externos)
    is_externo_logistica = any(p in t for p in ["placa", "mvm", "transportadora", "condutor", "motorista", "carreta", "truck", "agregado"])
    tem_re = bool(re.search(r'\b(re|reg\.?|registro|matrícula|matricula|cnh|cpf|rg|n[°º]|re\s*\d+)\s*[:\-]?\s*\d{3,}', t))
    
    if not tem_re and not is_externo_logistica and not tem_fotos:
        pendencias.append({
            "campo": "Identificação do Envolvido",
            "mensagem": "Ausência de RE ou identificação de veículo externo (Placa/MVM/Transportadora)."
        })

    # 3. Contato
    tem_tel = bool(re.search(r'(\(?\d{2}\)?\s*\d{4,5}[\s\-]?\d{4}|\btel\.?|\bfone|\bcelular|\bwhatsapp|\b319|\b31\s*9)', t))
    if not tem_tel:
        pendencias.append({
            "campo": "Telefone de Contato",
            "mensagem": "Ausência de número de telefone de contato no relato."
        })

    # 4. Liderança ou Solicitante Ciente
    tem_lider = bool(re.search(r'\b(lider|líder|liderança|supervisor|supervisora|gerente|inspetor|inspetora|técnico de segurança|tst|team leader|tean lider|coordenador|lopes|katleen|rafael|robson)\b', t))
    if not tem_lider:
        pendencias.append({
            "campo": "Liderança Ciente",
            "mensagem": "O BO exige a indicação da liderança ou solicitante responsável ciente do fato."
        })

    # 5. Histórico / Dinâmica
    tem_alegacao = bool(re.search(r'\b(disse que|alegou|declarou|informou que|relatou que|afirmou que|mencionou que|solicitado|chegada|encaminhados|solicitou|apresentou)\b', t))
    if not tem_alegacao:
        pendencias.append({
            "campo": "Histórico dos Fatos",
            "mensagem": "O relato precisa conter a descrição da dinâmica ou alegação do condutor."
        })

    # 6. Desfecho
    palavras_desfecho = [
        "encaminhado", "liberado", "recolhido", "orientado", "retirado",
        "acionado", "notificado", "saiu", "retornou", "foi para", "reparação",
        "cso", "alfândega", "galpão", "portaria", "gerado", "registrado",
        "solicitado", "providenciado", "regularizado", "removido", "trancado", "pátio", "patio", "saída"
    ]
    tem_desfecho = any(p in t for p in palavras_desfecho)
    if not tem_desfecho:
        pendencias.append({
            "campo": "Desfecho / Resolução",
            "mensagem": "Informe a resolução ou o direcionamento final dado ao veículo/fato."
        })

    # 7. Bloqueio de termo proibido (Apenas se não for do próprio texto do usuário aprovado)
    if "danificado" in t or "danificada" in t:
        pendencias.append({
            "campo": "Terminologia Técnica",
            "mensagem": "Uso do termo genérico 'danificado'. Substitua por termos específicos (amassado, riscado, quebrado)."
        })

    return pendencias

# ─── Processamento do Boletim ─────────────────────────────────────────────────
if st.button("🛡️ Auditar e Gerar Boletim", type="primary"):

    if not relato_bruto.strip():
        st.warning("⚠️ O campo de Relato Bruto não pode estar vazio.")
        st.stop()

    tem_fotos = len(imagens_processadas) > 0
    pendencias = executar_auditoria_local(relato_bruto, local_detalhado, tem_fotos)
    st.session_state.pendencias_cache = pendencias

    if pendencias:
        st.error(f"⛔ **PRÉ-AUDITORIA: {len(pendencias)} pendência(s) encontrada(s)**")
        for p in pendencias:
            st.markdown(f"<div class='pendencia-box'>❌ <strong>{p['campo']}</strong><br>{p['mensagem']}</div>", unsafe_allow_html=True)
    else:
        with st.spinner("⚡ Processando e aplicando formatação Stellantis..."):
            try:
                modelo = genai.GenerativeModel("gemini-2.0-flash")

                prompt_final = f"""Você é o Boletinista Técnico da Gestão de Segurança Patrimonial da Stellantis Betim.
Sua função é estruturar as informações validadas em um Boletim de Ocorrência Interno formal, seguindo os padrões corporativos.

DADOS DA TELA:
- Data: {data_fato.strftime('%d/%m/%Y')}
- Hora: {hora_fato}
- Local: {local_detalhado if local_detalhado.strip() else 'Declarado no relato técnico'}

RELATO INTEGRAL ENVIADO:
\"\"\"
{relato_bruto}
\"\"\"

REGRAS DE CONSTRUÇÃO DO BO:
1. Use o título padrão em caixa alta de acordo com a natureza exata técnica encontrada.
2. Escreva em linguagem culta, impessoal (terceira pessoa do plural: Registramos, Verificamos).
3. Mantenha fielmente todas as informações: nomes de motoristas agregados, placas de cavalos mecânicos/carretas, MVMs, fornecedores, transportadoras e telefones de contato.
4. Caso imagens estejam anexadas abaixo, faça a varredura visual inteligente para complementar dados de CNH/RG/MVM ou ratificar avarias relatadas.
5. Nunca use a palavra "danificado". Prefira avariado, amassado, quebrado, riscado, conforme o padrão industrial.

ESTRUTURA COMPLETA EXIGIDA:
[TÍTULO DA OCORRÊNCIA EM MAIÚSCULAS]

1. DADOS LOGÍSTICOS E CLASSIFICAÇÃO
- Data do Fato: [Aplicar data correta]
- Hora do Fato: [Aplicar horário correto]
- Local Exato: [Indicar galpão/portaria/colunas citadas]

2. QUALIFICAÇÃO DOS ENVOLVIDOS
[Listar condutor, empresa fornecedora, transportadora, veículo, placas, MVM e contatos disponíveis]

3. HISTÓRICO DOS FATOS
[Narrativa cronológica limpa, contendo horários de acesso e a dinâmica técnica do defeito apresentado]

4. PROVIDÊNCIAS ADOTADAS / DESFECHO
[Autorizações de lideranças, remoções/reparos de peças e direcionamento final de pátio]
----------------------------------------------------------------------
Emissão: {datetime.datetime.now().strftime('%d/%m/%Y às %H:%M')}
"""
                
                conteudo_envio = [prompt_final]
                if tem_fotos:
                    conteudo_envio.append("\n[EVIDÊNCIAS ANEXADAS PARA ANÁLISE]:")
                    conteudo_envio.extend(imagens_processadas)

                resposta = modelo.generate_content(
                    conteudo_envio,
                    generation_config={"max_output_tokens": 1200, "temperature": 0.1}
                )

                if resposta and resposta.text:
                    st.session_state.documento_final = resposta.text
                    st.session_state.nome_arquivo = f"BO_{data_fato.strftime('%Y%m%d')}_{hora_fato.replace(':', '')}.txt"
                else:
                    st.error("❌ Resposta vazia da API. Por favor, clique novamente.")

            except Exception as e:
                if "429" in str(e):
                    st.error("⚠️ Limite de tráfego temporário atingido. Aguarde 10 segundos e tente gerar novamente.")
                else:
                    st.error(f"❌ Erro operacional do motor: {str(e)}")

# ─── Exibição do Resultado ────────────────────────────────────────────────────
if st.session_state.documento_final:
    st.success("✅ Boletim estruturado com sucesso!")
    st.text_area(label="", value=st.session_state.documento_final, height=520, key="visualizador_bo")

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
