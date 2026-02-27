import requests
import json
import pandas as pd
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class AIAnalyzer:
    """AI分析器 - 支持DeepSeek和本地Ollama模型"""

    def __init__(self, use_local_model: bool = False):
        self.use_local_model = use_local_model
        self.deepseek_api_key = settings.DEEPSEEK_API_KEY
        self.deepseek_api_url = settings.DEEPSEEK_API_URL
        self.deepseek_model = settings.DEEPSEEK_MODEL
        self.ollama_base_url = settings.OLLAMA_BASE_URL
        self.ollama_model = settings.OLLAMA_MODEL

    def analyze(
        self,
        data: Dict[str, Any],
        user_query: Optional[str] = None,
        analysis_type: str = "general"
    ) -> Dict[str, Any]:
        """
        执行AI分析

        Args:
            data: 解析后的数据
            user_query: 用户自定义查询
            analysis_type: 分析类型 (general/anomaly/trend/report)
        """
        try:
            if self.use_local_model:
                return self._analyze_with_ollama(data, user_query, analysis_type)
            else:
                return self._analyze_with_deepseek(data, user_query, analysis_type)

        except Exception as e:
            logger.error(f"AI分析失败: {str(e)}")
            return {
                "status": "error",
                "message": f"AI分析失败: {str(e)}",
                "result": None
            }

    def _prepare_context(self, data: Dict[str, Any]) -> str:
        """准备分析上下文"""
        tables_info = []

        for table in data.get("tables", []):
            table_summary = {
                "table_name": table.get("table_name"),
                "row_count": table.get("row_count", 0),
                "columns": table.get("columns", [])[:20]
            }
            tables_info.append(table_summary)

        context = {
            "file_name": data.get("file_name"),
            "total_tables": len(tables_info),
            "total_records": data.get("total_records", 0),
            "tables": tables_info
        }

        return json.dumps(context, ensure_ascii=False, indent=2)

    def _build_prompt(
        self,
        data: Dict[str, Any],
        user_query: Optional[str],
        analysis_type: str
    ) -> str:
        """构建分析提示词"""
        context = self._prepare_context(data)

        base_prompt = f"""
## 数据概览
```json
{context}
```

## 分析要求
"""

        if analysis_type == "general":
            base_prompt += """
请对以上设备运行数据进行全面分析：
1. 数据整体概况：有多少张表、总记录数、涉及哪些业务领域
2. 数据质量检查：是否有缺失值、异常值、数据类型问题
3. 关键发现：有哪些值得关注的规律或问题
4. 建议：基于数据给出改进建议

请用中文回答，分析要专业、详细、有参考价值。
"""
        elif analysis_type == "anomaly":
            base_prompt += """
请对以上设备运行数据进行异常检测分析：
1. 识别潜在的数据异常（如：极端值、缺失率高的字段、异常时间戳等）
2. 分析可能的异常原因
3. 给出异常预警建议

请用中文回答，重点关注异常点。
"""
        elif analysis_type == "trend":
            base_prompt += """
请对以上设备运行数据进行趋势分析：
1. 识别时间相关字段，分析时间趋势
2. 分析关键指标的变化趋势
3. 预测未来走势

请用中文回答，关注趋势和预测。
"""
        elif analysis_type == "report":
            base_prompt += """
请生成一份完整的设备运行数据分析报告：
1. 摘要
2. 数据概况
3. 详细分析
4. 问题诊断
5. 改进建议
6. 总结

请用中文生成正式的分析报告格式。
"""
        else:
            base_prompt += f"""
请根据以下问题进行分析：
{user_query}

请用中文回答。
"""

        if user_query and analysis_type == "general":
            base_prompt += f"\n\n## 用户自定义问题\n{user_query}"

        return base_prompt

    def _call_deepseek(self, prompt: str) -> str:
        """调用DeepSeek API"""
        if not self.deepseek_api_key:
            raise Exception("DeepSeek API Key未配置")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.deepseek_api_key}"
        }

        payload = {
            "model": self.deepseek_model,
            "messages": [
                {
                    "role": "system",
                    "content": "你是一位资深的设备数据分析专家，擅长从设备运行数据中发现问题、分析趋势、提供优化建议。请用中文回答问题。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7,
            "max_tokens": 4096
        }

        response = requests.post(
            self.deepseek_api_url,
            headers=headers,
            json=payload,
            timeout=120
        )

        if response.status_code != 200:
            raise Exception(f"DeepSeek API调用失败: {response.text}")

        result = response.json()
        return result["choices"][0]["message"]["content"]

    def _call_ollama(self, prompt: str) -> str:
        """调用本地Ollama模型"""
        url = f"{self.ollama_base_url}/api/generate"

        payload = {
            "model": self.ollama_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "num_predict": 4096
            }
        }

        response = requests.post(url, json=payload, timeout=300)

        if response.status_code != 200:
            raise Exception(f"Ollama API调用失败: {response.text}")

        result = response.json()
        return result.get("response", "")

    def _analyze_with_deepseek(
        self,
        data: Dict[str, Any],
        user_query: Optional[str],
        analysis_type: str
    ) -> Dict[str, Any]:
        """使用DeepSeek进行分析"""
        try:
            prompt = self._build_prompt(data, user_query, analysis_type)
            result = self._call_deepseek(prompt)

            return {
                "status": "success",
                "message": "分析完成",
                "model": "deepseek",
                "result": {
                    "analysis_type": analysis_type,
                    "content": result,
                    "timestamp": datetime.now().isoformat()
                }
            }

        except Exception as e:
            logger.error(f"DeepSeek分析失败: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "model": "deepseek",
                "result": None
            }

    def _analyze_with_ollama(
        self,
        data: Dict[str, Any],
        user_query: Optional[str],
        analysis_type: str
    ) -> Dict[str, Any]:
        """使用本地Ollama进行分析"""
        try:
            prompt = self._build_prompt(data, user_query, analysis_type)
            result = self._call_ollama(prompt)

            return {
                "status": "success",
                "message": "分析完成",
                "model": "ollama",
                "result": {
                    "analysis_type": analysis_type,
                    "content": result,
                    "timestamp": datetime.now().isoformat()
                }
            }

        except Exception as e:
            logger.error(f"Ollama分析失败: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "model": "ollama",
                "result": None
            }

    def quick_summary(self, data: Dict[str, Any]) -> str:
        """快速摘要"""
        summary = f"""
文件: {data.get('file_name')}
表数量: {len(data.get('tables', []))}
总记录数: {data.get('total_records', 0)}

表结构:
"""
        for table in data.get("tables", [])[:10]:
            summary += f"- {table.get('table_name')}: {table.get('row_count')} 行, {len(table.get('columns', []))} 列\n"

        return summary


def get_analyzer(use_local_model: bool = False) -> AIAnalyzer:
    """获取AI分析器实例"""
    if use_local_model or settings.USE_LOCAL_MODEL:
        return AIAnalyzer(use_local_model=True)
    return AIAnalyzer(use_local_model=False)
