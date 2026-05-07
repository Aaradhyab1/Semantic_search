# AI-Powered RAG & Semantic Search Engine

An end-to-end Retrieval-Augmented Generation (RAG) platform that transforms static study notes and PDFs into an interactive, queryable knowledge base. Built with a high-performance **FastAPI** backend and a responsive **React** frontend, this system leverages **FAISS** for rapid vector similarity search and **Google Gemini 1.5 Flash** for highly accurate, cited AI summarization.

##  Key Features

* **Intelligent Semantic Search:** Context-aware querying that goes beyond keyword matching using dense vector embeddings.
* **Automated Knowledge Extraction:** Upload documents to have them automatically parsed, cleaned, chunked, and embedded into a local FAISS index.
* **AI-Synthesized Answers:** Generates clean, pointer-based summaries with exact source citations to prevent AI hallucinations.
* **Secure Authentication:** Fully isolated user environments protected by secure JWT (JSON Web Token) authentication and hashed passwords.
* **Modern UI/UX:** Responsive React dashboard with drag-and-drop file uploads, dark/light mode toggles, and seamless clipboard integration.

**Backend Engine**
* **Framework:** Python / FastAPI
* **Vector Database:** FAISS (Facebook AI Similarity Search)
