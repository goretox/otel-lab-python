from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import time

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# 1. Configurar recursos del servicio
resource = Resource.create(attributes={"service.name": "order-service-python"})

# 2. Configurar el TracerProvider global
provider = TracerProvider(resource=resource)
trace.set_tracer_provider(provider)

# 3. Exportador OTLP hacia el OTel Collector (gRPC puerto 4317)
otlp_exporter = OTLPSpanExporter(endpoint="http://localhost:4317", insecure=True)
span_processor = BatchSpanProcessor(otlp_exporter)
provider.add_span_processor(span_processor)

tracer = trace.get_tracer("order-service-python-tracer")

app = FastAPI()

# 4. Auto-instrumentar FastAPI
FastAPIInstrumentor.instrument_app(app)

class OrderRequest(BaseModel):
    user_id: str
    total_amount: float

@app.get("/hello")
def say_hello():
    return {"message": "¡Hola desde Python y FastAPI instrumentado con OTel!"}

@app.post("/orders")
def process_order(order: OrderRequest):
    with tracer.start_as_current_span("process_payment") as span:
        try:
            span.set_attribute("app.user_id", order.user_id)
            span.set_attribute("app.payment.total", order.total_amount)

            if order.total_amount <= 0:
                raise ValueError("Monto de la orden inválido en Python")

            time.sleep(0.15)
            return {"status": "success", "orderId": "ORD-PY-8841"}
            
        except ValueError as e:
            span.record_exception(e)
            span.set_status(trace.StatusCode.ERROR, str(e))
            raise HTTPException(status_code=400, detail=str(e))
