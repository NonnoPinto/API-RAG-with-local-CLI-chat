import argparse
import asyncio
import os
from typing import List

# ==========================================
# 1. INIEZIONE TRACELOOP (OPENLLMETRY)
# ==========================================
# Inizializzazione prima di importare i modelli per garantire l'auto-instrumentation
from traceloop.sdk import Traceloop
from traceloop.sdk.decorators import task, workflow

# Initialize Traceloop for OpenLLMetry observability
Traceloop.init(app_name="lightrag_ingestor", disable_batch=True)

from firecrawl import FirecrawlApp
from lightrag.llm.ollama import ollama_embed 
from lightrag.llm.openai import openai_complete
from lightrag import LightRAG
from lightrag.utils import EmbeddingFunc

# --- CONFIGURAZIONE AMBIENTE ---
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://ollama:11434")
LLM_MODEL = os.environ.get("INGEST_LLM_MODEL", "gemini-2.5-flash-lite")
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "bge-m3")
LLM_CONTEXT_WINDOW = int(os.environ.get("LLM_CONTEXT_WINDOW", "8192"))
WORKSPACE = os.environ.get("LIGHTRAG_WORKSPACE", "/app/kb")
DOCS_DIR = os.environ.get("DOCS_DIR", "/docs")

# --- INIZIALIZZAZIONE LIGHTRAG ---
rag = LightRAG(
    working_dir=WORKSPACE,
    llm_model_func=openai_complete,
    llm_model_name=LLM_MODEL,
    embedding_func=EmbeddingFunc(
        embedding_dim=1024, 
        max_token_size=8192,
        func=lambda texts: ollama_embed(
            texts, 
            embed_model=EMBEDDING_MODEL, 
            host=OLLAMA_HOST
        )
    ),
    llm_model_kwargs={
        "api_key": os.environ.get("GEMINI_API_KEY"),
        "base_url": "https://generativelanguage.googleapis.com/v1beta/",
    }
)

@task(name="read_local_files")
async def read_local_files(directory: str) -> List[str]:
    """Reads all text/markdown/pdf files from the specified local directory."""
    documents = []
    if not os.path.exists(directory):
        print(f"Directory {directory} does not exist.")
        return documents

    for root, _, files in os.walk(directory):
        for file in files:
            filepath = os.path.join(root, file)
            try:
                if file.endswith((".txt", ".md", ".rst")):
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()
                        if content.strip():
                            documents.append(content)
                            print(f"Loaded {filepath} ({len(content)} chars)")
                elif file.lower().endswith(".pdf"):
                    from pypdf import PdfReader

                    reader = PdfReader(filepath)
                    content = "\n".join(
                        [page.extract_text() or "" for page in reader.pages]
                    )
                    if content.strip():
                        documents.append(content)
                        print(f"Loaded {filepath} ({len(content)} chars)")
            except Exception as e:
                print(f"Error reading {filepath}: {e}")
    return documents


@task(name="crawl_and_clean_url")
async def crawl_and_clean_url(url: str) -> str:
    """Fetches a URL and extracts clean text content using Firecrawl."""
    print(f"Crawling URL: {url}")
    try:
        api_key = os.environ.get("FIRECRAWL_API_KEY")
        if not api_key or api_key == "your_firecrawl_api_key_here":
            print(f"Warning: FIRECRAWL_API_KEY not set. Cannot crawl {url}.")
            return ""

        app = FirecrawlApp(api_key=api_key)

																						   
        def scrape():
            return app.scrape_url(url, params={"formats": ["markdown"]})

        result = await asyncio.to_thread(scrape)

																									   
        if isinstance(result, dict):
            if "markdown" in result:
                return result["markdown"]
				  
								
            elif "data" in result and isinstance(result["data"], dict) and "markdown" in result["data"]:
												
			  
                return result["data"]["markdown"]

        return str(result)
    except Exception as e:
        print(f"Error crawling {url} with Firecrawl: {e}")
        return ""


@workflow(name="ingestion_pipeline")
async def run_ingestion(docs_dir: str = DOCS_DIR, urls: List[str] = None):
    """Main workflow to ingest local files and URLs into LightRAG."""
    documents_to_insert = []

    # 1. Process local files
												  
    local_docs = await read_local_files(docs_dir)
    documents_to_insert.extend(local_docs)

    # 2. Process URLs
    if urls:
											 
								   
        crawl_tasks = [crawl_and_clean_url(url) for url in urls]
        web_docs = await asyncio.gather(*crawl_tasks)
								  
        web_docs = [doc for doc in web_docs if doc]
        documents_to_insert.extend(web_docs)

									  
    if not documents_to_insert:
        print("No documents found for ingestion.")
        return

		  
    print(f"Starting async insertion of {len(documents_to_insert)} documents...")
    
											
    try:
        # Inizializza gli storage prima dell'inserimento
        await rag.initialize_storages()
        # Inserimento nel database LightRAG
        await rag.ainsert(documents_to_insert)
        print("✅ Ingestion completed successfully.")
    except Exception as e:
        print(f"❌ Error during LightRAG insertion: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LightRAG Ingestor")
    parser.add_argument("--url", type=str, action="append", help="URL to crawl")
				
				 
						
																	
	 
    args = parser.parse_args()

    urls_to_crawl = args.url if args.url else []

							
    asyncio.run(run_ingestion(docs_dir=DOCS_DIR, urls=urls_to_crawl))
