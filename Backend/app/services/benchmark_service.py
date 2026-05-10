import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, List, Dict, Optional, Tuple
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

    def _dedupe_items_preserve_order(self, items: List[int]) -> List[int]:
        """去重但保留第一次出現順序，確保所有演算法拿到同一批 item。"""
        deduped: List[int] = []
        seen = set()
        for item_id in items:
            if item_id in seen:
                continue
            seen.add(item_id)
            deduped.append(item_id)
        return deduped

    def _ceil_distance(self, pos1: Position3D, pos2: Position3D) -> int:
        """計算兩點間距離並向上取整成步數。"""
        return int(self.step_counter.calculate_distance(pos1, pos2) + 0.999999)

    def _resolve_path_positions(
        self,
        path: List[int],
        id_to_position: Dict[int, Position3D]
    ) -> List[Position3D]:
        """把 item id 路徑轉成貨位路徑。"""
        positions: List[Position3D] = []
        for item_id in path:
            if item_id not in id_to_position:
                raise ValueError(f"項目 {item_id} 不存在於 cargo_data 中")
            positions.append(id_to_position[item_id])
        return positions

    def _count_stack_clear_steps(
        self,
        positions: List[Position3D],
        column_positions: Dict[str, List[Position3D]]
    ) -> int:
        """估算搬離同 x/z 欄位上方阻擋物的額外步數。"""
        stack_clear_steps = 0
        for pos in positions:
            column_key = f"{pos.x:.3f}-{pos.z:.3f}"
            blockers = sum(1 for candidate in column_positions.get(column_key, []) if candidate.y > pos.y)
            stack_clear_steps += blockers * 2
        return stack_clear_steps

    def _count_single_item_round_trip_steps(
        self,
        path: List[int],
        id_to_position: Dict[int, Position3D],
        column_positions: Dict[str, List[Position3D]],
        start_position: Position3D
    ) -> Tuple[int, List[Position3D], int, int]:
        """
        單件往返成本：每件貨物都獨立執行 dock -> item -> dock。

        這個模式會保留既有公式，但它不會反映排序演算法的順序差異，
        因此只適合估算單件搬運成本，不適合拿來評排序演算法。
        """
        positions = self._resolve_path_positions(path, id_to_position)

        route_steps = 0
        return_steps = 0
        for pos in positions:
            outbound = self._ceil_distance(start_position, pos)
            inbound = self._ceil_distance(pos, start_position)
            route_steps += outbound
            return_steps += inbound

        stack_clear_steps = self._count_stack_clear_steps(positions, column_positions)
        total_steps = route_steps + return_steps + stack_clear_steps
        return total_steps, positions, return_steps, stack_clear_steps

    def _count_continuous_route_steps(
        self,
        path: List[int],
        id_to_position: Dict[int, Position3D],
        column_positions: Dict[str, List[Position3D]],
        start_position: Position3D
    ) -> Tuple[int, List[Position3D], int, int]:
        """
        單車連續路徑成本：dock -> item1 -> item2 -> ... -> dock。

        此模式會將相鄰 item 的移動距離納入成本，排序演算法輸出的順序
        才會實際影響分數，是一般 benchmark 排序演算法的預設計分方式。
        """
        positions = self._resolve_path_positions(path, id_to_position)
        if not positions:
            return 0, positions, 0, 0

        route_steps = 0
        current_position = start_position
        for pos in positions:
            route_steps += self._ceil_distance(current_position, pos)
            current_position = pos

        return_steps = self._ceil_distance(current_position, start_position)
        stack_clear_steps = self._count_stack_clear_steps(positions, column_positions)
        total_steps = route_steps + return_steps + stack_clear_steps
        return total_steps, positions, return_steps, stack_clear_steps

    def _count_operational_steps(
        self,
        path: List[int],
        id_to_position: Dict[int, Position3D],
        column_positions: Dict[str, List[Position3D]],
        start_position: Position3D,
        mode: str = "continuous_route"
    ) -> Tuple[int, List[Position3D], int, int]:
        """
        計算 operational steps。

        支援兩種模式：
        - continuous_route：單車連續路徑，dock -> item1 -> item2 -> ... -> dock。
        - single_item_round_trip：單件往返成本，每件 item 都 dock -> item -> dock。
        """
        if mode == "continuous_route":
            return self._count_continuous_route_steps(
                path, id_to_position, column_positions, start_position
            )
        if mode == "single_item_round_trip":
            return self._count_single_item_round_trip_steps(
                path, id_to_position, column_positions, start_position
            )
        raise ValueError(
            "未知的步數模式: "
            f"{mode}，可用模式: continuous_route, single_item_round_trip"
        )

    def _build_costed_batch(
        self,
        batch_number: int,
        items: List[int],
        id_to_position: Dict[int, Position3D],
        column_positions: Dict[str, List[Position3D]],
        start_position: Position3D,
        step_mode: str = "continuous_route"
    ):
        """建立含步數與位置的 BatchInfo。"""
        from app.models.benchmark import BatchInfo

        steps, positions, return_steps, stack_clear_steps = self._count_operational_steps(
            items,
            id_to_position,
            column_positions,
            start_position,
            mode=step_mode
        )
        return BatchInfo(
            batch_number=batch_number,
            items=items,
            path=items,
            step_count=steps,
            positions=positions,
            metadata={
                "step_mode": step_mode,
                "return_steps": return_steps,
                "stack_clear_steps": stack_clear_steps
            }
        )

    def _assign_path_to_vehicle_batches(
        self,
        path: List[int],
        id_to_position: Dict[int, Position3D],
        column_positions: Dict[str, List[Position3D]],
        max_items_per_batch: int,
        num_vehicles: int,
        start_position: Position3D,
        step_mode: str = "continuous_route"
    ) -> Tuple[List[Any], Dict[str, Any]]:
        """
        依照成本函數把排序後路徑分配到多車批次。

        每一 wave 最多有 num_vehicles 個 batch；每個 batch 最多
        max_items_per_batch 件。若 item 數超過單 wave 容量，會產生下一 wave。
        在每一 wave 內使用 greedy list scheduling：每次把下一個 item 放到
        增量成本最低的可用車輛，避免固定從中間硬切兩半。
        """
        if max_items_per_batch <= 0:
            raise ValueError("max_items_per_batch 必須大於 0")
        if num_vehicles <= 0:
            raise ValueError("num_vehicles 必須大於 0")

        batches = []
        waves = []
        cursor = 0
        batch_number = 1
        wave_number = 1

        while cursor < len(path):
            wave_items = path[cursor:cursor + max_items_per_batch * num_vehicles]
            cursor += len(wave_items)

            vehicle_paths: List[List[int]] = [[] for _ in range(num_vehicles)]
            vehicle_costs = [0 for _ in range(num_vehicles)]

            for item_id in wave_items:
                best_vehicle = None
                best_candidate_cost = None

                for vehicle_idx, vehicle_path in enumerate(vehicle_paths):
                    if len(vehicle_path) >= max_items_per_batch:
                        continue

                    candidate_path = vehicle_path + [item_id]
                    candidate_cost, _, _, _ = self._count_operational_steps(
                        candidate_path,
                        id_to_position,
                        column_positions,
                        start_position,
                        mode=step_mode
                    )
                    incremental_cost = candidate_cost - vehicle_costs[vehicle_idx]
                    tie_breaker = (incremental_cost, candidate_cost, len(vehicle_path), vehicle_idx)

                    if best_candidate_cost is None or tie_breaker < best_candidate_cost:
                        best_candidate_cost = tie_breaker
                        best_vehicle = vehicle_idx

                if best_vehicle is None:
                    raise ValueError("無法分配 item，請檢查 max_items_per_batch 與 num_vehicles")

                vehicle_paths[best_vehicle].append(item_id)
                vehicle_costs[best_vehicle], _, _, _ = self._count_operational_steps(
                    vehicle_paths[best_vehicle],
                    id_to_position,
                    column_positions,
                    start_position,
                    mode=step_mode
                )

            wave_batch_numbers = []
            for vehicle_idx, vehicle_path in enumerate(vehicle_paths):
                if not vehicle_path:
                    continue

                batch = self._build_costed_batch(
                    batch_number,
                    vehicle_path,
                    id_to_position,
                    column_positions,
                    start_position,
                    step_mode=step_mode
                )
                batch.metadata.update({
                    "vehicle_number": vehicle_idx + 1,
                    "wave_number": wave_number,
                    "max_items_per_batch": max_items_per_batch
                })
                batches.append(batch)
                wave_batch_numbers.append(batch_number)
                batch_number += 1

            waves.append({
                "wave_number": wave_number,
                "batch_numbers": wave_batch_numbers,
                "duration_steps": max(vehicle_costs) if vehicle_costs else 0
            })
            wave_number += 1

        return batches, {
            "num_vehicles": num_vehicles,
            "max_items_per_batch": max_items_per_batch,
            "waves": waves,
            "step_mode": step_mode,
            "assignment_strategy": "greedy_incremental_cost"
        }

    def _estimate_parallel_simulation_cost(
        self,
        batches: List[Any],
        assignment_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        估算與 2D 多車避碰展示更一致的排名成本。

        後端目前沒有前端逐 frame 模擬器；這裡以每個 wave 的並行 makespan
        為基礎，再加入同 wave 多車訪問相同 aisle/column 時的等待懲罰。
        """
        total_time_steps = 0
        waiting_events = 0
        collision_avoidance_steps = 0

        by_wave: Dict[int, List[Any]] = {}
        for batch in batches:
            wave_number = batch.metadata.get("wave_number", 1)
            by_wave.setdefault(wave_number, []).append(batch)

        for wave_number in sorted(by_wave):
            wave_batches = by_wave[wave_number]
            total_time_steps += max((batch.step_count for batch in wave_batches), default=0)

            occupied_columns: Dict[str, int] = {}
            for batch in wave_batches:
                for pos in batch.positions:
                    column_key = f"{pos.x:.3f}-{pos.z:.3f}"
                    occupied_columns[column_key] = occupied_columns.get(column_key, 0) + 1

            conflicts = sum(count - 1 for count in occupied_columns.values() if count > 1)
            waiting_events += conflicts
            collision_avoidance_steps += conflicts * 2

        simulation_total_steps = total_time_steps + collision_avoidance_steps
        return {
            **assignment_metadata,
            "ranking_cost_mode": "parallel_2d_simulation_estimate",
            "total_time_steps": total_time_steps,
            "waiting_events": waiting_events,
            "collision_avoidance_steps": collision_avoidance_steps,
            "simulation_total_steps": simulation_total_steps
        }

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
        
        # 載入貨物資料，並統一所有排序演算法的輸入條件：
        # benchmark/run 比較的是「同一批 item 的排序」，重複 item 只計一次。
        cargo_data = self._load_cargo_data()
        benchmark_items = self._dedupe_items_preserve_order(order.items)
        self._validate_order_items(benchmark_items, cargo_data)
        
        # 初始化結果容器
        id_to_position, column_positions = self._build_cargo_indices(cargo_data)
        step_mode = "continuous_route"
        results = []
        best_step_count = float('inf')
        best_algorithm = None
        
        # 對每個演算法執行測試
        for algo_name in algorithm_names:
            start_time = time.perf_counter()
            
            # 獲取演算法實例
            algorithm = algorithm_registry.get(algo_name)
            
            # 計算路徑
            path = algorithm.calculate_path(benchmark_items, cargo_data)
            
            start_position = Position3D(x=0, y=0, z=0)
            step_count, positions, return_steps, stack_clear_steps = self._count_operational_steps(
                path,
                id_to_position,
                column_positions,
                start_position,
                mode=step_mode
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
                positions=positions,
                metadata={
                    "step_mode": step_mode,
                    "input_policy": "same_unique_items_preserve_first_seen_order",
                    "original_item_count": len(order.items),
                    "scored_item_count": len(benchmark_items),
                    "duplicates_removed": len(order.items) - len(benchmark_items),
                    "return_steps": return_steps,
                    "stack_clear_steps": stack_clear_steps
                }
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

        本 API 比較的是「多訂單合併 + 去重成同一批 item + 分車 + 排序」。
        重複 item 以同一貨位只取一次處理；original 與其他演算法都使用
        同一份去重後輸入，避免不同基準混在一起。
        """
        from app.models.benchmark import BatchOptimizationComparison, BatchOptimizationResult

        if max_items_per_batch <= 0:
            raise ValueError("max_items_per_batch 必須大於 0")
        if num_vehicles <= 0:
            raise ValueError("num_vehicles 必須大於 0")
        if not algorithm_names:
            raise ValueError("至少需要一個演算法")

        # 讀取所有訂單（從 main.py 的全局變量）
        try:
            from app.main import orders_db
            all_orders = orders_db.copy()
        except Exception as e:
            raise ValueError(f"無法讀取訂單列表: {e}")

        if not all_orders:
            raise ValueError("沒有可用的訂單")

        # 使用所有可用訂單，依 id 由新到舊保留來源順序；不再固定只取兩張。
        source_orders = sorted(all_orders, key=lambda o: o.get('id', 0), reverse=True)

        merged_items: List[int] = []
        for order in source_orders:
            merged_items.extend(order.get('items', []))

        all_items = self._dedupe_items_preserve_order(merged_items)
        if not all_items:
            raise ValueError("訂單中沒有項目")

        # 載入貨物資料
        cargo_data = self._load_cargo_data()
        self._validate_order_items(all_items, cargo_data)

        id_to_position, column_positions = self._build_cargo_indices(cargo_data)
        start_position = Position3D(x=0, y=0, z=0)
        step_mode = "continuous_route"
        input_policy = {
            "comparison_scope": "merge_orders_dedupe_split_vehicles_and_sort",
            "duplicate_item_policy": "count_once_preserve_first_seen_order",
            "source_order_count": len(source_orders),
            "original_item_count": len(merged_items),
            "scored_item_count": len(all_items),
            "duplicates_removed": len(merged_items) - len(all_items),
            "step_mode": step_mode,
            "ranking_cost_mode": "parallel_2d_simulation_estimate"
        }

        # 對每個演算法執行批次優化
        results = []
        best_total_steps = float('inf')
        best_algorithm = None

        for algo_name in algorithm_names:
            start_time = time.perf_counter()
            algorithm = algorithm_registry.get(algo_name)

            # 所有演算法（包含 original）都吃同一份去重後的 item 清單。
            optimized_path = algorithm.calculate_path(all_items, cargo_data)
            batches, assignment_metadata = self._assign_path_to_vehicle_batches(
                optimized_path,
                id_to_position,
                column_positions,
                max_items_per_batch=max_items_per_batch,
                num_vehicles=num_vehicles,
                start_position=start_position,
                step_mode=step_mode
            )
            simulation_metadata = self._estimate_parallel_simulation_cost(batches, assignment_metadata)
            total_steps = simulation_metadata["simulation_total_steps"]

            end_time = time.perf_counter()
            execution_time = (end_time - start_time) * 1000

            result = BatchOptimizationResult(
                algorithm_name=algo_name,
                algorithm_type=algorithm.get_type(),
                total_batches=len(batches),
                batches=batches,
                total_steps=total_steps,
                execution_time_ms=execution_time,
                total_items=len(all_items),
                metadata={
                    **input_policy,
                    **simulation_metadata,
                    "optimized_path": optimized_path
                }
            )

            results.append(result)

            if total_steps < best_total_steps:
                best_total_steps = total_steps
                best_algorithm = algo_name

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
            timestamp=datetime.now(timezone.utc),
            input_policy=input_policy
        )

        return comparison

# 全域單例
benchmark_service = BenchmarkService()
