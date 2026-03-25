
import math
from typing import List, Dict
from app.models.benchmark import Position3D
from app.services.interfaces import IStepCounter


class StepCounter(IStepCounter):
    """步數計算器實作"""
    
    def calculate_distance(self, pos1: Position3D, pos2: Position3D) -> float:
        """
        計算歐幾里得距離
        
        Args:
            pos1: 第一個位置
            pos2: 第二個位置
            
        Returns:
            兩點間的歐幾里得距離
        """
        dx = pos2.x - pos1.x
        dy = pos2.y - pos1.y
        dz = pos2.z - pos1.z
        distance = math.sqrt(dx * dx + dy * dy + dz * dz)
        
        assert distance >= 0, "距離必須非負"
        return distance
    
    def count_steps(self, positions: List[Position3D], start_position: Position3D) -> int:
        """
        計算完成路徑所需步數
        
        Args:
            positions: 位置序列
            start_position: 起始位置
            
        Returns:
            總步數（向上取整）
        """
        if not positions:
            return 0
        
        total_steps = 0
        current_pos = start_position
        
        for next_pos in positions:
            distance = self.calculate_distance(current_pos, next_pos)
            steps = math.ceil(distance)
            total_steps += steps
            current_pos = next_pos
        
        assert total_steps >= 0, "步數必須非負"
        return total_steps
    
    def get_position(self, item_id: int, cargo_data: List[Dict]) -> Position3D:
        """
        從 cargo_data 獲取項目位置
        
        Args:
            item_id: 項目編號
            cargo_data: 貨物資料列表
            
        Returns:
            項目的 3D 位置
            
        Raises:
            ValueError: 如果項目不存在
        """
        for item in cargo_data:
            # 處理 "case 1" 格式的 ID，提取數字部分
            cargo_id_str = str(item['id'])
            if cargo_id_str.startswith('case '):
                cargo_id = int(cargo_id_str.replace('case ', ''))
            else:
                cargo_id = int(cargo_id_str)
            
            if cargo_id == item_id:
                pos = item['position']
                return Position3D(x=pos['x'], y=pos['y'], z=pos['z'])
        
        raise ValueError(f"項目 {item_id} 不存在於 cargo_data 中")
