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
    placeholder="Ex: Galpão 24, adjacente à Sala 28..."
)

relato_bruto = st.text_area(
    "Relato Bruto do Plantão",
    placeholder=(
        "Cole aqui o texto do WhatsApp ou anotações de campo.\n\n"
        "Campos do Modelo:\n"
        "• Envolvidos / Líderes / Solicitantes\n"
        "• Alegação do motorista OU orientação/restrição da liderança\n"
        "• Providências e Desfecho"
    ),
    height=250
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
        st.success(f"✅ {len(imagens_processadas)} imagem(ns) carregada(s) para validação visual.")

st.markdown("---")

# ─── MOTOR DE PRÉ-AUDITORIA PYTHON ATUALIZADO ──────────────────────────────────
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

    # 2. Dados de Contato / Identificação
    tem_tel = bool(re.search(r'(\(?\d{2}\)?\s*\d{4,5}[\s\-]?\d{4}|\btel\.?|\bfone|\bcelular|\bwhatsapp|\b319|\b31\s*9|\b7151|\b6299)', t))
    if not tem_tel:
        pendencias.append({
            "campo": "Telefone de Contato",
            "mensagem": "Ausência de número de telefone de contato do condutor ou da liderança no relato."
        })

    # 3. Presença de Responsável (Lideranças / Solicitantes / Técnicos)
    tem_lider = bool(re.search(r'\b(lider|líder|liderança|supervisor|supervisora|gerente|inspetor|inspetora|técnico|tecnico|tst|team leader|tean lider|coordenador|lopes|katleen|rafael|robson|bruno|giordano|solicitante)\b', t))
    if not tem_lider:
        pendencias.append({
            "campo": "Liderança / Solicitante",
            "mensagem": "Identifique o Líder, Supervisor, Técnico ou Solicitante responsável no corpo do texto."
        })

    # 4. Checagem Inteligente de Relato Técnico / Alegações / Restrições de Entrada
    tem_dinamica = bool(re.search(
        r'\b(disse|alegou|declarou|informou|relatou|afirmou|mencionou|solicitou|autorizou'
        r'|constatou|ausência de condições|ausencia de condições|restrito|área restrita|area restrita'
        r'|não foi possível|nao foi possivel|orientou|impossibilitando|não podia|nao podia'
        r'|recusa|defeito|falha|problema|vazamento|chiller)\b', 
        t
    ))
    if not tem_dinamica:
        pendencias.append({
            "campo": "Histórico / Alegação",
            "mensagem": "O relato precisa conter a justificativa do envolvido ou a diretriz/restrição da liderança."
        })

    # 5. Desfecho Técnico / Direcionamento
    palavras_desfecho = [
        "encaminhado", "liberado", "recolhido", "orientado", "retirado",
        "acionado", "notificado", "saiu", "retornou", "foi para", "reparação",
        "cso", "alfândega", "galpão", "portaria", "gerado", "registrado",
        "solicitado", "providenciado", "regularizado", "removido", "trancado", "pátio", "patio", "saída", "previsão", "encerrada", "contato"
    ]
    tem_desfecho = any(p in t for p in palavras_desfecho)
    if not tem_desfecho:
        pendencias.append({
            "campo": "Desfecho / Resolução",
            "mensagem": "Informe a resolução ou o direcionamento final do plantão."
        })

    # 6. Validação de Termo Genérico Proibido
    if "danificado" in t or "danificada" in t:
        pendencias.append({
            "campo": "Terminologia Técnica",
            "mensagem": "Substitua o termo genérico 'danificado' por especificações técnicas (ex: amassado, quebrado, trincado)."
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
        with st.spinner("⚡ Formatando BO conforme o modelo oficial Stellantis..."):
            try:
                modelo = genai.GenerativeModel("gemini-2.0-flash")

                prompt_final = f"""Você é o Boletinista Técnico da Gestão de Segurança Patrimonial da Stellantis Betim.
Sua função é estruturar as informações validadas rigorosamente de acordo com o modelo de relatório técnico corporativo da planta.

DADOS DE ENTRADA DA TELA:
- Data: {data_fato.strftime('%d/%m/%Y')}
- Hora: {hora_fato}
- Local: {local_detalhado if local_detalhado.strip() else 'Declarado no relato técnico'}

RELATO INTEGRAL ENVIADO:
\"\"\"
{relato_bruto}
\"\"\"

REGRAS DE CONSTRUÇÃO MANDATÓRIAS:
1. TÍTULO: Em letras maiúsculas baseado na natureza exata (Ex: VAZAMENTO DE FLUIDO EM MAQUINÁRIO INDUSTRIAL / DEFEITO EM VEÍCULO EXTERNO).
2. LINGUAGEM: Formal, técnica e impessoal ("Registramos", "Verificamos", "Constatou-se").
3. FIDELIDADE: Mantenha todos os nomes, registros (RE, Matrícula, IDSAP), empresas, placas de veículos, MVMs e contatos telefônicos exatamente como digitados.
4. IMAGENS: Se houver evidências abaixo, use-as para conferência ou extração de dados complementares.
5. TERMO PROIBIDO: Nunca utilize a palavra "danificado". Use termos específicos como "avariado", "quebrado", "vazamento", "falha na válvula".

ESTRUTURA FIXA DO BOLETIM (MONTE EXATAMENTE NESTES CAMPOS):

[TÍTULO DA OCORRÊNCIA EM MAIÚSCULAS]

1. DADOS LOGÍSTICOS E CLASSIFICAÇÃO
- Data do Fato: {data_fato.strftime('%d/%m/%Y')}
- Hora do Fato: {hora_fato}
- Local Exato: [Local detalhado da planta/galpão]

2. QUALIFICAÇÃO DOS ENVOLVIDOS / SOLICITANTES / LIDERANÇAS
[Listar de forma organizada todos os personagens identificados no relato: Motoristas (com Empresa/Placas/MVM), Técnicos de Segurança (Matrículas/IDSAP) e Team Leaders de Manutenção, acompanhados de seus respectivos telefones de contato]

3. HISTÓRICO DOS FATOS
[Narrar aqui o texto corrido de forma culta, cronológica e limpa, detalhando a dinâmica completa dos fatos e horários citados]

4. ALEGAÇÃO DOS ENVOLVIDOS / RESTRIÇÕES OPERACIONAIS DA LIDERANÇA
[Separar claramente: 
- Se for motorista/agregado: registrar a alegação dele sobre a falha mecânica/logística.
- Se for técnico/liderança: registrar a impossibilidade de entrada, restrição da área ou orientação dada por eles (ex: a restrição técnica da TST de não adentrar ao maquinário industrial por falta de acesso técnico).]

5. PROVIDÊNCIAS ADOTADAS / DESFECHO
[Listar autorizações dadas, contatos realizados para apoio externo, vistorias de avarias pela Patrimonial e o encerramento do atendimento no local]
----------------------------------------------------------------------
Emissão: {datetime.datetime.now().strftime('%d/%m/%Y às %H:%M')}
Relator: Vigilante Cleidir Alves
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
                    st.error("❌ Resposta em branco do servidor da API. Clique novamente.")

            except Exception as e:
                if "429" in str(e):
                    st.error("⚠️ Limite de tráfego temporário atingido. Aguarde 10 segundos e clique em gerar novamente.")
                else:
                    st.error(f"❌ Erro operacional do motor: {str(e)}")

# ─── Exibição do Resultado ────────────────────────────────────────────────────
if st.session_state.documento_final:
    st.success("✅ Boletim estruturado com sucesso!")
    st.text_area(label="", value=st.session_state.documento_final, height=550, key="visualizador_bo")

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
