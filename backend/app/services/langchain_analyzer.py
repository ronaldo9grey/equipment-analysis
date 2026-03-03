from langchain_community.chat_models import ChatOpenAI, ChatOllama
from langchain.schema import HumanMessage, SystemMessage
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.chains import LLMChain
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.tools import Tool
from langchain.memory import ConversationBufferMemory
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from typing import Dict, Any, List, Optional
import json
import logging
from datetime import datetime

from app.core.config import settings

logger = logging.getLogger(__name__)


class RAGRetriever:
    """RAG 检索器 - 基于历史案例的知识检索"""

    def __init__(self):
        self.embeddings = None
        self.vectorstore = None
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
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
                    persist_directory="./data/vectorstore",
                    embedding_function=self.embeddings
                )
                logger.info("RAG 向量数据库初始化成功")
        except Exception as e:
            logger.error(f"RAG 向量数据库初始化失败: {str(e)}")

    def add_documents(self, texts: List[str], metadatas: List[Dict] = None):
        """添加文档到知识库"""
        if not self.vectorstore:
            logger.warning("向量数据库未初始化")
            return

        documents = [
            Document(page_content=text, metadata=metadata or {})
            for text, metadata in zip(texts, metadatas or [{}] * len(texts))
        ]

        self.vectorstore.add_documents(documents)
        logger.info(f"已添加 {len(texts)} 个文档到知识库")

    def retrieve(self, query: str, k: int = 3) -> List[Dict]:
        """检索相似文档"""
        if not self.vectorstore:
            return []

        try:
            results = self.vectorstore.similarity_search(query, k=k)
            return [
                {
                    "content": doc.page_content,
                    "metadata": doc.metadata
                }
                for doc in results
            ]
        except Exception as e:
            logger.error(f"检索失败: {str(e)}")
            return []

    def as_retriever(self, k: int = 3):
        """返回 LangChain 检索器"""
        if not self.vectorstore:
            return None
        return self.vectorstore.as_retriever(search_kwargs={"k": k})


