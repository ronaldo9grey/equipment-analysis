# rectifier_analysis_actual.ipynb
import pandas as pd
import subprocess
import json
import requests
import os
from datetime import datetime

class RectifierAnalyzer:
    def __init__(self):
        # 你的实际文件路径
        self.mdb_path = "/home/aiadmin/industrial-llm/data/元件温度.mdb"
        self.ollama_url = "http://localhost:11434/api/generate"
        self.model = "qwen2.5:32b"
        
        # 验证文件存在
        if not os.path.exists(self.mdb_path):
            raise FileNotFoundError(f"找不到文件: {self.mdb_path}")
        print(f"✓ 已加载数据库: {self.mdb_path}")
        
        # 列出所有表（处理中文表名）
        self.tables = self._list_tables()
        print(f"✓ 发现数据表: {self.tables}")
    
    def _list_tables(self):
        """获取所有表名（自动处理中文编码）"""
        try:
            result = subprocess.run(
                ['mdb-tables', '-1', self.mdb_path], 
                capture_output=True
            )
            # 尝试多种编码解码
            for encoding in ['utf-8', 'gbk', 'gb2312']:
                try:
                    tables = result.stdout.decode(encoding).strip().split('\n')
                    return [t.strip() for t in tables if t.strip()]
                except:
                    continue
            return []
        except Exception as e:
            print(f"读取表列表失败: {e}")
            return []
    
    def read_table(self, table_name):
        """读取指定表（自动处理中文表名和编码）"""
        try:
            result = subprocess.run(
                ['mdb-export', self.mdb_path, table_name],
                capture_output=True
            )
            
            # 智能解码（工控系统通常是GBK）
            raw_data = result.stdout
            for encoding in ['gbk', 'gb2312', 'utf-8']:
                try:
                    decoded = raw_data.decode(encoding)
                    df = pd.read_csv(pd.io.common.StringIO(decoded))
                    print(f"✓ 成功读取表 [{table_name}]，共 {len(df)} 行")
                    return df
                except:
                    continue
                    
            # 如果都失败，使用容错解码
            decoded = raw_data.decode('gbk', errors='ignore')
            return pd.read_csv(pd.io.common.StringIO(decoded))
            
        except Exception as e:
            print(f"读取表 {table_name} 失败: {e}")
            return pd.DataFrame()
    
    def query_llm(self, prompt, system=None):
        """调用本地大模型"""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1, "num_ctx": 16384}
        }
        if system:
            payload["system"] = system
            
        try:
            r = requests.post(self.ollama_url, json=payload, timeout=30000)
            return r.json()['response']
        except Exception as e:
            return f"模型调用失败: {e}"
    
    def analyze_temperature_data(self):
        """专门针对温度数据的分析（元件温度.mdb 大概率是温度监测表）"""
        # 尝试常见中文表名
        target_tables = ['温度数据', 'Temperature', '温度记录', '元件温度', 'TempData']
        target_tables.extend(self.tables)  # 加上实际探测到的表名
        
        df = None
        used_table = None
        
        for table in target_tables:
            if table in self.tables:
                df = self.read_table(table)
                if not df.empty:
                    used_table = table
                    break
        
        if df is None or df.empty:
            print("可用表名列表：", self.tables)
            return "未找到有效的温度数据表"
        
        print(f"正在分析表: {used_table}")
        print(f"数据列: {list(df.columns)}")
        print(f"前5行预览:\n{df.head()}")
        
        # 数据摘要（发送给大模型）
        stats = {
            "表名": used_table,
            "总行数": len(df),
            "列名": list(df.columns),
            "数据类型": {col: str(dtype) for col, dtype in df.dtypes.items()},
            "统计摘要": df.describe().to_dict() if df.select_dtypes(include=['number']).columns.any() else "无数值列",
            "时间范围": f"{df.iloc[0,0]} 到 {df.iloc[-1,0]}" if not df.empty else "未知"
        }
        
        system_prompt = """你是整流机组热管理专家，精通大功率硅元件（晶闸管/二极管）的温度监测分析。
擅长识别：散热器过热、冷却水流量不足、触发不均导致的热斑、环境温度影响等热故障模式。
请基于温度数据给出专业的热状态评估和预警建议。"""
        
        prompt = f"""请分析以下整流机组元件温度监测数据：

【数据概况】
{json.dumps(stats, ensure_ascii=False, indent=2)}

【样本数据（前3行）】
{df.head(3).to_string()}

【分析任务】
1. **温度分布评估**：各监测点温度是否均衡，是否存在局部过热（热点）
2. **超限分析**：是否有超过晶闸管允许结温（通常125°C）或报警阈值的情况
3. **热故障诊断**：如果存在温度异常，分析可能原因（水路堵塞、风机故障、负荷不均等）
4. **预测性建议**：基于当前温升趋势，预测是否需要调整冷却系统或降负荷运行
5. **维护优先级**：如果有多个异常点，给出检修优先级排序

注意：整流元件温度过高可能导致硅片热击穿，需严肃对待。"""
        
        return self.query_llm(prompt, system_prompt)

# 执行分析（在 Jupyter Cell 中直接运行）
analyzer = RectifierAnalyzer()
result = analyzer.analyze_temperature_data()
print("\n" + "="*50)
print("大模型分析结果：")
print(result)