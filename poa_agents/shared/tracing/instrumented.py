"""
Instrumented client wrappers for automatic tracing.

These wrap existing LLM and Supabase clients to automatically
capture calls, prompts, responses, and timing data.
"""

import time
from typing import Any, Optional, TYPE_CHECKING

from .context import current_trace, current_span
from .models import Span

if TYPE_CHECKING:
    from openai import AsyncOpenAI
    from supabase import Client


class InstrumentedLLMClient:
    """
    Wrapper around OpenAI/Azure client that automatically traces LLM calls.

    Usage:
        llm = InstrumentedLLMClient(base_client, model_name="gpt-4o")
        response = await llm.chat(messages=[...])
    """

    def __init__(
        self,
        client: "AsyncOpenAI",
        model_name: str = "gpt-4o",
        embedding_model: str = "text-embedding-3-small",
    ):
        self._client = client
        self.model_name = model_name
        self.embedding_model = embedding_model

    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        response_format: Optional[dict] = None,
        **kwargs,
    ) -> str:
        """
        Send a chat completion request with automatic tracing.

        Captures: system prompt, user prompt, response, tokens, latency.
        """
        trace = current_trace()

        # If no trace context, just call the underlying client
        if trace is None:
            return await self._raw_chat(messages, temperature, max_tokens, response_format, **kwargs)

        # Create span for this LLM call
        span = trace.span(f"llm_{self.model_name}", type="llm_call")

        with span:
            # Extract prompts for logging
            system_msg = next((m["content"] for m in messages if m["role"] == "system"), "")
            user_msg = next((m["content"] for m in messages if m["role"] == "user"), "")

            span.event("prompt", {
                "system": system_msg[:2000] if system_msg else None,
                "user": user_msg[:5000] if user_msg else None,
                "model": self.model_name,
                "temperature": temperature,
                "message_count": len(messages),
            })

            # Make the actual call
            start_ns = time.perf_counter_ns()
            response = await self._client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format=response_format,
                **kwargs,
            )
            latency_ms = int((time.perf_counter_ns() - start_ns) / 1_000_000)

            content = response.choices[0].message.content or ""
            usage = response.usage

            # Record response and metrics
            span.set_attributes({
                "model": self.model_name,
                "temperature": temperature,
                "latency_ms": latency_ms,
                "input_tokens": usage.prompt_tokens if usage else 0,
                "output_tokens": usage.completion_tokens if usage else 0,
                "total_tokens": usage.total_tokens if usage else 0,
                "finish_reason": response.choices[0].finish_reason,
            })

            span.event("response", {
                "content": content[:5000],
                "truncated": len(content) > 5000,
                "finish_reason": response.choices[0].finish_reason,
            })

            return content

    async def chat_json(
        self,
        messages: list[dict],
        temperature: float = 0.3,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Chat expecting JSON output."""
        return await self.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )

    async def get_embedding(self, text: str, model: Optional[str] = None) -> list[float]:
        """
        Generate an embedding with automatic tracing.

        Captures: input text sample, dimensions, latency.
        """
        model = model or self.embedding_model
        trace = current_trace()

        if trace is None:
            return await self._raw_embedding(text, model)

        span = trace.span(f"embed_{model}", type="embedding")

        with span:
            span.event("embed_input", {
                "text_sample": text[:500],
                "text_length": len(text),
                "model": model,
            })

            start_ns = time.perf_counter_ns()
            response = await self._client.embeddings.create(
                model=model,
                input=text,
            )
            latency_ms = int((time.perf_counter_ns() - start_ns) / 1_000_000)

            embedding = response.data[0].embedding
            usage = response.usage

            span.set_attributes({
                "model": model,
                "latency_ms": latency_ms,
                "dimensions": len(embedding),
                "total_tokens": usage.total_tokens if usage else 0,
            })

            return embedding

    async def _raw_chat(
        self,
        messages: list[dict],
        temperature: float,
        max_tokens: Optional[int],
        response_format: Optional[dict],
        **kwargs,
    ) -> str:
        """Raw chat call without tracing."""
        response = await self._client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
            **kwargs,
        )
        return response.choices[0].message.content or ""

    async def _raw_embedding(self, text: str, model: str) -> list[float]:
        """Raw embedding call without tracing."""
        response = await self._client.embeddings.create(model=model, input=text)
        return response.data[0].embedding


class InstrumentedSupabaseClient:
    """
    Wrapper around Supabase client that traces semantic search calls.

    Usage:
        supabase = InstrumentedSupabaseClient(base_client)
        results = supabase.semantic_search(embedding, limit=10)
    """

    def __init__(self, client: "Client"):
        self._client = client

    def semantic_search(
        self,
        query_embedding: list[float],
        language: str = "english",
        limit: int = 5,
        similarity_threshold: float = 0.3,
    ) -> list[dict]:
        """
        Perform semantic search with automatic tracing.

        Captures: query params, result count, similarities, top articles.
        """
        trace = current_trace()

        if trace is None:
            return self._raw_semantic_search(query_embedding, language, limit, similarity_threshold)

        span = trace.span("semantic_search", type="retrieval")

        with span:
            span.event("retrieval_query", {
                "language": language,
                "limit": limit,
                "threshold": similarity_threshold,
                "embedding_dim": len(query_embedding),
            })

            start_ns = time.perf_counter_ns()
            results = self._raw_semantic_search(query_embedding, language, limit, similarity_threshold)
            latency_ms = int((time.perf_counter_ns() - start_ns) / 1_000_000)

            # Calculate similarity stats
            similarities = [r.get("similarity", 0) for r in results]
            avg_sim = sum(similarities) / len(similarities) if similarities else 0
            top_sim = max(similarities) if similarities else 0

            span.set_attributes({
                "language": language,
                "limit": limit,
                "threshold": similarity_threshold,
                "latency_ms": latency_ms,
                "result_count": len(results),
                "avg_similarity": round(avg_sim, 4),
                "top_similarity": round(top_sim, 4),
            })

            span.event("retrieval_result", {
                "result_count": len(results),
                "articles": [
                    {
                        "article_number": r.get("article_number"),
                        "similarity": round(r.get("similarity", 0), 4),
                    }
                    for r in results[:10]
                ],
            })

            return results

    def _raw_semantic_search(
        self,
        query_embedding: list[float],
        language: str,
        limit: int,
        similarity_threshold: float,
    ) -> list[dict]:
        """Raw semantic search without tracing."""
        response = self._client.rpc(
            "match_poa_articles",
            {
                "query_embedding": query_embedding,
                "match_threshold": float(similarity_threshold),
                "match_count": int(limit),
                "language": language,
            }
        ).execute()
        return response.data if response.data else []

    def get_legal_brief(self, application_id: str) -> Optional[dict]:
        """
        Get legal brief with tracing.
        """
        trace = current_trace()

        if trace is None:
            return self._raw_get_legal_brief(application_id)

        span = trace.span("get_legal_brief", type="db_query")

        with span:
            span.set_attribute("application_id", application_id)

            start_ns = time.perf_counter_ns()
            result = self._raw_get_legal_brief(application_id)
            latency_ms = int((time.perf_counter_ns() - start_ns) / 1_000_000)

            span.set_attributes({
                "latency_ms": latency_ms,
                "found": result is not None,
            })

            return result

    def _raw_get_legal_brief(self, application_id: str) -> Optional[dict]:
        """Raw get_legal_brief without tracing."""
        response = (
            self._client.table("legal_briefs")
            .select("*")
            .eq("application_id", application_id)
            .order("generated_at", desc=True)
            .limit(1)
            .execute()
        )
        return response.data[0] if response.data else None

    def rpc(self, function_name: str, params: dict) -> Any:
        """
        Execute an RPC function with tracing.
        """
        trace = current_trace()

        if trace is None:
            return self._client.rpc(function_name, params).execute()

        span = trace.span(f"rpc_{function_name}", type="db_query")

        with span:
            span.set_attributes({
                "function": function_name,
                "param_keys": list(params.keys()),
            })

            start_ns = time.perf_counter_ns()
            result = self._client.rpc(function_name, params).execute()
            latency_ms = int((time.perf_counter_ns() - start_ns) / 1_000_000)

            span.set_attributes({
                "latency_ms": latency_ms,
                "result_count": len(result.data) if result.data else 0,
            })

            return result

    def table(self, table_name: str):
        """
        Access a table - returns a traced query builder.
        Note: For simplicity, table queries are not individually traced.
        Use explicit spans if needed.
        """
        return self._client.table(table_name)


def traced_tool_call(name: str):
    """
    Decorator to trace a tool/function call.

    Usage:
        @traced_tool_call("decompose")
        async def decompose(brief: str) -> dict:
            ...
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            trace = current_trace()
            if trace is None:
                return await func(*args, **kwargs)

            span = trace.span(name, type="tool_call")
            with span:
                span.event("tool_input", {
                    "args_count": len(args),
                    "kwargs_keys": list(kwargs.keys()),
                })

                start_ns = time.perf_counter_ns()
                result = await func(*args, **kwargs)
                latency_ms = int((time.perf_counter_ns() - start_ns) / 1_000_000)

                span.set_attribute("latency_ms", latency_ms)

                # Try to capture result size
                if isinstance(result, dict):
                    span.set_attribute("result_keys", list(result.keys()))
                elif isinstance(result, list):
                    span.set_attribute("result_count", len(result))

                return result

        return wrapper
    return decorator
