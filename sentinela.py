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


def init_page() -> None:
    st.set_page_config(page_title=APP_TITLE, page_icon="🛡️", layout="centered")
    st.markdown("""
    <style>
    .main { background-color: #0d1117; }
    h1, h2, h3 { color: #f97316; }
    .subtitle { color: #8b949e; text-align: center; font-size: 1.02rem; margin-bottom: 1.2rem; }
    .section-card { background-color: #161b22; padding: 16px; border-radius: 14px; border: 1px solid #30363d; margin-bottom: 14px; }
    .section-title { color: #f97316; font-size: 1.08rem; font-weight: 700; margin-bottom: 10px; }
    .bo-output { background-color: #161b22; padding: 20px; border-radius: 10px; border: 1px solid #f97316; font-family: monospace; font-size: 0.9rem; white-space: pre-wrap; color: #e6edf3; line-height: 1.7; }
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
    return OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)


def compress_and_encode(uploaded_file: Any) -> Tuple[str, Image.Image]:
    raw = uploaded_file.read()
    img = Image.open(io.BytesIO(raw))
    if img.mode != "RGB":
        img = img.convert("RGB")
    img.thumbnail((MAX_IMAGE_WIDTH, MAX_IMAGE_WIDTH))
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    return base64.b64encode(buffer.getvalue()).decode("utf-8"), img


def build_prompt(payload: Dict[str, Any]) -> str:
    return f"""
Você é a Skill BO Sentinela Bravo, sistema especializado em boletins de ocorrência da Segurança Patrimonial Stellantis (Grupo Souza Lima), planta de Betim/MG.

═══════════════════════════════════════════
REGRAS ABSOLUTAS DO MANUAL
═══════════════════════════════════════════
1. Linguagem clara, objetiva, factual. Sem opinião pessoal. Sem "danificado" — use amassado, arranhado, quebrado, empenado etc.
2. NÃO invente dados. Se faltar, escreva exatamente: NÃO INFORMADO
3. A hora informada é a do FATO, nunca do preenchimento.
4. Motoristas/externos sem vínculo Stellantis: exigir nome completo, CNH, filiação (pai e mãe), endereço, telefone.
5. Todo BO precisa de DESFECHO — para onde foi o veículo, se houve medicação, se foi liberado para atividades ou casa.
6. Em acidentes: TST presente (nome, reg., tel.), CSO (enfermeira/médico, reg., desfecho médico, placa ambulância se houver).
7. Em ocorrências com veículos: sempre citar lados (L/D ou L/E) e tipos de dano.
8. Alegação obrigatória de CADA envolvido citado — "O Sr. X disse que..."
9. Liderança responsável: somente Líder, Supervisor ou Gerente — não Team Leader.
10. Relator ao final: "Relator: Vigilante Patrimonial [nome e registro do relator]"
11. Carta de próprio punho: sinalizar quando obrigatória (notebook, objetos, peças, mau procedimento).

═══════════════════════════════════════════
32+ MODELOS DO MANUAL — IDENTIFICAR AUTOMATICAMENTE
═══════════════════════════════════════════
Recolhimento Notebook em Revista | Recolhimento Objetos em Revista | Confecção Crachá Manual |
Saída Visitantes Fora do Horário | Veículo Rebocado | Excesso de Carga Horária/Overtime |
Estacionamento Irregular (carro) | Estacionamento Irregular (moto) | Colisão | Abalroamento |
Choque | Colisão Empilhadeira x Carreta | Queda de Peças da Empilhadeira |
Carga Tombada/Peças Danificadas | Peças Molhadas | Container Danificado |
Peças em Vasilhames Galpão 89 | DEEM Maior | DEEM Menor | Carga com Destino ao CKD |
Protótipo sem Lacres | Utilização Indevida de Veículos | Fiscalização de Trânsito |
Fiscalização com Radar | KM Lançado Erroneamente P4 | MVM Extraviado na Portaria |
MVM Extraviado no Guichê | Estado de Conservação de Veículos P1 | O.S com Empilhadeira P1 |
Carteira/Celular Deixado na Portaria | Mau Procedimento Revista | Sinais de Embriaguez |
Sider Aberto | Recusa de Carregamento | Ronda - Notebook | Ronda - Portas Destrancadas |
Ronda - Vazamento de Líquido | Ronda - Cercas Danificadas | Atendimento Médico |
Perda do Transporte Fretado | Trajando Bermuda | Motorista sem EPIs |
Caminhão com Defeito no Interior | Instabilidade no Ronda |
+ OUTROS: Se a situação não se encaixar em nenhum modelo, crie um modelo adequado
  mantendo a espinha central: identificação → dinâmica → danos → alegações → providências → desfecho

═══════════════════════════════════════════
ESTRUTURA OBRIGATÓRIA DO BO (NARRATIVA)
═══════════════════════════════════════════
O boletim deve ser gerado como TEXTO NARRATIVO corrido, no padrão do manual, seguindo:

[TÍTULO DO MODELO IDENTIFICADO EM MAIÚSCULAS]

Parágrafo 1 - IDENTIFICAÇÃO: Quem registra/informa, função, registro, sobre o quê.
Parágrafo 2 - DINÂMICA: O que aconteceu, quando, onde, como, sequência cronológica.
Parágrafo 3 - DANOS (se houver): Veículo 1: [danos lado/tipo]. Veículo 2: [danos lado/tipo].
Parágrafo(s) - ALEGAÇÕES: "O Sr. [nome] disse que [alegação completa]." — um parágrafo por envolvido.
Parágrafo - LIDERANÇA/TST: "Compareceu ao local o [função] Sr. [nome], reg. [X], cientificando-se dos fatos."
Parágrafo - CSO (se acidente): encaminhamento, ambulância placa, enfermeiro/médico nome+reg, diagnóstico, liberação.
Parágrafo - PROVIDÊNCIAS: o que foi feito, para onde foi encaminhado, chamado gerado.
Parágrafo - DESFECHO: situação final, previsão, status.
DADOS COMPLEMENTARES (se motorista externo): Filiação: | Endereço: | Telefone: | CNH:
CARTA DE PRÓPRIO PUNHO: [Necessária / Não necessária] — com justificativa.
Anexo: fotos. (quando aplicável)
Relator: Vigilante Patrimonial [nome] [registro]

═══════════════════════════════════════════
AUDITORIA (retornar separado)
═══════════════════════════════════════════
Após o BO, retorne a auditoria indicando:
- Modelo identificado
- Conformidade (APROVADO / PENDÊNCIAS)
- Dados críticos localizados (inclusive extraídos de imagens)
- Lacunas (dados faltantes que precisam ser coletados)
- Carta de próprio punho necessária? S/N

═══════════════════════════════════════════
FORMATO DE SAÍDA — JSON PURO (sem markdown)
═══════════════════════════════════════════
{{
  "bo_texto": "TEXTO NARRATIVO COMPLETO DO BOLETIM AQUI",
  "audit": {{
    "modelo_identificado": "",
    "conformidade": "",
    "dados_criticos_localizados": [],
    "dados_extraidos_imagens": [],
    "carta_proprio_punho": "",
    "lacunas": []
  }}
}}

═══════════════════════════════════════════
DADOS DO FORMULÁRIO
═══════════════════════════════════════════
{json.dumps(payload, ensure_ascii=False, indent=2)}
""".strip()


def chamar_api(client: OpenAI, prompt: str, imagens_b64: List[str]) -> Optional[str]:
    content: List[Any] = [{"type": "text", "text": prompt}]
    for b64 in imagens_b64:
        content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})
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
                st.warning(f"⚠️ `{model_name}` indisponível. Tentando próximo...")
            else:
                st.error(f"❌ Todos os modelos falharam: {str(e)}")
    return None


def parse_response(texto: str) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(texto)
    except Exception:
        pass
    match = re.search(r"\{.*\}", texto, flags=re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass
    return None


def main() -> None:
    init_page()

    api_key = get_api_key()
    if not api_key:
        st.error("Configure OPENROUTER_API_KEY nos Secrets do Streamlit.")
        st.stop()

    client = get_client(api_key)
    st.caption("✅ OpenRouter — 100% gratuito, sem limite de cota")

    col1, col2 = st.columns([1, 4])
    with col1:
        try:
            st.image(Image.open("sentinela bravo.jpg"), width=96)
        except Exception:
            st.write("🛡️")
    with col2:
        st.title("Sentinela Bravo")
        st.markdown("<p class='subtitle'>Skill BO • Boletim de Ocorrência Inteligente — Stellantis Betim</p>",
                    unsafe_allow_html=True)

    with st.form("bo_form", clear_on_submit=False):

        # ── BLOCO 1: IDENTIFICAÇÃO DA OCORRÊNCIA ──────────────────────
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">🚨 Identificação da Ocorrência</div>', unsafe_allow_html=True)
        data_fato = st.date_input("Data da ocorrência")
        hora_fato = st.time_input("Hora da ocorrência (hora do fato)")
        local_exato = st.text_input("Local exato", placeholder="Ex.: Galpão 04, coluna 26AB, Portaria 03 baia 02")
        tipo_referencia = st.text_input("Referência / tipo (opcional — a IA identifica automaticamente)",
                                        placeholder="Ex.: Carga tombada, Abalroamento, Ronda — ou deixe em branco")
        st.markdown('</div>', unsafe_allow_html=True)

        # ── BLOCO 2: RELATOR ──────────────────────────────────────────
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">👤 Vigilante Relator</div>', unsafe_allow_html=True)
        relator_nome = st.text_input("Nome completo do vigilante relator")
        relator_registro = st.text_input("Registro do vigilante relator")
        st.markdown('</div>', unsafe_allow_html=True)

        # ── BLOCO 3: RELATO BRUTO ─────────────────────────────────────
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">📝 Relato bruto dos fatos</div>', unsafe_allow_html=True)
        relato_bruto = st.text_area("Descreva os fatos com o máximo de detalhes", height=200,
                                    placeholder="Descreva cronologicamente: o que aconteceu, quem estava envolvido, o que foi dito, quais providências foram tomadas, qual foi o desfecho...")
        st.markdown('</div>', unsafe_allow_html=True)

        # ── BLOCO 4: ENVOLVIDO 1 ─────────────────────────────────────
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">👥 Envolvido Principal</div>', unsafe_allow_html=True)
        env1_nome = st.text_input("Nome completo")
        env1_funcao = st.text_input("Função / cargo", placeholder="Ex.: Operador Veículo Logístico, Motorista, Colaborador")
        env1_registro = st.text_input("Registro / matrícula")
        env1_empresa = st.text_input("Empresa / setor")
        env1_telefone = st.text_input("Telefone")
        env1_externo = st.checkbox("Motorista / pessoa sem vínculo Stellantis (exige dados extras)")
        env1_endereco = ""
        env1_filiacao = ""
        env1_cnh = ""
        if env1_externo:
            env1_endereco = st.text_input("Endereço completo (Rua, nº, bairro, cidade/UF)")
            env1_filiacao = st.text_input("Filiação (nome do pai e da mãe)")
            env1_cnh = st.text_input("CNH — categoria e validade")
        env1_alegacao = st.text_area("Alegação do envolvido 1 — o que ele disse", height=80,
                                     placeholder="Ex.: disse que não percebeu o portão ao recuar...")
        st.markdown('</div>', unsafe_allow_html=True)

        # ── BLOCO 5: ENVOLVIDO 2 (opcional) ──────────────────────────
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">👥 Envolvido 2 (se houver)</div>', unsafe_allow_html=True)
        env2_nome = st.text_input("Nome completo (envolvido 2)", key="env2n")
        env2_funcao = st.text_input("Função / cargo", key="env2f")
        env2_registro = st.text_input("Registro / matrícula", key="env2r")
        env2_empresa = st.text_input("Empresa / setor", key="env2e")
        env2_telefone = st.text_input("Telefone", key="env2t")
        env2_alegacao = st.text_area("Alegação do envolvido 2", height=80, key="env2a")
        st.markdown('</div>', unsafe_allow_html=True)

        # ── BLOCO 6: LIDERANÇA PRESENTE ──────────────────────────────
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">🏢 Liderança presente (Líder / Supervisor / Gerente)</div>',
                    unsafe_allow_html=True)
        lider_nome = st.text_input("Nome do líder / supervisor / gerente responsável")
        lider_funcao = st.text_input("Função", placeholder="Ex.: Líder de Produção, Supervisor, Gerente")
        lider_registro = st.text_input("Registro", key="lreg")
        lider_telefone = st.text_input("Telefone / ramal", key="ltel")
        lider_alegacao = st.text_area("Parecer / ciência do líder", height=60,
                                      placeholder="Ex.: cientificou-se dos fatos e autorizou...")
        st.markdown('</div>', unsafe_allow_html=True)

        # ── BLOCO 7: TST (apenas em acidentes) ───────────────────────
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">⛑️ Técnico de Segurança do Trabalho (TST) — se presente</div>',
                    unsafe_allow_html=True)
        tst_nome = st.text_input("Nome do TST")
        tst_registro = st.text_input("Registro TST")
        tst_telefone = st.text_input("Telefone TST")
        tst_parecer = st.text_area("Parecer do TST", height=60,
                                   placeholder="Ex.: informou Near Miss / encaminhou ao CSO / não necessário encaminhamento...")
        st.markdown('</div>', unsafe_allow_html=True)

        # ── BLOCO 8: CSO (acidentes com vítimas) ─────────────────────
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">🏥 CSO — Atendimento médico (se houver)</div>',
                    unsafe_allow_html=True)
        cso_ambulancia = st.text_input("Placa da ambulância (se acionada)")
        cso_enfermeiro = st.text_input("Nome e registro do enfermeiro / médico que atendeu")
        cso_diagnostico = st.text_input("Diagnóstico / CID", placeholder="Ex.: Near Miss, contusão leve, medicado...")
        cso_liberacao = st.selectbox("Desfecho médico",
                                     ["Não houve atendimento", "Liberado para atividades laborais",
                                      "Encaminhado para casa", "Encaminhado para hospital", "Em observação"])
        st.markdown('</div>', unsafe_allow_html=True)

        # ── BLOCO 9: VEÍCULOS / DOCUMENTOS ───────────────────────────
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">🚛 Veículos / documentos / ativos envolvidos</div>',
                    unsafe_allow_html=True)
        veiculos_docs = st.text_area("Descreva placas, MVM, DANFE, chassi, rack, notebook, objetos etc.",
                                     height=100,
                                     placeholder="Ex.: Carreta KEW5F00, cavalo GAT3070, MVM 30916656, DANFE 12345...")
        danos_descricao = st.text_area("Danos identificados (citar lado L/D ou L/E e tipo de dano)",
                                       height=80,
                                       placeholder="Veículo 01: para-choque dianteiro L/D amassado. Portão: coluna arranhada...")
        st.markdown('</div>', unsafe_allow_html=True)

        # ── BLOCO 10: PROVIDÊNCIAS E DESFECHO ────────────────────────
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">✅ Providências e Desfecho</div>', unsafe_allow_html=True)
        providencias = st.text_area("Providências tomadas", height=80,
                                    placeholder="Ex.: Central 2400 acionada, veículo encaminhado ao galpão 36 para manutenção, chamado nº X aberto...")
        desfecho = st.text_area("Desfecho final", height=80,
                                placeholder="Ex.: Veículo saiu pela P01 às 06h00. Peças encaminhadas à qualidade. Colaborador liberado para casa.")
        st.markdown('</div>', unsafe_allow_html=True)

        # ── BLOCO 11: EVIDÊNCIAS ──────────────────────────────────────
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">📸 Evidências fotográficas</div>', unsafe_allow_html=True)
        arquivos = st.file_uploader("Anexe até 5 imagens (a IA extrai placas, documentos, textos)",
                                    type=["png", "jpg", "jpeg", "webp"], accept_multiple_files=True)
        st.markdown('</div>', unsafe_allow_html=True)

        submit = st.form_submit_button("🚀 Gerar Boletim de Ocorrência")

    if not submit:
        return

    if not relato_bruto.strip():
        st.warning("O relato bruto é obrigatório.")
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
        "ocorrencia": {
            "data": data_fato.isoformat(),
            "hora": hora_fato.strftime("%H:%M"),
            "local_exato": local_exato.strip(),
            "tipo_referencia": tipo_referencia.strip() or "IDENTIFICAR AUTOMATICAMENTE",
        },
        "relator": {
            "nome": relator_nome.strip() or "NÃO INFORMADO",
            "registro": relator_registro.strip() or "NÃO INFORMADO",
        },
        "relato_bruto": relato_bruto.strip(),
        "envolvido_1": {
            "nome": env1_nome.strip() or "NÃO INFORMADO",
            "funcao": env1_funcao.strip() or "NÃO INFORMADO",
            "registro": env1_registro.strip() or "NÃO INFORMADO",
            "empresa": env1_empresa.strip() or "NÃO INFORMADO",
            "telefone": env1_telefone.strip() or "NÃO INFORMADO",
            "externo": env1_externo,
            "endereco": env1_endereco.strip() if env1_externo else "N/A",
            "filiacao": env1_filiacao.strip() if env1_externo else "N/A",
            "cnh": env1_cnh.strip() if env1_externo else "N/A",
            "alegacao": env1_alegacao.strip() or "NÃO INFORMADO",
        },
        "envolvido_2": {
            "nome": env2_nome.strip() or "NÃO INFORMADO",
            "funcao": env2_funcao.strip() or "NÃO INFORMADO",
            "registro": env2_registro.strip() or "NÃO INFORMADO",
            "empresa": env2_empresa.strip() or "NÃO INFORMADO",
            "telefone": env2_telefone.strip() or "NÃO INFORMADO",
            "alegacao": env2_alegacao.strip() or "NÃO INFORMADO",
        } if env2_nome.strip() else None,
        "lideranca": {
            "nome": lider_nome.strip() or "NÃO INFORMADO",
            "funcao": lider_funcao.strip() or "NÃO INFORMADO",
            "registro": lider_registro.strip() or "NÃO INFORMADO",
            "telefone": lider_telefone.strip() or "NÃO INFORMADO",
            "alegacao": lider_alegacao.strip() or "NÃO INFORMADO",
        } if lider_nome.strip() else None,
        "tst": {
            "nome": tst_nome.strip() or "NÃO INFORMADO",
            "registro": tst_registro.strip() or "NÃO INFORMADO",
            "telefone": tst_telefone.strip() or "NÃO INFORMADO",
            "parecer": tst_parecer.strip() or "NÃO INFORMADO",
        } if tst_nome.strip() else None,
        "cso": {
            "ambulancia_placa": cso_ambulancia.strip() or "NÃO INFORMADO",
            "enfermeiro": cso_enfermeiro.strip() or "NÃO INFORMADO",
            "diagnostico": cso_diagnostico.strip() or "NÃO INFORMADO",
            "liberacao": cso_liberacao,
        } if cso_liberacao != "Não houve atendimento" else None,
        "veiculos_documentos": veiculos_docs.strip() or "NÃO INFORMADO",
        "danos": danos_descricao.strip() or "NÃO INFORMADO",
        "providencias": providencias.strip() or "NÃO INFORMADO",
        "desfecho": desfecho.strip() or "NÃO INFORMADO",
        "qtd_imagens": len(imagens_b64),
        "instrucao": "Gerar BO narrativo completo no padrão Stellantis. Identificar modelo automaticamente. Desfecho obrigatório. Relator ao final.",
    }

    prompt_text = build_prompt(payload)

    with st.spinner("Gerando boletim completo..."):
        texto = chamar_api(client, prompt_text, imagens_b64)

    if not texto:
        st.stop()

    parsed = parse_response(texto)

    st.success("✅ Boletim gerado com sucesso.")

    if parsed:
        bo_texto = parsed.get("bo_texto", "")
        audit = parsed.get("audit", {})

        if bo_texto:
            st.subheader("📄 Boletim de Ocorrência")
            st.markdown(f'<div class="bo-output">{bo_texto}</div>', unsafe_allow_html=True)

            st.download_button(
                label="⬇️ Baixar BO em .txt",
                data=bo_texto,
                file_name=f"BO_{data_fato.strftime('%d%m%Y')}_{hora_fato.strftime('%H%M')}.txt",
                mime="text/plain",
            )

        if audit:
            st.subheader("🔍 Auditoria de Conformidade")
            conf = audit.get("conformidade", "")
            if "APROVADO" in conf.upper():
                st.success(f"**{conf}**")
            else:
                st.warning(f"**{conf}**")

            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown(f"**Modelo identificado:** {audit.get('modelo_identificado', 'NÃO INFORMADO')}")
                st.markdown(f"**Carta próprio punho:** {audit.get('carta_proprio_punho', 'NÃO INFORMADO')}")
            with col_b:
                extraidos = audit.get("dados_extraidos_imagens", [])
                if extraidos:
                    st.markdown("**🔎 Extraído das imagens:**")
                    for item in extraidos:
                        st.write(f"- {item}")

            lacunas = audit.get("lacunas", [])
            if lacunas:
                st.markdown("**⚠️ Lacunas — dados a coletar:**")
                for item in lacunas:
                    st.write(f"- {item}")

            criticos = audit.get("dados_criticos_localizados", [])
            if criticos:
                st.markdown("**✅ Dados críticos confirmados:**")
                for item in criticos:
                    st.write(f"- {item}")
    else:
        st.warning("Resposta bruta (formato livre):")
        st.markdown(f'<div class="bo-output">{texto}</div>', unsafe_allow_html=True)
        st.download_button("⬇️ Baixar resposta .txt", data=texto,
                           file_name=f"BO_{data_fato.strftime('%d%m%Y')}.txt", mime="text/plain")


if __name__ == "__main__":
    main()
