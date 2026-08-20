import os
import streamlit as st
import requests
import json
import uuid
import base64
from datetime import datetime
import urllib.request
import urllib.parse
import re
import random
from dotenv import load_dotenv
import re 

load_dotenv()

st.set_page_config(page_title="Amoria", page_icon="🤖", layout="wide")

TEXT_API_KEY = os.getenv("TEXT_API_KEY")
IMAGE_API_KEY = os.getenv("IMAGE_API_KEY")

TEXT_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
IMAGE_URL = "https://ai.api.nvidia.com/v1/genai/black-forest-labs/flux.2-klein-4b"

headers_text = {
    "Authorization": f"Bearer {TEXT_API_KEY}",
    "Accept": "application/json",
    "Content-Type": "application/json"
}

headers_image = {
    "Authorization": f"Bearer {IMAGE_API_KEY}",
    "Accept": "application/json",
    "Content-Type": "application/json"
}

def limpar_resposta_ia(texto):
    # Remove blocos <think>...</think> caso o modelo utilize
    texto = re.sub(r'<think>.*?</think>', '', texto, flags=re.DOTALL)
    
    # Se o modelo retornar "Here's a thinking process:" ou similar, remove até o início da resposta real
    if "Here's a thinking process:" in texto or "Analyze User Input:" in texto:
        # Tenta separar o raciocínio da resposta final pelo padrão de texto em português
        partes = re.split(r'\n(?=[A-ZÁÀÂÃÉÈÊÍÓÔÕÚÇ][a-záàâãéèêíóôõúç]+)', texto)
        # Filtra apenas parágrafos que não estejam em inglês/análise
        linhas_validas = [p for p in partes if not any(k in p for k in ["Analyze", "Constraints", "Evaluate", "thinking process"])]
        if linhas_validas:
            return "\n".join(linhas_validas).strip()
            
    return texto.strip()

def extrair_json(texto):
    if not texto:
        return None
        
    texto_limpo = re.sub(r'```(?:json)?', '', texto, flags=re.IGNORECASE)
    texto_limpo = re.sub(r'```', '', texto_limpo).strip()

    match_json = re.search(r'\{.*\}', texto_limpo, re.DOTALL)
    if match_json:
        try:
            return json.loads(match_json.group(0))
        except Exception:
            pass

    try:
        padrao_questao = r'\{\s*"pergunta"\s*:.*?\}(?=\s*,|\s*\]|\s*\}|\s*$)'
        blocos = re.findall(padrao_questao, texto_limpo, re.DOTALL)
        questoes = []
        for bloco in blocos:
            try:
                obj = json.loads(bloco)
                if "pergunta" in obj:
                    questoes.append(obj)
            except Exception:
                continue
        if questoes:
            return {"questoes": questoes}
    except Exception:
        pass

    return None

def pesquisar_na_internet(termo):
    resultados = ""
    
    try:
        wiki_url = f"https://pt.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(termo)}&utf8=&format=json&srlimit=2"
        req = urllib.request.Request(wiki_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=3) as response:
            data = json.loads(response.read().decode())
            if data.get('query', {}).get('search'):
                resultados += "Base de Dados Enciclopédica:\n"
                for item in data['query']['search']:
                    snippet = re.sub(r'<[^>]+>', '', item['snippet'])
                    resultados += f"- {item['title']}: {snippet}\n"
    except Exception:
        pass
        
    try:
        url = f"https://br.search.yahoo.com/search?p={urllib.parse.quote(termo)}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as response:
            html = response.read().decode('utf-8')
            snippets = re.findall(r'<div class="compText[^>]*>(.*?)</div>', html, re.IGNORECASE | re.DOTALL)
            if snippets:
                resultados += "\nResultados em Tempo Real da Web:\n"
                for snip in snippets[:4]:
                    clean_snip = re.sub(r'<[^>]+>', '', snip).strip()
                    if clean_snip:
                        resultados += f"- {clean_snip}\n"
    except Exception:
        pass

    return resultados.strip() if resultados else None

