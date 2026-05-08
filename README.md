# MLflow Observability with OpenTelemetry (OTel) SDK

End-to-end observability for LLM applications using **MLflow 3**, **OpenAI GPT-4o**, and the **OpenTelemetry Collector** — traces flow from your Python app through the OTel Collector into the MLflow UI.

**Repo:** https://github.com/anjijava16/mlflow_-observability_sdk_otel.git

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Your Python App                              │
│                                                                     │
│   run_openai_mlflow.py                                              │
│   ┌───────────────────────────────────────────────────────────┐    │
│   │  mlflow.openai.autolog()   ←  auto-instruments OpenAI SDK │    │
│   │  mlflow_tracing.enable()   ←  enables MLflow trace SDK    │    │
│   │  OpenAI(gpt-4o).chat()     ←  actual LLM call             │    │
│   └───────────┬───────────────────────────────────────────────┘    │
└───────────────┼─────────────────────────────────────────────────────┘
                │ OTLP HTTP (protobuf)
                │ http://localhost:4318/v1/traces
                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   OpenTelemetry Collector                           │
│                   otelcol-contrib v0.151.0 (darwin/arm64)          │
│                                                                     │
│   Receiver:   otlp (HTTP :4318)                                    │
│   Processor:  batch (5s timeout)                                   │
│   Exporters:                                                        │
│     traces  → otlp_http/mlflow  → localhost:5747/v1/traces        │
│     metrics → debug             → collector console                │
│     logs    → debug             → collector console                │
└───────────────┬─────────────────────────────────────────────────────┘
                │ OTLP HTTP
                │ http://localhost:5747/v1/traces
                │ Header: x-mlflow-experiment-id: "2"
                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      MLflow Server :5747                            │
│                                                                     │
│   Backend:   SQLite (mlflow.db)                                    │
│   Artifacts: ./mlruns                                              │
│   UI:        http://localhost:5747                                  │
│                                                                     │
│   Experiment: GPT-4o-Experiment  (ID: 2)                          │
│     └── Runs → Traces → Spans (ChatCompletion calls)               │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Component | Library / Tool | Version | Role |
|---|---|---|---|
| LLM Client | `openai` | ≥2.20.0 | Calls GPT-4o API |
| Tracing SDK | `mlflow[genai]` | ≥3.10 | Auto-instruments & exports traces |
| OTel API | `opentelemetry-api` | latest | Core OTel interfaces |
| OTel SDK | `opentelemetry-sdk` | latest | Trace/metric/log SDK |
| OTel Exporter | `opentelemetry-exporter-otlp` | latest | Sends telemetry via OTLP |
| OTel Auto-Instr | `opentelemetry-instrumentation-openai` | latest | Wraps OpenAI calls as spans |
| OTel Collector | `otelcol-contrib` | 0.151.0 | Receives, processes, exports telemetry |
| MLflow Server | `mlflow` | ≥3.10 | Stores and visualises traces |
| Python | - | ≥3.13 | Runtime |
| Package manager | `uv` | - | Dependency management |

---

## Prerequisites

- Python 3.13+
- `uv` package manager (`pip install uv`)
- OpenAI API key (`OPENAI_API_KEY` env var)
- macOS Apple Silicon (arm64) — see OTel Collector install below

---

## Step 1 — Clone & Install Dependencies

```bash
git clone https://github.com/anjijava16/mlflow_-observability_sdk_otel.git
cd mlflow_-observability_sdk_otel

# Create virtual environment and install all dependencies
uv sync
source .venv/bin/activate
```

**`pyproject.toml` dependencies:**
```toml
dependencies = [
    "mlflow[genai]>=3.10",
    "openai>=2.20.0",
    "opentelemetry-api",
    "opentelemetry-sdk",
    "opentelemetry-exporter-otlp",
    "opentelemetry-instrumentation-openai",
]
```

---

## Step 2 — Set OpenAI API Key

```bash
export OPENAI_API_KEY="sk-..."
```

---

## Step 3 — Start MLflow Tracking Server

```bash
mlflow server \
  --backend-store-uri sqlite:///mlflow.db \
  --default-artifact-root ./mlruns \
  --host 0.0.0.0 --port 5747
```

MLflow UI available at: **http://localhost:5747**

| Flag | Value | Purpose |
|---|---|---|
| `--backend-store-uri` | `sqlite:///mlflow.db` | Stores runs/experiments in local SQLite |
| `--default-artifact-root` | `./mlruns` | Stores model artifacts locally |
| `--host` | `0.0.0.0` | Listens on all interfaces |
| `--port` | `5747` | HTTP port for UI and API |

---

## Step 4 — Install OTel Collector (macOS Apple Silicon)

