import mlflow
import mlflow.tracing as mlflow_tracing
from openai import OpenAI

# Configure MLflow
mlflow.set_tracking_uri("http://localhost:5747")
mlflow.set_experiment("Demo Experiment")

# Enable tracing and OpenAI autologging
mlflow_tracing.enable()
mlflow.openai.autolog()

# Create an OpenAI-compatible client pointing to LlamaStack
# client = OpenAI(
#     base_url="http://localhost:8321/v1",
#     api_key="fake",
# )

client = OpenAI()

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "user", "content": "Give a one-sentence description of LlamaStack."}
    ],
)
print(response.choices[0].message.content)