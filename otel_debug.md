# OTel Collector Debug & Fix Log

## Problem

```
zsh: exec format error: ./otelcol-contrib
```

### Root Cause

The binary downloaded by `otel_install.sh` was built for **Linux x86_64** (ELF format),
but the machine is an **Apple Silicon Mac (arm64)**. These two architectures are incompatible —
macOS cannot execute Linux ELF binaries.

| Property | Old Binary | New Binary |
|---|---|---|
| Format | ELF 64-bit LSB (Linux) | Mach-O 64-bit (macOS) |
| Architecture | x86_64 (Intel/AMD) | arm64 (Apple Silicon) |
| OS target | Linux | macOS (darwin) |
| Version | 0.143.1 | 0.151.0 |
| Source (`otel_install.sh`) | `otelcol-contrib_0.143.1_linux_amd64.tar.gz` | `otelcol-contrib_0.151.0_darwin_arm64.tar.gz` |

---

## Fix Applied

Downloaded the correct macOS arm64 binary from the OpenTelemetry Collector releases:

```bash
curl -L -o otelcol-contrib_darwin_arm64.tar.gz \
  "https://github.com/open-telemetry/opentelemetry-collector-releases/releases/download/v0.151.0/otelcol-contrib_0.151.0_darwin_arm64.tar.gz"

tar -xzf otelcol-contrib_darwin_arm64.tar.gz otelcol-contrib
rm otelcol-contrib_darwin_arm64.tar.gz
chmod +x otelcol-contrib
```

Verification:
```
file otelcol-contrib
# otelcol-contrib: Mach-O 64-bit executable arm64  ✅
```

---

## Fix `otel_install.sh`

The install script still references the Linux binary. Update it for macOS arm64:

```bash
# Before (Linux x86_64 — wrong on Apple Silicon Mac)
curl -LO https://github.com/open-telemetry/opentelemetry-collector-releases/releases/download/v0.143.1/otelcol-contrib_0.143.1_linux_amd64.tar.gz
tar -xzf otelcol-contrib_0.143.1_linux_amd64.tar.gz

# After (macOS arm64 — correct for Apple Silicon)
curl -LO https://github.com/open-telemetry/opentelemetry-collector-releases/releases/download/v0.151.0/otelcol-contrib_0.151.0_darwin_arm64.tar.gz
tar -xzf otelcol-contrib_0.151.0_darwin_arm64.tar.gz
```

---

## Current Working Setup

### Run the Collector

```bash
./otelcol-contrib --config otel-collector-config.yaml
```

### `otel-collector-config.yaml` Overview

```yaml
receivers:
  otlp:
    protocols:
      http:
        endpoint: 0.0.0.0:4318   # Receives traces on this port

exporters:
  otlphttp/mlflow:
    endpoint: http://localhost:5747      # MLflow server
    traces_endpoint: /v1/traces          # MLflow OTLP traces endpoint
    tls:
      insecure: true
    headers:
      x-mlflow-experiment-id: "1"        # Routes to experiment ID 1

processors:
  batch:
    timeout: 5s                          # Batches spans every 5 seconds

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch]
      exporters: [otlphttp/mlflow]
```

**Data flow:**
```
Python app (mlflow.openai.autolog)
    → OTLP HTTP :4318
        → otelcol-contrib (batch processor)
            → MLflow server :5747/v1/traces
                → MLflow UI (http://localhost:5747)
```

---

---

## Successful Startup Output

```
(mlflow-observability-sdk-otel) welcome@jaisairams-Laptop mlflow_-observability_sdk_otel % ./otelcol-contrib --config otel-collector-config.yaml
2026-05-08T13:54:49.872-0400	warn	builders/builders.go:40	"otlphttp" alias is deprecated; use "otlp_http" instead
2026-05-08T13:54:49.873-0400	info	service@v0.151.0/service.go:241	Starting otelcol-contrib...	{"Version": "0.151.0", "NumCPU": 10}
2026-05-08T13:54:49.873-0400	info	extensions/extensions.go:41	Starting extensions...
2026-05-08T13:54:49.873-0400	info	otlpreceiver@v0.151.0/otlp.go:175	Starting HTTP server	{"endpoint": "[::]:4318"}
2026-05-08T13:54:49.873-0400	info	service@v0.151.0/service.go:264	Everything is ready. Begin running and processing data.
```

### Log Line Explanations

| Log Level | Message | Meaning |
|---|---|---|
| `warn` | `"otlphttp" alias is deprecated; use "otlp_http" instead` | The exporter key in `otel-collector-config.yaml` uses the old name `otlphttp/mlflow`. Should be updated to `otlp_http/mlflow` in a future version. Collector still works. |
| `info` | `Starting otelcol-contrib... Version: 0.151.0, NumCPU: 10` | Collector started successfully on version 0.151.0 using all 10 CPU cores. |
| `info` | `Starting extensions...` | Any configured extensions are initializing (none configured here). |
| `info` | `Starting HTTP server {"endpoint": "[::]:4318"}` | OTLP HTTP receiver is now listening on port **4318** on all network interfaces. |
| `info` | `Everything is ready. Begin running and processing data.` | Collector is fully up and processing traces. ✅ |

### Deprecation Warning Fix

Update `otel-collector-config.yaml` to silence the warning:

```yaml
# Before (deprecated)
exporters:
  otlphttp/mlflow:

# After (current)
exporters:
  otlp_http/mlflow:
```

Also update the `service.pipelines.traces.exporters` reference accordingly:
```yaml
service:
  pipelines:
    traces:
      exporters: [otlp_http/mlflow]   # was [otlphttp/mlflow]
```

---

## Notes

- MLflow server must be running on port **5747** before starting the collector.
- The `x-mlflow-experiment-id: "1"` header routes traces to experiment ID 1 in MLflow.
- If macOS blocks the binary on first run, go to **System Settings → Privacy & Security → Allow Anyway**.
