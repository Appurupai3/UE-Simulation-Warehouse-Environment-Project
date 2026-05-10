import math
from abc import ABC
from typing import List, Dict
from app.models.benchmark import AlgorithmType, Position3D
from app.services.interfaces import IAlgorithm


class BaseAlgorithm(IAlgorithm, ABC):
    """演算法基礎類別"""
    
    def __init__(self, name: str, algorithm_type: AlgorithmType):
        self._name = name
        self._type = algorithm_type
    
    def get_name(self) -> str:
        """返回演算法名稱"""
        return self._name
    
    def get_type(self) -> AlgorithmType:
        """返回演算法類型"""
        return self._type
    
    def _get_item_positions(self, order_items: List[int], cargo_data: List[Dict]) -> Dict[int, Dict]:
        """建立項目到位置的映射"""
        item_positions = {}
        for item in cargo_data:
            # 處理 "case 1" 格式的 ID，提取數字部分
            cargo_id_str = str(item['id'])
            if cargo_id_str.startswith('case '):
                item_id = int(cargo_id_str.replace('case ', ''))
            else:
                item_id = int(cargo_id_str)
            
            if item_id in order_items:
                item_positions[item_id] = item['position']
        return item_positions
    
    def _calculate_distance(self, pos1: Dict, pos2: Dict) -> float:
        """計算兩點間的歐幾里得距離"""
        dx = pos2['x'] - pos1['x']
        dy = pos2['y'] - pos1['y']
        dz = pos2['z'] - pos1['z']
        return math.sqrt(dx * dx + dy * dy + dz * dz)


class GreedyAlgorithm(BaseAlgorithm):
    """貪婪演算法：每次選擇最近的未訪問項目"""
    
    def __init__(self):
        super().__init__("greedy", AlgorithmType.GREEDY)
    
    def calculate_path(self, order_items: List[int], cargo_data: List[Dict]) -> List[int]:
        """
        計算訪問路徑（貪婪策略）
        
        Args:
            order_items: 訂單項目編號列表
            cargo_data: 貨物資料
            
        Returns:
            優化後的訪問順序
        """
        if not order_items:
            return []
        
        item_positions = self._get_item_positions(order_items, cargo_data)
        
        path = []
        remaining = set(order_items)
        current_pos = {'x': 0, 'y': 0, 'z': 0}  # 起始位置
        
        while remaining:
            # 找到最近的項目
            nearest_item = None
            min_distance = float('inf')
            
            for item_id in remaining:
                item_pos = item_positions[item_id]
                distance = self._calculate_distance(current_pos, item_pos)
                
                if distance < min_distance:
                    min_distance = distance
                    nearest_item = item_id
            
            # 訪問最近項目
            path.append(nearest_item)
            remaining.remove(nearest_item)
            current_pos = item_positions[nearest_item]
        
        assert len(path) == len(order_items), "路徑長度必須等於訂單項目數量"
        assert set(path) == set(order_items), "路徑必須包含所有訂單項目"
        
        return path


class AStarAlgorithm(BaseAlgorithm):
    """A* 演算法：使用啟發式搜尋找到最優路徑"""
    
    def __init__(self):
        super().__init__("astar", AlgorithmType.GREEDY)
    
    def calculate_path(self, order_items: List[int], cargo_data: List[Dict]) -> List[int]:
        """
        計算訪問路徑（A* 策略）
        
        使用 A* 演算法找到訪問所有項目的最優路徑。
        啟發式函數 h(n) = 當前位置到最近未訪問項目的距離
        
        Args:
            order_items: 訂單項目編號列表
            cargo_data: 貨物資料
            
        Returns:
            優化後的訪問順序
        """
        if not order_items:
            return []
        
        item_positions = self._get_item_positions(order_items, cargo_data)
        
        # A* 搜尋：找到訪問所有項目的最優路徑
        # 狀態：(當前位置, 已訪問項目集合)
        # g(n)：從起點到當前狀態的實際成本
        # h(n)：從當前狀態到目標的啟發式估計成本
        # f(n) = g(n) + h(n)
        
        import heapq
        
        start_pos = {'x': 0, 'y': 0, 'z': 0}
        
        # 優先隊列：(f_score, counter, g_score, current_pos, visited_items, path)
        # counter 用於打破 f_score 相同時的平局，避免比較字典
        # visited_items 使用 frozenset 以便作為字典鍵
        counter = 0
        pq = [(0, counter, 0, start_pos, frozenset(), [])]
        
        # 記錄已訪問的狀態：(current_pos_tuple, visited_items) -> best_g_score
        visited_states = {}
        
        while pq:
            f_score, _, g_score, current_pos, visited_items, path = heapq.heappop(pq)
            
            # 如果已訪問所有項目，返回路徑
            if len(visited_items) == len(order_items):
                assert len(path) == len(order_items), "路徑長度必須等於訂單項目數量"
                assert set(path) == set(order_items), "路徑必須包含所有訂單項目"
                return path
            
            # 狀態鍵
            pos_tuple = (current_pos['x'], current_pos['y'], current_pos['z'])
            state_key = (pos_tuple, visited_items)
            
            # 如果這個狀態已經用更低的成本訪問過，跳過
            if state_key in visited_states and visited_states[state_key] <= g_score:
                continue
            
            visited_states[state_key] = g_score
            
            # 探索所有未訪問的項目
            for item_id in order_items:
                if item_id in visited_items:
                    continue
                
                item_pos = item_positions[item_id]
                
                # 計算移動到這個項目的成本
                move_cost = self._calculate_distance(current_pos, item_pos)
                new_g_score = g_score + move_cost
                
                # 計算啟發式成本：到最近未訪問項目的距離
                new_visited = visited_items | {item_id}
                h_score = self._heuristic(item_pos, new_visited, order_items, item_positions)
                
                new_f_score = new_g_score + h_score
                new_path = path + [item_id]
                
                counter += 1
                heapq.heappush(pq, (new_f_score, counter, new_g_score, item_pos, new_visited, new_path))
        
        # 如果沒有找到路徑（理論上不應該發生），返回貪婪算法的結果
        return self._greedy_fallback(order_items, cargo_data, item_positions)
    
    def _heuristic(self, current_pos: Dict, visited_items: frozenset, 
                   all_items: List[int], item_positions: Dict[int, Dict]) -> float:
        """
        啟發式函數：估計從當前位置訪問所有剩餘項目的最小成本
        
        使用最小生成樹（MST）的近似值作為啟發式
        """
        remaining_items = [item for item in all_items if item not in visited_items]
        
        if not remaining_items:
            return 0
        
        # 簡化版：返回到最近未訪問項目的距離
        min_distance = float('inf')
        for item_id in remaining_items:
            item_pos = item_positions[item_id]
            distance = self._calculate_distance(current_pos, item_pos)
            min_distance = min(min_distance, distance)
        
        return min_distance
    
    def _greedy_fallback(self, order_items: List[int], cargo_data: List[Dict], 
                        item_positions: Dict[int, Dict]) -> List[int]:
        """貪婪算法作為後備方案"""
        path = []
        remaining = set(order_items)
        current_pos = {'x': 0, 'y': 0, 'z': 0}
        
        while remaining:
            nearest_item = None
            min_distance = float('inf')
            
            for item_id in remaining:
                item_pos = item_positions[item_id]
                distance = self._calculate_distance(current_pos, item_pos)
                
                if distance < min_distance:
                    min_distance = distance
                    nearest_item = item_id
            
            path.append(nearest_item)
            remaining.remove(nearest_item)
            current_pos = item_positions[nearest_item]
        
        return path