> **Note:** The original `otel_install.sh` downloads a Linux x86_64 binary which fails with `exec format error` on Apple Silicon. Use the correct darwin/arm64 binary:

```bash
curl -L -o otelcol-contrib_darwin_arm64.tar.gz \
  "https://github.com/open-telemetry/opentelemetry-collector-releases/releases/download/v0.151.0/otelcol-contrib_0.151.0_darwin_arm64.tar.gz"

tar -xzf otelcol-contrib_darwin_arm64.tar.gz otelcol-contrib
rm otelcol-contrib_darwin_arm64.tar.gz
chmod +x otelcol-contrib

# Verify
file otelcol-contrib
# otelcol-contrib: Mach-O 64-bit executable arm64  ✅
```

> **Warning:** Extract only the `otelcol-contrib` binary — do NOT extract all files (`tar -xzf` without specifying `otelcol-contrib`) as it will overwrite your project's `README.md` with the collector's own README.

> First launch: macOS may block the binary — go to **System Settings → Privacy & Security → Allow Anyway**

---

## Step 5 — Configure OTel Collector

**`otel-collector-config.yaml`:**

```yaml
receivers:
  otlp:
    protocols:
      http:
        endpoint: 0.0.0.0:4318      # Receives OTLP traces/metrics/logs

exporters:
  otlp_http/mlflow:
    endpoint: http://localhost:5747  # MLflow server
    tls:
      insecure: true
    headers:
      x-mlflow-experiment-id: "2"   # Routes to "GPT-4o-Experiment" (ID=2)
  debug:
    verbosity: basic                 # Prints metrics/logs to console

processors:
  batch:
    timeout: 5s                      # Batches spans before exporting

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch]
      exporters: [otlp_http/mlflow, debug]  # Traces → MLflow + console
    metrics:
      receivers: [otlp]
      processors: [batch]
      exporters: [debug]             # Metrics → console only (MLflow has no /v1/metrics)
    logs:
      receivers: [otlp]
      processors: [batch]
      exporters: [debug]             # Logs → console only
```

**Key design decisions:**
- `traces_endpoint` is omitted — `otlp_http` auto-appends `/v1/traces` to `endpoint`
- Metrics and logs go to `debug` only — MLflow only accepts traces via OTLP
- `x-mlflow-experiment-id` header must match the actual MLflow experiment ID

Get the correct experiment ID:
```bash
curl -s "http://localhost:5747/api/2.0/mlflow/experiments/search?max_results=10" | python3 -m json.tool
```

---

## Step 6 — Start OTel Collector

```bash
./otelcol-contrib --config otel-collector-config.yaml
```

**Expected startup logs:**
```
INFO  Starting otelcol-contrib...  {"Version": "0.151.0", "NumCPU": 10}
INFO  Starting HTTP server         {"endpoint": "[::]:4318"}
INFO  Everything is ready. Begin running and processing data.
```

---

## Step 7 — Run the Python App

**`run_openai_mlflow.py`:**
```python
import mlflow
import mlflow.tracing as mlflow_tracing
from openai import OpenAI

mlflow.set_tracking_uri("http://localhost:5747")
mlflow.set_experiment("GPT-4o-Experiment")

mlflow_tracing.enable()       # Register MLflow as OTel TracerProvider
mlflow.openai.autolog()       # Monkey-patch OpenAI SDK to emit spans

client = OpenAI()
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Give a one-sentence description of LlamaStack."}],
)
print(response.choices[0].message.content)
```

### Option A — MLflow native tracing only

```bash
export MLFLOW_TRACKING_URI=http://localhost:5747
python run_openai_mlflow.py
```

### Option B — OTel auto-instrumentation via Collector

```bash
MLFLOW_ENABLE_TRACING=0 \
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318 \
OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf \
OTEL_SERVICE_NAME=GPT-4o-Experiment \
opentelemetry-instrument python run_openai_mlflow.py
```

| Env Var | Value | Purpose |
|---|---|---|
| `MLFLOW_ENABLE_TRACING` | `0` | Disables MLflow's own OTLP exporter (avoids duplicate traces) |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://localhost:4318` | Points OTel SDK to the Collector |
| `OTEL_EXPORTER_OTLP_PROTOCOL` | `http/protobuf` | Use HTTP+protobuf (not gRPC) |
| `OTEL_SERVICE_NAME` | `GPT-4o-Experiment` | Tags all spans with this service name |

---

## How It Works — Deep Dive

### MLflow SDK Tracing

```python
mlflow_tracing.enable()      # Registers MLflow as an OTel TracerProvider
mlflow.openai.autolog()      # Monkey-patches OpenAI client to emit spans
```

