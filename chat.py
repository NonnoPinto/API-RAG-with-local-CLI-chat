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
    print(f"Errore: Il workspace del Knowledge Graph ({WORKSPACE}) non esiste.")
    print("Per favore, esegui prima l'ingestion dei documenti.")
    sys.exit(1)

# ==========================================
# 3. INIZIALIZZAZIONE LIGHTRAG
# ==========================================
print("\n[Sistema]: Inizializzazione di LightRAG in corso...")
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
    # Inizializza gli storage in modo asincrono (richiesto dalle nuove versioni di LightRAG)
    await rag.initialize_storages()

    print("\n==========================================")
    print(" 🤖 LightRAG CLI (Modalità MIX)")
    print(f" LLM: {CHAT_LLM_MODEL} | Embedding: {EMBEDDING_MODEL}")
    print(" Scrivi 'exit' o premi Ctrl+C per uscire")
    print("==========================================\n")

    while True:
        try:
            # Attendiamo l'input dell'utente
            query = input("🧑 [Tu]: ")

            # Gestione uscita
            if query.strip().lower() in ["exit", "quit", "esci"]:
                print("\n[Sistema]: Chiusura in corso. Arrivederci!")
                break

            # Ignoriamo input vuoti
            if not query.strip():
                continue

            print("⚙️  [LightRAG]: Analisi del grafo e ricerca vettoriale in corso...")

            # Esecuzione della query forzando la modalità 'mix' (Vincolo di qualità)
            # await rag.aquery utilizza Traceloop in background
            response = await rag.aquery(query, param=query_params)

            print(f"\n🤖 [Risposta]:\n{response}\n")
            print("-" * 42)

        except KeyboardInterrupt:
            print("\n\n[Sistema]: Interruzione da tastiera rilevata. Arrivederci!")
            break
        except Exception as e:
            print(f"\n❌ [Errore]: Si è verificato un problema: {e}\n")


if __name__ == "__main__":
    # Avvia il loop asincrono
    asyncio.run(chat_loop())
