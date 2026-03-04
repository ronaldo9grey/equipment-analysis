import os
import uuid
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.core.config import settings

logger = logging.getLogger(__name__)

text_splitter = None
vectorstore = None


def _get_text_splitter():
    global text_splitter
    if text_splitter is None:
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
    return text_splitter


def _get_vectorstore():
    global vectorstore
    if vectorstore is None:
        try:
            from langchain_community.vectorstores import Chroma
            
            embeddings = None
            if settings.OPENAI_API_KEY:
                from langchain_openai import OpenAIEmbeddings
                embeddings = OpenAIEmbeddings(
                    model="text-embedding-3-small",
                    openai_api_key=settings.OPENAI_API_KEY
                )
                logger.info("知识库使用 OpenAI Embedding")
            elif settings.DEEPSEEK_API_KEY:
                # DeepSeek 不支持 embedding API，知识库功能不可用
                logger.info("DeepSeek 不支持 embedding API，知识库功能已禁用。请配置 OPENAI_API_KEY 以使用知识库功能。")
                return None
            else:
                logger.info("未配置 API Key，知识库功能不可用")
                return None
            
            vectorstore = Chroma(
                persist_directory=os.path.join(settings.BASE_DIR, "data", "knowledge_vectorstore"),
                embedding_function=embeddings
            )
            logger.info("知识库向量数据库初始化成功")
        except Exception as e:
            logger.error(f"知识库向量数据库初始化失败: {str(e)}")
    return vectorstore


class KnowledgeBaseManager:
    """知识库管理器"""

    def __init__(self):
        self.docs_dir = os.path.join(settings.BASE_DIR, "data", "knowledge_docs")
        os.makedirs(self.docs_dir, exist_ok=True)

    def _extract_text_from_pdf(self, file_path: str) -> str:
        """从 PDF 提取文本"""
        try:
            from pypdf import PdfReader
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
        vs = _get_vectorstore()
        if not vs:
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

            splitter = _get_text_splitter()
            chunks = splitter.split_text(text)
            
            from langchain_core.documents import Document
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

            vs.add_documents(documents)
            
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
        vs = _get_vectorstore()
        if not vs:
            return []

        try:
            docs = vs.get()
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
        vs = _get_vectorstore()
        if not vs:
            return {
                "success": False,
                "message": "知识库未初始化"
            }

        try:
            docs = vs.get()
            ids_to_delete = []
            
            for doc_id_item, metadata in zip(docs.get("ids", []), docs.get("metadatas", [])):
                if metadata.get("doc_id") == doc_id:
                    ids_to_delete.append(doc_id_item)

            if ids_to_delete:
                vs.delete(ids_to_delete)
                
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