def responder_ia_estudos(mensagem_usuario, modelo="nvidia/nemotron-3.5-lightning-30b-a3b"):
    # 1. Obter a data atual formatada
    hoje = datetime.now().strftime("%d/%m/%Y")

    # 2. Definir o prompt do sistema restringindo o tema e informando a data
    prompt_sistema = f"""Você é a Amoria, uma assistente educacional.

Regras estritas de comportamento:
1. SEMPRE responda em português (pt-br)
2. Data de Hoje: Hoje é dia {hoje}. Utilize esta informação sempre que o usuário perguntar sobre a data atual.
3. Sempre seja educado e respeitoso
4. Seu nome é Amoria, você é uma IA educacional que auxilia quem precisar
5. Tente não desviar o assunto de estudos."""

    payload = {
        "model": modelo,
        "messages": [
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": mensagem_usuario}
        ],
        "temperature": 0.5,
        "max_tokens": 1024
    }

    try:
        res = requests.post(TEXT_URL, headers=headers_text, json=payload, timeout=60)
        if res.status_code == 200:
            conteudo_bruto = res.json()['choices'][0]['message']['content']
            return limpar_resposta_ia(conteudo_bruto)
        else:
            print(f"Erro na API: {res.status_code}")
    except Exception as e:
        print(f"Exceção ao chamar IA: {e}")

    return "Não foi possível obter resposta no momento. Tente novamente."

def normalizar_texto(texto):
    if not texto:
        return ""
    txt = str(texto).strip().lower()
    match = re.match(r'^([a-d])[\)\-\.\s]', txt)
    if match:
        return match.group(1)
    return txt

def requisitar_ia_questoes(assunto, modelo="nvidia/nemotron-3.5-lightning-30b-a3b"):
    perspectivas = [
        "estudos de caso práticos", "análise de causa e efeito", "perspectiva histórica e evolução",
        "aplicações no mundo real", "erros e mitos comuns", "comparação de conceitos",
        "cenários hipotéticos", "impactos socioeconômicos ou científicos", "resolução de problemas"
    ]
    publicos = ["estudantes universitários", "especialistas da área", "alunos do ensino médio", "pesquisadores"]
    focos = ["detalhes técnicos e específicos", "visão panorâmica e crítica", "conceitos fundamentais e aplicações"]

    p_sorteada = random.sample(perspectivas, 3)
    pub_sorteado = random.choice(publicos)
    foco_sorteado = random.choice(focos)
    seed = random.randint(100000, 999999)

    prompt_sistema = (
        "Você é um professor e elaborador de exames extremamente criativo. "
        "Sua tarefa é criar avaliações inéditas, profundas e variadas. "
        "Responda EXCLUSIVAMENTE com um objeto JSON válido, sem texto explicativo antes ou depois."
    )

    prompt_usuario = f"""Gere um teste inédito com 10 questões sobre o tema: '{assunto}'.
ID Único de Variação: {seed}

Diretrizes de Conteúdo:
- Nível do público: {pub_sorteado}.
- Foco principal: {foco_sorteado}.
- Explore abordagens como: {', '.join(p_sorteada)}.
- NENHUMA pergunta deve ser genérica ou reutilizar padrões.
- Cada pergunta deve abordar um fato, conceito, exemplo ou cenário específico sobre '{assunto}'.

Formato Obrigatório do JSON:
{{
  "questoes": [
    {{
      "pergunta": "Texto da questão de múltipla escolha...",
      "tipo": "multipla",
      "opcoes": ["A) ...", "B) ...", "C) ...", "D) ..."],
      "resposta_correta": "A) ..."
    }},
    ... (7 questões do tipo "multipla")
    {{
      "pergunta": "Texto da questão discursiva...",
      "tipo": "escrita",
      "resposta_esperada": "Critérios detalhados do que se espera na resposta..."
    }}
    ... (3 questões do tipo "escrita")
  ]
}}"""

    payload = {
        "model": modelo,
        "messages": [
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": prompt_usuario}
        ],
        "temperature": 0.7,
        "top_p": 0.9,
        "max_tokens": 3500
    }

    try:
        res = requests.post(TEXT_URL, headers=headers_text, json=payload, timeout=90)
        if res.status_code == 200:
            conteudo = res.json()['choices'][0]['message']['content']
            dados = extrair_json(conteudo)
            if dados and "questoes" in dados and isinstance(dados["questoes"], list):
                return dados["questoes"]
        else:
            print(f"Erro na API ({modelo}): Status {res.status_code} - {res.text}")
    except Exception as e:
        print(f"Exceção ao chamar modelo {modelo}: {e}")

    return []

