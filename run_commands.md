

# Just MLFLOW 

# Start the MLflow Tracking Server

Launch a local MLflow server with SQLite as the backend store:

mlflow server \
  --backend-store-uri sqlite:///mlflow.db \
  --default-artifact-root ./mlruns \
  --host 0.0.0.0 --port 5000#


# Run the Python code 

export MLFLOW_TRACKING_URI=http://localhost:5747

python run_openai_mlflow.py


# Add otel config just run the code again


export MLFLOW_ENABLE_TRACING=0
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
export OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
export OTEL_SERVICE_NAME=GPT-4o-Experiment
export OTEL_METRICS_EXPORTER=none
export OTEL_LOGS_EXPORTER=none
opentelemetry-instrument python run_openai_mlflow.py


MLFLOW_ENABLE_TRACING=0 \
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318 \
OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf \
OTEL_SERVICE_NAME=GPT-4o-Experiment \
opentelemetry-instrument python run_openai_mlflow.py