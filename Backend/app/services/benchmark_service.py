import json
import time
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple
from pathlib import Path

from app.models.benchmark import (
    BenchmarkOrder, BenchmarkResult, AlgorithmResult,
    BenchmarkComparison, Position3D
)
from app.services.interfaces import IBenchmarkService
from app.services.algorithm_registry import algorithm_registry
from app.services.step_counter import StepCounter


class BenchmarkService(IBenchmarkService):
    """Benchmark 服務"""
    
    def __init__(
        self,
        cargo_data_path: Optional[str] = None,
        results_path: Optional[str] = None
    ):
        # 使用絕對路徑，與執行目錄無關
        base_dir = Path(__file__).resolve().parents[2]  # 回到 Backend 目錄
        data_dir = base_dir / "data"
        
        self.cargo_data_path = cargo_data_path or str(data_dir / "cargo_data.json")
        self.results_path = results_path or str(data_dir / "benchmark_results.json")
        self.step_counter = StepCounter()
        self._cargo_data_cache = None
        
        # 確保資料目錄存在
        data_dir.mkdir(parents=True, exist_ok=True)
        
        # 檢查 cargo_data.json 是否存在
        if not Path(self.cargo_data_path).exists():
            raise FileNotFoundError(
                f"找不到 cargo_data.json 文件: {self.cargo_data_path}\n"
                f"請確保文件存在於 Backend/data/ 目錄中"
            )
        
        # 確保結果檔案存在
        if not Path(self.results_path).exists():
            with open(self.results_path, 'w', encoding='utf-8') as f:
                json.dump([], f)
    
    def _load_cargo_data(self) -> List[Dict]:
        """載入貨物資料（帶快取）"""
        if self._cargo_data_cache is None:
            try:
                with open(self.cargo_data_path, 'r', encoding='utf-8') as f:
                    self._cargo_data_cache = json.load(f)
            except FileNotFoundError:
                raise FileNotFoundError(
                    f"找不到 cargo_data.json: {self.cargo_data_path}"
                )
            except json.JSONDecodeError as e:
                raise ValueError(
                    f"cargo_data.json 格式錯誤: {e}"
                )
        return self._cargo_data_cache
    
    def _validate_order_items(self, order_items: List[int], cargo_data: List[Dict]):
        """驗證訂單項目是否有效"""
        cargo_ids = set()
        for item in cargo_data:
            # 處理 "case 1" 格式的 ID
            cargo_id_str = str(item['id'])
            if cargo_id_str.startswith('case '):
                cargo_id = int(cargo_id_str.replace('case ', ''))
            else:
                cargo_id = int(cargo_id_str)
            cargo_ids.add(cargo_id)
        
        invalid_items = [item for item in order_items if item not in cargo_ids]
        
        if invalid_items:
            raise ValueError(f"無效的訂單項目: {invalid_items}")
    

    def _build_cargo_indices(self, cargo_data: List[Dict]) -> Tuple[Dict[int, Position3D], Dict[str, List[Position3D]]]:
        """建立 cargo 快速索引（id 與同 x/z 欄位）"""
        id_to_position: Dict[int, Position3D] = {}
        column_positions: Dict[str, List[Position3D]] = {}

        for item in cargo_data:
            cargo_id_str = str(item['id'])
            cargo_id = int(cargo_id_str.replace('case ', '')) if cargo_id_str.startswith('case ') else int(cargo_id_str)
            pos = item['position']
            position = Position3D(x=pos['x'], y=pos['y'], z=pos['z'])
            id_to_position[cargo_id] = position

            column_key = f"{position.x:.3f}-{position.z:.3f}"
            column_positions.setdefault(column_key, []).append(position)

        return id_to_position, column_positions

    def _count_operational_steps(
        self,
        path: List[int],
        id_to_position: Dict[int, Position3D],
        column_positions: Dict[str, List[Position3D]],
        start_position: Position3D
    ) -> Tuple[int, List[Position3D], int, int]:
        """
        計算更貼近實務的步數：
        - 每件貨物都從出貨口出發，搬運後回到出貨口
        - 搬離堆疊阻擋物的額外距離（每層阻擋預設 2 步）
        """
        positions: List[Position3D] = []
        for item_id in path:
            if item_id not in id_to_position:
                raise ValueError(f"項目 {item_id} 不存在於 cargo_data 中")
            positions.append(id_to_position[item_id])

        # 每搬一個貨物都要回出貨口：
        # 單件成本 = 出貨口 -> 貨位 + 貨位 -> 出貨口
        route_steps = 0
        return_steps = 0
        for pos in positions:
            outbound = int(self.step_counter.calculate_distance(start_position, pos) + 0.999999)
            inbound = int(self.step_counter.calculate_distance(pos, start_position) + 0.999999)
            route_steps += outbound
            return_steps += inbound

        stack_clear_steps = 0
        for pos in positions:
            column_key = f"{pos.x:.3f}-{pos.z:.3f}"
            blockers = sum(1 for candidate in column_positions.get(column_key, []) if candidate.y > pos.y)
            stack_clear_steps += blockers * 2

        total_steps = route_steps + return_steps + stack_clear_steps
        return total_steps, positions, return_steps, stack_clear_steps


    def get_cargo_layout(self) -> List[Dict]:
        """提供前端 2D 模擬用的倉庫貨位資料"""
        return self._load_cargo_data()

    async def run_benchmark(
        self, 
        order: BenchmarkOrder, 
        algorithm_names: List[str]
    ) -> BenchmarkResult:
        """
        執行 benchmark 測試
        
        Args:
            order: 測試訂單
            algorithm_names: 演算法名稱列表
            
        Returns:
            Benchmark 結果
        """
        # 前置條件檢查
        if not order.items:
            raise ValueError("訂單不能為空")
        
        if not algorithm_names:
            raise ValueError("至少需要一個演算法")
        
        # 載入貨物資料
        cargo_data = self._load_cargo_data()
        self._validate_order_items(order.items, cargo_data)
        
        # 初始化結果容器
        id_to_position, column_positions = self._build_cargo_indices(cargo_data)
        results = []
        best_step_count = float('inf')
        best_algorithm = None
        
        # 對每個演算法執行測試
        for algo_name in algorithm_names:
            start_time = time.perf_counter()
            
            # 獲取演算法實例
            algorithm = algorithm_registry.get(algo_name)
            
            # 計算路徑
            path = algorithm.calculate_path(order.items, cargo_data)
            
            start_position = Position3D(x=0, y=0, z=0)
            step_count, positions, _, _ = self._count_operational_steps(
                path,
                id_to_position,
                column_positions,
                start_position
            )
            
            end_time = time.perf_counter()
            execution_time = (end_time - start_time) * 1000  # 轉換為毫秒
            
            # 記錄結果
            result = AlgorithmResult(
                algorithm_name=algo_name,
                algorithm_type=algorithm.get_type(),
                step_count=step_count,
                execution_time_ms=execution_time,
                path=path,
                positions=positions
            )
            results.append(result)
            
            # 更新最佳結果
            if step_count < best_step_count:
                best_step_count = step_count
                best_algorithm = algo_name
        
        # 建立完整結果
        benchmark_result = BenchmarkResult(
            benchmark_id=str(uuid.uuid4()),
            order=order,
            results=results,
            best_algorithm=best_algorithm,
            best_step_count=int(best_step_count),
            timestamp=datetime.now(timezone.utc)
        )
        
        # 保存結果
        await self._save_result(benchmark_result)
        
        # 後置條件檢查
        assert len(results) == len(algorithm_names)
        assert best_algorithm in algorithm_names
        assert best_step_count == min(r.step_count for r in results)
        
        return benchmark_result
    
    async def _save_result(self, result: BenchmarkResult):
        """保存結果到檔案"""
        try:
            # 讀取現有結果
            with open(self.results_path, 'r', encoding='utf-8') as f:
                results = json.load(f)
            
            # 加入新結果
            result_dict = result.model_dump(mode='json')
            results.append(result_dict)
            
            # 保留最近 1000 筆
            if len(results) > 1000:
                results = results[-1000:]
            
            # 寫回檔案
            with open(self.results_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
        
        except Exception as e:
            print(f"保存結果失敗: {e}")
    
    async def get_history(
        self, 
        limit: int = 50, 
        algorithm_filter: Optional[str] = None
    ) -> List[BenchmarkResult]:
        """
        獲取歷史測試結果
        
        Args:
            limit: 返回結果數量限制
            algorithm_filter: 演算法名稱過濾器
            
        Returns:
            歷史結果列表
        """
        try:
            with open(self.results_path, 'r', encoding='utf-8') as f:
                results = json.load(f)
            
            # 過濾演算法
            if algorithm_filter:
                filtered_results = []
                for result in results:
                    has_algorithm = any(
                        r['algorithm_name'] == algorithm_filter 
                        for r in result['results']
                    )
                    if has_algorithm:
                        filtered_results.append(result)
                results = filtered_results
            
            # 限制數量（取最新的）
            results = results[-limit:]
            
            # 轉換為 Pydantic 模型
            return [BenchmarkResult(**r) for r in reversed(results)]
        
        except Exception as e:
            print(f"讀取歷史結果失敗: {e}")
            return []
    
    async def compare_algorithms(
        self, 
        algorithm_names: List[str], 
        test_orders: List[BenchmarkOrder]
    ) -> Dict[str, BenchmarkComparison]:
        """
        比較多個演算法的效能
        
        Args:
            algorithm_names: 演算法名稱列表
            test_orders: 測試訂單列表
            
        Returns:
            演算法比較結果字典
        """
        # 收集每個演算法的步數
        algorithm_steps: Dict[str, List[int]] = {name: [] for name in algorithm_names}
        
        # 對每個測試訂單執行 benchmark
        for order in test_orders:
            result = await self.run_benchmark(order, algorithm_names)
            
            for algo_result in result.results:
                algorithm_steps[algo_result.algorithm_name].append(algo_result.step_count)
        
        # 計算統計資料
        comparisons = {}
        baseline_avg = None
        
        for algo_name in algorithm_names:
            steps = algorithm_steps[algo_name]
            avg_steps = sum(steps) / len(steps) if steps else 0
            
            # 第一個演算法作為基準
            if baseline_avg is None:
                baseline_avg = avg_steps
            
            improvement = None
            if baseline_avg > 0 and algo_name != algorithm_names[0]:
                improvement = ((baseline_avg - avg_steps) / baseline_avg) * 100
            
            comparisons[algo_name] = BenchmarkComparison(
                algorithm_name=algo_name,
                average_steps=avg_steps,
                min_steps=min(steps) if steps else 0,
                max_steps=max(steps) if steps else 0,
                total_runs=len(steps),
                improvement_percentage=improvement
            )
        
        return comparisons
    
    async def optimize_all_orders(
        self,
        algorithm_names: List[str],
        max_items_per_batch: int = 20,
        num_vehicles: int = 2
    ) -> 'BatchOptimizationComparison':
        """
        批次優化所有訂單（支援多車並行）
        
        Args:
            algorithm_names: 演算法名稱列表
            max_items_per_batch: 每批次最大項目數
            num_vehicles: 車輛數量
            
        Returns:
            批次優化比較結果
        """
        from app.models.benchmark import (
            BatchOptimizationComparison, BatchOptimizationResult,
            BatchInfo, AlgorithmType
        )
        
        # 讀取所有訂單（從 main.py 的全局變量）
        try:
            from app.main import orders_db
            all_orders = orders_db.copy()
        except Exception as e:
            raise ValueError(f"無法讀取訂單列表: {e}")

        if not all_orders:
            raise ValueError("沒有可用的訂單")

        # 只取最高順位前 2 張訂單（以 id 最大視為最新、優先）
        source_orders = sorted(all_orders, key=lambda o: o.get('id', 0), reverse=True)[:2]

        # 合併這兩張訂單項目
        all_items = []
        for order in source_orders:
            items = order.get('items', [])
            all_items.extend(items)
        
        # 去重
        all_items = list(set(all_items))
        
        if not all_items:
            raise ValueError("訂單中沒有項目")
        
        # 載入貨物資料
        cargo_data = self._load_cargo_data()
        self._validate_order_items(all_items, cargo_data)
        
        id_to_position, column_positions = self._build_cargo_indices(cargo_data)

        # 對每個演算法執行批次優化
        results = []
        best_total_steps = float('inf')
        best_algorithm = None
        
        for algo_name in algorithm_names:
            start_time = time.perf_counter()
            
            # 獲取演算法實例
            algorithm = algorithm_registry.get(algo_name)
            
            # 特殊處理：原始順序演算法保持原訂單不變
            if algo_name == 'original':
                # 保持原訂單結構，顯示所有訂單
                batches = []
                total_steps = 0
                
                for idx, order in enumerate(source_orders):  # 顯示所有訂單
                    order_items = order.get('items', [])
                    
                    if not order_items:  # 跳過空訂單
                        continue
                    
                    start_position = Position3D(x=0, y=0, z=0)
                    steps, positions, _, _ = self._count_operational_steps(
                        order_items,
                        id_to_position,
                        column_positions,
                        start_position
                    )
                    
                    batch_info = BatchInfo(
                        batch_number=idx + 1,
                        items=order_items,
                        path=order_items,
                        step_count=steps,
                        positions=positions
                    )
                    batches.append(batch_info)
                    total_steps += steps  # 原始訂單是順序執行，所以是累加
                
                # 確保至少有一個批次
                if not batches:
                    batches.append(BatchInfo(
                        batch_number=1,
                        items=[],
                        path=[],
                        step_count=0,
                        positions=[]
                    ))
            
            else:
                # 其他演算法：合併所有項目並使用演算法排序
                optimized_path = algorithm.calculate_path(all_items, cargo_data)
                
                # 分成兩個訂單（對應兩台車）
                mid_point = len(optimized_path) // 2
                
                order1_items = optimized_path[:mid_point]
                order2_items = optimized_path[mid_point:]
                
                start_position = Position3D(x=0, y=0, z=0)
                order1_steps, order1_positions, _, _ = self._count_operational_steps(
                    order1_items,
                    id_to_position,
                    column_positions,
                    start_position
                )

                order2_steps, order2_positions, _, _ = self._count_operational_steps(
                    order2_items,
                    id_to_position,
                    column_positions,
                    start_position
                )
                
                # 總步數 = 兩台車並行，取最大值
                total_steps = max(order1_steps, order2_steps)
                
                # 創建兩個批次資訊
                batches = [
                    BatchInfo(
                        batch_number=1,
                        items=order1_items,
                        path=order1_items,
                        step_count=order1_steps,
                        positions=order1_positions
                    ),
                    BatchInfo(
                        batch_number=2,
                        items=order2_items,
                        path=order2_items,
                        step_count=order2_steps,
                        positions=order2_positions
                    )
                ]
            
            end_time = time.perf_counter()
            execution_time = (end_time - start_time) * 1000
            
            # 創建批次優化結果
            result = BatchOptimizationResult(
                algorithm_name=algo_name,
                algorithm_type=algorithm.get_type(),
                total_batches=len(batches),
                batches=batches,
                total_steps=total_steps,
                execution_time_ms=execution_time,
                total_items=len(all_items) if algo_name != 'original' else sum(len(b.items) for b in batches)
            )
            
            results.append(result)
            
            # 更新最佳結果
            if total_steps < best_total_steps:
                best_total_steps = total_steps
                best_algorithm = algo_name
        
        # 創建比較結果
        comparison = BatchOptimizationComparison(
            optimization_id=str(uuid.uuid4()),
            source_orders=[
                {
                    'id': o.get('id'),
                    'content': o.get('content'),
                    'items': o.get('items', [])
                }
                for o in source_orders
            ],
            results=results,
            best_algorithm=best_algorithm,
            best_total_steps=best_total_steps,
            timestamp=datetime.now(timezone.utc)
        )
        
        return comparison


# 全域單例
benchmark_service = BenchmarkService()