When `client.chat.completions.create()` is called:
1. MLflow wraps it in an OTel span with attributes: model, prompt tokens, completion tokens, latency
2. The span is exported via OTLP to whatever endpoint is configured

### OTel SDK Signal Flow

```
openai.chat.completions.create()
    ↓ (auto-instrumented by opentelemetry-instrumentation-openai)
OTel Tracer → creates Span {
    name: "openai.chat",
    attributes: {
        "gen_ai.system": "openai",
        "gen_ai.request.model": "gpt-4o",
        "gen_ai.usage.prompt_tokens": N,
        "gen_ai.usage.completion_tokens": N,
    }
}
    ↓ OTLP HTTP protobuf → localhost:4318/v1/traces
OTel Collector — otlp receiver
    ↓ batch processor (groups spans, 5s window)
otlp_http/mlflow exporter
    ↓ POST http://localhost:5747/v1/traces
      Header: x-mlflow-experiment-id: "2"
MLflow Server — stores trace in SQLite (mlflow.db)
    ↓
MLflow UI → Experiments → GPT-4o-Experiment → Runs → Traces tab
```

### What Each Signal Does

| Signal | Sender | Destination | Visible in UI |
|---|---|---|---|
| **Traces** | `opentelemetry-instrumentation-openai` | MLflow via collector | Yes — Traces tab |
| **Metrics** | OTel SDK runtime (request counts, latency) | `debug` exporter (console) | No — MLflow has no `/v1/metrics` |
| **Logs** | OTel SDK | `debug` exporter (console) | No |

### Span Data in MLflow

Each GPT-4o call becomes a trace visible in the MLflow UI:

| Span Field | Example Value |
|---|---|
| Span name | `openai.chat` |
| Service | `GPT-4o-Experiment` |
| Model | `gpt-4o` |
| Prompt tokens | 18 |
| Completion tokens | 32 |
| Duration | ~2s |
| Status | `OK` |

---

## MLflow Experiments

| ID | Name | Description |
|---|---|---|
| 0 | Default | Auto-created default experiment |
| 1 | GPT-4o Demo | First test run |
| 2 | GPT-4o-Experiment | Active experiment |

---

## Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `exec format error: ./otelcol-contrib` | Linux binary on Apple Silicon | Download `darwin_arm64` binary (Step 4) |
| `Failed to export metrics batch code: 404` | MLflow has no `/v1/metrics` endpoint | Add `metrics` pipeline with `debug` exporter in collector config |
| `unsupported protocol scheme ""` | `traces_endpoint: /v1/traces` used as standalone URL | Remove `traces_endpoint` — `otlp_http` appends it automatically |
| Traces not in MLflow UI | Wrong `x-mlflow-experiment-id` header | Check actual experiment ID via API and update config |
| `"otlphttp" alias is deprecated` | Old exporter key name | Rename `otlphttp/mlflow` → `otlp_http/mlflow` in config |
| README.md overwritten | `tar -xzf` without specifying binary extracts all files | Always extract: `tar -xzf archive.tar.gz otelcol-contrib` |

---

## Project Structure

```
mlflow_-observability_sdk_otel/
├── run_openai_mlflow.py          # Main app — GPT-4o call with MLflow tracing
├── main.py                       # Entry point placeholder
├── otel-collector-config.yaml    # OTel Collector pipeline configuration
├── otelcol-contrib               # OTel Collector binary (darwin/arm64 v0.151.0)
├── otel_install.sh               # Original install script (Linux — needs update for macOS)
├── run_mlflow_server.sh          # Script to start MLflow server on :5747
├── run_commands.md               # All run commands reference
├── otel_debug.md                 # Debug log — binary fix & startup details
├── pyproject.toml                # Python dependencies (uv)
├── mlflow.db                     # SQLite database (auto-created by MLflow)
├── mlruns/                       # MLflow artifact storage (auto-created)
└── .venv/                        # Virtual environment
```

---

## Quick Start (All Steps)

```bash
# 1. Clone and install
git clone https://github.com/anjijava16/mlflow_-observability_sdk_otel.git
cd mlflow_-observability_sdk_otel
uv sync && source .venv/bin/activate

# 2. Set API key
export OPENAI_API_KEY="sk-..."

# 3. Start MLflow (Terminal 1)
bash run_mlflow_server.sh

# 4. Start OTel Collector (Terminal 2)
./otelcol-contrib --config otel-collector-config.yaml

# 5. Run the app (Terminal 3)
MLFLOW_ENABLE_TRACING=0 \
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318 \
OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf \
OTEL_SERVICE_NAME=GPT-4o-Experiment \
opentelemetry-instrument python run_openai_mlflow.py

# 6. View traces in MLflow UI
open http://localhost:5747
```
