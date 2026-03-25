from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from app.models.benchmark import (
    AlgorithmType, Position3D, CargoItem, BenchmarkOrder,
    BenchmarkResult, BenchmarkComparison, AlgorithmTemplate,
    CodeExecutionResult, CodeValidationResult
)


class IAlgorithm(ABC):
    """演算法介面"""
    
    @abstractmethod
    def get_name(self) -> str:
        """返回演算法名稱"""
        pass
    
    @abstractmethod
    def get_type(self) -> AlgorithmType:
        """返回演算法類型"""
        pass
    
    @abstractmethod
    def calculate_path(self, order_items: List[int], cargo_data: List[Dict]) -> List[int]:
        """
        計算訪問路徑
        
        Args:
            order_items: 訂單項目編號列表
            cargo_data: 貨物資料
            
        Returns:
            優化後的訪問順序
        """
        pass


class IStepCounter(ABC):
    """步數計算器介面"""
    
    @abstractmethod
    def count_steps(self, positions: List[Position3D], start_position: Position3D) -> int:
        """
        計算完成路徑所需步數
        
        Args:
            positions: 位置序列
            start_position: 起始位置
            
        Returns:
            總步數
        """
        pass
    
    @abstractmethod
    def calculate_distance(self, pos1: Position3D, pos2: Position3D) -> float:
        """計算兩點間距離"""
        pass


class IBenchmarkService(ABC):
    """Benchmark 服務介面"""
    
    @abstractmethod
    async def run_benchmark(
        self, 
        order: BenchmarkOrder, 
        algorithm_names: List[str]
    ) -> BenchmarkResult:
        """執行 benchmark 測試"""
        pass
    
    @abstractmethod
    async def get_history(
        self, 
        limit: int = 50, 
        algorithm_filter: Optional[str] = None
    ) -> List[BenchmarkResult]:
        """獲取歷史測試結果"""
        pass
    
    @abstractmethod
    async def compare_algorithms(
        self, 
        algorithm_names: List[str], 
        test_orders: List[BenchmarkOrder]
    ) -> Dict[str, BenchmarkComparison]:
        """比較多個演算法的效能"""
        pass


class ICodeValidator(ABC):
    """程式碼驗證器介面"""
    
    @abstractmethod
    def validate_syntax(self, code: str) -> CodeValidationResult:
        """
        驗證程式碼語法
        
        Args:
            code: Python 程式碼字串
            
        Returns:
            驗證結果
        """
        pass
    
    @abstractmethod
    def check_security(self, code: str) -> List[str]:
        """
        檢查程式碼安全性
        
        Args:
            code: Python 程式碼字串
            
        Returns:
            禁止操作列表
        """
        pass
    
    @abstractmethod
    def validate_algorithm_interface(self, code: str) -> bool:
        """
        驗證程式碼是否實作正確的演算法介面
        
        Args:
            code: Python 程式碼字串
            
        Returns:
            是否符合介面要求
        """
        pass


class ISandboxExecutor(ABC):
    """沙箱執行器介面"""
    
    @abstractmethod
    async def execute_code(
        self, 
        code: str, 
        order: BenchmarkOrder,
        timeout: int = 5
    ) -> CodeExecutionResult:
        """
        在沙箱環境中執行程式碼
        
        Args:
            code: Python 程式碼
            order: 測試訂單
            timeout: 超時時間（秒）
            
        Returns:
            執行結果
        """
        pass
    
    @abstractmethod
    def create_restricted_globals(self) -> Dict[str, Any]:
        """
        建立受限的全域命名空間
        
        Returns:
            受限的全域變數字典
        """
        pass


class ITemplateManager(ABC):
    """模板管理器介面"""
    
    @abstractmethod
    def get_template(self, name: str) -> Optional[AlgorithmTemplate]:
        """獲取演算法模板"""
        pass
    
    @abstractmethod
    def list_templates(self) -> List[AlgorithmTemplate]:
        """列出所有可用模板"""
        pass
    
    @abstractmethod
    def get_template_code(self, name: str) -> Optional[str]:
        """獲取模板程式碼"""
        pass
