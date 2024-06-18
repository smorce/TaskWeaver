# できたはず。model_name を変えれば簡単に切り替えられるはず
import os
from langchain_community.chat_models import ChatOpenAI  # これをラッピングして使う
from typing import Optional
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import (
    ChatPromptTemplate,
    FewShotChatMessagePromptTemplate,
)


try:
    OPENROUTER_API_KEY = os.environ["OPENROUTER_API_KEY"]
except:
    raise Exception(
        "OPENROUTER API key not found. Please set the OPENROUTER_API_KEY environment variable.")


# --------------------------------------------------
# ヘルパー関数
# --------------------------------------------------
def extract_braces_content(text):
    """余計な出力がくる場合があるのでJSONデータだけを取り出す"""
    # 文字列から最初の '{' を探す
    start_index = text.find('{')
    # '{' 以降の文字列を抽出
    remaining_text = text[start_index:]
    # 抽出した文字列から最後の '}' の位置を探す
    end_index = remaining_text.rfind('}')
    # '{' から最後の '}' までの文字列を返す
    return remaining_text[:end_index+1]


# --------------------------------------------------
# プロンプト
# --------------------------------------------------
template = """<|user|>
{input}<|end|>
<|assistant|>\n"""


# --------------------------------------------------
# Few-shotプロンプト の作成
# --------------------------------------------------
FewShotBasePrompt = ""

# いじるのはココ
examples = [
    {"input": "Can you provide ways to eat combinations of bananas and dragonfruits?", "output": "Sure! Here are some ways to eat bananas and dragonfruits together: 1. Banana and dragonfruit smoothie: Blend bananas and dragonfruits together with some milk and honey. 2. Banana and dragonfruit salad: Mix sliced bananas and dragonfruits together with some lemon juice and honey."},
    {"input": "What about solving an 2x + 3 = 7 equation?", "output": "To solve the equation 2x + 3 = 7, you need to isolate the variable x. Here are the steps:\n\n1. Subtract 3 from both sides of the equation to get: 2x = 4.\n2. Divide both sides of the equation by 2 to solve for x: x = 2.\n\nSo, the solution to the equation 2x + 3 = 7 is x = 2."},
]

for ex in examples:
    # print("<|user|>\n" + ex["input"] + "<|end|>")
    # print("<|assistant|>\n" + ex["output"] + "<|end|>")
    FewShotBasePrompt += "<|user|>\n" + ex["input"] + "<|end|>\n" + "<|assistant|>\n" + ex["output"] + "<|end|>\n"

FewShotPromptTemplate = FewShotBasePrompt + template
# --------------------------------------------------



class OpenRouterProvider(ChatOpenAI):
    openai_api_base: str
    openai_api_key: str
    model_name: str

    def __init__(
        self,
        model_name,
        temperature,
        max_tokens,
        openai_api_key: Optional[str] = None,
        openai_api_base: str = "https://openrouter.ai/api/v1",   # これが base_url
        model_kwargs: Optional[dict] = None,
        **kwargs
    ):
        # 指定がなければ Free の phi-3-mini を使う
        self.model_name = model_name if model_name is not None else "microsoft/phi-3-mini-128k-instruct:free"
        self.temperature = temperature
        self.max_tokens = max_tokens
        # self.base_url = self.get_base_url()
        self.llm = self.get_llm_model()
        openai_api_key = openai_api_key or OPENROUTER_API_KEY
        model_kwargs = model_kwargs or {}

        super().__init__(openai_api_base=openai_api_base,
                         openai_api_key=openai_api_key,
                         model_name=model_name,
                         model_kwargs=model_kwargs,
                         **kwargs)


    # def get_base_url(self):
    #     """
    #     Gets the Ollama Base URL from the environment variable if defined otherwise use the default one
    #     Returns:

    #     """
    #     base_url = os.environ.get("OLLAMA_BASE_URL", None)
    #     return base_url


    def get_llm_model(self):
        # Initializing the chat model

        params = {
            "top_p": 0.95,
            "presence_penalty": 1.1,       # repetition_penalty の代わり
        }

        kwargs = {
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            # "top_k": 40,                 # SDK にはない
            "streaming": True,             # stream ではない。また、ストリーミングしない場合でも True のままで問題ない
        }

        # llm = ChatOllama(
        #     model=self.model_name,
        #     temperature=self.temperature,
        #     keep_alive=None
        # )
        # if self.base_url:
        #     llm.base_url = self.base_url
        chat = ChatOpenRouter(
            model_name=self.model_name,
            model_kwargs=params,
            **kwargs
        )

        prompt = ChatPromptTemplate.from_template(template)
        fewshotprompt = ChatPromptTemplate.from_template(FewShotPromptTemplate)

        chain = prompt | chat | StrOutputParser()
        fewshotchain = fewshotprompt | chat | StrOutputParser()

        # return llm
        # chain を返すように変更
        return chain


    async def get_chat_response(self, messages, stream, websocket=None):
        # if not stream:
        #     # Getting output from the model chain using ainvoke for asynchronous invoking
        #     output = await self.llm.ainvoke(messages)

        #     return output.content

        # else:
        #     return await self.stream_response(messages, websocket)
        
        
        if not stream:
            # Phi 用にプロンプトテンプレートを指定しているので input に入れるように変更
            output = await self.llm.ainvoke({"input": messages})

            return output

        else:
            return await self.stream_response(messages, websocket)




    async def stream_response(self, messages, websocket=None):
        paragraph = ""
        response = ""

        # # Streaming the response using the chain astream method from langchain
        # async for chunk in self.llm.astream(messages):
        #     content = chunk.content
        #     if content is not None:
        #         response += content
        #         paragraph += content
        #         if "\n" in paragraph:
        #             if websocket is not None:
        #                 await websocket.send_json({"type": "report", "output": paragraph})
        #             else:
        #                 print(f"{Fore.GREEN}{paragraph}{Style.RESET_ALL}")
        #             paragraph = ""

        # return response


        # Phi 用にプロンプトテンプレートを指定しているので input に入れるように変更
        async for content in self.llm.astream({"input": messages}):
            # content = chunk.content ← StrOutputParser() を使っているので不要
            if content is not None:
                response += content
                paragraph += content
                if "\n" in paragraph:
                    if websocket is not None:
                        await websocket.send_json({"type": "report", "output": paragraph})
                    else:
                        print(f"{Fore.GREEN}{paragraph}{Style.RESET_ALL}")
                    paragraph = ""

        return response
