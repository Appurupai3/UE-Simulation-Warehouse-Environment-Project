from typing import List, Optional, Dict
from app.models.benchmark import AlgorithmTemplate
from app.services.interfaces import ITemplateManager


class TemplateManager(ITemplateManager):
    """模板管理器"""
    
    def __init__(self):
        self._templates: Dict[str, AlgorithmTemplate] = {}
        self._initialize_templates()
    
    def _initialize_templates(self):
        """初始化內建模板"""
        
        # 貪婪演算法模板
        greedy_code = """import math

def calculate_path(order_items, cargo_data):
    \"\"\"
    貪婪演算法：每次選擇最近的未訪問項目
    
    Args:
        order_items: 訂單項目編號列表，例如 [75, 12, 43]
        cargo_data: 貨物資料列表，每個項目包含 id 和 position
        
    Returns:
        優化後的訪問順序列表
    \"\"\"
    # 建立項目到位置的映射
    item_positions = {}
    for item in cargo_data:
        item_id = int(item['id'])
        if item_id in order_items:
            item_positions[item_id] = item['position']
    
    path = []
    remaining = set(order_items)
    current_pos = {'x': 0, 'y': 0, 'z': 0}  # 起始位置
    
    while remaining:
        # 找到最近的項目
        nearest_item = None
        min_distance = float('inf')
        
        for item_id in remaining:
            item_pos = item_positions[item_id]
            dx = item_pos['x'] - current_pos['x']
            dy = item_pos['y'] - current_pos['y']
            dz = item_pos['z'] - current_pos['z']
            distance = math.sqrt(dx*dx + dy*dy + dz*dz)
            
            if distance < min_distance:
                min_distance = distance
                nearest_item = item_id
        
        # 訪問最近項目
        path.append(nearest_item)
        remaining.remove(nearest_item)
        current_pos = item_positions[nearest_item]
    
    return path
"""
        
        self._templates['greedy'] = AlgorithmTemplate(
            name='greedy',
            display_name='貪婪演算法',
            description='每次選擇最近的未訪問項目',
            code=greedy_code,
            category='basic'
        )
        
        # 順序演算法模板
        sequential_code = """def calculate_path(order_items, cargo_data):
    \"\"\"
    順序演算法：按訂單原始順序訪問
    
    這是最簡單的演算法，不進行任何優化，
    直接按照訂單中項目的順序訪問。
    
    Args:
        order_items: 訂單項目編號列表
        cargo_data: 貨物資料列表（此演算法不使用）
        
    Returns:
        與輸入相同的訪問順序
    \"\"\"
    # 直接返回原始順序
    return order_items.copy()
"""
        
        self._templates['sequential'] = AlgorithmTemplate(
            name='sequential',
            display_name='順序演算法',
            description='按訂單原始順序訪問',
            code=sequential_code,
            category='basic'
        )
        
        # 反向順序演算法模板
        reverse_code = """def calculate_path(order_items, cargo_data):
    \"\"\"
    反向順序演算法：按訂單反向順序訪問
    
    將訂單項目反轉後訪問，用於測試順序對效能的影響。
    
    Args:
        order_items: 訂單項目編號列表
        cargo_data: 貨物資料列表（此演算法不使用）
        
    Returns:
        反轉後的訪問順序
    \"\"\"
    # 反轉順序
    return list(reversed(order_items))
"""
        
        self._templates['reverse'] = AlgorithmTemplate(
            name='reverse',
            display_name='反向順序演算法',
            description='按訂單反向順序訪問',
            code=reverse_code,
            category='basic'
        )
    
    def get_template(self, name: str) -> Optional[AlgorithmTemplate]:
        """
        獲取演算法模板
        
        Args:
            name: 模板名稱
            
        Returns:
            模板物件，如果不存在則返回 None
        """
        return self._templates.get(name)
    
    def list_templates(self) -> List[AlgorithmTemplate]:
        """
        列出所有可用模板
        
        Returns:
            模板列表
        """
        return list(self._templates.values())
    
    def get_template_code(self, name: str) -> Optional[str]:
        """
        獲取模板程式碼
        
        Args:
            name: 模板名稱
            
        Returns:
            模板程式碼，如果不存在則返回 None
        """
        template = self.get_template(name)
        return template.code if template else None


# 全域單例
template_manager = TemplateManager()
