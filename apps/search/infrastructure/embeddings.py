from functools import cached_property

import openai
from langchain_openai import OpenAIEmbeddings
from langsmith import tracing_context

from apps.search.application.errors import SearchTimeout, SearchUnavailable


class LangChainEmbeddings:
    def __init__(self, config):
        self.config = config

    @cached_property
    def model(self):
        if self.config.spec.provider == "openai":
            if not self.config.api_key:
                raise SearchUnavailable("OPENAI_API_KEY ausente.")
            return OpenAIEmbeddings(
                model=self.config.spec.model, api_key=self.config.api_key,
                request_timeout=self.config.timeout, max_retries=0,
                # Avoid an implicit tiktoken download; input limits apply before invocation.
                check_embedding_ctx_length=False,
            )
        from langchain_huggingface import HuggingFaceEmbeddings

        kwargs = {"device": "cpu", "local_files_only": True}
        if self.config.spec.revision:
            kwargs["revision"] = self.config.spec.revision
        return HuggingFaceEmbeddings(model_name=self.config.spec.model, model_kwargs=kwargs)

    def invoke(self, method, value):
        try:
            with tracing_context(enabled=False):
                return getattr(self.model, method)(value)
        except openai.APITimeoutError as exc:
            raise SearchTimeout() from exc
        except (openai.APIError, OSError, ImportError, ValueError) as exc:
            raise SearchUnavailable("Embeddings indisponíveis.") from exc

    def embed_documents(self, texts):
        return self.invoke("embed_documents", texts)

    def embed_query(self, text):
        return self.invoke("embed_query", text)
