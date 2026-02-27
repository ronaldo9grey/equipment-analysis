import pandas as pd
import os
import json
import subprocess
import platform
import shutil
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class DatabaseParser:
    """数据库文件解析器基类"""

    def parse(self, file_path: str) -> Dict[str, Any]:
        raise NotImplementedError

    def get_table_list(self, file_path: str) -> List[str]:
        raise NotImplementedError

    def read_table(self, file_path: str, table_name: str, limit: int = 1000) -> pd.DataFrame:
        raise NotImplementedError


class MDBParser(DatabaseParser):
    """Microsoft Access MDB/ACCDB 文件解析器 - 使用mdb-tools"""

    def __init__(self):
        self._parser_method = "mdb_tools"

    def parse(self, file_path: str) -> Dict[str, Any]:
        """解析MDB文件"""
        try:
            tables = self.get_table_list(file_path)

            result = {
                "file_path": file_path,
                "file_name": os.path.basename(file_path),
                "file_size": os.path.getsize(file_path),
                "file_type": "mdb",
                "tables": [],
                "total_records": 0,
                "parsed_at": datetime.now().isoformat(),
                "parser_method": self._parser_method
            }

            for table_name in tables:
                df = self.read_table(file_path, table_name)
                if not df.empty:
                    result["tables"].append({
                        "table_name": table_name,
                        "columns": list(df.columns),
                        "row_count": len(df),
                        "preview": df.head(10).to_dict(orient="records")
                    })
                    result["total_records"] += len(df)

            return result

        except Exception as e:
            logger.error(f"解析MDB文件失败: {str(e)}")
            raise Exception(f"MDB文件解析失败: {str(e)}")

    def get_table_list(self, file_path: str) -> List[str]:
        """获取MDB文件中的表列表"""
        try:
            # 尝试mdb-tables命令
            result = subprocess.run(
                ['mdb-tables', '-1', file_path],
                capture_output=True,
                text=True,
                timeout=30,
                shell=True
            )

            if result.returncode == 0 and result.stdout.strip():
                # 尝试多种编码
                for encoding in ['utf-8', 'gbk', 'gb2312', 'latin-1']:
                    try:
                        tables = result.stdout.decode(encoding).strip().split('\n')
                        return [t.strip() for t in tables if t.strip()]
                    except:
                        continue

                # 如果都失败，使用原始输出
                tables = result.stdout.strip().split('\n')
                return [t.strip() for t in tables if t.strip()]

            return []

        except Exception as e:
            logger.error(f"获取表列表失败: {str(e)}")
            return []

    def read_table(self, file_path: str, table_name: str, limit: int = 1000) -> pd.DataFrame:
        """读取指定表的数据"""
        try:
            # 使用mdb-export导出
            result = subprocess.run(
                ['mdb-export', file_path, table_name],
                capture_output=True,
                timeout=60,
                shell=True
            )

            if result.returncode == 0 and result.stdout:
                # 尝试多种编码
                for encoding in ['gbk', 'gb2312', 'utf-8', 'latin-1']:
                    try:
                        decoded = result.stdout.decode(encoding)
                        from io import StringIO
                        df = pd.read_csv(StringIO(decoded), nrows=limit)
                        df = df.where(pd.notnull(df), None)
                        return df
                    except:
                        continue

                # 如果都失败，使用容错解码
                decoded = result.stdout.decode('gbk', errors='ignore')
                from io import StringIO
                df = pd.read_csv(StringIO(decoded), nrows=limit)
                df = df.where(pd.notnull(df), None)
                return df

            return pd.DataFrame()

        except Exception as e:
            logger.error(f"读取表 {table_name} 失败: {str(e)}")
            return pd.DataFrame()

    def read_full_table(self, file_path: str, table_name: str) -> pd.DataFrame:
        """读取完整表数据"""
        return self.read_table(file_path, table_name, limit=100000)


class SQLServerBackupParser(DatabaseParser):
    """SQL Server 备份文件 (.bak) 解析器"""

    def __init__(self):
        self.temp_dir = "temp_bak"

    def parse(self, file_path: str) -> Dict[str, Any]:
        """解析SQL Server备份文件"""
        try:
            os.makedirs(self.temp_dir, exist_ok=True)

            result = {
                "file_path": file_path,
                "file_name": os.path.basename(file_path),
                "file_size": os.path.getsize(file_path),
                "file_type": "sqlserver_bak",
                "tables": [],
                "total_records": 0,
                "parsed_at": datetime.now().isoformat(),
                "note": "SQL Server备份文件(.bak)需要连接到SQL Server实例进行恢复和分析。当前仅保存文件信息。"
            }

            return result

        except Exception as e:
            logger.error(f"解析SQL Server备份文件失败: {str(e)}")
            raise Exception(f"SQL Server备份文件解析失败: {str(e)}")

    def get_table_list(self, file_path: str) -> List[str]:
        """获取备份文件中的表列表"""
        return []

    def read_table(self, file_path: str, table_name: str, limit: int = 1000) -> pd.DataFrame:
        """读取表数据"""
        return pd.DataFrame()


