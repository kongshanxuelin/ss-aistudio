import os

from langchain_text_splitters.base import Language
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
print(base_dir)
import sys
sys.path.append(base_dir)

from langchain_community.document_loaders import (TextLoader, PDFPlumberLoader, PyMuPDFLoader, PyPDFLoader, CSVLoader, BSHTMLLoader, JSONLoader, UnstructuredMarkdownLoader,
    UnstructuredWordDocumentLoader,  # 新增docx支持
    UnstructuredPowerPointLoader,    # 新增pptx支持
    UnstructuredExcelLoader,         # 新增xlsx支持
    UnstructuredEPubLoader           # 新增epub支持
)
from src.processors.markdown import MarkdownLoader
from langchain_community.document_transformers import Html2TextTransformer
from langchain_text_splitters import NLTKTextSplitter, RecursiveCharacterTextSplitter, MarkdownTextSplitter, HTMLSectionSplitter, MarkdownHeaderTextSplitter

class LangChainFileProcessor:
    def __init__(self, chunk_size=512, overlap=64):
        # Initialize the text splitter from langchain
        # self._text_splitter = CharacterTextSplitter(chunk_size=chunk_size, overlap=overlap)
        self.chunk_size = chunk_size
        self.overlap = overlap
        self._text_splitter = RecursiveCharacterTextSplitter(chunk_size=self.chunk_size, chunk_overlap=self.overlap)

    def parse(self, file_path, file_type):
        # Load the document based on the file type
        try:
            if file_type == 'pdf':
                loader = PDFPlumberLoader(file_path)
                # loader = PyMuPDFLoader(file_path)
                # loader = PyPDFLoader(file_path)
                documents = loader.load()
            elif file_type == 'txt':
                loader = TextLoader(file_path, encoding="utf-8", autodetect_encoding=True)
                documents = loader.load()
            elif file_type == 'html':
                loader = BSHTMLLoader(file_path, open_encoding="utf-8")  # Use TextLoader for simplicity (alternative: BeautifulSoup)
                documents = Html2TextTransformer().transform_documents(loader.load())         # 转文本
            elif file_type == 'csv':
                loader = CSVLoader(file_path, encoding="utf-8", autodetect_encoding=True)
                documents = loader.load()
                self._text_splitter = RecursiveCharacterTextSplitter(separators=["\n\n", "\n"])
            elif file_type in ['markdown','md']:
                # loader = UnstructuredMarkdownLoader(file_path, encoding="utf-8", autodetect_encoding=True)

                cache_dir = os.path.dirname(file_path)
                temp_file_dir = os.path.join(cache_dir, "images")
                share_file_dir = "<cache_images_path>"

                os.makedirs(temp_file_dir, exist_ok=True)
                loader = MarkdownLoader(file_path, encoding="utf-8", autodetect_encoding=True, temp_file_dir=temp_file_dir, share_file_dir=share_file_dir)
                documents = loader.load()
                # self._text_splitter = MarkdownTextSplitter(chunk_size=self.chunk_size, chunk_overlap=self.overlap)
                self._text_splitter = RecursiveCharacterTextSplitter.from_language(language=Language.MARKDOWN, chunk_size=self.chunk_size, chunk_overlap=self.overlap)
            elif file_type in ['docx', 'doc']:
                loader = UnstructuredWordDocumentLoader(file_path, encoding="utf-8", mode="paged")
                documents = loader.load()
            elif file_type == 'pptx':
                loader = UnstructuredPowerPointLoader(file_path, encoding="utf-8", mode="paged")
                documents = loader.load()
            elif file_type in ['xlsx', 'xls']:
                loader = UnstructuredExcelLoader(file_path, encoding="utf-8", mode="elements")
                documents = loader.load()
                # self._text_splitter = RecursiveCharacterTextSplitter(separators=["\n\n", "\n", " "])
            elif file_type == 'epub':
                loader = UnstructuredEPubLoader(file_path)
                documents = loader.load()
            elif file_type == 'json':
                loader = JSONLoader(file_path, jq_schema='.[]', text_content=False)
                documents = loader.load()
            else:
                raise ValueError(f"Unsupported file type: {file_type}")

            # Split the document text using LangChain's TextSplitter
            text_chunks = self._text_splitter.split_documents(documents)
            if file_type in ['markdown', 'md']:
                # 获取纯文本内容
                raw_chunks = [chunk.page_content for chunk in text_chunks]
                # 智能还原
                restored_texts = loader.smart_restore_links(raw_chunks, chunk_overlap=32)
                # 将还原后的文本重新写入 chunk 对象中
                for chunk, restored_text in zip(text_chunks, restored_texts):
                    chunk.page_content = restored_text
                print("Markdown links restored successfully.")
            
            return text_chunks
        except Exception as e:
            print(f"An error occurred while processing the file: {e}")
            # return []
            raise e
    
    
    
if __name__ == "__main__":
    processor = LangChainFileProcessor()
    test_file_path = r"D:\desktop\work\localpy\test_file"
    pdf_file = os.path.join(test_file_path, "test.pdf")
    txt_file = os.path.join(test_file_path, "test.txt")
    html_file = os.path.join(test_file_path, "test.html")
    csv_file = os.path.join(test_file_path, "test.csv")
    md_file = os.path.join(test_file_path, "test.md")
    docx_file = os.path.join(test_file_path, "test.docx")
    pptx_file = os.path.join(test_file_path, "test.pptx")
    xlsx_file = os.path.join(test_file_path, "test.xlsx")
    epub_file = os.path.join(test_file_path, "test.epub")
    json_file = os.path.join(test_file_path, "test.json")
    
    test_params = [
        (pdf_file, 'pdf'), 
        # (txt_file, 'txt'), 
        # (html_file, 'html'),
        # (csv_file, 'csv'),
        # (md_file, 'markdown'),
        # (docx_file, 'docx'),
        # (pptx_file, 'pptx'),
        # (xlsx_file, 'xlsx'),
        # (epub_file, 'epub'),
        # (json_file, 'json')
    ]
    test_params = [(json_file, 'json'), (epub_file, 'epub')]
    test_params = [("C:\\Users\\junjie.ding\\Desktop\\面向WEB应用的智能化服务封装系统设计与实现.pdf", 'pdf')]
    success = 0
    for file_path, file_type in test_params:
        print(f"\n\n###############################\nProcessing file: {file_path}")
        chunks = processor.parse(file_path, file_type)
        print(f"Number of chunks: {len(chunks)}")
        print("\n--------------------------\n".join([chunk.page_content[:120]+"..." for chunk in chunks[:5]]))
        if len(chunks):
            success += 1
    print(f"Success: {success}/{len(test_params)}")