def gerar_questoes_formulario(assunto):
    questoes_raw = requisitar_ia_questoes(assunto, modelo="nvidia/nemotron-3.5-lightning-30b-a3b")

    if len(questoes_raw) < 10:
        questoes_raw = requisitar_ia_questoes(assunto, modelo="meta/llama-3.1-70b-instruct")

    if len(questoes_raw) < 10:
        questoes_raw = requisitar_ia_questoes(assunto, modelo="meta/llama-3.1-8b-instruct")

    if not questoes_raw:
        return "Servidor ocupado no momento. Por favor, clique em 'Gerar Formulário' novamente."

    questoes_finais = []
    prefixos = ["A) ", "B) ", "C) ", "D) "]

    for i, q in enumerate(questoes_raw[:10]):
        q_copia = dict(q)
        q_copia["id"] = i + 1

        is_multipla = "opcoes" in q_copia and isinstance(q_copia["opcoes"], list) and len(q_copia["opcoes"]) >= 2
        q_copia["tipo"] = "multipla" if is_multipla else "escrita"

        if q_copia["tipo"] == "multipla":
            opcoes_brutas = q_copia.get("opcoes", [])
            opcoes_limpas = [re.sub(r'^[A-Da-d][\)\-\.\s]+', '', str(opt)).strip() for opt in opcoes_brutas[:4]]
            
            while len(opcoes_limpas) < 4:
                opcoes_limpas.append("Outra alternativa relacionada ao tema")

            random.shuffle(opcoes_limpas)
            q_copia["opcoes"] = [f"{prefixos[j]}{opcoes_limpas[j]}" for j in range(4)]

            resp_orig = str(q_copia.get("resposta_correta", "")).strip()
            resp_norm = normalizar_texto(resp_orig)

            idx = 0
            if resp_norm in ['a', 'b', 'c', 'd']:
                idx = ['a', 'b', 'c', 'd'].index(resp_norm)
            else:
                resp_limpa = re.sub(r'^[A-Da-d][\)\-\.\s]+', '', resp_orig).strip().lower()
                for j, opt in enumerate(opcoes_limpas):
                    if opt.lower() == resp_limpa:
                        idx = j
                        break
            
            q_copia["resposta_correta"] = q_copia["opcoes"][idx]
            q_copia.pop("resposta_esperada", None)
        else:
            q_copia.pop("opcoes", None)
            q_copia.pop("resposta_correta", None)
            if not q_copia.get("resposta_esperada"):
                q_copia["resposta_esperada"] = f"Análise detalhada esperada sobre {assunto}."

        questoes_finais.append(q_copia)

    return questoes_finais

