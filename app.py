import streamlit as st
import requests
import json
import uuid
import base64
import time
import datetime
import urllib.request
import urllib.parse
import re


st.set_page_config(page_title="Amoria", page_icon="🤖", layout="wide")

TEXT_API_KEY = "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"
IMAGE_API_KEY = "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"

TEXT_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
IMAGE_URL = "https://ai.api.nvidia.com/v1/genai/black-forest-labs/flux.2-klein-4b"

headers_text = {
    "Authorization": f"Bearer {TEXT_API_KEY}",
    "Accept": "text/event-stream",
    "Content-Type": "application/json"
}

headers_image = {
    "Authorization": f"Bearer {IMAGE_API_KEY}",
    "Accept": "application/json",
    "Content-Type": "application/json"
}


def pesquisar_na_internet(termo):
    """Busca robusta na web usando Yahoo (estável e sem bloqueios) e Wikipedia."""
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
                for snip in snippets[:4]: # Pega os 4 melhores
                    clean_snip = re.sub(r'<[^>]+>', '', snip).strip()
                    if clean_snip:
                        resultados += f"- {clean_snip}\n"
    except Exception:
        pass

    return resultados.strip() if resultados else None


def gerar_questoes_formulario(assunto):
    prompt_sistema = """
    Você é um gerador de formulários educativos. 
    Crie EXATAMENTE 10 questões inéditas, criativas e variadas sobre o assunto solicitado.
    Retorne APENAS um JSON no seguinte formato:
    [
      {"tipo": "multipla", "pergunta": "Texto", "opcoes": ["A", "B", "C", "D"], "correta": "A"},
      {"tipo": "escrita", "pergunta": "Texto dissertativo"}
    ]
    """
    payload = {
        "model": "nvidia/nemotron-3.5-lightning-30b-a3b",
        "messages": [
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": f"Assunto: {assunto}"}
        ],
        "temperature": 0.8 
    }
    try:
        res = requests.post(TEXT_URL, headers=headers_text, json=payload)
        conteudo = res.json()['choices'][0]['message']['content'].replace('```json', '').replace('```', '').strip()
        return json.loads(conteudo)
    except Exception:
        return None


HOJE_STR = datetime.datetime.now().strftime("%d/%m/%Y")

PROMPT_AMORIA = (
    f"Seu nome é Amoria. Você é uma assistente educacional doce, didática e muito inteligente. "
    f"Fale sempre de forma natural, direta e amigável. A data de hoje é {HOJE_STR}."
)

if "chats" not in st.session_state:
    st.session_state.chats = {} 
if "current_chat" not in st.session_state:
    primeiro_id = str(uuid.uuid4())
    st.session_state.chats[primeiro_id] = [{"role": "system", "content": PROMPT_AMORIA}]
    st.session_state.current_chat = primeiro_id
if "historico_forms" not in st.session_state:
    st.session_state.historico_forms = []
if "modo_form" not in st.session_state:
    st.session_state.modo_form = False
if "questoes" not in st.session_state:
    st.session_state.questoes = None


with st.sidebar:
    st.title("⚙️ Painel Amoria")
    gerar_imagem = st.toggle("🎨 Modo Gerar Imagem")
    st.divider()

    st.subheader("💬 Conversas")
    if st.button("➕ Nova Conversa", use_container_width=True):
        novo_id = str(uuid.uuid4())
        st.session_state.chats[novo_id] = [{"role": "system", "content": PROMPT_AMORIA}]
        st.session_state.current_chat = novo_id
        st.rerun()
    
    if len(st.session_state.chats) > 1:
        st.session_state.current_chat = st.selectbox(
            "Alternar entre conversas:",
            options=list(st.session_state.chats.keys()),
            format_func=lambda x: f"Conversa {x[:8]}..."
        )

    st.divider()
    st.subheader("📝 Ferramentas")
    if st.button("📝 Criar Formulário", use_container_width=True):
        st.session_state.modo_form = True
        st.session_state.questoes = None
        st.rerun()
    
    if st.button("🗑️ Limpar Tudo", use_container_width=True):
        st.session_state.chats = {}
        st.session_state.historico_forms = []
        st.rerun()
        
    st.divider()
    for chat_id in list(st.session_state.chats.keys()):
        titulo_chat = next((m["content"][:20] + "..." for m in st.session_state.chats[chat_id] if m["role"] == "user"), "Nova Conversa")
        col1, col2 = st.columns([4, 1])
        with col1:
            if st.button(f"{'📍 ' if chat_id == st.session_state.current_chat else ''}{titulo_chat}", key=f"btn_{chat_id}", use_container_width=True):
                st.session_state.current_chat = chat_id
                st.rerun()
        with col2:
            if st.button("🗑️", key=f"del_{chat_id}"):
                del st.session_state.chats[chat_id]
                if not st.session_state.chats:
                    st.session_state.current_chat = None
                st.rerun()


