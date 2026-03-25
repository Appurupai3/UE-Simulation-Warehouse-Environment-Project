import asyncio
import math
import time
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from app.models.benchmark import BenchmarkOrder, CodeExecutionResult, Position3D
from app.services.interfaces import ISandboxExecutor
from app.services.step_counter import StepCounter


class SandboxExecutor(ISandboxExecutor):
    """沙箱執行器"""
    
    def __init__(self, cargo_data_path: Optional[str] = None):
        # 使用絕對路徑，與執行目錄無關
        if cargo_data_path is None:
            base_dir = Path(__file__).resolve().parents[2]  # 回到 Backend 目錄
            data_dir = base_dir / "data"
            cargo_data_path = str(data_dir / "cargo_data.json")
        
        self.cargo_data_path = cargo_data_path
        self.step_counter = StepCounter()
        self._cargo_data_cache = None
    
    def create_restricted_globals(self) -> Dict[str, Any]:
        """
        建立受限的全域命名空間
        
        Returns:
            受限的全域變數字典
        """
        return {
            '__builtins__': {
                'len': len,
                'range': range,
                'enumerate': enumerate,
                'min': min,
                'max': max,
                'abs': abs,
                'sum': sum,
                'sorted': sorted,
                'list': list,
                'dict': dict,
                'set': set,
                'tuple': tuple,
                'int': int,
                'float': float,
                'str': str,
                'bool': bool,
                'isinstance': isinstance,
                'type': type,
                'zip': zip,
                'map': map,
                'filter': filter,
                'any': any,
                'all': all,
                'reversed': reversed,
                'round': round,
                'pow': pow,
            },
            'math': math,
        }
    
    def _load_cargo_data(self) -> List[Dict]:
        """載入貨物資料（帶快取）"""
        if self._cargo_data_cache is None:
            with open(self.cargo_data_path, 'r', encoding='utf-8') as f:
                self._cargo_data_cache = json.load(f)
        return self._cargo_data_cache
    
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
        start_time = time.perf_counter()
        
        # 步驟 1: 建立受限的全域命名空間
        restricted_globals = self.create_restricted_globals()
        local_namespace = {}
        
        # 步驟 2: 執行程式碼（帶超時保護）
        try:
            # 使用 asyncio.wait_for 實現超時
            async def run_code():
                exec(code, restricted_globals, local_namespace)
            
            await asyncio.wait_for(run_code(), timeout=timeout)
            
        except asyncio.TimeoutError:
            return CodeExecutionResult(
                success=False,
                error_message=f"執行超時（超過 {timeout} 秒）",
                error_type="TimeoutError"
            )
        except Exception as e:
            return CodeExecutionResult(
                success=False,
                error_message=str(e),
                error_type=type(e).__name__,
                line_number=getattr(e, 'lineno', None)
            )
        
        # 步驟 3: 驗證函數存在
        if 'calculate_path' not in local_namespace:
            return CodeExecutionResult(
                success=False,
                error_message="程式碼未定義 calculate_path 函數",
                error_type="NameError"
            )
        
        # 步驟 4: 執行演算法
        try:
            cargo_data = self._load_cargo_data()
            calculate_path_func = local_namespace['calculate_path']
            
            path = calculate_path_func(order.items, cargo_data)
            
            # 驗證路徑
            if not isinstance(path, list):
                raise TypeError("calculate_path 必須返回列表")
            
            if set(path) != set(order.items):
                raise ValueError("返回的路徑不包含所有訂單項目")
            
            # 計算步數
            positions = []
            for item_id in path:
                pos = self.step_counter.get_position(item_id, cargo_data)
                positions.append(pos)
            
            start_position = Position3D(x=0, y=0, z=0)
            step_count = self.step_counter.count_steps(positions, start_position)
            
            end_time = time.perf_counter()
            execution_time = (end_time - start_time) * 1000
            
            return CodeExecutionResult(
                success=True,
                step_count=step_count,
                path=path,
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            return CodeExecutionResult(
                success=False,
                error_message=str(e),
                error_type=type(e).__name__
            )


# 全域單例
sandbox_executor = SandboxExecutor()
