# 1 Document Processing Architecture


---

## Pipeline Overview

The workflow monitors a Google Drive folder, extracts text from PDF/DOCX/TXT files, chunks the text, generates embeddings and stores them in a vector database. Correct chunking is crucial; good chunks increase retrieval accuracy and reduce hallucinations, while poor chunking injects irrelevant text or loses context.

---

## Chunking Strategies

### i.Select chunk size and overlap dynamically

Research shows that fixed-size chunks either lose specificity when too large or lose context when too small. Pinecone’s engineers note that “smaller, semantically coherent units” improve retrieval and reduce hallucinations. LlamaIndex experiments found that 128-token chunks give granular retrieval but may miss important context, whereas 512-token chunks capture more information at the cost of slower responses. A balanced default for English documents is **400–800 tokens with 10–20 % overlap**. Overlap ensures that information spanning boundaries is not lost.

### ii.Use hierarchical splitting and semantic chunkers

The 2025 PIC method uses document summaries as pseudo-instructions and groups sentences based on semantic similarity to preserve topic coherence. LangChain’s `RecursiveCharacterTextSplitter` employs similar semantics by recursively splitting on headings or paragraphs before falling back to characters; Chroma’s 2024 evaluation shows that this heuristic performs well when parameterized properly. For long reports and structured formats, first split on sections (e.g., headings, bullet lists) using regular expressions or the DOCX/PDF structure, then apply the recursive splitter.

### iii.Token-aware splitting

Tokenization varies by language. DataCamp notes that languages like Chinese or Japanese lack clear word boundaries and benefit from character or sub-word tokenization. LangChain recommends using `CharacterTextSplitter` with a `tiktoken`-based encoder to ensure chunks end on valid token boundaries and avoid splitting multi-byte characters; `TokenTextSplitter` can corrupt Unicode. Thus, choose a tokenizer appropriate for the document language (e.g., Jieba for Chinese) and pass the resulting text to the chunker.

### iv.Adaptive chunking and retrieval evaluation

Recent research introduces cluster-based chunkers and LLM-guided chunkers that adapt chunk sizes to semantic boundaries. These dynamic chunkers work well for heterogeneous document sets (contracts, slide decks, spreadsheets) because they adjust to topic shifts. Use retrieval-quality metrics (relevancy, faithfulness) to tune chunk size for your data.


### v.Handling multi-language documents

Detect the document language (`fastText` or `langdetect`). For Latin-script languages, word-level splitting is acceptable; for East-Asian scripts, prefer character or sub-word splitting to preserve words. Use multilingual embedding models (e.g., `sentence-transformers/LaBSE` or `XLM-R`) to generate embeddings across languages.

### vi.Multi-modal content

If documents contain images or tables, store references and optionally use an OCR pipeline or image embedding model (e.g., OpenAI’s vision models) to extract text. Generate separate embeddings for text and images and link them in metadata.


---
---

# 2 Production Monitoring & Observability

Building a reliable RAG system requires continuous monitoring across ingestion, vector storage, retrieval, and generation.

---

## Key Performance Indicators (KPIs)

* **Latency and Throughput**: Measure time to first token (TTFT) and total response latency, monitor throughput. Caching intermediate states can reduce TTFT by up to 4× and improve throughput by 2.1×.
    * Track latency at each stage: extraction, embedding, vector search, LLM inference.

* **Retrieval Quality Metrics**: Log recall/precision (how many ground-truth chunks appear in top-K results) and use faithfulness or hallucination detection metrics. It is recommended to monitor relevance, toxicity, and context adherence to detect injection attacks.

* **System Health**: Monitor success/failure rates for each pipeline step, embedding generation times, vector DB health, and concurrency to detect throughput bottlenecks.

---

## Observability Architecture

* **Instrumentation and Tracing**: Insert logging and tracing at every component. It is crucial to log user queries, retrieved documents, and generated responses so that the entire request path can be reconstructed. Use **OpenTelemetry** to collect spans and propagate trace IDs across n8n, the embedding service, vector DB, and LLM service. Correlate logs with metadata (document ID, chunk ID, model version).

