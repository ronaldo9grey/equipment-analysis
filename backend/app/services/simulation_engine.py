import logging
import random
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class SimulationEngine:
    """数据模拟引擎"""
    
    def __init__(self):
        self.active_simulations: Dict[str, Dict] = {}
    
    def generate_simulation_data(
        self,
        columns: List[str],
        row_count: int = 100,
        analysis_features: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """生成模拟数据"""
        
        if not columns:
            return []
        
        simulation_data = []
        
        for i in range(row_count):
            row = {}
            for col in columns:
                row[col] = self._generate_field_value(
                    col, 
                    analysis_features.get(col, {}) if analysis_features else {}
                )
            row['_timestamp'] = datetime.now().isoformat()
            row['_index'] = i
            simulation_data.append(row)
        
        return simulation_data
    
    def _generate_field_value(
        self, 
        column_name: str, 
        features: Dict[str, Any]
    ) -> Any:
        """根据字段特征生成模拟值"""
        
        col_lower = column_name.lower()
        
        if features:
            missing_rate = features.get('missing_rate', 0)
            if random.random() < missing_rate:
                return None
            
            anomaly_rate = features.get('anomaly_rate', 0)
            if random.random() < anomaly_rate:
                return self._generate_anomaly_value(col_lower)
            
            value_range = features.get('value_range')
            if value_range:
                return random.uniform(value_range[0], value_range[1])
        
        if any(keyword in col_lower for keyword in ['温度', 'temp', 'temperature']):
            return round(random.uniform(20, 100), 1)
        
        elif any(keyword in col_lower for keyword in ['压力', 'pressure']):
            return round(random.uniform(0.1, 1.0), 3)
        
        elif any(keyword in col_lower for keyword in ['电流', 'current']):
            return round(random.uniform(0, 100), 2)
        
        elif any(keyword in col_lower for keyword in ['电压', 'voltage']):
            return round(random.uniform(220, 250), 1)
        
        elif any(keyword in col_lower for keyword in ['功率', 'power']):
            return round(random.uniform(0, 50), 2)
        
        elif any(keyword in col_lower for keyword in ['效率', 'efficiency']):
            return round(random.uniform(60, 95), 1)
        
        elif any(keyword in col_lower for keyword in ['转速', 'speed', 'rpm']):
            return random.randint(500, 3000)
        
        elif any(keyword in col_lower for keyword in ['时间', 'time', 'date']):
            return datetime.now().isoformat()
        
        elif any(keyword in col_lower for keyword in ['状态', 'status', 'flag']):
            return random.choice(['正常', '运行', '停止', '告警', '正常', '运行'])
        
        elif any(keyword in col_lower for keyword in ['id', '编号', 'no']):
            return f"EQ{random.randint(1000, 9999)}"
        
        else:
            return random.randint(1, 100)
    
    def _generate_anomaly_value(self, column_name: str) -> Any:
        """生成异常值"""
        anomaly_type = random.choice(['high', 'low', 'zero', 'negative'])
        
        if '温度' in column_name or 'temp' in column_name:
            return 150 if anomaly_type == 'high' else -10
        
        elif '压力' in column_name or 'pressure' in column_name:
            return 2.0 if anomaly_type == 'high' else 0
        
        elif '电流' in column_name or 'current' in column_name:
            return -5 if anomaly_type == 'negative' else 500
        
        elif '电压' in column_name or 'voltage' in column_name:
            return 0 if anomaly_type == 'zero' else 380
        
        else:
            return 9999
    
    def extract_features_from_analysis(
        self, 
        analysis_result: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """从AI分析结果中提取字段特征"""
        
        features = {}
        
        content = analysis_result.get('content', '')
        
        import re
        
        missing_pattern = r'缺失[率高]*.?(\d+\.?\d*)%?'
        missing_matches = re.findall(missing_pattern, content)
        if missing_matches:
            for match in missing_matches[:5]:
                rate = float(match) / 100 if float(match) > 1 else float(match)
                features[f'field_{len(features)}'] = {
                    'missing_rate': rate,
                    'type': 'missing'
                }
        
        anomaly_pattern = r'异常[值高]*.?(\d+\.?\d*)%?'
        anomaly_matches = re.findall(anomaly_pattern, content)
        if anomaly_matches:
            for match in anomaly_matches[:5]:
                rate = float(match) / 100 if float(match) > 1 else float(match)
                features[f'field_{len(features)}'] = {
                    'anomaly_rate': rate,
                    'type': 'anomaly'
                }
        
        logger.info(f"提取到模拟特征: {features}")
        return features
    
    def start_simulation(
        self,
        simulation_id: str,
        columns: List[str],
        interval: int = 5,
        analysis_features: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """启动模拟"""
        
        self.active_simulations[simulation_id] = {
            'columns': columns,
            'interval': interval,
            'analysis_features': analysis_features or {},
            'status': 'running',
            'start_time': datetime.now().isoformat(),
            'data_count': 0
        }
        
        return {
            'simulation_id': simulation_id,
            'status': 'started',
            'message': f'模拟已启动，间隔 {interval} 秒'
        }
    
    def stop_simulation(self, simulation_id: str) -> Dict[str, Any]:
        """停止模拟"""
        
        if simulation_id in self.active_simulations:
            self.active_simulations[simulation_id]['status'] = 'stopped'
            return {
                'simulation_id': simulation_id,
                'status': 'stopped',
                'message': '模拟已停止'
            }
        
        return {
            'simulation_id': simulation_id,
            'status': 'error',
            'message': '模拟不存在'
        }
    
    def get_simulation_status(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        """获取模拟状态"""
        return self.active_simulations.get(simulation_id)


simulation_engine = SimulationEngine()
