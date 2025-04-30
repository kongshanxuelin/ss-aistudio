import logging
from pathlib import Path
from typing import Iterator, List, Optional, Tuple, Union, cast
import re
from langchain_core.documents import Document
import base64
import os
import uuid
from langchain_community.document_loaders.base import BaseLoader
from langchain_community.document_loaders.helpers import detect_file_encodings
from langchain_text_splitters import Language, MarkdownTextSplitter, RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)


class MarkdownLoader(BaseLoader):
    """Load Markdown files.

    Args:
        file_path: Path to the file to load.
        remove_hyperlinks: Whether to remove hyperlinks from the content.
        remove_images: Whether to remove images from the content.
        encoding: File encoding to use. If `None`, the file will be loaded
            with the default system encoding.
        autodetect_encoding: Whether to try to autodetect the file encoding
            if the specified encoding fails.
    """

    def __init__(
        self,
        file_path: Union[str, Path],
        remove_hyperlinks: bool = False,
        remove_images: bool = False,
        encoding: Optional[str] = None,
        autodetect_encoding: bool = False,
        temp_file_dir: Optional[str] = os.path.join(os.path.dirname(__file__), "temp_images_files"),
        share_file_dir: Optional[str] = os.path.join(os.path.dirname(__file__), "share_images_files")
    ):
        """Initialize with file path."""
        self.file_path = Path(file_path)
        self.remove_hyperlinks = remove_hyperlinks
        self.remove_images = remove_images
        self.encoding = encoding
        self.autodetect_encoding = autodetect_encoding
        self.temp_file_dir = temp_file_dir          # 临时图片真实保存目录
        self.share_file_dir = share_file_dir        # 数据库中保存时显示目录，后续要替换成真实路径
        self.image_links = {}  # e.g., {"__IMG_0__": "![desc](path)"}
        self.hyper_links = {}  # e.g., {"__LINK_1__": "[desc](url)"}

    def extract_and_replace_links(self, content: str) -> str:
        """提取并替换图片和超链接为占位符"""
        def replace_img(match):
            key = f"__IMG_{len(self.image_links)}__"
            self.image_links[key] = match.group(0)
            return key
        
        def replace_link(match):
            key = f"__LINK_{len(self.hyper_links)}__"
            self.hyper_links[key] = match.group(0)
            return key
        
        # 图片: ![alt](url)
        content = re.sub(r'!\[.*?\]\(.*?\)', replace_img, content)
        # 超链接: [text](url)
        content = re.sub(r'(?<!!)\[[^\]]*?\]\([^\)]*?\)', replace_link, content)
        return content
    
    def lazy_load(self) -> Iterator[Document]:
        """Lazily load the markdown file and yield Documents."""
        tups = self.parse_tups(self.file_path)

        for header, value in tups:
            value = value.strip()
            metadata = {"source": str(self.file_path)}
            if header is not None:
                page_content = f"\n\n{header}\n{value}"
            else:
                page_content = value
            yield Document(page_content=page_content, metadata=metadata)

    def markdown_to_tups(self, markdown_text: str) -> List[Tuple[Optional[str], str]]:
        """Convert a markdown file to a list of tuples.

        The first element of each tuple is the header (if any), and the second
        element is the text under that header.
        """
        markdown_tups: List[Tuple[Optional[str], str]] = []
        lines = markdown_text.split("\n")

        current_header = None
        current_text = ""
        code_block_flag = False

        for line in lines:
            if line.startswith("```"):
                code_block_flag = not code_block_flag
                current_text += line + "\n"
                continue
            if code_block_flag:
                current_text += line + "\n"
                continue

            header_match = re.match(r"^#+\s", line)
            if header_match:
                if current_header is not None:
                    markdown_tups.append((current_header, current_text))

                current_header = line
                current_text = ""
            else:
                current_text += line + "\n"

        markdown_tups.append((current_header, current_text))

        # Clean up headers and values
        markdown_tups = [
            (
                re.sub(r"#", "", cast(str, key)).strip() if key else None,
                re.sub(r"<.*?>", "", value),
            )
            for key, value in markdown_tups
        ]

        return markdown_tups

    def remove_images(self, content: str) -> str:
        """Remove images from markdown content."""
        pattern = r"!{1}$\[(.*)$\]"
        return re.sub(pattern, "", content)

    def remove_hyperlinks(self, content: str) -> str:
        """Remove hyperlinks from markdown content."""
        pattern = r"$(.*?)$$(.*?)$"
        return re.sub(pattern, r"\1", content)
    
    def save_base64_image(self, base64_str: str, md_file_path: Path) -> str:
        """保存base64图片到本地并返回相对路径"""
        # 创建图片保存目录
        local_img_dir = os.path.join(self.temp_file_dir, os.path.basename(md_file_path).split('.')[0])
        share_img_dir = os.path.join(self.share_file_dir , os.path.basename(md_file_path).split('.')[0])
        os.makedirs(local_img_dir, exist_ok=True)
        local_img_dir = Path(local_img_dir)
        share_img_dir = Path(share_img_dir)
        
        # 解析base64数据
        try:
            header, data = base64_str.split(",", 1)
            img_format = header.split("/")[1].split(";")[0]
            img_data = base64.b64decode(data)
        except Exception as e:
            logger.warning(f"Invalid base64 image: {e}")
            return base64_str
            
        # 生成唯一文件名并保存
        filename = f"{uuid.uuid4().hex}.{img_format}"
        img_path = local_img_dir / filename
        with open(img_path, "wb") as f:
            f.write(img_data)
            
        # 返回相对路径
        # return f"images/{filename}"
        return (share_img_dir / filename).as_posix()
        # return os.path.join(share_img_dir,filename)

    def process_images(self, content: str, md_file_path: Path) -> str:
        """处理内容中的base64图片"""
        pattern = r'!\[.*?\]\(data:image/(.*?);base64,(.*?)\)'
        
        def replace_match(match):
            alt_text = match.group(0).split(']')[0][2:]
            base64_str = match.group(2)
            local_path = self.save_base64_image(f"data:image/{match.group(1)};base64,{base64_str}", md_file_path)
            return f'![{alt_text}]({local_path})'
            
        return re.sub(pattern, replace_match, content)
    
    def smart_restore_links(self, chunks: List[str], chunk_overlap: int = 32) -> List[str]:
        """智能还原链接，避免出现在开头"""
        restored_chunks = []
        
        for i, chunk in enumerate(chunks):
            original_chunk = chunk
            modified_chunk = chunk
            moved = False

            for key, val in {**self.image_links, **self.hyper_links}.items():
                if modified_chunk.startswith(key):
                    prev_chunk = restored_chunks[i - 1] if i > 0 else None

                    if prev_chunk and val in prev_chunk:
                        # 保留当前开头占位符，同时拼接前一个 chunk 的结尾
                        ind = prev_chunk.rfind(val)
                        overlap_text = prev_chunk[ind-chunk_overlap:ind]
                        modified_chunk = overlap_text + modified_chunk
                    elif prev_chunk:
                        # 把占位符放回上一段，并删除当前段开头的占位符
                        restored_chunks[i - 1] = prev_chunk + " " + val
                        modified_chunk = val + modified_chunk[len(key):]  # 去除占位符
                        overlap_text = prev_chunk[-chunk_overlap:]
                        modified_chunk = overlap_text + modified_chunk
                        moved = True
                    else:
                        # 第一段就是占位符开头，无法挪动，只能保留
                        modified_chunk = modified_chunk.replace(key, val)
                else:
                    modified_chunk = modified_chunk.replace(key, val)

            if not moved:
                # 如果没有发生移动，我们把当前所有占位符还原
                for key, val in {**self.image_links, **self.hyper_links}.items():
                    modified_chunk = modified_chunk.replace(key, val)

            restored_chunks.append(modified_chunk)

        return restored_chunks

    def parse_tups(self, filepath: Union[str, Path]) -> List[Tuple[Optional[str], str]]:
        """Parse file into tuples."""
        content = ""
        try:
            content = Path(filepath).read_text(encoding=self.encoding)
        except UnicodeDecodeError as e:
            if self.autodetect_encoding:
                detected_encodings = detect_file_encodings(filepath)
                for encoding in detected_encodings:
                    logger.debug(f"Trying encoding: {encoding.encoding}")
                    try:
                        content = Path(filepath).read_text(encoding=encoding.encoding)
                        break
                    except UnicodeDecodeError:
                        continue
            else:
                raise RuntimeError(f"Error loading {filepath}") from e
        except Exception as e:
            raise RuntimeError(f"Error loading {filepath}") from e

        # 先处理图片再执行其他操作
        content = self.process_images(content, Path(filepath))
        # 替换为占位符
        content = self.extract_and_replace_links(content)

        if self.remove_hyperlinks:
            content = self.remove_hyperlinks(content)

        if self.remove_images:
            content = self.remove_images(content)

        return self.markdown_to_tups(content)
    