* **Centralized Logging and Analytics**: Store structured logs (e.g., JSON) in a log aggregation system such as **ELK (Elasticsearch/Logstash/Kibana)** or **OpenSearch**. Index logs by trace ID and provide dashboards showing latency distribution, errors, and token usage.


* **Alerting**: Define thresholds for critical metrics (latency, error rate, cost). Use **Prometheus Alertmanager** or **PagerDuty** to send alerts when thresholds are exceeded (e.g., >95th percentile TTFT, sudden spike in hallucinations or cost). Alerts should include contextual information (trace IDs) for debugging.

* **Debugging Tools**: Provide a “query inspector” to view the retrieved chunks, system prompts, and final responses. Support side-by-side comparisons of different model outputs. Use embedding visualisation (**t-SNE, UMAP**) to spot clusters and anomalies; visualising high-dimensional embeddings is valuable for detecting outliers.

* **Continuous Evaluation & Human-in-the-Loop**: Implement pipelines that periodically sample outputs and ask domain experts to rate relevance, correctness, and bias. It is important to monitor feedback loops and adjust the system based on user feedback.

---

## Performance Optimization Framework

Incorporate automatic caching (e.g., query-based or semantic caching) to reduce retrieval load. Evaluate new chunking or embedding models in a staging environment. Automate A/B tests using your observability metrics to compare retrieval and generation strategies. Integrate cost-monitoring dashboards so that prompt length changes can be linked to cost variations.


---
---



# 3 LLM selection - competetive analysis

| Provider & Model (2025) | Context window | Multimodal | Approximate cost per 1M tokens† | Strengths / Notes |
|---|---|---|---|---|
| **OpenAI GPT‑5** | 128 K–1 M | Text only (vision via GPT‑4o) | Input: $1.25; Cached: $0.125; Output: $10 | High reasoning and coding ability; large context; good for general queries. |
| **OpenAI GPT‑4o** | 128 K | Text & image | Input: $2.50; Cached: $1.25; Output: $10 | Multimodal (images & vision); supports function calls; balanced reasoning. |
| **OpenAI o3** | 128 K | Text-only | Input: $10; Output: $40 | “Thinking” model that explains reasoning; slower and more expensive; ideal for scientific or complex reasoning. |
| **Anthropic Claude 3.7** | 200 K | Text & image | Input: ~$3; Cached: $0.30; Output: $15 | Excellent reasoning and factual accuracy; strong code performance; can be set to “Extended Thinking” mode. |
| **Google Gemini 2.5 Pro** | 1 M | Text, images, audio | Input: $1.25; Cached: $0.125; Output: $10 | Very large context window; strong for research and long documents; multi-modal (image/audio). |
| **xAI Grok 3** | 1 M | Text & image | Input: $3; Output: $15 | Emphasizes math and visual reasoning; high speed when run on Groq hardware; smaller ecosystem. |
| **DeepSeek V3** | 64–128 K | Text & images | Input: $0.28; Cached: $0.028; Output: $0.42 | Cost-effective; competitive performance; suitable for budget-conscious apps. |
| **Meta LLaMA 3.3** | 128 K | Text-only | Free for self‑hosting; hardware & ops cost | Good baseline for research; requires fine‑tuning; smaller benchmarks vs proprietary models. |
| **Mistral & Mixtral** | 32–65 K | Text-only | Free; hardware & ops cost | Good for on‑prem deployment; mixture‑of‑experts; tuneable; limited context. |



## LLM Selection: Considerations for the Document Management in consultation firm Use Case

---

### Context Window

Summarizing long documents (100+ pages) requires a large context window. Models such as Gemini 2.5 Pro (1 M tokens) or GPT-5 (up to 1 M tokens with caching) handle long sequences efficiently. However, injecting entire documents is expensive; therefore, proper chunking is still needed.

### Response Quality vs. Cost

* **High Accuracy**: GPT-4.1 offers very high accuracy with moderate cost ($2 input, $8 output per 1M tokens). Claude 3.7 matches or exceeds GPT-4 on coding tasks and costs $3 per input million tokens.
* **Cost-Effective**: DeepSeek V3 is more affordable ($0.28 input, $0.42 output) with good performance.
* **Self-Hosted**: For cost-sensitive summarization, open-source LLaMA 3.3 or DeepSeek might be used via self-hosting, but will require prompt-engineering and tuning.

