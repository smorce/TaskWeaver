from langchain_community.vectorstores import FAISS
import os


class Memory:
    def __init__(self, embedding_provider, **kwargs):

        _embeddings = None
        match embedding_provider:
            case "ollama":
                from langchain.embeddings import OllamaEmbeddings
                _embeddings = OllamaEmbeddings(model="llama2")
            case "openai":
                from langchain_openai import OpenAIEmbeddings
                _embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
            case "azureopenai":
                from langchain_openai import AzureOpenAIEmbeddings
                _embeddings = AzureOpenAIEmbeddings(deployment=os.environ["AZURE_EMBEDDING_MODEL"], chunk_size=16)
            case "huggingface":
                from langchain_community.embeddings import HuggingFaceEmbeddings
                # model_name = "intfloat/multilingual-e5-large"  # 2.24 GBは重いので一旦なし
                # model_name = "intfloat/multilingual-e5-base"     # 1.1 GB で次に重いサイズ。一番軽いのは「intfloat/multilingual-e5-small」
                model_name = "intfloat/multilingual-e5-small"
                _embeddings = HuggingFaceEmbeddings(model_name=model_name)

            case _:
                raise Exception("Embedding provider not found.")

        self._embeddings = _embeddings

    def get_embeddings(self):
        return self._embeddings
