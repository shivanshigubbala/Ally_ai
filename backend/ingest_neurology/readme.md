# Neurology Offline RAG Pipeline

## Overview

This module is responsible for preparing the Neurology knowledge base used by the AI assistant.

The purpose of the Offline Retrieval-Augmented Generation (RAG) pipeline is to convert unstructured Neurology PDF documents into searchable vector representations that can later be retrieved during user conversations.

At the end of this pipeline, every important section of every PDF is stored inside PostgreSQL as a vector embedding.

**Note**

This module **does not answer user questions**.

It only prepares the knowledge that will later be used by the Online RAG pipeline.

---

# What is Offline RAG?

Offline RAG is the preprocessing stage of a Retrieval-Augmented Generation system.

Instead of allowing the AI model to read complete PDF documents every time a user asks a question, the documents are processed once beforehand.

This significantly improves:

- Retrieval speed
- Scalability
- Response quality
- Token efficiency

---

# Pipeline Workflow

```
                Neurology PDF Documents
                         │
                         ▼
                PDF Text Extraction
                         │
                         ▼
                 Text Chunking
                         │
                         ▼
              Vector Embedding Generation
                         │
                         ▼
         PostgreSQL + pgvector Storage
```

---

# Project Structure

```
ingest_neurology/

│
├── documents/
│     ├── Epilepsy.pdf
│     ├── Stroke.pdf
│     ├── Migraine.pdf
│     ├── Parkinsons.pdf
│     ├── Dementia.pdf
│     └── ...
│
├── loader.py
├── chunker.py
├── embedder.py
├── ingest_neurology.py
│
└── README.md
```

---

# Step 1 — Document Loading

File:

```
loader.py
```

### Purpose

Loads every Neurology PDF from the `documents/` folder.

### Responsibilities

- Scan document folder
- Read every PDF
- Extract plain text
- Return extracted document contents

### Input

```
Stroke.pdf
```

### Output

```python
{
    "source": "Stroke.pdf",
    "text": "Stroke is a neurological disorder..."
}
```

No chunking or embeddings happen in this step.

---

# Step 2 — Text Chunking

File:

```
chunker.py
```

### Purpose

Large documents cannot be embedded efficiently.

The extracted text is therefore divided into smaller overlapping chunks.

Current configuration

```
Chunk Size     : 500
Chunk Overlap  : 50
```

Example

Original text

```
Stroke symptoms include:

Sudden weakness

Slurred speech

Vision loss

Immediate treatment improves survival.
```

Chunk 1

```
Stroke symptoms include:

Sudden weakness

Slurred speech
```

Chunk 2

```
Slurred speech

Vision loss

Immediate treatment improves survival.
```

The overlap preserves context between neighbouring chunks.

---

# Step 3 — Embedding Generation

File

```
embedder.py
```

### Purpose

Convert every text chunk into a numerical vector.

Embedding model

```
sentence-transformers/all-MiniLM-L6-v2
```

Embedding dimension

```
384
```

Example

Chunk

```
Stroke causes sudden weakness.
```

Embedding

```
[
0.184,
-0.731,
0.418,
...
384 floating-point values
]
```

These vectors capture the semantic meaning of the text.

Similar concepts produce similar vectors.

---

# Step 4 — PostgreSQL Storage

File

```
ingest_neurology.py
```

### Purpose

Coordinates the complete ingestion pipeline.

Workflow

```
Load Documents

↓

Chunk Text

↓

Generate Embeddings

↓

Insert into PostgreSQL
```

Each chunk becomes one database record.

---

# Database Storage

Temporary development table

```
knowledge_chunks_neurology_dev
```

Each row contains

| Column | Description |
|----------|-------------|
| id | Primary key |
| department | Neurology |
| source | PDF filename |
| page | Source page |
| content | Text chunk |
| embedding | 384-dimensional vector |
| created_at | Timestamp |

---

# Example Database Record

```
id

1

department

Neurology

source

Stroke.pdf

content

Stroke symptoms include sudden weakness...

embedding

[0.184, -0.731, 0.418, ...]

created_at

2026-07-01
```

---

# Documents Processed

The current Neurology knowledge base consists of:

- Epilepsy
- Headache Classification
- Migraine
- Vertigo
- Brain Tumor
- Dementia
- Multiple Sclerosis
- Neuropathy
- Parkinson's Disease
- Stroke

Total

```
10 PDF Documents
```

---

# Ingestion Results

Current output

```
Documents Processed : 10

Generated Chunks : 56

Embeddings Generated : 56

Database Records : 56
```

---

# Why Embeddings?

Computers cannot understand medical language directly.

Embedding models convert text into vectors.

Example

```
Stroke symptoms

↓

MiniLM

↓

[0.184, -0.731, ...]
```

Later, when a user asks

```
My left arm suddenly became weak.
```

the same embedding model converts the question into another vector.

Because both vectors exist in the same semantic space, PostgreSQL can retrieve the Stroke chunk even though the question never explicitly mentions the word "stroke".

---

# Offline RAG Summary

```
Neurology PDFs

↓

Extract Text

↓

Split into Chunks

↓

Generate MiniLM Embeddings

↓

Store in PostgreSQL
```

At this point, the knowledge base is fully prepared.

No Large Language Model (LLM) is involved during Offline RAG.

---

# What Offline RAG Does NOT Do

This module does not

- Answer user questions
- Perform similarity search
- Use Ollama
- Use Qwen or Llama
- Generate AI responses

These tasks belong to the Online RAG pipeline.

---

# Technologies Used

- Python 3.12
- Docker
- PostgreSQL
- pgvector
- PyMuPDF
- Sentence Transformers
- all-MiniLM-L6-v2
- LangChain Text Splitter
- psycopg2
- NumPy

---

# Next Phase

After completing Offline RAG, the project moves to the Online RAG pipeline.

Workflow

```
User Question

↓

Generate Question Embedding

↓

Retrieve Relevant Chunks

↓

Build Prompt

↓

Qwen (Ollama)

↓

Generate Final Answer
```

The Online RAG pipeline will use the vectors generated by this module to provide context-aware responses to user queries.