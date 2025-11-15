# AI Orchestration Backend

Multi-agent orchestration system with **LangGraph**, **SSE streaming**, and **context-aware memory management**.

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-009688.svg)](https://fastapi.tiangolo.com)
[![MongoDB](https://img.shields.io/badge/MongoDB-7.0-47A248.svg)](https://www.mongodb.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.0.28-FF6B6B.svg)](https://github.com/langchain-ai/langgraph)

---

## **Overview**

This backend implements a **4-agent pipeline** for intelligent conversation orchestration:

1. **Planner** → Expands user prompts into 1-3 subtasks with data access planning
2. **Worker** → Executes subtasks with database tool invocation
3. **Critic** → Validates output and triggers retry if needed (max 1 retry)
4. **Synthesizer** → Generates final response with 3 contextual suggestions

### **Key Features**

**Context-Aware Memory**: Short-term (last K turns) + long-term summary compression  
**Streaming SSE**: Real-time token streaming with observability events  
**DB Tool Calling**: Automatic MongoDB queries with metrics logging  
**Multi-User Sessions**: Isolated conversations with persistent state  
**Performance Metrics**: TTFT, total time, tool call latency tracking  

---

## **Architecture**
```
┌─────────────────────────────────────────────────────────────────┐
│                     FastAPI Application                          │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  POST /v1/chat/stream (SSE Streaming Endpoint)         │    │
│  └─────────────────────┬──────────────────────────────────┘    │
│                        │                                         │
│                        ▼                                         │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │           LangGraph Agent Pipeline                       │  │
│  │                                                           │  │
│  │  ┌──────────┐   ┌──────────┐   ┌──────────┐            │  │
│  │  │ Planner  │──►│  Worker  │──►│  Critic  │            │  │
│  │  └────┬─────┘   └─────┬────┘   └─────┬────┘            │  │
│  │       │               │              │                   │  │
│  │  Subtasks +      DB Tools       Validate                │  │
│  │  Data Plan      (db.find)        Pass?                  │  │
│  │       │               │              │                   │  │
│  │       │               │         No (retry < 1)           │  │
│  │       │               │              │                   │  │
│  │       │               └──────────────┘                   │  │
│  │       │                    │                             │  │
│  │       │              Yes or retry=1                      │  │
│  │       │                    │                             │  │
│  │       ▼                    ▼                             │  │
│  │  ┌────────────────────────────┐                         │  │
│  │  │      Synthesizer           │                         │  │
│  │  │  - Final answer            │                         │  │
│  │  │  - 3 suggestions           │                         │  │
│  │  └────────────────────────────┘                         │  │
│  └──────────────────────────────────────────────────────────┘  │
│                        │              │                         │
│                        ▼              ▼                         │
│  ┌──────────────┐   ┌────────────────────┐                    │
│  │   DB Tools   │   │   Memory Manager   │                    │
│  │  (MongoDB)   │   │  Context Packing   │                    │
│  │  - db.find   │   │  - Short-term (K)  │                    │
│  │  - db.insert │   │  - Long-term sum   │                    │
│  │  - db.aggr   │   │  - Token budget    │                    │
│  └──────────────┘   └────────────────────┘                    │
└─────────────────────────────────────────────────────────────────┘
                        │              │
                        ▼              ▼
                ┌────────────────────────────┐
                │        MongoDB             │
                │  Collections:              │
                │  - messages                │
                │  - sessions (+ summary)    │
                │  - tool_calls              │
                │  - suggestions             │
                │  - metrics (TTFT, total)   │
                └────────────────────────────┘

Flow:
  User Request → Planner (context-aware) → Worker (DB tools) 
  → Critic (validate/retry) → Synthesizer (answer + suggestions) 
  → SSE Stream → Client
```

---

## **Quick Start**

### **Prerequisites**

- Python 3.11+
- Docker & Docker Compose
- OpenAI API Key (or use mock LLM)

### **1. Clone & Setup**
```bash
# Clone repository
git clone <repository-url>
cd ai-orchestration-backend

# Copy environment template
cp .env.example .env

# Edit .env with your OpenAI API key
# LLM_PROVIDER=openai
# OPENAI_API_KEY=sk-proj-YOUR_KEY_HERE
```

### **2. Run with Docker (Recommended)**
```bash
# Build Docker images
docker-compose build

# Build and start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f backend
```
API will be available at: **http://localhost:8000**
And also check in : **http://localhost:8000/docs**

**Services Started:**
- **Backend API**: http://localhost:8000
- **MongoDB**: localhost:27017 (internal)
- **API Docs**: http://localhost:8000/docs
---

## **Context Packing & Memory Management**

### **Memory Strategy**

The system implements a **two-tier memory architecture**:

#### **1. Short-Term Memory**
- Stores last **K turns** (configurable, default=10)
- Direct message retrieval from MongoDB
- Fast access for recent context

#### **2. Long-Term Summary**
- Activated when token budget exceeded
- Compresses conversation history into summary
- Updated incrementally

### **Token Estimation Formula**
```python
estimated_tokens = ceil(len(text_chars) / 4)
```

Simple heuristic that approximates token count without expensive tokenizer calls.

### **Context Packing Strategy**
```
[system meta]
[session summary (if present)]
[last K user/assistant turns]
[current user prompt]
```
**Token Budget**: 3000 tokens (configurable via `TOKEN_BUDGET` env var)

---

## **Performance Metrics**

### **TTFT (Time To First Token)**
```python
TTFT = (first_token_timestamp - request_start_timestamp) * 1000  # milliseconds
```

Measures latency from request receipt to first streamed token.

### **Total Request Time**
```python
Total_Time = (completed_timestamp - request_start_timestamp) * 1000  # milliseconds
```

End-to-end request processing time.

### **Tool Call Metrics**

Each DB tool invocation logs:
- Tool name (`db.find`, `db.insert`, `db.aggregate`)
- Arguments
- Result status
- Latency (ms)
- Timestamp

All metrics persisted to `metrics` and `tool_calls` collections for analytics.

---

## **Testing**

### **1. Seed Script (Context-Aware Verification)**
```bash
python seed_data.py
```

**What it tests:**
- Multi-turn conversation
- Context memory across turns
- Turn 1: "My name is Alice"
- Turn 2: "What is my name?" → Should respond "Alice"
- Turn 3: Summary of entire conversation

### **2. Acceptance Tests**
```bash
python test_acceptance.py
```

**Validates:**
- ✅ All SSE event types emitted (agent, tool_call_*, token, done)
- ✅ Context-aware memory (remembers previous turns)
- ✅ DB tool calling and logging
- ✅ Persistence (messages, metrics, suggestions)

**Expected output:**
```
RESULTS: 9/9 passed
```
### ** 3. Testing in CMD **
```
Question 1
curl -N -X POST "http://localhost:8000/v1/chat/stream" ^
  -H "Authorization: Bearer devkey" ^
  -H "Content-Type: application/json" ^
  -d "{\"sessionId\":\"cmd_test1\",\"userId\":\"user11\",\"prompt\":\"What is AI?\"}"

Question 2 (different topic)
curl -N -X POST "http://localhost:8000/v1/chat/stream" ^
  -H "Authorization: Bearer devkey" ^
  -H "Content-Type: application/json" ^
  -d "{\"sessionId\":\"cmd_test2\",\"userId\":\"user1\",\"prompt\":\"Explain quantum computing\"}"

Question 3 (context test)
curl -N -X POST "http://localhost:8000/v1/chat/stream" ^
  -H "Authorization: Bearer devkey" ^
  -H "Content-Type: application/json" ^
  -d "{\"sessionId\":\"cmd_test3\",\"userId\":\"user1\",\"prompt\":\"My favorite color is blue\"}"

Question 3 (Testing Memory)
curl -N -X POST "http://localhost:8000/v1/chat/stream" ^
  -H "Authorization: Bearer devkey" ^
  -H "Content-Type: application/json" ^
  -d "{\"sessionId\":\"cmd_test3\",\"userId\":\"user1\",\"prompt\":\"What color did I say?\"}"

```


### **4. Manual Testing**

#### **Health Check**
```bash
curl http://localhost:8000/health
```

#### **Stream Chat**
```bash
curl -N -X POST http://localhost:8000/v1/chat/stream \
  -H "Authorization: Bearer devkey" \
  -H "Content-Type: application/json" \
  -d '{
    "sessionId": "test1",
    "userId": "user1",
    "prompt": "Hi My name is Kurnia Anwar Ra'if, What is artificial intelligence?"
  }'
```

#### **Interactive API Docs**
```
http://localhost:8000/docs
```

---

## **API Endpoints**

### **POST /v1/chat/stream**
Stream chat response with SSE.

**Headers:**
```
token : devkey
authorization: Bearer devkey
Content-Type: application/json
```

**Request Body:**
```json
{
  "sessionId": "session_123",
  "userId": "user_abc",
  "prompt": "Your question here"
}
```

- After put Request Body, execute it.

**SSE Events:**
```
event: agent
data: {"name":"planner"}

event: tool_call_started
data: {"tool":"db.find","args":{...}}

event: tool_call_completed
data: {"tool":"db.find","ok":true,"latencyMs":7.5}

event: token
data: {"text":"Hello"}

event: done
data: {
  "fullText":"Hello, how can I help?",
  "suggestions":["Ask about features","Get examples","Learn more"],
  "timings":{"ttft_ms":150,"total_ms":2340}
}
```

### **GET /v1/sessions/{session_id}**
Retrieve session metadata and summary.

**Response:**
```json
{
  "sessionId": "session_123",
  "userId": "user_abc",
  "summary": "User discussed AI topics...",
  "messageCount": 10,
  "createdAt": "2025-11-14T10:00:00Z",
  "updatedAt": "2025-11-14T11:30:00Z"
}
```

### **GET /v1/sessions/{session_id}/messages**
Get conversation history.

**Query Parameters:**
- `limit`: Max messages (default: 50)

### **GET /v1/metrics/{session_id}**
Retrieve aggregated metrics.

**Response:**
```json
{
  "sessionId": "session_123",
  "totalRequests": 15,
  "avgTtftMs": 180.5,
  "avgTotalTimeMs": 2100.3,
  "totalToolCalls": 45
}
```

### **GET /v1/vitals**
System-wide statistics.

**Response:**
```json
{
  "uptime_seconds": 3600.5,
  "total_sessions": 42,
  "total_messages": 356,
  "total_tool_calls": 128,
  "avg_response_time_ms": 1850.3
}
```

### **GET /health**
Health check (no auth required).

---

## **Database Schema**

### **Collections**

#### **messages**
```javascript
{
  _id: ObjectId,
  sessionId: "session_123",
  userId: "user_abc",
  role: "user" | "assistant",
  content: "Message text",
  metadata: {
    suggestions: [...],
    timings: {...}
  },
  timestamp: 1699790400.0,
  createdAt: "2025-11-14T10:00:00Z"
}
```

#### **sessions**
```javascript
{
  _id: ObjectId,
  sessionId: "session_123",
  userId: "user_abc",
  summary: "Long-term conversation summary",
  createdAt: "2025-11-14T10:00:00Z",
  updatedAt: "2025-11-14T12:00:00Z"
}
```

#### **tool_calls**
```javascript
{
  _id: ObjectId,
  sessionId: "session_123",
  userId: "user_abc",
  tool: "db.find",
  args: {...},
  result: {...},
  latency_ms: 7.5,
  timestamp: "2025-11-14T10:00:00Z"
}
```

#### **suggestions**
```javascript
{
  _id: ObjectId,
  sessionId: "session_123",
  messageId: "msg_456",
  suggestions: ["...", "...", "..."],
  createdAt: "2025-11-14T10:00:00Z"
}
```

#### **metrics**
```javascript
{
  _id: ObjectId,
  sessionId: "session_123",
  messageId: "msg_456",
  ttft_ms: 150.5,
  total_time_ms: 2345.8,
  tool_call_count: 2,
  agent_timings: {
    planner: 120.3,
    worker: 500.2,
    critic: 80.1,
    synthesizer: 200.5
  },
  timestamp: "2025-11-14T10:00:00Z"
}
```

---

#### **Option 2: Local Development with Virtual Environment**

This option allows you to run the backend locally while using Docker only for MongoDB.

##### **Step 1: Setup Virtual Environment**
```bash
# 1. Clone repository
git clone 
cd ai-orchestration-backend

# 2. Create virtual environment
python -m venv venv
# Or if python command doesn't work:
# python3 -m venv venv
# py -m venv venv  (Windows alternative)

# 3. Activate virtual environment

# Windows (Command Prompt):
venv\Scripts\activate.bat

# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# If PowerShell blocks execution, run first:
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Mac/Linux (Bash/Zsh):
source venv/bin/activate

# Verify activation - you should see (venv) in prompt:
# (venv) C:\Projects\ai-orchestration-backend>
```

##### **Step 2: Install Dependencies**
```bash
# Upgrade pip to latest version
pip install --upgrade pip

# Install all project dependencies
pip install -r requirements.txt

# This will install:
# - FastAPI and Uvicorn (web framework)
# - LangGraph and LangChain (agent orchestration)
# - Motor and PyMongo (MongoDB async driver)
# - OpenAI client (LLM integration)
# - Pydantic (data validation)
# - And other dependencies...

# Verify installation
pip list
# Should show ~30 packages installed
```

##### **Step 3: Configure Environment**
```bash
# 1. Create environment file
cp .env.example .env

# 2. Edit .env with your configuration
# Windows: notepad .env
# Mac/Linux: nano .env

# 3. IMPORTANT: Change MongoDB URI for local development
# In .env, set:
MONGO_URI=mongodb://admin:admin123@localhost:27017
# (Note: "localhost" instead of "mongodb")

# 4. Set your OpenAI API key
OPENAI_API_KEY=sk-proj-YOUR_ACTUAL_KEY_HERE

# 5. Configure LLM provider
LLM_PROVIDER=openai
OPENAI_MODEL=gpt-4o-mini
```

##### **Step 4: Start MongoDB**
```bash
# Start only MongoDB via Docker
docker-compose up -d mongodb

# Verify MongoDB is running
docker-compose ps mongodb
# Expected: "Up (healthy)"

# Test MongoDB connection
docker exec -it ai_orchestration_mongodb mongosh -u admin -p admin123 --eval "db.version()"
# Should show MongoDB version
```

##### **Step 5: Run Backend Application**
```bash
# Make sure virtual environment is activated (see (venv) in prompt)

# Run backend with hot-reload
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Expected output:
# INFO:     Uvicorn running on http://0.0.0.0:8000
# INFO:     Application startup complete.
# 2025-11-15 08:00:00 - INFO - ✓ MongoDB connected
# 2025-11-15 08:00:00 - INFO - ✓ LLM Provider: openai
# 2025-11-15 08:00:00 - INFO - ✓ Application started successfully

# Keep this terminal running - it will show request logs
```

##### **Step 6: Test the Application**

Open a **new terminal** (keep backend running in first terminal):
```bash
# Activate venv in new terminal
# Windows: venv\Scripts\activate.bat
# Mac/Linux: source venv/bin/activate

# Test health endpoint
curl http://localhost:8000/health

# Test interactive docs
# Open browser: http://localhost:8000/docs

# Run seed script (context-aware test)
python seed_data.py

# Run acceptance tests
python test_acceptance.py
```

##### **Step 7: Development Workflow**
```bash
# Edit code in src/ directory
# Uvicorn will auto-reload on file changes

# View logs in the terminal running uvicorn

# To stop backend: Press Ctrl+C in uvicorn terminal

# To stop MongoDB:
docker-compose stop mongodb

# To deactivate virtual environment:
deactivate
```

## **Environment Variables**
- attach in .env.example
```bash
# MongoDB
MONGO_URI=mongodb://admin:admin123@mongodb:27017
MONGO_DB_NAME=ai_orchestration

# LLM Provider (mock | openai | anthropic)
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-proj-YOUR_KEY_HERE
OPENAI_MODEL=gpt-4o-mini

# API Configuration
CORS_ORIGINS=*
DEBUG=true

# Memory Configuration
SHORT_TERM_K=10          # Recent turns to keep
TOKEN_BUDGET=3000        # Max tokens for context

# Auth
DEV_AUTH_TOKEN=devkey
```

---

## **Configuration**

### **Adjust Memory Settings**

Edit `.env`:
```bash
SHORT_TERM_K=15        # Keep last 15 turns
TOKEN_BUDGET=5000      # Increase budget to 5000 tokens
```

### **Switch LLM Provider**

**Use OpenAI:**
```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-proj-...
OPENAI_MODEL=gpt-4o-mini
```

**Use Mock (No API):**
```bash
LLM_PROVIDER=mock
```

---

## **Trade-offs & Design Decisions**

### **1. Mock LLM as Default**

**Decision**: Use mock LLM by default, toggle for real providers  
**Reason**: Enables testing without API costs  
**Trade-off**: Less realistic responses in development

### **2. Single Retry Path**

**Decision**: Critic can trigger maximum 1 retry  
**Reason**: Balance quality vs latency (prevent infinite loops)  
**Trade-off**: May miss edge cases requiring multiple iterations

### **3. Simple Token Estimation**

**Decision**: Use `ceil(len/4)` heuristic instead of tokenizer  
**Reason**: Fast approximation, no dependency on model-specific tokenizers  
**Trade-off**: Not exact, but sufficient for budgeting (~10% variance)

### **4. MongoDB for All Storage**

**Decision**: Single database for messages, sessions, metrics  
**Reason**: Simplicity, async support, flexible schema  
**Trade-off**: Could use Redis for hot data caching, but adds complexity

### **5. SSE over WebSocket**

**Decision**: Server-Sent Events for streaming  
**Reason**: Simpler protocol, automatic reconnection, HTTP/2 friendly  
**Trade-off**: Unidirectional only (sufficient for this use case)

---

## **Future Improvements**

### **Performance**
- [ ] Redis caching for session summaries
- [ ] Connection pooling optimization
- [ ] Parallel subtask execution in Worker
- [ ] Batch tool call aggregation

### **Features**
- [ ] Multi-language support
- [ ] Custom agent configurations per user
- [ ] Streaming tool call results
- [ ] WebSocket alternative for bidirectional communication
- [ ] Voice input/output integration

### **Observability**
- [ ] OpenTelemetry integration
- [ ] Structured JSON logging
- [ ] Prometheus metrics export
- [ ] Grafana dashboards
- [ ] Distributed tracing

### **Security**
- [ ] JWT-based authentication
- [ ] Rate limiting per user/session
- [ ] API key rotation mechanism
- [ ] Input sanitization & validation
- [ ] Secrets management (Vault integration)

### **Testing**
- [ ] Integration tests for full pipeline
- [ ] Load testing with Locust
- [ ] Chaos engineering scenarios
- [ ] Performance regression tests

---

## **Development**

### **Project Structure**
```
```
src/
  api/
    main.py
    routers/
      chat.py
      sessions.py
      suggestions.py
      metrics.py
      vitals.py
      health.py
  orchestration/
    graph.py                # LangGraph or ADK graph
    state.py
    agents/
      planner.py
      worker.py
      critic.py
      synthesizer.py
    tools/
      db_tools.py           # db.find / db.insert / db.aggregate
      time.py               # utility for timestamps
    memory/
      store.py              # Mongo-backed
      context_manager.py    # packing & budgets
      summarizer.py
    llm/
      mock.py               # default mock model
      provider.py           # optional real provider
  db/
    client.py               # Mongo connection
    models.py               # Pydantic DTOs
    indexes.py
.env.example
requirements.txt
docker-compose.yml
Dockerfile    
README.md

```

### **Code Quality**

- **Type Hints**: Full Pydantic model typing throughout
- **Async/Await**: Idiomatic async I/O for performance
- **Error Handling**: Comprehensive try-catch with logging
- **Documentation**: Docstrings for all public functions

### **Running Tests**
```bash
# Unit tests
pytest tests/

# With coverage
pytest --cov=src --cov-report=html

# Acceptance tests
python test_acceptance.py
```

---

## **Troubleshooting**

### **Port 8000 Already in Use**
```bash
# Find process
lsof -ti:8000 | xargs kill -9  # Mac/Linux
netstat -ano | findstr :8000   # Windows

# Or change port in docker-compose.yml
ports:
  - "8001:8000"
```

### **MongoDB Connection Error**
```bash
# Restart MongoDB
docker-compose restart mongodb

# Check logs
docker-compose logs mongodb
```

### **OpenAI API Error**
```bash
# Verify API key
echo $OPENAI_API_KEY

# Test directly
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

### **No Response from Agents**
```bash
# Check backend logs
docker-compose logs backend --tail=100

# Verify LLM provider is set
docker exec ai_orchestration_backend env | grep LLM
```

## **Support**

For issues and questions:
- Check `/docs` for interactive API documentation
- Review logs: `docker-compose logs -f backend`
- Open an issue on the repository
- Contact me -> gmail : kurniaanwarraif@gmail.com or linkedin : https://www.linkedin.com/in/anwaraif/


**End of README.md**
