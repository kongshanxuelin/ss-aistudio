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
        self.temp_file_dir = temp_file_dir
        self.share_file_dir = share_file_dir
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
        return share_img_dir +"/"+ filename

    def process_images(self, content: str, md_file_path: Path) -> str:
        """处理内容中的base64图片"""
        pattern = r'!\[.*?\]\(data:image/(.*?);base64,(.*?)\)'
        
        def replace_match(match):
            alt_text = match.group(0).split(']')[0][2:]
            base64_str = match.group(2)
            local_path = self.save_base64_image(f"data:image/{match.group(1)};base64,{base64_str}", md_file_path)
            return f'![{alt_text}]({local_path})'
            
        return re.sub(pattern, replace_match, content)

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

        if self.remove_hyperlinks:
            content = self.remove_hyperlinks(content)

        if self.remove_images:
            content = self.remove_images(content)

        return self.markdown_to_tups(content)
    
if __name__ == "__main__":
    # share_file_dir = "http://192.168.10.171/files/"
    # temp_file_dir = "D:/desktop/work/remotepy/db_date/uploads/"
    # file_path = "D:\\desktop\\project\\video_exact\\sdp帮助\\编写触发器.md"
    # file_path = "D:\\desktop\\project\\video_exact\\md_process\\175.md"
    # loader = MarkdownLoader(file_path, encoding="utf-8", temp_file_dir=temp_file_dir, share_file_dir=share_file_dir)
    # docs = loader.load()
    # print(docs)
    pass