class OriginalAlgorithm(BaseAlgorithm):
    """原始順序演算法：不做任何整理，保持訂單原始順序"""
    
    def __init__(self):
        super().__init__("original", AlgorithmType.SEQUENTIAL)
    
    def calculate_path(self, order_items: List[int], cargo_data: List[Dict]) -> List[int]:
        """
        計算訪問路徑（原始順序，不做任何整理）
        
        Args:
            order_items: 訂單項目編號列表
            cargo_data: 貨物資料（此演算法不使用）
            
        Returns:
            與輸入完全相同的訪問順序
        """
        path = order_items.copy()
        
        assert len(path) == len(order_items), "路徑長度必須等於訂單項目數量"
        assert set(path) == set(order_items), "路徑必須包含所有訂單項目"
        
        return path



class SequentialAlgorithm(BaseAlgorithm):
    """順序演算法：依 item id 由小到大排序。"""

    def __init__(self):
        super().__init__("sequential", AlgorithmType.SEQUENTIAL)

    def calculate_path(self, order_items: List[int], cargo_data: List[Dict]) -> List[int]:
        return sorted(order_items)


class ReverseAlgorithm(BaseAlgorithm):
    """反向順序演算法：依 item id 由大到小排序。"""

    def __init__(self):
        super().__init__("reverse", AlgorithmType.REVERSE)

    def calculate_path(self, order_items: List[int], cargo_data: List[Dict]) -> List[int]:
        return sorted(order_items, reverse=True)


class ObstacleAvoidanceAlgorithm(BaseAlgorithm):
    """避障優先演算法：優先選擇阻擋層數較少且距離較近的貨物。"""

    def __init__(self):
        super().__init__("obstacle_aware", AlgorithmType.OPTIMIZED)

    def _build_blocker_count(self, cargo_data: List[Dict]) -> Dict[int, int]:
        columns = {}
        for item in cargo_data:
            cargo_id_str = str(item["id"])
            item_id = int(cargo_id_str.replace("case ", "")) if cargo_id_str.startswith("case ") else int(cargo_id_str)
            pos = item["position"]
            key = f"{pos['x']:.3f}-{pos['z']:.3f}"
            columns.setdefault(key, []).append((item_id, float(pos["y"])))

        blocker_count = {}
        for entries in columns.values():
            ordered = sorted(entries, key=lambda row: row[1], reverse=True)
            for idx, (item_id, _) in enumerate(ordered):
                blocker_count[item_id] = idx
        return blocker_count

    def calculate_path(self, order_items: List[int], cargo_data: List[Dict]) -> List[int]:
        if not order_items:
            return []

        item_positions = self._get_item_positions(order_items, cargo_data)
        blocker_count = self._build_blocker_count(cargo_data)

        remaining = set(order_items)
        current_pos = {'x': 0, 'y': 0, 'z': 0}
        path = []

        while remaining:
            best_item = None
            best_score = float("inf")

            for item_id in remaining:
                pos = item_positions[item_id]
                distance = self._calculate_distance(current_pos, pos)
                blockers = blocker_count.get(item_id, 0)
                score = distance + blockers * 2.5

                if score < best_score:
                    best_score = score
                    best_item = item_id

            path.append(best_item)
            remaining.remove(best_item)
            current_pos = item_positions[best_item]

        return path
