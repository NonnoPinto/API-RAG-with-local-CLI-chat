# OpenLLMetry LightRAG con Ollama (CLI Version)

Questo progetto è un'architettura basata su **LightRAG (Graph-RAG)**, alimentata localmente tramite **Ollama** e interamente monitorata (osservabilità) utilizzando **Traceloop SDK (OpenLLMetry)**.

Il sistema è stato semplificato per offrire un'esperienza **puramente da linea di comando (CLI)**, eliminando le complessità dei server web e offrendo un'interazione diretta e veloce con i tuoi documenti tramite terminale.

## Architettura

Il progetto utilizza `docker compose` per orchestrare i servizi:

1.  **ollama**: Il motore LLM locale. Si occupa di servire i modelli di embedding e generazione in background.
2.  **ollama-init**: Un container temporaneo che scarica automaticamente i modelli necessari al primo avvio.
3.  **ingest-local-firecrawl**: Un container di utilità che carica i dati locali (dalla cartella `./docs`) o le URL fornite (via Firecrawl), popola il Knowledge Graph di LightRAG (`./kb`), e poi termina.
4.  **chat**: L'interfaccia interattiva a riga di comando che ti permette di porre domande al tuo Knowledge Graph.

## Funzionalità Principali

-   **Grafi della Conoscenza (Graph-RAG)**: Costruisce relazioni e nodi usando [LightRAG](https://github.com/HKUDS/LightRAG). Il progetto fa uso della modalità "hybrid" per combinare la ricerca vettoriale a quella topologica.
-   **Motore 100% Locale e Leggero**: Utilizza Ollama ottimizzato per hardware consumer (LLM: `llama3.2:3b`, Embedding: `bge-m3` con contesto a 8KB). Nessun dato sensibile viene inviato ai provider LLM cloud.
-   **Osservabilità OpenLLMetry**: Traceloop intercetta automaticamente tutte le invocazioni dei modelli e i task di indicizzazione.
-   **Web Crawling**: Integrazione con Firecrawl per scaricare pagine web complesse, ripulire l'HTML, e salvare i dati nel database come Markdown.
-   **Interfaccia Terminale (CLI)**: Nessun endpoint API, solo una chat pulita e reattiva direttamente nel tuo terminale.

## Prerequisiti

-   [Docker Desktop](https://www.docker.com/products/docker-desktop/) (o Docker Engine + Docker Compose)
-   Una chiave API di Traceloop (Gratuita su [app.traceloop.com](https://app.traceloop.com))
-   Una chiave API di Firecrawl (Gratuita su [firecrawl.dev](https://www.firecrawl.dev)) per lo scraping web.

## Configurazione Iniziale

1.  **Clona il repository**:
    ```bash
    git clone https://github.com/tuo-utente/otel-rag-traceloop.git
    cd otel-rag-traceloop
    ```

2.  **Imposta le Variabili d'Ambiente**:
    Copia il file di esempio e inserisci le tue chiavi API:
    ```bash
    cp .env.example .env
    ```
    Apri il file `.env` appena creato e compila i campi obbligatori (`TRACELOOP_API_KEY` e `FIRECRAWL_API_KEY`).

## Utilizzo

### 1. Avvia il Motore e Scarica i Modelli
Avvia Ollama in background. Il container `ollama-init` scaricherà automaticamente `llama3.2:3b` e `bge-m3`.
```bash
docker compose up -d ollama ollama-init
```
*(Attendi qualche minuto al primo avvio affinché i modelli vengano scaricati. Puoi controllare lo stato con `docker logs ollama_init`)*.

### 2. Inserimento Dati (Ingestion)

Prima di poter chattare, devi fornire a LightRAG delle informazioni. Puoi popolare il tuo Knowledge Graph (`./kb`) in due modi.

**Da file Locali:**
Posiziona i tuoi file Markdown (`.md`) o di Testo (`.txt`) nella cartella `./docs`. Quindi avvia l'ingestor:
```bash
docker compose run --build --rm ingest-local-firecrawl python ingest_local_and_firecrawl.py
```

**Da Indirizzi Web (usando Firecrawl):**
```bash
docker compose run --build --rm ingest-local-firecrawl python ingest_local_and_firecrawl.py --url "https://esempio.com/documentazione/intro"
```

### 3. Entra nella Chat (CLI)
Una volta che l'ingestion ha creato il database nella cartella `./kb`, puoi avviare l'interfaccia interattiva nel terminale:

```bash
docker compose run --build --rm chat
```

Si aprirà un prompt `[Tu]:` dove potrai fare domande basate sui documenti inseriti. Digita `exit` per uscire.

## Monitoraggio e Osservabilità (Traceloop)

Il progetto integra **OpenLLMetry** per garantire la visibilità completa sulle operazioni del RAG. Il tracciamento è attivo in entrambe le fasi critiche del sistema:

1.  **Fase di Ingestion (`ingest-local-firecrawl`)**: Monitora il processo di caricamento dei documenti, lo splitting in chunk e l'estrazione iniziale delle entità nel Knowledge Graph.
2.  **Fase di Chat (`chat`)**: Registra l'intero workflow della domanda, dall'estrazione delle keyword alla generazione della risposta finale.

### Stato dell'integrazione
> [!IMPORTANT]
> **Supporto Parziale**: A causa dell'utilizzo di *wrapper custom* necessari per la compatibilità tra LightRAG e l'API locale di Ollama, il monitoraggio è attualmente **parziale**. 
> - **Cosa vedrai**: La struttura degli "Span", la sequenza temporale (workflow), le eccezioni e i metadati delle chiamate.
> - **Limitazioni**: Alcune metriche automatiche, come il conteggio esatto dei token per i modelli locali, potrebbero non essere intercettate nativamente dall'SDK se non esplicitamente passate nel wrapper.