def corrigir_formulario_com_ia(questoes, respostas_usuario):
    qtd_questoes = len(questoes)
    if qtd_questoes == 0:
        return None

    valor_por_questao = 10.0 / qtd_questoes
    detalhes = []
    questoes_escritas_para_ia = []

    for i, q in enumerate(questoes):
        q_id = i + 1
        tipo = q.get("tipo", "multipla")
        resposta_aluno = respostas_usuario.get(i, "")

        if tipo == "multipla":
            gabarito = q.get("resposta_correta", "")
            aluno_norm = normalizar_texto(resposta_aluno)
            gabarito_norm = normalizar_texto(gabarito)
            
            acertou = (aluno_norm != "" and aluno_norm == gabarito_norm) or (str(resposta_aluno).strip().lower() == str(gabarito).strip().lower())
            pontos = round(valor_por_questao, 2) if acertou else 0.0

            detalhes.append({
                "id": q_id,
                "pontuacao": pontos,
                "feedback": ""
            })
        else:
            questoes_escritas_para_ia.append({
                "id": q_id,
                "pergunta": q.get("pergunta"),
                "resposta_esperada": q.get("resposta_esperada"),
                "resposta_do_aluno": resposta_aluno,
                "valor_maximo": round(valor_por_questao, 2)
            })

    comentario_geral = "Parabéns por concluir a atividade! Continue praticando."
    
    if questoes_escritas_para_ia:
        prompt_sistema = f"""Você é uma professora corrigindo questões discursivas de alunos.
Avalie cada resposta discursiva comparando com o gabarito. Atribua a nota proporcional até o valor_maximo.

Retorne um JSON com a estrutura:
{{
  "comentario_geral": "Mensagem motivadora",
  "correcoes": [
    {{
      "id": id_da_questao,
      "pontuacao": valor_da_nota,
      "feedback": "Comentário construtivo"
    }}
  ]
}}"""

        payload = {
            "model": "nvidia/nemotron-3.5-lightning-30b-a3b",
            "messages": [
                {"role": "system", "content": prompt_sistema},
                {"role": "user", "content": json.dumps(questoes_escritas_para_ia, ensure_ascii=False)}
            ],
            "temperature": 0.2,
            "max_tokens": 1500
        }

        try:
            res = requests.post(TEXT_URL, headers=headers_text, json=payload, timeout=100)
            if res.status_code == 200:
                conteudo = res.json()['choices'][0]['message']['content']
                res_ia = extrair_json(conteudo)

                if res_ia and isinstance(res_ia.get("correcoes"), list):
                    correcoes_map = {item["id"]: item for item in res_ia["correcoes"] if "id" in item}
                    for item in detalhes:
                        if item["id"] in correcoes_map:
                            item["pontuacao"] = float(correcoes_map[item["id"]].get("pontuacao", 0.0))
                            item["feedback"] = str(correcoes_map[item["id"]].get("feedback", ""))
                    
                    comentario_geral = res_ia.get("comentario_geral", comentario_geral)
        except Exception:
            pass

        for q_escrita in questoes_escritas_para_ia:
            q_id = q_escrita["id"]
            if not any(d["id"] == q_id and d["feedback"] for d in detalhes):
                txt_aluno = str(q_escrita["resposta_do_aluno"]).strip()
                pts = round(valor_por_questao, 2) if len(txt_aluno) > 15 else 0.0
                fb = "Boa resposta!" if pts > 0 else "Resposta muito curta ou ausente."
                detalhes.append({
                    "id": q_id,
                    "pontuacao": pts,
                    "feedback": fb
                })

    nota_final = round(sum(d["pontuacao"] for d in detalhes), 2)

    return {
        "nota_final": min(nota_final, 10.0),
        "comentario_geral": comentario_geral,
        "detalhes": detalhes
    }

HOJE_STR = datetime.now().strftime("%d/%m/%Y") if not hasattr(datetime, 'datetime') else datetime.datetime.now().strftime("%d/%m/%Y")

PROMPT_AMORIA = (
    f"Você é a Amoria, uma assistente educacional doce, didática e amigável. "
    f"Responda SEMPRE em Português (PT-BR) de forma direta ao usuário.\n\n"
    f"REGRAS:\n"
    f"1. A data de hoje é {HOJE_STR}.\n"
    f"2. SAUDAÇÕES: Responda cumprimentos como 'oi', 'olá' e 'tudo bem' com simpatia e pergunte como pode ajudar nos estudos.\n"
    f"3. TEMA: Responda APENAS a dúvidas sobre matérias, escola, ciência, vestibuarl e métodos de estudo. Para fofocas, piadas ou papos informais, recuse educadamente focando na sua função de tutora.\n"
    f"4. RESPOSTA DIRETA: NÃO exiba raciocínio interno, análises de regras, listas de checagem ou textos em inglês. Entregue apenas a mensagem final ao usuário."
)

if "chats" not in st.session_state:
    st.session_state.chats = {}

if "current_chat" not in st.session_state or not st.session_state.chats:
    primeiro_id = str(uuid.uuid4())
    st.session_state.chats[primeiro_id] = {
        "titulo": "Nova Conversa",
        "mensagens": [{"role": "system", "content": PROMPT_AMORIA}]
    }
    st.session_state.current_chat = primeiro_id

for cid, cdata in list(st.session_state.chats.items()):
    if isinstance(cdata, list):
        st.session_state.chats[cid] = {
            "titulo": "Conversa Antiga",
            "mensagens": cdata
        }

if "modo_form" not in st.session_state:
    st.session_state.modo_form = False
if "questoes" not in st.session_state:
    st.session_state.questoes = None
if "resultado_correcao" not in st.session_state:
    st.session_state.resultado_correcao = None