class MySQLDumpParser(DatabaseParser):
    """MySQL SQL转储文件解析器"""

    def parse(self, file_path: str) -> Dict[str, Any]:
        """解析MySQL SQL文件"""
        try:
            tables = self.get_table_list(file_path)

            result = {
                "file_path": file_path,
                "file_name": os.path.basename(file_path),
                "file_size": os.path.getsize(file_path),
                "file_type": "mysql_sql",
                "tables": tables,
                "total_records": 0,
                "parsed_at": datetime.now().isoformat()
            }

            total_records = 0
            for table_name in tables.get("tables", []):
                df = self._parse_table_data(file_path, table_name)
                if not df.empty:
                    total_records += len(df)

            result["total_records"] = total_records

            return result

        except Exception as e:
            logger.error(f"解析MySQL文件失败: {str(e)}")
            raise Exception(f"MySQL文件解析失败: {str(e)}")

    def get_table_list(self, file_path: str) -> Dict:
        """获取SQL文件中的表列表"""
        try:
            tables = []
            create_statements = {}

            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            statements = content.split(';')

            for stmt in statements:
                stmt = stmt.strip()
                if stmt.upper().startswith('CREATE TABLE'):
                    import re
                    match = re.search(r'CREATE TABLE [`"\'](?:IF NOT EXISTS\s+)?[`"\']([^`"\']+)[`"\']', stmt, re.IGNORECASE)
                    if match:
                        table_name = match.group(1)
                        tables.append(table_name)
                        create_statements[table_name] = stmt

            return {
                "tables": tables,
                "create_statements": create_statements
            }

        except Exception as e:
            logger.error(f"获取表列表失败: {str(e)}")
            return {"tables": [], "create_statements": {}}

    def read_table(self, file_path: str, table_name: str, limit: int = 1000) -> pd.DataFrame:
        """读取指定表的数据"""
        try:
            df = self._parse_table_data(file_path, table_name, limit)
            return df

        except Exception as e:
            logger.error(f"读取表 {table_name} 失败: {str(e)}")
            return pd.DataFrame()

    def _parse_table_data(self, file_path: str, table_name: str, limit: int = 1000) -> pd.DataFrame:
        """解析表数据"""
        try:
            data_rows = []
            in_table = False
            current_table = None

            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if f'INSERT INTO `{table_name}`' in line or f'INSERT INTO {table_name}' in line:
                        in_table = True
                        current_table = table_name
                        line = line.strip()

                        values_match = re.search(r'VALUES\s*(.+)', line, re.IGNORECASE)
                        if values_match:
                            values_str = values_match.group(1)

                            values_str = values_str.strip('();')
                            if values_str.startswith(','):
                                values_str = values_str[1:]

                            try:
                                row_data = self._parse_values(values_str)
                                if row_data:
                                    data_rows.append(row_data)
                                    if len(data_rows) >= limit:
                                        break
                            except:
                                pass

                    elif in_table and current_table == table_name:
                        line = line.strip().strip('();')
                        if line:
                            try:
                                row_data = self._parse_values(line)
                                if row_data:
                                    data_rows.append(row_data)
                                    if len(data_rows) >= limit:
                                        break
                            except:
                                pass
                        else:
                            in_table = False

            if data_rows:
                df = pd.DataFrame(data_rows)
                return df

            return pd.DataFrame()

        except Exception as e:
            logger.error(f"解析表数据失败: {str(e)}")
            return pd.DataFrame()

    def _parse_values(self, values_str: str) -> Optional[Dict]:
        """解析VALUES语句"""
        import re
        try:
            values_str = values_str.strip()

            values_str = re.sub(r'\),\s*\(', '|', values_str)
            values_str = values_str.strip('(),')

            parts = []
            current = ""
            in_string = False
            string_char = None

            for char in values_str:
                if char in ("'", '"') and (not in_string or char == string_char):
                    if in_string and char == string_char:
                        in_string = False
                        string_char = None
                    else:
                        in_string = True
                        string_char = char
                    current += char
                elif char == ',' and not in_string:
                    parts.append(current.strip())
                    current = ""
                else:
                    current += char

            if current:
                parts.append(current.strip())

            if len(parts) > 0:
                return {"_row_data": parts}

            return None

        except Exception as e:
            return None


def get_parser(file_path: str) -> DatabaseParser:
    """根据文件扩展名获取对应的解析器"""
    ext = os.path.splitext(file_path)[1].lower()

    parsers = {
        ".mdb": MDBParser,
        ".accdb": MDBParser,
        ".bak": SQLServerBackupParser,
        ".sql": MySQLDumpParser,
    }

    parser_class = parsers.get(ext)
    if parser_class:
        return parser_class()

    raise ValueError(f"不支持的文件格式: {ext}")
