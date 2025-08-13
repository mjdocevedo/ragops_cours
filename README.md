# RAGOPS
Simple minimal RAG LLMOps architecture following best practices


Architecture RAG 100 % CPU — version simplifiée mais robuste

Ci-dessous la nouvelle topologie qui intègre les recommandations :

* un seul proxy LiteLLM (il gère à la fois Groq LLM et TEI-CPU pour les embeddings),
* un service TEI-CPU dédié mais allégé,
* une couche Redis pour le cache exact + embeddings,
* toujours Meilisearch pour l’index hybride,
* un backend unique pour la logique RAG,
* un job d’ingestion déclenché manuellement ou par cron,
* Nginx en frontal HTTPS.

## Lancement

RAGOPS - CPU-only RAG stack with Meilisearch, TEI, LiteLLM, Redis, FastAPI + LangChain

Run:
- Create .env with MEILI_KEY, GROQ_API_KEY, LITELLM_KEY
- docker compose up -d --build