### Reasoning vs. Non-Reasoning Models

Reasoning models (o1, o3, Claude Extended) perform explicit step-by-step reasoning but are slower and much more costly. Standard models (GPT-4o, GPT-4.1, standard Claude) are faster and cheaper but may not expose their reasoning chains. Use thinking models for critical decisions; use standard models for routine document summarization.

### Multimodal Capability

For documents with figures or images (charts, scanned text), choose multimodal models like GPT-4o or Gemini 2.5 Pro that accept images. If only text is needed, text-only models can reduce cost.

### Self-hosted vs. API

Proprietary models (OpenAI, Anthropic, Google) are accessed via API; they provide high performance but require sharing data with providers, which may raise compliance concerns. Open-source models (LLaMA 3, Mistral) allow full control and data privacy but require infrastructure (GPUs, Kubernetes), fine-tuning, and maintenance. A hybrid approach can be used: use open-source models for development and sensitive queries, and call proprietary APIs for high-quality summarization or multi-modal tasks, caching outputs to reduce costs.

---

## Recommendation

For the consulting firm’s RAG system, start with **GPT-4.1 or Claude 3.7** for high-quality summarization and question answering; both support 128–200 K contexts and strong reasoning. Use **DeepSeek V3 or open-source LLaMA 3** for lower-cost tasks or fallback when budgets are tight. Evaluate multi-modal models (**GPT-4o, Gemini 2.5 Pro**) if images or scanned documents are part of the workflow. Implement an abstraction layer (e.g., LangChain’s `LLMChain`) to allow swapping models based on cost/performance requirements.

---
---
# 4  Security and Privacy Architecture

---

## Data Masking

* **Pre-ingestion Redaction**: Use **Named-Entity Recognition (NER)** to detect PII (names, addresses, phone numbers, account numbers) and mask or remove it before embedding. Data minimization is critical because storing unnecessary data violates privacy laws.
* **Tokenization and Pseudonymization**: Replace sensitive identifiers with random tokens; maintain a secure mapping table outside the vector DB. This allows retrieval without exposing raw PII.
* **Differential Privacy & Federated Learning**: Add noise to aggregated data to prevent re-identification; train models without transferring raw data.

---

## Encryption and Secure Storage

* **Encryption at Rest and in Transit**: Apply **AES-256 encryption** for stored embeddings and metadata; use **TLS/HTTPS** and, where applicable, end-to-end encryption for client communications.
* **Application-layer Encryption and Homomorphic Encryption**: Encrypt sensitive fields before passing them to the vector DB or LLM; homomorphic encryption enables operations on encrypted vectors (though currently expensive).
* **Separate Security Zones**: Store encryption keys in a **Hardware Security Module (HSM)** or a managed key service (e.g., AWS KMS); isolate the vector DB and LLM inference on private subnets.

---

## Access Control and Zero-Trust

* **Role-Based Access Control (RBAC) / Attribute-Based Access Control (ABAC)**: Assign privileges based on user roles (e.g., consultant, admin) and attributes. Only authorized users can read or write specific vectors.
* **Zero-Trust Architecture**: Verify every request; require re-authentication when crossing system boundaries. Divide the pipeline into micro-segments (ingestion, embedding, retrieval, generation) with separate credentials.
* **Multi-Factor Authentication (MFA)**: Protect critical components like retriever and generator systems.

---

## Guardrails, Validation, and Prompt Security

* **Prompt Injection Defenses**: Validate and sanitize user queries; block malicious instructions. Injection attacks can cause unauthorized actions or data leaks.
* **Salted Tags & Guardrails**: Use random tags (e.g., `<secure-12345>`) in prompt templates and enforce strict grammar; this makes it hard for attackers to guess the tags and insert hidden commands.
* **Output Filtering & Sanitization**: Apply NLP filters to detect and redact sensitive data before returning responses. This may involve regex or classification models to remove PII.

