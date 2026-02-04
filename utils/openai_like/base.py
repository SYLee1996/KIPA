"""OpenAI embeddings file."""

from typing import Any, Dict, List, Optional

import httpx
from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core.bridge.pydantic import Field, PrivateAttr
from llama_index.core.callbacks.base import CallbackManager
from llama_index.embeddings.openai.utils import (
    DEFAULT_OPENAI_API_BASE,
    DEFAULT_OPENAI_API_VERSION,
    create_retry_decorator,
)

from llama_index.embeddings.openai.base import OpenAIEmbedding

from openai import AsyncOpenAI, OpenAI

embedding_retry_decorator = create_retry_decorator(
    max_retries=6,
    random_exponential=True,
    stop_after_delay_seconds=60,
    min_seconds=1,
    max_seconds=20,
)


@embedding_retry_decorator
def get_embedding(client: OpenAI, text: str, engine: str, **kwargs: Any) -> List[float]:
    """Get embedding.

    NOTE: Copied from OpenAI's embedding utils:
    https://github.com/openai/openai-python/blob/main/openai/embeddings_utils.py

    Copied here to avoid importing unnecessary dependencies
    like matplotlib, plotly, scipy, sklearn.

    """
    text = text.replace("\n", " ")

    return (
        client.embeddings.create(input=[text], model=engine, **kwargs).data[0].embedding
    )


@embedding_retry_decorator
async def aget_embedding(
    aclient: AsyncOpenAI, text: str, engine: str, **kwargs: Any
) -> List[float]:
    """Asynchronously get embedding.

    NOTE: Copied from OpenAI's embedding utils:
    https://github.com/openai/openai-python/blob/main/openai/embeddings_utils.py

    Copied here to avoid importing unnecessary dependencies
    like matplotlib, plotly, scipy, sklearn.

    """
    text = text.replace("\n", " ")

    return (
        (await aclient.embeddings.create(input=[text], model=engine, **kwargs))
        .data[0]
        .embedding
    )


@embedding_retry_decorator
def get_embeddings(
    client: OpenAI, list_of_text: List[str], engine: str, **kwargs: Any
) -> List[List[float]]:
    """Get embeddings.

    NOTE: Copied from OpenAI's embedding utils:
    https://github.com/openai/openai-python/blob/main/openai/embeddings_utils.py

    Copied here to avoid importing unnecessary dependencies
    like matplotlib, plotly, scipy, sklearn.

    """
    assert len(list_of_text) <= 2048, "The batch size should not be larger than 2048."

    list_of_text = [text.replace("\n", " ") for text in list_of_text]

    data = client.embeddings.create(input=list_of_text, model=engine, **kwargs).data
    return [d.embedding for d in data]


@embedding_retry_decorator
async def aget_embeddings(
    aclient: AsyncOpenAI,
    list_of_text: List[str],
    engine: str,
    **kwargs: Any,
) -> List[List[float]]:
    """Asynchronously get embeddings.

    NOTE: Copied from OpenAI's embedding utils:
    https://github.com/openai/openai-python/blob/main/openai/embeddings_utils.py

    Copied here to avoid importing unnecessary dependencies
    like matplotlib, plotly, scipy, sklearn.

    """
    assert len(list_of_text) <= 2048, "The batch size should not be larger than 2048."

    list_of_text = [text.replace("\n", " ") for text in list_of_text]

    data = (
        await aclient.embeddings.create(input=list_of_text, model=engine, **kwargs)
    ).data
    return [d.embedding for d in data]


