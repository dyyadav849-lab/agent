# Comprehensive Technical Documentation: TI-Bot Baseline Pipeline Services

## Executive Summary

This document provides a complete technical analysis of the TI-Bot Baseline Pipeline consisting of two primary microservices:
1. **hades-kb-service**: Knowledge Base service for document and Slack RAG (Retrieval-Augmented Generation)
2. **Zion**: LLM Agents service with multi-agent orchestration capabilities

Both services implement traditional AI/ML pipelines with basic vector storage, simple chunking, and standard monitoring.

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                TI-Bot Baseline Pipeline Architecture            │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐         ┌─────────────────────────────────┐ │
│  │                 │         │                                 │ │
│  │  Zion Service   │◄────────┤  hades-kb-service              │ │
│  │  (Port 8000)    │         │  (Port 8088)                   │ │
│  │                 │         │                                 │ │
│  │ ┌─────────────┐ │         │ ┌─────────────┐                 │ │
│  │ │Basic Agent  │ │         │ │Basic RAG    │                 │ │
│  │ │System       │ │         │ │Processor    │                 │ │
│  │ └─────────────┘ │         │ └─────────────┘                 │ │
│  │ ┌─────────────┐ │         │ ┌─────────────┐                 │ │
│  │ │Simple Tool  │ │         │ │Simple Slack │                 │ │
│  │ │Handlers     │ │         │ │Processor    │                 │ │
│  │ └─────────────┘ │         │ └─────────────┘                 │ │
│  │ ┌─────────────┐ │         │ ┌─────────────┐                 │ │
│  │ │Standard     │ │         │ │Vector Store │                 │ │
│  │ │Workflows    │ │         │ │(pgvector)   │                 │ │
│  │ └─────────────┘ │         │ └─────────────┘                 │ │
│  └─────────────────┘         └─────────────────────────────────┘ │
│           │                              │                       │
│           │                              │                       │
│  ┌─────────────────┐         ┌─────────────────────────────────┐ │
│  │                 │         │                                 │ │
│  │ External APIs   │         │ Databases & Storage             │ │
│  │                 │         │                                 │ │
│  │ • OpenAI        │         │ • PostgreSQL + pgvector        │ │
│  │ • Confluence    │         │ • MySQL                         │ │
│  │ • Jira          │         │ • Basic Storage                 │ │
│  │ • GitLab        │         │                                 │ │
│  └─────────────────┘         └─────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📊 Service 1: hades-kb-service (Knowledge Base)

### Directory Structure
```
hades-kb-service/
├── app/                              # Main application code
│   ├── auth/                         # Authentication & authorization
│   │   ├── bearer.py                 # Bearer token handling
│   │   ├── modes.py                  # Auth modes (proxy, session)
│   │   ├── oidc.py                   # OpenID Connect integration
│   │   └── sessions/                 # Session management
│   ├── core/                         # Core business logic
│   │   ├── azure_em/                 # Azure Embedding Models
│   │   ├── config.py                 # Configuration management
│   │   ├── dependencies.py           # Dependency injection
│   │   ├── log/                      # Logging infrastructure
│   │   ├── ragdocument/              # RAG Document processing
│   │   │   └── client.py            # Main RAG client implementation
│   │   ├── ragslack/                 # RAG Slack processing
│   │   ├── s3/                       # S3 storage integration
│   │   └── transformer/              # Text processing & chunking
│   │       ├── client.py            # Text transformation client
│   │       └── text_splitter/       # Chunking strategies
│   │           ├── client.py        # Text splitting implementation
│   │           └── models.py        # Splitter configuration
│   ├── models/                       # Data models
│   │   ├── azure_openai_model.py    # Azure OpenAI model definitions
│   │   └── utils.py                 # Model utilities
│   ├── routes/                       # API route handlers
│   │   ├── api.py                   # Main API router
│   │   ├── doc_kb_route/            # Document KB endpoints
│   │   ├── health_check.py          # Health check endpoint
│   │   ├── oidc.py                  # OIDC authentication routes
│   │   ├── s3_route/                # S3 storage routes
│   │   └── slack_kb_route/          # Slack KB endpoints
│   ├── server.py                    # FastAPI application setup
│   ├── storage/                     # Database & storage layer
│   │   ├── connection.py            # Database connection management
│   │   ├── ragdocument_db/          # Document storage
│   │   │   ├── client.py           # Database client
│   │   │   ├── models.py           # SQLAlchemy models
│   │   │   └── constant.py         # Database constants
│   │   └── ragslack_db/             # Slack storage
│   ├── tools/                       # LLM tools and utilities
│   ├── tracing/                     # OpenTelemetry tracing
│   │   └── tracer.py               # Trace configuration
│   └── utils/                       # Utility functions
├── configs/                         # Configuration files
│   ├── dev.ini                     # Development config
│   ├── prd.ini                     # Production config
│   ├── stg.ini                     # Staging config
│   └── secret.ini.example          # Secret configuration template
├── databases/                       # Database migrations
├── scripts/                         # Utility scripts
└── tests/                          # Test suites
```