with st.sidebar:
    st.title("⚙️ Painel Amoria")
    gerar_imagem = st.toggle("🎨 Modo Gerar Imagem")
    st.divider()

    st.subheader("💬 Conversas")
    if st.button("➕ Nova Conversa", use_container_width=True):
        novo_id = str(uuid.uuid4())
        st.session_state.chats[novo_id] = {
            "titulo": "Nova Conversa",
            "mensagens": [{"role": "system", "content": PROMPT_AMORIA}]
        }
        st.session_state.current_chat = novo_id
        st.rerun()

    if len(st.session_state.chats) > 0:
        st.session_state.current_chat = st.selectbox(
            "Alternar entre conversas:",
            options=list(st.session_state.chats.keys()),
            format_func=lambda x: st.session_state.chats[x]["titulo"] if isinstance(st.session_state.chats.get(x), dict) else "Conversa"
        )

    st.divider()
    st.subheader("📝 Ferramentas")
    if st.button("📝 Criar Formulário", use_container_width=True):
        st.session_state.modo_form = True
        st.session_state.questoes = None
        st.session_state.resultado_correcao = None
        st.rerun()
    
    if st.button("🗑️ Limpar Tudo", use_container_width=True):
        st.session_state.chats = {}
        st.session_state.modo_form = False
        st.session_state.questoes = None
        st.session_state.resultado_correcao = None
        st.rerun()

st.title("🎓 Amoria: IA Educacional")

if st.session_state.modo_form:
    st.info("📝 **Modo Formulário Educativo**")
    
    if st.session_state.questoes is None:
        tema = st.text_input("Sobre qual assunto vamos praticar hoje?", placeholder="Ex: Reprodução humana, Fotossíntese, Revolução Francesa...")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🚀 Gerar Formulário", use_container_width=True):
                if not tema.strip():
                    st.warning("Por favor, digite um assunto antes de gerar!")
                else:
                    with st.spinner("Amoria está gerando seu formulário..."):
                        resultado = gerar_questoes_formulario(tema)
                        if isinstance(resultado, list):
                            st.session_state.questoes = resultado
                            st.session_state.tema_atual = tema
                            st.session_state.resultado_correcao = None
                            st.rerun()
                        else:
                            st.error(f"⚠️ {resultado}")
        with col2:
            if st.button("❌ Sair", use_container_width=True):
                st.session_state.modo_form = False
                st.rerun()
        st.stop()
        
    else:
        if st.button("⬅️ Voltar ao Chat Principal", use_container_width=True):
            st.session_state.modo_form = False
            st.session_state.questoes = None
            st.session_state.resultado_correcao = None
            st.rerun()
            
        st.subheader(f"📌 Formulário: {st.session_state.get('tema_atual', 'Exercício')}")
        st.divider()
        
        if st.session_state.resultado_correcao:
            resultado = st.session_state.resultado_correcao
            nota = resultado.get("nota_final", 0.0)
            
            st.metric("🏆 Sua Nota Final", f"{nota:.1f} / 10.0")
            st.markdown(f"**💬 Mensagem da Amoria:** {resultado.get('comentario_geral', '')}")
            st.divider()
            
            detalhes_map = {item['id']: item for item in resultado.get("detalhes", []) if isinstance(item, dict) and 'id' in item}
            max_ponto_por_q = 10.0 / len(st.session_state.questoes)
            
            for i, q in enumerate(st.session_state.questoes):
                detalhe = detalhes_map.get(i + 1, {})
                pontos = detalhe.get("pontuacao", 0.0)
                feedback = detalhe.get("feedback", "Sem feedback disponível.")
                
                status_icon = "✅" if pontos >= (max_ponto_por_q * 0.7) else ("⚠️" if pontos > 0 else "❌")
                st.markdown(f"### {status_icon} Questão {i+1}: {q.get('pergunta')}")
                st.write(f"**Pontuação:** {pontos:.2f} / {max_ponto_por_q:.2f}")
                if q.get('tipo') == 'escrita' and feedback and str(feedback).strip():
                    st.info(f"**Feedback da Amoria:** {feedback}")
                if q.get('tipo') == 'multipla':
                    st.write(f"**Gabarito:** {q.get('resposta_correta')}")
                else:
                    st.write(f"**Resposta Esperada:** {q.get('resposta_esperada')}")
                st.divider()
                
            if st.button("🔄 Tentar Novo Formulário", use_container_width=True):
                st.session_state.questoes = None
                st.session_state.resultado_correcao = None
                st.rerun()
            st.stop()

        respostas_usuario = {}
        with st.form("form_exercicio"):
            for i, q in enumerate(st.session_state.questoes):
                st.markdown(f"#### **{i+1}. {q.get('pergunta')}**")
                if q.get('tipo') == "multipla":
                    respostas_usuario[i] = st.radio(
                        "Escolha uma opção:", 
                        q.get('opcoes', []), 
                        key=f"q_{i}", 
                        index=None
                    )
                else:
                    respostas_usuario[i] = st.text_area(
                        "Sua resposta discursiva:", 
                        key=f"q_{i}", 
                        placeholder="Escreva sua resposta detalhada aqui..."
                    )
                st.divider()
            
            submitted = st.form_submit_button("✨ Enviar para Correção da Amoria", use_container_width=True)
            if submitted:
                with st.spinner("Amoria está lendo e corrigindo suas respostas minuciosamente..."):
                    res = corrigir_formulario_com_ia(st.session_state.questoes, respostas_usuario)
                    if res:
                        st.session_state.resultado_correcao = res
                        st.rerun()
                    else:
                        st.error("Houve uma falha ao processar a correção pela IA. Tente enviar novamente!")
        st.stop()

