import json
import torch
import streamlit as st
from transformers import AutoModelForCausalLM, AutoTokenizer
from transformers.generation.utils import GenerationConfig
from rag.vector_retriever import VectorRetriever
from rag.graph_retriever import GraphRetriever


st.set_page_config(page_title="FudanDISC-LawLLM")
st.title("FudanDISC-LawLLM🤖️")


@st.cache_resource
def init_retriever():
    try:
        return GraphRetriever("rag/law_db")
    except Exception:
        return VectorRetriever("rag/law_db")


@st.cache_resource
def init_model():
    model_path = "ShengbinYue/DISC-LawLLM"
    model = AutoModelForCausalLM.from_pretrained(
        model_path, torch_dtype=torch.float16, device_map="auto", trust_remote_code=True
    )
    model.generation_config = GenerationConfig.from_pretrained(model_path)
    tokenizer = AutoTokenizer.from_pretrained(
        model_path, use_fast=False, trust_remote_code=True
    )
    return model, tokenizer


def clear_chat_history():
    del st.session_state.messages
    del st.session_state.model_messages


def init_chat_history():
    with st.chat_message("assistant", avatar="🤖"):
        st.markdown("您好，我是复旦 DISC-LawLLM，很高兴为您服务💖")

    if "messages" in st.session_state:
        for message in st.session_state.messages:
            avatar = "🙋‍♂️" if message["role"] == "user" else "🤖"
            with st.chat_message(message["role"], avatar=avatar):
                st.markdown(message["content"])
    else:
        st.session_state.messages = []

    return st.session_state.messages


def main():
    model, tokenizer = init_model()
    retriever = init_retriever()
    messages = init_chat_history()

    if "model_messages" not in st.session_state:
        st.session_state.model_messages = []
    model_messages = st.session_state.model_messages

    if prompt := st.chat_input("Shift + Enter 换行，Enter 发送"):
        with st.chat_message("user", avatar="🙋‍♂️"):
            st.markdown(prompt)
        context = retriever.format_context(prompt)
        augmented = context + prompt if context else prompt
        messages.append({"role": "user", "content": prompt})
        model_messages.append({"role": "user", "content": augmented})
        print(f"[user] {prompt}", flush=True)
        with st.chat_message("assistant", avatar="🤖"):
            placeholder = st.empty()
            for response in model.chat(tokenizer, model_messages, stream=True):
                placeholder.markdown(response)
                if torch.backends.mps.is_available():
                    torch.mps.empty_cache()
        messages.append({"role": "assistant", "content": response})
        model_messages.append({"role": "assistant", "content": response})
        print(json.dumps(messages, ensure_ascii=False), flush=True)

        st.button("清空对话", on_click=clear_chat_history)


if __name__ == "__main__":
    main()
