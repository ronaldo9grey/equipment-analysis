import os
import uuid
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from pypdf import PdfReader

from app.core.config import settings

logger = logging.getLogger(__name__)


class KnowledgeBaseManager:
    """知识库管理器"""

    def __init__(self):
        self.embeddings = None
        self.vectorstore = None
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        self.docs_dir = os.path.join(settings.BASE_DIR, "data", "knowledge_docs")
        os.makedirs(self.docs_dir, exist_ok=True)
        self._init_vectorstore()

    def _init_vectorstore(self):
        """初始化向量数据库"""
        try:
            if settings.OPENAI_API_KEY:
                self.embeddings = OpenAIEmbeddings(
                    model="text-embedding-3-small",
                    openai_api_key=settings.OPENAI_API_KEY
                )
                self.vectorstore = Chroma(
                    persist_directory=os.path.join(settings.BASE_DIR, "data", "knowledge_vectorstore"),
                    embedding_function=self.embeddings
                )
                logger.info("知识库向量数据库初始化成功")
        except Exception as e:
            logger.error(f"知识库向量数据库初始化失败: {str(e)}")

    def _extract_text_from_pdf(self, file_path: str) -> str:
        """从 PDF 提取文本"""
        try:
            reader = PdfReader(file_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text
        except Exception as e:
            logger.error(f"PDF 提取文本失败: {str(e)}")
            return ""

    def _extract_text_from_txt(self, file_path: str) -> str:
        """从 TXT 提取文本"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"TXT 读取失败: {str(e)}")
            return ""

    def add_document(self, file_content: bytes, file_name: str) -> Dict[str, Any]:
        """添加文档到知识库"""
        if not self.vectorstore:
            return {
                "success": False,
                "message": "知识库未初始化，请配置 OPENAI_API_KEY"
            }

        try:
            doc_id = str(uuid.uuid4())
            file_ext = os.path.splitext(file_name)[1].lower()
            file_path = os.path.join(self.docs_dir, f"{doc_id}_{file_name}")

            with open(file_path, 'wb') as f:
                f.write(file_content)

            if file_ext == '.pdf':
                text = self._extract_text_from_pdf(file_path)
            elif file_ext == '.txt':
                text = self._extract_text_from_txt(file_path)
            else:
                os.remove(file_path)
                return {
                    "success": False,
                    "message": f"不支持的文件类型: {file_ext}，仅支持 PDF 和 TXT"
                }

            if not text.strip():
                os.remove(file_path)
                return {
                    "success": False,
                    "message": "无法从文档中提取文本"
                }

            chunks = self.text_splitter.split_text(text)
            
            documents = [
                Document(
                    page_content=chunk,
                    metadata={
                        "doc_id": doc_id,
                        "file_name": file_name,
                        "chunk_index": i,
                        "added_at": datetime.now().isoformat()
                    }
                )
                for i, chunk in enumerate(chunks)
            ]

            self.vectorstore.add_documents(documents)
            
            logger.info(f"知识库添加文档成功: {file_name}, {len(chunks)} 个 chunks")

            return {
                "success": True,
                "doc_id": doc_id,
                "file_name": file_name,
                "chunks_count": len(chunks),
                "message": f"成功添加文档，包含 {len(chunks)} 个知识片段"
            }

        except Exception as e:
            logger.error(f"添加文档到知识库失败: {str(e)}")
            return {
                "success": False,
                "message": str(e)
            }

    def list_documents(self) -> List[Dict[str, Any]]:
        """列出知识库中的文档"""
        if not self.vectorstore:
            return []

        try:
            docs = self.vectorstore.get()
            doc_info = {}
            
            for doc_id, metadata in zip(docs.get("ids", []), docs.get("metadatas", [])):
                file_name = metadata.get("file_name", "未知")
                if file_name not in doc_info:
                    doc_info[file_name] = {
                        "doc_id": metadata.get("doc_id"),
                        "file_name": file_name,
                        "chunks_count": 0,
                        "added_at": metadata.get("added_at", "")
                    }
                doc_info[file_name]["chunks_count"] += 1

            return list(doc_info.values())
        except Exception as e:
            logger.error(f"获取知识库列表失败: {str(e)}")
            return []

    def delete_document(self, doc_id: str) -> Dict[str, Any]:
        """删除知识库中的文档"""
        if not self.vectorstore:
            return {
                "success": False,
                "message": "知识库未初始化"
            }

        try:
            docs = self.vectorstore.get()
            ids_to_delete = []
            
            for doc_id_item, metadata in zip(docs.get("ids", []), docs.get("metadatas", [])):
                if metadata.get("doc_id") == doc_id:
                    ids_to_delete.append(doc_id_item)

            if ids_to_delete:
                self.vectorstore.delete(ids_to_delete)
                
                for file_name in os.listdir(self.docs_dir):
                    if file_name.startswith(doc_id):
                        os.remove(os.path.join(self.docs_dir, file_name))
                        break

                logger.info(f"知识库删除文档成功: {doc_id}")
                return {
                    "success": True,
                    "message": "文档已从知识库中删除"
                }
            else:
                return {
                    "success": False,
                    "message": "文档不存在"
                }

        except Exception as e:
            logger.error(f"删除文档失败: {str(e)}")
            return {
                "success": False,
                "message": str(e)
            }


knowledge_manager = KnowledgeBaseManager()