### 🔧 RAG Implementation Details

#### 1. **Chunking Strategies** (`app/core/transformer/`)

**File**: `app/core/transformer/text_splitter/client.py`

```python
class TextSplitterClient:
    def split_text(self, text: str, chunk_size: int, chunk_overlap: int = 0, splitter_selector: int = 0):
        """
        Available Chunking Strategies:
        - DEFAULT (0): CharacterTextSplitter with tiktoken encoding
        - RECURSIVE (1): RecursiveCharacterTextSplitter with tiktoken encoding
        """
```

**Chunking Configuration**:
- **Default Chunk Size**: 512 tokens
- **Default Overlap**: 200 tokens
- **Encoding**: `cl100k_base` (GPT-4 tokenizer)
- **Strategy**: Basic character-based splitting

#### 2. **Vector Storage** (`app/storage/ragdocument_db/`)

**Database Schema** (`models.py`):
```python
class DocumentEmbedding(Base):
    __tablename__ = "document_embedding"
    id = Column(BigInteger, primary_key=True)
    token_number = Column(BigInteger, nullable=False)
    embedding = Column(Vector(1536), nullable=False)  # OpenAI ada-002 dimensions
    document_information_id = Column(BigInteger, ForeignKey("document_information.id"))
    text_snipplet = Column(Text, nullable=False)
    status = Column(Text, nullable=False, default=ACTIVE_STATUS)
```

**Vector Search Implementation** (`client.py`):
```python
def read_document_embedding_data(self, embeded_query: List[float], document_collection_uuids: List[str], 
                                embedding_operator: str = "<#>", vector_threshold: float = 0.7):
    """
    Vector similarity search using pgvector
    Standard operators: <#> (negative inner product), <-> (L2 distance), <=> (cosine distance)
    """
```

#### 3. **Embedding Models** (`app/core/azure_em/`)

**Default Model**: `text-embedding-ada-002`
**Supported Models**: Azure OpenAI embedding models
**Timeout**: 300 seconds (configurable)

#### 4. **Document Processing Pipeline**

**Flow**:
1. **Document Ingestion** → **Basic Text Extraction** → **Simple Preprocessing** → **Basic Chunking** → **Embedding** → **Vector Storage**

**Text Preprocessing** (`ragdocument/client.py`):
```python
def text_pre_processing(self, text: str, chunk_size: int = 512, chunk_overlap: int = 200, splitter_selector: int = 1):
    text = text.lower()  # Convert to lowercase
    # Basic chunk validation
    # Standard chunking via transformer client
```

---

## 🤖 Service 2: Zion (LLM Agents Service)

### Directory Structure
```
zion/
├── zion/                            # Main application code
│   ├── agent/                       # Agent implementations
│   │   ├── agent_builder.py         # Agent construction logic
│   │   ├── model.py                 # LLM model abstractions
│   │   ├── multi_agent/             # Multi-agent workflows
│   │   │   ├── multi_agent_workflow.py  # Basic workflows
│   │   │   ├── able_to_answer_agent.py  # Answer validation agent
│   │   │   ├── internal_search_agent.py # Internal search agent
│   │   │   ├── query_categorizer_agent.py # Query classification
│   │   │   └── ti_bot_agent.py      # Main TI-Bot agent
│   │   ├── single_agent/            # Single agent workflows
│   │   ├── react_agent_builder.py   # ReAct agent implementation
│   │   └── zion_agent.py           # Main agent orchestrator
│   ├── config.py                    # Configuration management
│   ├── credentials/                 # Authentication credentials
│   ├── data/                        # Data models and schemas
│   ├── evaluations/                 # Basic evaluation framework
│   ├── jobs/                        # Background job processing
│   ├── main.py                      # FastAPI application
│   ├── stats/                       # Metrics and monitoring
│   │   └── datadog.py              # Datadog integration
│   ├── tool/                        # Agent tools and capabilities
│   │   ├── hades_kb_service.py     # Integration with hades-kb-service
│   │   ├── glean_search.py         # Enterprise search
│   │   ├── gitlab_job_trace_tool.py # GitLab integration
│   │   ├── jira_jql_search_tool.py # Jira integration
│   │   ├── kibana_search_tool.py   # Log search
│   │   └── [40+ other tools]       # Standard tool ecosystem
│   ├── tracing/                     # OpenTelemetry tracing
│   └── util/                        # Utility functions
├── configs/                         # Configuration files
├── docs/                           # Documentation
├── playground/                      # Development playground
└── tests/                          # Test suites
```

