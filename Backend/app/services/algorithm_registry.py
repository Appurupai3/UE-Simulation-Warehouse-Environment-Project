from typing import Dict, List, Optional
from app.services.interfaces import IAlgorithm
from app.services.algorithms import (
    GreedyAlgorithm, AStarAlgorithm, OriginalAlgorithm,
    ObstacleAvoidanceAlgorithm, SequentialAlgorithm, ReverseAlgorithm
)


class AlgorithmRegistry:
    """演算法註冊表"""
    
    def __init__(self):
        self._algorithms: Dict[str, IAlgorithm] = {}
        self._register_builtin_algorithms()
    
    def _register_builtin_algorithms(self):
        """註冊內建演算法"""
        self.register("greedy", GreedyAlgorithm())
        self.register("astar", AStarAlgorithm())
        self.register("obstacle_aware", ObstacleAvoidanceAlgorithm())
        self.register("original", OriginalAlgorithm())
        self.register("sequential", SequentialAlgorithm())
        self.register("reverse", ReverseAlgorithm())
    
    def register(self, name: str, algorithm: IAlgorithm):
        """
        註冊演算法
        
        Args:
            name: 演算法名稱
            algorithm: 演算法實例
        """
        self._algorithms[name] = algorithm
    
    def get(self, name: str) -> IAlgorithm:
        """
        獲取演算法實例
        
        Args:
            name: 演算法名稱
            
        Returns:
            演算法實例
            
        Raises:
            KeyError: 如果演算法不存在
        """
        if name not in self._algorithms:
            available = list(self._algorithms.keys())
            raise KeyError(f"演算法 '{name}' 不存在。可用演算法: {available}")
        
        return self._algorithms[name]
    
    def list_all(self) -> List[str]:
        """
        列出所有已註冊演算法
        
        Returns:
            演算法名稱列表
        """
        return list(self._algorithms.keys())
    
    def exists(self, name: str) -> bool:
        """
        檢查演算法是否存在
        
        Args:
            name: 演算法名稱
            
        Returns:
            是否存在
        """
        return name in self._algorithms


# 全域單例
algorithm_registry = AlgorithmRegistry()