if st.session_state.current_chat and st.session_state.current_chat in st.session_state.chats:
    chat_atual = st.session_state.chats[st.session_state.current_chat]

    for message in chat_atual["mensagens"]:
        if message["role"] != "system":
            with st.chat_message(message["role"]):
                if message.get("type") == "image":
                    st.image(message["content"])
                else:
                    st.markdown(message["content"])

    if prompt := st.chat_input("Pergunte algo..."):
        if chat_atual["titulo"] == "Nova Conversa":
            chat_atual["titulo"] = prompt[:30] + ("..." if len(prompt) > 30 else "")

        chat_atual["mensagens"].append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            if gerar_imagem:
                with st.spinner("Preparando a imagem..."):
                    try:
                        response = requests.post(IMAGE_URL, headers=headers_image, json={"prompt": prompt})
                        if response.status_code == 200:
                            img_b64 = response.json().get("artifacts", [{}])[0].get("base64") or response.json().get("image")
                            if img_b64:
                                image_bytes = base64.b64decode(img_b64)
                                st.image(image_bytes)
                                chat_atual["mensagens"].append({"role": "assistant", "content": image_bytes, "type": "image"})
                    except Exception:
                        st.error("Erro ao gerar imagem.")
            else:
                prompt_limpo = prompt.strip().lower()
                e_conversa_curta = len(prompt.split()) <= 4 and not any(p in prompt_limpo for p in ["explique", "pesquise", "por que", "como funciona", "resuma"])

                if e_conversa_curta:
                    resposta_rapida = responder_ia_estudos(prompt)
                    st.markdown(resposta_rapida)
                    chat_atual["mensagens"].append({"role": "assistant", "content": resposta_rapida})

                else:
                    placeholder = st.empty()
                    full_response = ""
                    
                    with st.spinner("Consultando dados..."):
                        dados_internet = pesquisar_na_internet(prompt)
                    
                    historico_api = [{"role": m["role"], "content": m["content"]} for m in chat_atual["mensagens"] if m.get("type") != "image"]

                    if dados_internet:
                        instrucao_silenciosa = (
                            f"Contexto de apoio (Baseie-se nisso se for útil, MAS NÃO MENCIONE QUE RECEBEU ESTE CONTEXTO OU QUE FEZ UMA BUSCA. Aja como se você já soubesse):\n"
                            f"{dados_internet}\n\n"
                            f"Mensagem do Usuário: {prompt}"
                        )
                        historico_api[-1]["content"] = instrucao_silenciosa

                    payload = {
                        "model": "nvidia/nemotron-3.5-lightning-30b-a3b",
                        "messages": historico_api,
                        "stream": True,
                        "temperature": 0.4
                    }
                    
                    try:
                        r = requests.post(TEXT_URL, headers=headers_text, json=payload, stream=True)
                        for line in r.iter_lines():
                            if line:
                                line_text = line.decode("utf-8")
                                if line_text.startswith("data: "):
                                    json_str = line_text[6:].strip()
                                    if json_str == "[DONE]": 
                                        break
                                    try:
                                        content = json.loads(json_str)['choices'][0].get('delta', {}).get('content', '')
                                        full_response += content
                                        placeholder.markdown(full_response + "▌")
                                    except Exception: 
                                        continue
                        placeholder.markdown(full_response)
                        chat_atual["mensagens"].append({"role": "assistant", "content": full_response})
                    except Exception:
                        st.error("Erro na conexão.")