### 🧠 Agent Architecture

#### **Agent Types Supported**:
1. **`react_agent`**: Basic ReAct (Reasoning + Acting) pattern
2. **`multi_agent`**: Simple multi-agent workflows
3. **`agent_executor`**: Standard LangChain agent executor

#### **Multi-Agent Workflow** (`multi_agent/multi_agent_workflow.py`):

```python
def get_ti_bot_multi_agent_system(tools, model, prompts, descriptions):
    workflow = StateGraph(AgentState)
    
    # Basic Agent Flow
    workflow.add_node("query_categorizer_agent", create_query_categorizer_agent_node(...))
    workflow.add_node("ti_bot_agent", create_ti_bot_agent_node(...))
    workflow.add_node("internal_search_agent", create_internal_search_agent_node(...))
    workflow.add_node("able_to_answer_agent", create_able_to_answer_agent_node(...))
```

**Basic Workflow Flow**:
```
Query → Simple Categorizer → TI-Bot Agent → Basic Search → Answer Validation → Response
```

### 🛠️ Tool Ecosystem (40+ Tools)

#### **Knowledge & Search Tools**:
- **`HadesKnowledgeBaseTool`**: Integration with hades-kb-service
- **`GleanSearchTool`**: Enterprise search
- **`KibanaSearchTool`**: Log and metrics search
- **`JiraJQLSearchTool`**: Issue tracking search

#### **Development Tools**:
- **`GitlabJobTraceTool`**: CI/CD pipeline investigation
- **`GitlabRepositoryAccessCheckerTool`**: Repository access verification
- **`SourcegraphTool`**: Code search

#### **Infrastructure Tools**:
- **`EC2LogRetrieverTool`**: AWS infrastructure logs
- **`GetServiceDependenciesTool`**: Service dependency mapping
- **`GetServicePlatformTool`**: Platform information

#### **Utility Tools**:
- **`CalculatorTool`**: Mathematical computations
- **`OpenAPITool`**: API documentation access
- **`UniversalSearchTool`**: Multi-source search

---

## 📊 Metrics & Monitoring

### **1. OpenTelemetry Tracing** (Both Services)

**Configuration** (`tracing/tracer.py`):
```python
otel_resource = Resource.create(attributes={
    SERVICE_NAME: "hades-kb-service" / "zion",
    SERVICE_VERSION: "1.0.0",
    KUBERNETES_NAMESPACE_NAME: os.environ.get(ENV_POD_NAMESPACE),
    KUBERNETES_POD_NAME: os.environ.get(ENV_POD_NAME),
    CONTAINER_IMAGE_NAME: container_image_name,
    CONTAINER_IMAGE_TAG: container_image_tag,
})
```

**Traced Components**:
- HTTP requests/responses
- Database queries
- LLM model calls
- Basic agent workflows
- Tool executions

### **2. Datadog Metrics** (Zion)

**Metric Categories** (`stats/datadog.py`):
```python
class DatadogClient:
    METRIC_SLACK = "slack"
    METRIC_AGENT = "agent" 
    METRIC_EXTERNAL = "external"
    EVENT_EVALUATION = "evaluation"
```

**Tracked Metrics**:
- Agent invocation counts
- Tool execution durations
- Model response times
- Error rates
- Basic evaluation scores

### **3. LangSmith Integration** (Both Services)

**Configuration**:
- **Endpoint**: `https://langsmith.stg.cauldron.myteksi.net/api`
- **Projects**: Per-agent project tracking
- **Traces**: Basic LLM conversation traces
- **Evaluations**: Standard testing datasets

---

## 🔧 How to Run Both Services Together