class LangChainAnalyzer:
    """基于 LangChain 的 AI 分析器"""

    def __init__(self, use_local_model: bool = False):
        self.use_local_model = use_local_model
        self.rag = RAGRetriever()
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        self._init_llm()

    def _init_llm(self):
        """初始化 LLM"""
        try:
            if self.use_local_model:
                self.llm = ChatOllama(
                    base_url=settings.OLLAMA_BASE_URL or "http://localhost:11434",
                    model=settings.OLLAMA_MODEL or "qwen:7b",
                    temperature=0.7
                )
            else:
                self.llm = ChatOpenAI(
                    model=settings.DEEPSEEK_MODEL or "deepseek-chat",
                    temperature=0.7,
                    api_key=settings.DEEPSEEK_API_KEY,
                    base_url=settings.DEEPSEEK_API_URL or "https://api.deepseek.com"
                )
            logger.info(f"LangChain LLM 初始化成功: {'本地模型' if self.use_local_model else 'DeepSeek'}")
        except Exception as e:
            logger.error(f"LLM 初始化失败: {str(e)}")
            self.llm = None

    def analyze(
        self,
        data: Dict[str, Any],
        user_query: Optional[str] = None,
        analysis_type: str = "general"
    ) -> Dict[str, Any]:
        """执行分析（带 RAG 增强）"""
        if not self.llm:
            return {
                "status": "error",
                "message": "LLM 未初始化",
                "result": None
            }

        try:
            context = self._prepare_context(data, analysis_type)
            
            retrieved_context = ""
            if analysis_type == "table" or analysis_type == "general":
                query = f"分析 {data.get('file_name', '')} {data.get('table_name', '')}"
                docs = self.rag.retrieve(query, k=3)
                if docs:
                    retrieved_context = "\n\n## 相关历史案例:\n"
                    for i, doc in enumerate(docs, 1):
                        retrieved_context += f"\n【案例 {i}】:\n{doc['content'][:500]}\n"

            prompt = self._build_prompt(context, retrieved_context, user_query, analysis_type)

            messages = [
                SystemMessage(content="你是一位专业的设备数据分析专家，擅长分析设备运行数据并给出专业建议。"),
                HumanMessage(content=prompt)
            ]

            response = self.llm.invoke(messages)
            result_content = response.content if hasattr(response, 'content') else str(response)

            self._save_to_knowledge_base(data, result_content, analysis_type)

            return {
                "status": "success",
                "content": result_content,
                "timestamp": datetime.now().isoformat(),
                "analysis_type": analysis_type,
                "rag_used": bool(retrieved_context)
            }

        except Exception as e:
            logger.error(f"LangChain 分析失败: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "result": None
            }

    def _prepare_context(self, data: Dict[str, Any], analysis_type: str) -> str:
        """准备数据上下文"""
        if analysis_type == "table":
            table_data = data.get("data", [])
            context = {
                "file_name": data.get("file_name"),
                "table_name": data.get("table_name"),
                "row_count": data.get("row_count", 0),
                "columns": data.get("columns", []),
                "data_mode": data.get("data_mode", "采样"),
                "sample_data": table_data[:20] if table_data else []
            }
            return json.dumps(context, ensure_ascii=False, indent=2)

        tables_info = []
        for table in data.get("tables", []):
            tables_info.append({
                "table_name": table.get("table_name"),
                "row_count": table.get("row_count", 0),
                "columns": table.get("columns", [])[:20]
            })

        context = {
            "file_name": data.get("file_name"),
            "total_tables": len(tables_info),
            "total_records": data.get("total_records", 0),
            "tables": tables_info
        }
        return json.dumps(context, ensure_ascii=False, indent=2)

    def _build_prompt(
        self,
        context: str,
        retrieved_context: str,
        user_query: Optional[str],
        analysis_type: str
    ) -> str:
        """构建提示词"""
        prompt = f"""
## 数据概览
```json
{context}
```
{retrieved_context}
"""

        if analysis_type == "table":
            prompt += """
请对指定表进行详细数据分析：
1. 表结构分析：字段含义、类型、数据特征
2. 数据质量分析：缺失值、异常值、数据分布
3. 字段特征分析：各字段的值域范围、重复度、关键字段识别
4. 数据洞察：发现的问题、规律、建议

请用中文回答，分析要专业、详细，包含具体数据支撑。
"""
        else:
            prompt += """
请对以上设备运行数据进行全面分析：
1. 数据整体概况
2. 数据质量检查
3. 关键发现
4. 改进建议

请用中文回答，分析要专业、详细。
"""

        if user_query:
            prompt += f"\n\n用户额外问题: {user_query}"

        return prompt

    def _save_to_knowledge_base(
        self,
        data: Dict[str, Any],
        result: str,
        analysis_type: str
    ):
        """保存到知识库"""
        try:
            text = f"文件: {data.get('file_name', '')}"
            if data.get('table_name'):
                text += f", 表: {data.get('table_name')}"
            text += f"\n分析结果: {result[:1000]}"

            metadata = {
                "file_name": data.get("file_name", ""),
                "table_name": data.get("table_name", ""),
                "analysis_type": analysis_type,
                "timestamp": datetime.now().isoformat()
            }

            self.rag.add_documents([text], [metadata])
        except Exception as e:
            logger.error(f"保存到知识库失败: {str(e)}")


_analyzer: Optional[LangChainAnalyzer] = None


def get_langchain_analyzer(use_local_model: bool = False) -> LangChainAnalyzer:
    """获取 LangChain 分析器实例"""
    global _analyzer
    if _analyzer is None or _analyzer.use_local_model != use_local_model:
        _analyzer = LangChainAnalyzer(use_local_model)
    return _analyzer
