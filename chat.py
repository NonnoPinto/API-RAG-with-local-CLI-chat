import asyncio
import os
import sys

# ==========================================
# 1. INIEZIONE TRACELOOP (OPENLLMETRY)
# ==========================================
# Inizializzazione prima di importare i modelli per garantire l'auto-instrumentation
from traceloop.sdk import Traceloop
from traceloop.sdk.decorators import workflow

Traceloop.init(app_name="lightrag_cli", disable_batch=True)

from lightrag import LightRAG, QueryParam
from lightrag.utils import EmbeddingFunc

from lightrag import LightRAG
from lightrag.llm.ollama import ollama_model_complete, ollama_embed
from lightrag.utils import EmbeddingFunc

# ==========================================
# 2. CONFIGURAZIONE AMBIENTE
# ==========================================
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://ollama:11434")
CHAT_LLM_MODEL = os.environ.get("CHAT_LLM_MODEL", "llama3.2:1b")
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "bge-m3")
LLM_CONTEXT_WINDOW = int(os.environ.get("LLM_CONTEXT_WINDOW", "8192"))
WORKSPACE = os.environ.get("LIGHTRAG_WORKSPACE", "/app/kb")

if not os.path.exists(WORKSPACE):
    print(f"Error: The Knowledge Graph workspace ({WORKSPACE}) does not exist.")
    print("Please run the ingestion script first.")
    sys.exit(1)

# ==========================================
# 3. INIZIALIZZAZIONE LIGHTRAG
# ==========================================
print("\n[System]: Initializing LightRAG...")
# 1. Definiamo la funzione per Llama (Keyword Extraction locale)
async def ollama_llm_complete(prompt, **kwargs):
    return await ollama_model_complete(
        prompt,
        **kwargs
    )

rag = LightRAG(
    working_dir=WORKSPACE,
    llm_model_func=ollama_llm_complete,
    llm_model_name=CHAT_LLM_MODEL, 
    llm_model_max_async=1,
    llm_model_kwargs={
        "host": OLLAMA_HOST,
        "options": {"num_ctx": 8192},
    },

    chunk_token_size=300,
    chunk_overlap_token_size=50,
    embedding_func=EmbeddingFunc(
        embedding_dim=1024,
        max_token_size=8192,
        func=lambda texts: ollama_embed(
            texts,
            embed_model=EMBEDDING_MODEL,
            host=OLLAMA_HOST
        ),
    ),
)

query_params = QueryParam(
    mode="hybrid",
    enable_rerank=False
)

# ==========================================
# 4. INTERFACCIA CHAT CLI
# ==========================================
@workflow(name="rag_chat_cli")
async def chat_loop():
    """
    Loop principale per l'interazione via terminale con il Knowledge Graph.
    Traceloop monitora ogni iterazione grazie al decoratore.
    """
    await rag.initialize_storages()

    print("\n==========================================")
    print(" 🤖 LightRAG CLI (Modalità MIX)")
    print(f" LLM: {CHAT_LLM_MODEL} | Embedding: {EMBEDDING_MODEL}")
    print(" Write 'exit' or press Ctrl+C to exit")
    print("==========================================\n")

    while True:
        try:
            query = input("🧑 [You]: ")

            # Gestione uscita
            if query.strip().lower() in ["exit", "quit", "esci"]:
                print("\n[System]: Closing in progress. Goodbye!")
                break

            if not query.strip():
                continue

            print("⚙️  [LightRAG]: Analysis of the graph and vector search in progress...")
            start_time = os.times()[4]
            response = await rag.aquery(query, param=query_params)
            
            end_time = os.times()[4]
            duration = end_time - start_time
            print(f"\n🤖 [Response]:\n{response}\n")
            print(f"⏱️  Response time: {duration:.2f} seconds")
            print("-" * 42)

        except KeyboardInterrupt:
            print("\n\n[System]: Interruption from keyboard detected. Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ [Error]: A problem occurred: {e}\n")


if __name__ == "__main__":
    asyncio.run(chat_loop())
