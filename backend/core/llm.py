from langchain_groq import ChatGroq
from langchain_core.rate_limiters import InMemoryRateLimiter
from backend.core.config import settings

# Rate limiter — stays within Groq free tier (30 req/min)
rate_limiter = InMemoryRateLimiter(
    requests_per_second=0.4,   # ~24 requests/min
    check_every_n_seconds=0.1,
    max_bucket_size=10
)


def get_llm(task_type: str = "reasoning") -> ChatGroq:
    """
    Route to the right model based on task complexity.

    reasoning → qwen/qwen3.8-27b  (planner, critic, responder)
    fast      → qwen/qwen3.8-27b  (simple classification)
    sql       → qwen/qwen3.8-27b  (needs accuracy, temp=0)
    """
    if task_type == "fast":
        model = settings.groq_fast_model
    else:
        model = settings.groq_model

    return ChatGroq(
        model=model,
        api_key=settings.groq_api_key,
        temperature=0.0 if task_type == "sql" else 0.1,
        max_tokens=768,
        max_retries=3,
        rate_limiter=rate_limiter
    )