if __name__ == "__main__":
    pass
    # share_file_dir = "http://192.168.10.171/files/"
    # temp_file_dir = "D:/desktop/work/remotepy/db_date/uploads/"
    # file_path = "D:\\desktop\\project\\video_exact\\sdp帮助\\编写触发器.md"
    # file_path = "D:\\desktop\\project\\video_exact\\md_process\\175.md"
    # file_path = "D:\\desktop\\work\\remotepy\\test_file\\sdp帮助\\首页DIY.md"
    # loader = MarkdownLoader(file_path, encoding="utf-8", temp_file_dir=temp_file_dir, share_file_dir=share_file_dir)
    # docs = loader.load()
    # print(len(docs))
    # for doc in docs:
    #     print(doc)
    # # print(docs)
    # print("---------------------")
    # text_splitter = MarkdownTextSplitter(chunk_size=256, chunk_overlap=32)
    # # text_splitter = RecursiveCharacterTextSplitter.from_language(language=Language.MARKDOWN, chunk_size=256, chunk_overlap=32)
    # text_chunks = text_splitter.split_documents(docs)
    
    # # 获取纯文本内容
    # raw_chunks = [chunk.page_content for chunk in text_chunks]

    # # 智能还原
    # restored_texts = loader.smart_restore_links(raw_chunks, chunk_overlap=32)
    # # 将还原后的文本重新写入 chunk 对象中
    # for chunk, restored_text in zip(text_chunks, restored_texts):
    #     chunk.page_content = restored_text
    # # 还原链接
    # # restored_chunks = []
    # for chunk in text_chunks:
    #     print(chunk)
    #     print("#######")