### **Prerequisites**:
```bash
# Required software
- Python 3.11+
- Poetry
- PostgreSQL with pgvector
- MySQL

# Services
- Docker (for databases)
- Git
```

### **Service Pipeline Setup Guide**:

#### **Step 1: Environment Setup**
```bash
# Navigate to baseline services
cd /Users/deepak.yadav/dp_grab/getlabtest/ti-bot_deep/baseline

# Setup both services
cd hades-kb-service && poetry install && cd ..
cd zion && poetry install && cd ..
```

#### **Step 2: Database Setup**
```bash
# PostgreSQL with pgvector (for hades-kb-service)
brew install postgresql pgvector
brew services start postgresql

# MySQL (for Zion)
brew install mysql
brew services start mysql

# Create databases
createdb hades_kb_service
mysql -u root -e "CREATE DATABASE zion;"
```

#### **Step 3: Configuration**
```bash
# hades-kb-service secrets
cd hades-kb-service
cp configs/secret.ini.example configs/secret.ini
# Edit configs/secret.ini with your secrets

# Zion secrets  
cd ../zion
cp configs/secret.ini.example configs/secret.ini
# Edit configs/secret.ini with your secrets
```

#### **Step 4: Database Migrations**
```bash
# hades-kb-service migrations
cd hades-kb-service
./scripts/db.sh --create
./scripts/db.sh --up

# Zion migrations
cd ../zion  
./scripts/db.sh --create
./scripts/db.sh --up
```

#### **Step 5: Start Services**

**Terminal 1 - hades-kb-service**:
```bash
cd baseline/hades-kb-service
poetry run python -m uvicorn app.server:app --reload --port 8088
```

**Terminal 2 - Zion**:
```bash
cd baseline/zion
poetry run python -m uvicorn zion.main:app --reload --port 8000
```

#### **Step 6: Verify Services**

**hades-kb-service**:
- Health Check: http://localhost:8088/health_check
- API Docs: http://localhost:8088/docs
- ReDoc: http://localhost:8088/redoc

**Zion**:
- Health Check: http://localhost:8000/
- API Docs: http://localhost:8000/docs
- Agent Playground: http://localhost:8000/agent/{agent_name}/playground/

### **Integration Points**:

1. **Zion → hades-kb-service**: 
   - Tool: `HadesKnowledgeBaseTool`
   - Endpoint: `/agent-plugin/{agent_name}`
   - Purpose: Basic knowledge base search for agent responses

2. **Shared Components**:
   - LangSmith tracing
   - OpenTelemetry monitoring
   - Standard authentication patterns

---

## 🎯 Baseline System Characteristics

### **hades-kb-service**:

**Core Features**:
- Standard RAG pipeline
- Basic vector storage with pgvector
- Simple chunking strategies
- Standard API documentation
- Basic separation of concerns

**Limitations**:
- Basic text preprocessing
- Fixed embedding dimensions
- Limited chunking strategies
- Minimal error handling

### **Zion**:

**Core Features**:
- Standard agent architecture
- Basic tool ecosystem (40+ tools)
- Simple workflow orchestration
- Standard monitoring and evaluation
- Basic agent configuration

**Limitations**:
- Simple workflow patterns
- Basic configuration management
- Standard error handling
- Limited context awareness

---

## 📈 Baseline Metrics

### **Performance Metrics**:
1. **Response Times**: Basic agent invocation latencies
2. **Throughput**: Standard requests per second
3. **Error Rates**: Failed requests percentage
4. **Token Usage**: LLM token consumption

### **Quality Metrics**:
1. **Relevance Scores**: Basic RAG retrieval accuracy
2. **Answer Confidence**: Standard agent response confidence
3. **User Satisfaction**: Basic feedback scores
4. **Tool Success Rates**: Standard tool performance

### **Operational Metrics**:
1. **Database Performance**: Standard query execution times
2. **Vector Search**: Basic similarity search latencies
3. **Memory Usage**: Standard service resource consumption
4. **Cache Hit Rates**: Basic cache effectiveness

---

## 🚀 Current Status Summary

**Both baseline services are functional:**

- ✅ **hades-kb-service**: Operational on port 8088
- ✅ **Zion**: Functional on port 8000
- ✅ **Integration**: Basic HTTP API communication
- ✅ **Monitoring**: Standard OpenTelemetry and Datadog integration
- ✅ **Documentation**: Basic API documentation available

The baseline pipeline represents a standard AI/ML system with traditional capabilities for knowledge base processing and basic agent orchestration.
