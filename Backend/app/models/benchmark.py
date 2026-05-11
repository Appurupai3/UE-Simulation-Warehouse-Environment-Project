from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class AlgorithmType(str, Enum):
    """演算法類型枚舉"""
    GREEDY = "greedy"
    NEAREST_NEIGHBOR = "nearest_neighbor"
    OPTIMIZED = "optimized"
    SEQUENTIAL = "sequential"
    REVERSE = "reverse"
    CUSTOM = "custom"


class Position3D(BaseModel):
    """3D 空間位置"""
    x: float
    y: float
    z: float


class CargoItem(BaseModel):
    """貨物項目"""
    id: str
    position: Position3D
    size: Position3D
    timestamp: str


class BenchmarkOrder(BaseModel):
    """測試訂單"""
    items: List[int] = Field(..., description="訂單項目編號列表，例如 [75, 12, 43]")
    content: Optional[str] = Field(None, description="訂單內容字串，例如 '75-12-43'")


class AlgorithmResult(BaseModel):
    """單一演算法執行結果"""
    algorithm_name: str
    algorithm_type: AlgorithmType
    step_count: int
    execution_time_ms: float
    path: List[int]  # 訪問順序
    positions: List[Position3D]  # 實際位置序列
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BenchmarkResult(BaseModel):
    """完整 Benchmark 結果"""
    benchmark_id: str
    order: BenchmarkOrder
    results: List[AlgorithmResult]
    best_algorithm: str
    best_step_count: int
    timestamp: datetime
    cargo_data_version: Optional[str] = None


class BenchmarkComparison(BaseModel):
    """演算法比較結果"""
    algorithm_name: str
    average_steps: float
    min_steps: int
    max_steps: int
    total_runs: int
    improvement_percentage: Optional[float] = None  # 相對於基準的改進百分比


# ===== 隨機多局 Benchmark 相關模型 =====


class RandomBenchmarkTaskResult(BaseModel):
    """隨機 Benchmark 單一任務結果"""
    round_number: int = Field(..., description="局數編號")
    task_number: int = Field(..., description="同一局中的任務編號")
    order: BenchmarkOrder = Field(..., description="隨機產生的訂單")
    results: List[AlgorithmResult] = Field(..., description="各演算法在此任務的結果")
    best_algorithm: str = Field(..., description="此任務最佳演算法")
    best_step_count: int = Field(..., description="此任務最少步數")


class RandomBenchmarkSummary(BaseModel):
    """隨機 Benchmark 演算法彙總"""
    algorithm_name: str = Field(..., description="演算法名稱")
    average_steps: float = Field(..., description="平均步數")
    min_steps: int = Field(..., description="最少步數")
    max_steps: int = Field(..., description="最多步數")
    total_steps: int = Field(..., description="總步數")
    wins: int = Field(..., description="最佳次數")
    total_runs: int = Field(..., description="執行任務數")


class RandomBenchmarkResult(BaseModel):
    """隨機多局 Benchmark 結果"""
    benchmark_id: str = Field(..., description="Benchmark ID")
    algorithms: List[str] = Field(..., description="比較的演算法")
    rounds: int = Field(..., description="隨機局數")
    tasks_per_round: int = Field(..., description="每局任務數")
    items_per_task: int = Field(..., description="每個任務的項目數")
    seed: Optional[int] = Field(None, description="隨機種子；提供後可重現結果")
    tasks: List[RandomBenchmarkTaskResult] = Field(..., description="所有任務明細")
    summaries: List[RandomBenchmarkSummary] = Field(..., description="演算法彙總")
    best_algorithm: str = Field(..., description="平均步數最低的演算法")
    timestamp: datetime = Field(..., description="執行時間戳")


# ===== 線上程式碼編輯器相關模型 =====

class AlgorithmTemplate(BaseModel):
    """演算法模板"""
    name: str = Field(..., description="模板名稱")
    display_name: str = Field(..., description="顯示名稱")
    description: str = Field(..., description="演算法描述")
    code: str = Field(..., description="模板程式碼")
    category: str = Field(default="basic", description="分類：basic, advanced, custom")


class CodeExecutionRequest(BaseModel):
    """程式碼執行請求"""
    code: str = Field(..., description="要執行的 Python 程式碼")
    order: BenchmarkOrder = Field(..., description="測試訂單")
    timeout: Optional[int] = Field(default=5, description="超時時間（秒）")


class CodeExecutionResult(BaseModel):
    """程式碼執行結果"""
    success: bool = Field(..., description="是否執行成功")
    step_count: Optional[int] = Field(None, description="步數（成功時）")
    path: Optional[List[int]] = Field(None, description="路徑（成功時）")
    execution_time_ms: Optional[float] = Field(None, description="執行時間（毫秒）")
    error_message: Optional[str] = Field(None, description="錯誤訊息（失敗時）")
    error_type: Optional[str] = Field(None, description="錯誤類型（失敗時）")
    line_number: Optional[int] = Field(None, description="錯誤行號（失敗時）")


class CodeValidationRequest(BaseModel):
    """程式碼驗證請求"""
    code: str = Field(..., description="要驗證的程式碼")


class CodeValidationResult(BaseModel):
    """程式碼驗證結果"""
    valid: bool = Field(..., description="是否有效")
    errors: List[str] = Field(default_factory=list, description="錯誤列表")
    warnings: List[str] = Field(default_factory=list, description="警告列表")
    forbidden_operations: List[str] = Field(default_factory=list, description="禁止的操作")


class AlgorithmCodeRequest(BaseModel):
    """演算法程式碼請求"""
    name: str = Field(..., description="演算法名稱")
    code: str = Field(..., description="Python 程式碼")
    description: Optional[str] = Field(None, description="演算法描述")


class AlgorithmCodeResponse(BaseModel):
    """演算法程式碼回應"""
    name: str
    code: str
    description: Optional[str] = None
    is_builtin: bool = Field(default=False, description="是否為內建演算法")
    last_modified: Optional[datetime] = None


# ===== 批次優化相關模型 =====

class BatchInfo(BaseModel):
    """批次資訊"""
    batch_number: int = Field(..., description="批次編號")
    items: List[int] = Field(..., description="批次中的項目列表")
    path: List[int] = Field(..., description="優化後的訪問順序")
    step_count: int = Field(..., description="此批次的步數")
    positions: List[Position3D] = Field(..., description="實際位置序列")


class BatchOptimizationResult(BaseModel):
    """批次優化結果"""
    algorithm_name: str = Field(..., description="使用的演算法")
    algorithm_type: AlgorithmType = Field(..., description="演算法類型")
    total_batches: int = Field(..., description="總批次數")
    batches: List[BatchInfo] = Field(..., description="批次列表")
    total_steps: int = Field(..., description="所有批次的總步數")
    execution_time_ms: float = Field(..., description="執行時間（毫秒）")
    total_items: int = Field(..., description="總項目數")


class BatchOptimizationComparison(BaseModel):
    """批次優化比較結果"""
    optimization_id: str = Field(..., description="優化 ID")
    source_orders: List[Dict] = Field(..., description="來源訂單列表")
    results: List[BatchOptimizationResult] = Field(..., description="各演算法的優化結果")
    best_algorithm: str = Field(..., description="最佳演算法")
    best_total_steps: int = Field(..., description="最少總步數")
    timestamp: datetime = Field(..., description="執行時間戳")