st.title("🎓 Amoria: IA Educacional")

if st.session_state.modo_form:
    st.info("📝 **Modo Formulário**")
    if st.session_state.questoes is None:
        tema = st.text_input("Sobre qual assunto vamos praticar hoje?")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Gerar Formulário", use_container_width=True) and tema:
                with st.spinner("Criando questões..."):
                    st.session_state.questoes = gerar_questoes_formulario(tema)
                    st.session_state.tema_atual = tema
                    st.rerun()
        with col2:
            if st.button("Sair", use_container_width=True):
                st.session_state.modo_form = False
                st.rerun()
        st.stop()
    else:
        if st.button("⬅️ Voltar ao Chat", use_container_width=True):
            st.session_state.modo_form = False
            st.session_state.questoes = None
            st.rerun()
        st.divider()
        respostas_usuario = {}
        for i, q in enumerate(st.session_state.questoes):
            st.write(f"**{i+1}. {q['pergunta']}**")
            if q['tipo'] == "multipla":
                respostas_usuario[i] = st.radio(f"Escolha:", q['opcoes'], key=f"q{i}")
            else:
                respostas_usuario[i] = st.text_area(f"Resposta:", key=f"q{i}")
            st.divider()
        if st.button("Corrigir"):
            acertos = sum(1 for i, q in enumerate(st.session_state.questoes) if q['tipo'] == "multipla" and respostas_usuario[i] == q['correta'])
            total = sum(1 for q in st.session_state.questoes if q['tipo'] == "multipla")
            st.metric("Nota", f"{(acertos/total)*10:.1f}/10" if total > 0 else "0/10")
            if st.button("Concluir"):
                st.session_state.modo_form = False
                st.session_state.questoes = None
                st.rerun()
        st.stop()


if st.session_state.current_chat and st.session_state.current_chat in st.session_state.chats:
    for message in st.session_state.chats[st.session_state.current_chat]:
        if message["role"] != "system":
            with st.chat_message(message["role"]):
                if message.get("type") == "image":
                    st.image(message["content"])
                else:
                    st.markdown(message["content"])

    if prompt := st.chat_input("Pergunte algo..."):
        st.session_state.chats[st.session_state.current_chat].append({"role": "user", "content": prompt})
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
                                st.session_state.chats[st.session_state.current_chat].append({"role": "assistant", "content": image_bytes, "type": "image"})
                    except Exception:
                        st.error("Erro ao gerar imagem.")
            else:
                placeholder = st.empty()
                full_response = ""
                
                with st.spinner("Consultando dados..."):
                    dados_internet = pesquisar_na_internet(prompt)
                
                
                historico_api = [{"role": m["role"], "content": m["content"]} for m in st.session_state.chats[st.session_state.current_chat] if m.get("type") != "image"]

                
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
                                if json_str == "[DONE]": break
                                try:
                                    content = json.loads(json_str)['choices'][0].get('delta', {}).get('content', '')
                                    full_response += content
                                    placeholder.markdown(full_response + "▌")
                                except Exception: continue
                    placeholder.markdown(full_response)
                    st.session_state.chats[st.session_state.current_chat].append({"role": "assistant", "content": full_response})
                except Exception:
                    st.error("Erro na conexão.")
                    