---

## Logging and Auditing

* **Audit Logs**: Record who accessed which documents, queries, retrieval results, and model responses. Monitor for unusual access patterns and maintain retention to meet compliance.
* **Compliance Frameworks**: Align with **GDPR** and **HIPAA**. Data minimization and anonymization reduce regulatory risk. Use audit trails to satisfy requests for deletion or inspection.
* **Incident Response Plan**: Define procedures for breach detection and notification. Continuous monitoring and intrusion detection systems should scan for anomalies.


---
---

# 5 Scalability Architecture

**Objective**: Handle millions of documents with low latency and high availability.

---

## Distributed Vector Search

### Sharding

Distribute the vector database across multiple machines (shards) based on a key range or hash. Sharding divides a dataset into smaller units to achieve scalability, load balancing, and fault tolerance.

* **Range-based sharding** partitions vectors into non-overlapping intervals (e.g., ID ranges). It provides efficient range queries but can suffer from data skew if keys are uneven.
* **Hash-based sharding** uses a hash of a key to assign vectors to shards. To avoid re-distributing the entire dataset when scaling, modern systems use **consistent hashing**, which remaps only a small fraction of data when nodes change.

### Partitioning Within Shards

Once data is on a node, partition it into logical subsets to improve query efficiency. Methods include range, list, k-means, and hash partitioning within a single machine. For example, k-means partitioning clusters similar vectors together, improving locality at the cost of re-clustering overhead.

### Replication

Maintain multiple copies of data for high availability. Leader-follower replication ensures strong consistency but can be a bottleneck; multi-leader or leaderless replication improves availability but requires conflict resolution.

---

## Caching Strategies

* **Query-based Caching**: Store exact retrieval results for common queries. This works for frequently repeated questions but not for paraphrases.
* **Semantic Caching**: Cache embeddings of previous queries and reuse results when new queries are semantically similar. This requires computing similarity between new and cached queries using a threshold.
* **Hybrid Caching**: Combine query and semantic caching; fall back to the semantic cache when an exact match is absent.
* **RAGCache**: For LLM inference, caching the intermediate key-value tensors of retrieved documents (knowledge tree) in GPU and host memory reduces time to first token by up to 4× and improves throughput by 2.1×. This approach caches frequently accessed documents’ hidden states and overlaps retrieval with inference.
* **Cache Eviction Policies**: Use LRU, LFU, or custom policies. Trade-offs exist: LRU suits temporal locality, while LFU suits long-lived popularity. Partitioned caches allocate separate caches per region or data category.
* **Cache Invalidation**: When documents are updated, invalidate or refresh cached embeddings to avoid stale context.

---

## Load Balancing and System Architecture

* **Modular Microservices**: Separate ingestion, embedding generation, vector search, and LLM inference into independent services. Use message queues (e.g., Kafka) for backpressure. Distributed RAG systems should be modular so each component can scale independently.
* **Data Locality & Intelligent Routing**: Keep frequently accessed data close to compute nodes to minimize cross-node calls. Use query routing to direct queries to the most relevant shard or pipeline; dynamic query construction improves accuracy and reduces latency.
* **Hybrid Retrieval and Indexing**: Combine dense vector search with keyword (BM25) search. Hybrid search addresses noisy datasets by balancing relevance and speed. Use dynamic switching between dense and sparse retrieval based on query complexity.
* **Load Balancing & Autoscaling**: Deploy vector DB shards and LLM inference servers behind load balancers. Scale horizontally using Kubernetes. Monitor query load and automatically add replicas when throughput increases.
* **Database and File Storage**: Store raw documents in scalable object storage (e.g., Google Cloud Storage) with versioning. Use distributed file systems for intermediate artifacts. Implement change-data-capture pipelines to update embeddings when documents change.

---

## Sharding/Partitioning Strategy Selection

Choose the sharding key based on query patterns. For time-series data or sequential IDs, range sharding is efficient; for unpredictable keys, consistent hash sharding is more balanced. Use geo-sharding for global deployments to comply with regional regulations. Combine sharding with partitioning within shards (range/list/hash or k-means) to optimise local queries.
