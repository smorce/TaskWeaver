import subprocess
import aiofiles
import urllib
import uuid
import mistune
from md2pdf.core import md2pdf
from docx import Document
from htmldocx import HtmlToDocx


async def write_to_file(filename: str, text: str) -> None:
    """Asynchronously write text to a file in UTF-8 encoding.

    Args:
        filename (str): The filename to write to.
        text (str): The text to write.
    """
    # Convert text to UTF-8, replacing any problematic characters
    text_utf8 = text.encode('utf-8', errors='replace').decode('utf-8')

    async with aiofiles.open(filename, "w", encoding='utf-8') as file:
        await file.write(text_utf8)


async def write_text_to_md(text: str, path: str) -> str:
    """Writes text to a Markdown file and returns the file path.

    Args:
        text (str): Text to write to the Markdown file.

    Returns:
        str: The file path of the generated Markdown file.
    """
    task = uuid.uuid4().hex
    file_path = f"{path}/{task}.md"
    await write_to_file(file_path, text)
    print(f"Report written to {file_path}")
    return file_path


async def write_md_to_pdf(text: str, path: str) -> str:
    """Converts Markdown text to a PDF file and returns the file path.

    Args:
        text (str): Markdown text to convert.

    Returns:
        str: The encoded file path of the generated PDF.
    """
    task = uuid.uuid4().hex
    file_path = f"{path}/{task}.pdf"

    try:
        md2pdf(file_path,
               md_content=text,
               # md_file_path=f"{file_path}.md",
               css_file_path="./agents/utils/pdf_styles.css",
               base_url=None)
        print(f"Report written to {file_path}")
    except Exception as e:
        print(f"Error in converting Markdown to PDF: {e}")
        return ""

    encoded_file_path = urllib.parse.quote(file_path)
    return encoded_file_path


async def write_md_to_word(text: str, path: str) -> str:
    """Converts Markdown text to a DOCX file and returns the file path.

    Args:
        text (str): Markdown text to convert.

    Returns:
        str: The encoded file path of the generated DOCX.
    """
    task = uuid.uuid4().hex
    file_path = f"{path}/{task}.docx"

    try:
        # Convert report markdown to HTML
        html = mistune.html(text)
        # Create a document object
        doc = Document()
        # Convert the html generated from the report to document format
        HtmlToDocx().add_html_to_document(html, doc)

        # Saving the docx document to file_path
        doc.save(file_path)

        print(f"Report written to {file_path}")

        encoded_file_path = urllib.parse.quote(f"{file_path}.docx")
        return encoded_file_path

    except Exception as e:
        print(f"Error in converting Markdown to DOCX: {e}")
        return ""


async def write_md_to_ppt(text: str, path: str) -> str:
    """Converts Markdown text to a PPTX file and returns the file path.

    Args:
        text (str): Markdown text to convert.

    Returns:
        str: The encoded file path of the generated PPTX.

    ★Marpに変換するためのプロンプト。LLMで変換が必要なら参考にする
        https://zenn.dev/yuarth/articles/2d0c77bef9791a
    
    ★PCに以下をインストールしておく(グローバルインストール)
        npm install -g @marp-team/marp-cli
    """
    task = uuid.uuid4().hex
    file_path = f"{path}/{task}.pptx"


    def generate_slides(markdown_content, output_path):
        """
        Marp CLIを使用してMarkdownファイルからスライドを生成する。

        Args:
            markdown_content (str): Markdown形式のテキスト。
            output_path (str): 生成されるスライドの出力ファイルのパス。
        """
        try:
            # 一時ファイルを作成
            # ファイルの内容を直接渡してプレゼンテーションを作成する機能は、Marp CLI自体には組み込まれていません。そのため、直接ファイルの中身を渡してプレゼンテーションを生成するには、一時ファイルを作成し、そのファイルパスをMarpに渡す方法を使用する必要があります。
            with tempfile.NamedTemporaryFile(delete=False, suffix=".md") as tmp:
                tmp_path = tmp.name
                tmp.write(markdown_content.encode('utf-8'))
                tmp.close()
            
                # Marp CLIを呼び出してpptxを生成
                command = ['marp', tmp_path, '-o', output_path]
                # subprocess.run を使用してコマンドを実行
                subprocess.run(command, check=True)
                # 一時ファイルを削除
                os.unlink(tmp_path)
                print(f"Slide generated successfully: {output_path}")
        
        except subprocess.CalledProcessError as e:
            print(f"Failed to generate slides: {e}")

    try:
        
        generate_slides(text, file_path)

        print(f"Report written to {file_path}")

        encoded_file_path = urllib.parse.quote(f"{file_path}.pptx")
        return encoded_file_path

    except Exception as e:
        print(f"Error in converting Markdown to PPTX: {e}")
        return ""
