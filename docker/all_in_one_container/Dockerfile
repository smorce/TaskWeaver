FROM python:3.10-slim

RUN python3 -m pip install --upgrade pip

# weasyprint のために色々インストールした
RUN apt-get update && \
    apt-get install -y git build-essential libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Node.jsのインストール
RUN apt-get update && \
    apt-get install -y nodejs npm curl gnupg wget && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# npmが正しくインストールされているか確認
RUN node -v && npm -v

# marp-cliのグローバルインストール
RUN npm install -g @marp-team/marp-cli

# marp-cliを使うために Chrome のインストール
RUN wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    apt-get update && \
    apt-get install -y ./google-chrome-stable_current_amd64.deb && \
    apt-get -f install -y && \
    rm google-chrome-stable_current_amd64.deb && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# CHROME_PATH環境変数の設定
ENV CHROME_PATH=/usr/bin/google-chrome

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --no-warn-script-location --default-timeout=100 -r requirements.txt

RUN pip install --no-cache-dir --no-warn-script-location -U "chainlit<1.1.300"

# Define a build argument
ARG WITH_WEB_SEARCH=true

# Copy the model downloader script
COPY docker/all_in_one_container/model_downloader.py .
# Install the web search dependencies
RUN if [ "$WITH_WEB_SEARCH" = "true" ]; then \
    pip install --no-cache-dir --no-warn-script-location --default-timeout=1000 "duckduckgo_search>=6.1.5" \
    "beautifulsoup4" \
    "md2pdf" \
    "playwright" \
    "pydantic" \
    "python-multipart" \
    "markdown" \
    "tavily-python==0.3.3" \
    "arxiv" \
    "PyMuPDF" \
    "jinja2" \
    "aiofiles" \
    "newspaper3k" \
    "SQLAlchemy" \
    "mistune" \
    "python-docx" \
    "htmldocx" \
    "lxml[html_clean]" \
    "websockets" \
    "unstructured" \
    "weasyprint" \
    "json_repair"; \
    fi
RUN if [ "$WITH_WEB_SEARCH" = "true" ]; then \
    pip install --no-cache-dir --no-warn-script-location --default-timeout=1000 "json5" \
    "langchain>=0.2,<0.3" \
    "langchain_community>=0.2,<0.3" \
    "langchain-openai>=0.1,<0.2" \
    "langchain-groq>=0.1,<0.2" \
    "langchain_anthropic>=0.1,<0.2" \
    "langchain_huggingface>=0.0.1,<0.1" \
    "langchain_together>=0.1,<0.2" \
    "langchain_cohere" \
    "langgraph==0.1.4"; \
    fi
RUN if [ "$WITH_WEB_SEARCH" = "true" ]; then \
    pip install --no-cache-dir --no-warn-script-location "langchain_mistralai>=0.1,<0.2" \
    "langchain-google-genai>=1,<2" \
    "langchain_google_vertexai" \
    "langchain_fireworks" \
    "langchain_aws"; \
    fi
RUN if [ "$WITH_WEB_SEARCH" = "true" ]; then \
    pip install --no-cache-dir --no-warn-script-location "markdownify==0.12.1" \
    "torch==2.3.1" \
    "transformers==4.42.3"; \
    fi
RUN if [ "$WITH_WEB_SEARCH" = "true" ]; then \
    pip install --no-cache-dir --no-warn-script-location --default-timeout=1000 "sentence_transformers==3.0.1"; \
    fi
RUN if [ "$WITH_WEB_SEARCH" = "true" ]; then \
    python model_downloader.py; \
    fi

COPY taskweaver taskweaver
COPY project project
COPY docker/all_in_one_container/taskweaver_config.json project/taskweaver_config.json
COPY docker/all_in_one_container/entrypoint.sh entrypoint.sh
RUN chmod +x entrypoint.sh
COPY docker/all_in_one_container/entrypoint_chainlit.sh entrypoint_chainlit.sh
RUN chmod +x entrypoint_chainlit.sh
COPY playground playground

ENV EXECUTION_SERVICE_KERNEL_MODE="local"

# Install dependencies for different LLM models
RUN pip install --no-cache-dir --no-warn-script-location google-generativeai
RUN pip install --no-cache-dir --no-warn-script-location zhipuai
RUN pip install --no-cache-dir --no-warn-script-location dashscope

ENTRYPOINT ["/app/entrypoint.sh"]