class OpenAILikeEmbedding(OpenAIEmbedding):
    """OpenaAILike for embeddings.

    OpenAILike is a thin wrapper around the OpenAI embedding model that makes it compatible with
    3rd party tools that provide an openai-compatible api.

    Currently, llama_index prevents using custom models with their OpenAI class
    because they need to be able to infer some metadata from the model name.

    NOTE: You still need to set the OPENAI_BASE_API and OPENAI_API_KEY environment
    variables or the api_key and api_base constructor arguments.
    OPENAI_API_KEY/api_key can normally be set to anything in this case,
    but will depend on the tool you're using.

    Examples:
        `pip install llama-index-llms-openai-like`

        ```python
        from llama_index.embeddings.openai_like import OpenAILike

        llm = OpenAILike(model="my model", api_base="https://hostname.com/v1", api_key="fake")

        response = llm.get_text_embedding("Hello World!")
        print(str(response))
        ```
    """

    additional_kwargs: Dict[str, Any] = Field(
        default_factory=dict, description="Additional kwargs for the OpenAI API."
    )

    api_key: str = Field(description="The OpenAI API key.")
    api_base: Optional[str] = Field(
        default=DEFAULT_OPENAI_API_BASE, description="The base URL for OpenAI API."
    )
    api_version: Optional[str] = Field(
        default=DEFAULT_OPENAI_API_VERSION, description="The version for OpenAI API."
    )

    max_retries: int = Field(default=10, description="Maximum number of retries.", ge=0)
    timeout: float = Field(default=60.0, description="Timeout for each request.", ge=0)
    default_headers: Optional[Dict[str, str]] = Field(
        default=None, description="The default headers for API requests."
    )
    reuse_client: bool = Field(
        default=True,
        description=(
            "Reuse the OpenAI client between requests. When doing anything with large "
            "volumes of async API calls, setting this to false can improve stability."
        ),
    )
    dimensions: Optional[int] = Field(
        default=None,
        description=(
            "The number of dimensions on the output embedding vectors. "
            "Works only with v3 embedding models."
        ),
    )

    _query_engine: str = PrivateAttr()
    _text_engine: str = PrivateAttr()
    _client: Optional[OpenAI] = PrivateAttr()
    _aclient: Optional[AsyncOpenAI] = PrivateAttr()
    _http_client: Optional[httpx.Client] = PrivateAttr()
    _async_http_client: Optional[httpx.AsyncClient] = PrivateAttr()

    def __init__(
            self,
            model,
            embed_batch_size: int = 100,
            dimensions: Optional[int] = None,
            additional_kwargs: Optional[Dict[str, Any]] = None,
            api_key: Optional[str] = None,
            api_base: Optional[str] = None,
            api_version: Optional[str] = None,
            max_retries: int = 10,
            timeout: float = 60.0,
            reuse_client: bool = True,
            callback_manager: Optional[CallbackManager] = None,
            default_headers: Optional[Dict[str, str]] = None,
            http_client: Optional[httpx.Client] = None,
            async_http_client: Optional[httpx.AsyncClient] = None,
            num_workers: Optional[int] = None,
            **kwargs: Any,
    ) -> None:
        additional_kwargs = additional_kwargs or {}
        if dimensions is not None:
            additional_kwargs["dimensions"] = dimensions

        api_key, api_base, api_version = self._resolve_credentials(
            api_key=api_key,
            api_base=api_base,
            api_version=api_version,
        )

        query_engine = text_engine = model_name = model

        super().__init__(
            embed_batch_size=embed_batch_size,
            dimensions=dimensions,
            callback_manager=callback_manager,
            model_name=model_name,
            additional_kwargs=additional_kwargs,
            api_key=api_key,
            api_base=api_base,
            api_version=api_version,
            max_retries=max_retries,
            reuse_client=reuse_client,
            timeout=timeout,
            default_headers=default_headers,
            num_workers=num_workers,
            **kwargs,
        )
        self._query_engine = query_engine
        self._text_engine = text_engine

        self._client = None
        self._aclient = None
        self._http_client = http_client
        self._async_http_client = async_http_client

    @classmethod
    def class_name(cls) -> str:
        return "OpenAILikeEmbedding"

    def _get_query_embedding(self, query: str) -> List[float]:
        """Get query embedding."""
        client = self._get_client()
        return get_embedding(
            client,
            query,
            engine=self._query_engine,
            **self.additional_kwargs,
        )

    async def _aget_query_embedding(self, query: str) -> List[float]:
        """The asynchronous version of _get_query_embedding."""
        aclient = self._get_aclient()
        return await aget_embedding(
            aclient,
            query,
            engine=self._query_engine,
            **self.additional_kwargs,
        )

    def _get_text_embedding(self, text: str) -> List[float]:
        """Get text embedding."""
        client = self._get_client()
        return get_embedding(
            client,
            text,
            engine=self._text_engine,
            **self.additional_kwargs,
        )

    async def _aget_text_embedding(self, text: str) -> List[float]:
        """Asynchronously get text embedding."""
        aclient = self._get_aclient()
        return await aget_embedding(
            aclient,
            text,
            engine=self._text_engine,
            **self.additional_kwargs,
        )

    def _get_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get text embeddings.

        By default, this is a wrapper around _get_text_embedding.
        Can be overridden for batch queries.

        """
        client = self._get_client()
        return get_embeddings(
            client,
            texts,
            engine=self._text_engine,
            **self.additional_kwargs,
        )

    async def _aget_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Asynchronously get text embeddings."""
        aclient = self._get_aclient()
        return await aget_embeddings(
            aclient,
            texts,
            engine=self._text_engine,
            **self.additional_kwargs,
        )
