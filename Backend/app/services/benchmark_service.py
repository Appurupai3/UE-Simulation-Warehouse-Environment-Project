import json
import math
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
    
    def _stable_unique_items_with_sources(self, source_orders: List[Dict]) -> Tuple[List[int], Dict[int, List[int]]]:
        """依訂單優先順序保留第一次出現的 item，並記錄涵蓋的來源訂單。"""
        ordered_items: List[int] = []
        item_sources: Dict[int, List[int]] = {}
        seen = set()

        for order in source_orders:
            order_id = order.get('id')
            for item in order.get('items', []):
                if item not in seen:
                    seen.add(item)
                    ordered_items.append(item)
                if order_id is not None:
                    item_sources.setdefault(item, [])
                    if order_id not in item_sources[item]:
                        item_sources[item].append(order_id)

        return ordered_items, item_sources

    def _count_route_steps(
        self,
        path: List[int],
        id_to_position: Dict[int, Position3D],
        column_positions: Dict[str, List[Position3D]],
        start_position: Position3D
    ) -> Tuple[int, List[Position3D], int]:
        """計算會受訪問順序影響的路線成本：起點 -> 各貨位 -> 起點 + 堆疊搬離成本。"""
        positions: List[Position3D] = []
        for item_id in path:
            if item_id not in id_to_position:
                raise ValueError(f"項目 {item_id} 不存在於 cargo_data 中")
            positions.append(id_to_position[item_id])

        travel_steps = self.step_counter.count_steps(positions, start_position)
        if positions:
            travel_steps += math.ceil(self.step_counter.calculate_distance(positions[-1], start_position))

        stack_clear_steps = 0
        for pos in positions:
            column_key = f"{pos.x:.3f}-{pos.z:.3f}"
            blockers = sum(1 for candidate in column_positions.get(column_key, []) if candidate.y > pos.y)
            stack_clear_steps += blockers * 2

        return travel_steps + stack_clear_steps, positions, stack_clear_steps

    def _route_cost_for_items(
        self,
        route: List[int],
        id_to_position: Dict[int, Position3D],
        column_positions: Dict[str, List[Position3D]],
        start_position: Position3D
    ) -> int:
        steps, _, _ = self._count_route_steps(route, id_to_position, column_positions, start_position)
        return steps

    def _improve_route_two_opt(
        self,
        route: List[int],
        id_to_position: Dict[int, Position3D],
        column_positions: Dict[str, List[Position3D]],
        start_position: Position3D
    ) -> List[int]:
        """用簡化 2-opt 改善單車路線，避免窮舉過久而限制迭代次數。"""
        if len(route) < 4:
            return route

        best_route = route[:]
        best_cost = self._route_cost_for_items(best_route, id_to_position, column_positions, start_position)
        improved = True
        passes = 0

        while improved and passes < 3:
            improved = False
            passes += 1
            for i in range(len(best_route) - 2):
                for j in range(i + 2, len(best_route) + 1):
                    candidate = best_route[:i] + list(reversed(best_route[i:j])) + best_route[j:]
                    candidate_cost = self._route_cost_for_items(candidate, id_to_position, column_positions, start_position)
                    if candidate_cost < best_cost:
                        best_route = candidate
                        best_cost = candidate_cost
                        improved = True
                        break
                if improved:
                    break

        return best_route

    def _rebalance_vehicle_routes(
        self,
        vehicles: List[Dict],
        id_to_position: Dict[int, Position3D],
        column_positions: Dict[str, List[Position3D]],
        start_position: Position3D
    ) -> List[Dict]:
        """在車輛之間搬移單一 item，只接受能降低 makespan 的調整。"""
        if len(vehicles) < 2:
            return vehicles

        for _ in range(20):
            current_makespan = max(vehicle.get('finish_time', 0) for vehicle in vehicles)
            best_move = None

            for source_index, source in enumerate(vehicles):
                if len(source['route']) <= 1:
                    continue
                for item_index, item in enumerate(source['route']):
                    source_candidate = source['route'][:item_index] + source['route'][item_index + 1:]
                    source_cost = self._route_cost_for_items(
                        source_candidate,
                        id_to_position,
                        column_positions,
                        start_position
                    )

                    for target_index, target in enumerate(vehicles):
                        if target_index == source_index:
                            continue
                        for insert_index in range(len(target['route']) + 1):
                            target_candidate = target['route'][:insert_index] + [item] + target['route'][insert_index:]
                            target_cost = self._route_cost_for_items(
                                target_candidate,
                                id_to_position,
                                column_positions,
                                start_position
                            )
                            candidate_finish_times = [v.get('finish_time', 0) for v in vehicles]
                            candidate_finish_times[source_index] = source_cost
                            candidate_finish_times[target_index] = target_cost
                            candidate_makespan = max(candidate_finish_times)

                            if candidate_makespan >= current_makespan:
                                continue

                            improvement = current_makespan - candidate_makespan
                            if best_move is None or improvement > best_move['improvement']:
                                best_move = {
                                    'improvement': improvement,
                                    'source_index': source_index,
                                    'target_index': target_index,
                                    'source_route': source_candidate,
                                    'target_route': target_candidate,
                                    'source_cost': source_cost,
                                    'target_cost': target_cost
                                }

            if best_move is None:
                break

            source = vehicles[best_move['source_index']]
            target = vehicles[best_move['target_index']]
            source['route'] = best_move['source_route']
            source['finish_time'] = best_move['source_cost']
            target['route'] = best_move['target_route']
            target['finish_time'] = best_move['target_cost']

        return vehicles

    def _build_vehicle_routes(
        self,
        ordered_items: List[int],
        num_vehicles: int,
        id_to_position: Dict[int, Position3D],
        column_positions: Dict[str, List[Position3D]],
        start_position: Position3D
    ) -> List[Dict]:
        """以最小邊際成本 + makespan 平衡，把 item 插入多台車路線。"""
        vehicles = [
            {
                'vehicle_id': f'car-{idx + 1}',
                'route': [],
                'finish_time': 0,
                'positions': []
            }
            for idx in range(num_vehicles)
        ]

        for item in ordered_items:
            best_move = None

            for vehicle_index, vehicle in enumerate(vehicles):
                current_route = vehicle['route']
                current_cost = self._route_cost_for_items(
                    current_route,
                    id_to_position,
                    column_positions,
                    start_position
                )

                for insert_index in range(len(current_route) + 1):
                    candidate_route = current_route[:insert_index] + [item] + current_route[insert_index:]
                    candidate_cost = self._route_cost_for_items(
                        candidate_route,
                        id_to_position,
                        column_positions,
                        start_position
                    )
                    candidate_finish_times = [v['finish_time'] for v in vehicles]
                    candidate_finish_times[vehicle_index] = candidate_cost
                    makespan = max(candidate_finish_times) if candidate_finish_times else candidate_cost
                    average = sum(candidate_finish_times) / len(candidate_finish_times)
                    balance = math.sqrt(
                        sum((finish_time - average) ** 2 for finish_time in candidate_finish_times) /
                        len(candidate_finish_times)
                    )
                    delta = candidate_cost - current_cost
                    score = delta + makespan * 0.35 + balance * 0.2

                    if best_move is None or score < best_move['score']:
                        best_move = {
                            'score': score,
                            'vehicle_index': vehicle_index,
                            'route': candidate_route,
                            'finish_time': candidate_cost
                        }

            if best_move is None:
                continue

            target = vehicles[best_move['vehicle_index']]
            target['route'] = best_move['route']
            target['finish_time'] = best_move['finish_time']

        for vehicle in vehicles:
            improved_route = self._improve_route_two_opt(
                vehicle['route'],
                id_to_position,
                column_positions,
                start_position
            )
            steps, _, _ = self._count_route_steps(
                improved_route,
                id_to_position,
                column_positions,
                start_position
            )
            vehicle['route'] = improved_route
            vehicle['finish_time'] = steps

        vehicles = self._rebalance_vehicle_routes(
            vehicles,
            id_to_position,
            column_positions,
            start_position
        )

        for vehicle in vehicles:
            improved_route = self._improve_route_two_opt(
                vehicle['route'],
                id_to_position,
                column_positions,
                start_position
            )
            steps, positions, stack_clear_steps = self._count_route_steps(
                improved_route,
                id_to_position,
                column_positions,
                start_position
            )
            vehicle['route'] = improved_route
            vehicle['finish_time'] = steps
            vehicle['travel_steps'] = steps
            vehicle['stack_clear_steps'] = stack_clear_steps
            vehicle['positions'] = positions

        return vehicles

    def _split_vehicle_batches(
        self,
        vehicles: List[Dict],
        max_items_per_batch: int,
        id_to_position: Dict[int, Position3D],
        column_positions: Dict[str, List[Position3D]],
        item_sources: Dict[int, List[int]],
        start_position: Position3D
    ) -> List['BatchInfo']:
        from app.models.benchmark import BatchInfo

        batches = []
        batch_number = 1
        for vehicle in vehicles:
            route = vehicle['route']
            for start in range(0, len(route), max_items_per_batch):
                batch_items = route[start:start + max_items_per_batch]
                steps, positions, _ = self._count_route_steps(
                    batch_items,
                    id_to_position,
                    column_positions,
                    start_position
                )
                source_order_ids = sorted({
                    order_id
                    for item in batch_items
                    for order_id in item_sources.get(item, [])
                })
                batches.append(BatchInfo(
                    batch_number=batch_number,
                    vehicle_id=vehicle['vehicle_id'],
                    source_order_ids=source_order_ids,
                    items=batch_items,
                    path=batch_items,
                    step_count=steps,
                    positions=positions
                ))
                batch_number += 1

        if not batches:
            batches.append(BatchInfo(
                batch_number=1,
                vehicle_id='car-1',
                source_order_ids=[],
                items=[],
                path=[],
                step_count=0,
                positions=[]
            ))

        return batches

    def _workload_balance(self, vehicles: List[Dict]) -> float:
        finish_times = [vehicle.get('finish_time', 0) for vehicle in vehicles]
        if not finish_times:
            return 0
        average = sum(finish_times) / len(finish_times)
        return math.sqrt(sum((finish_time - average) ** 2 for finish_time in finish_times) / len(finish_times))

    async def optimize_all_orders(
        self,
        algorithm_names: List[str],
        max_items_per_batch: int = 20,
        num_vehicles: int = 2
    ) -> 'BatchOptimizationComparison':
        """
        批次優化所有訂單（支援多車並行）：
        1. 穩定合併訂單 item 並保留來源訂單。
        2. 用演算法產生處理順序。
        3. 以最小邊際成本將 item 插入多台車路線。
        4. 對每台車做 2-opt 微調，再依容量切批。
        """
        from app.models.benchmark import (
            BatchOptimizationComparison, BatchOptimizationResult
        )

        if not algorithm_names:
            raise ValueError("至少需要一個演算法")
        if max_items_per_batch < 1:
            raise ValueError("每批次最大項目數必須大於 0")
        if num_vehicles < 1:
            raise ValueError("車輛數量必須大於 0")

        # 讀取所有訂單（從 main.py 的全局變量）
        try:
            from app.main import orders_db
            all_orders = orders_db.copy()
        except Exception as e:
            raise ValueError(f"無法讀取訂單列表: {e}")

        if not all_orders:
            raise ValueError("沒有可用的訂單")

        # 依 id 由小到大保留實際建立順序；若缺 id 則維持原始相對位置。
        source_orders = sorted(all_orders, key=lambda order: order.get('id', 0))
        all_items, item_sources = self._stable_unique_items_with_sources(source_orders)

        if not all_items:
            raise ValueError("訂單中沒有項目")

        cargo_data = self._load_cargo_data()
        self._validate_order_items(all_items, cargo_data)

        id_to_position, column_positions = self._build_cargo_indices(cargo_data)
        start_position = Position3D(x=0, y=0, z=0)

        results = []
        best_total_steps = float('inf')
        best_algorithm = None

        for algo_name in algorithm_names:
            start_time = time.perf_counter()
            algorithm = algorithm_registry.get(algo_name)

            if algo_name == 'original':
                ordered_path = all_items[:]
            else:
                ordered_path = algorithm.calculate_path(all_items, cargo_data)

            vehicles = self._build_vehicle_routes(
                ordered_path,
                num_vehicles,
                id_to_position,
                column_positions,
                start_position
            )
            batches = self._split_vehicle_batches(
                vehicles,
                max_items_per_batch,
                id_to_position,
                column_positions,
                item_sources,
                start_position
            )

            finish_times = [vehicle.get('finish_time', 0) for vehicle in vehicles]
            makespan = max(finish_times) if finish_times else 0
            total_travel_steps = sum(finish_times)
            workload_balance = self._workload_balance(vehicles)
            vehicle_routes = [
                {
                    'vehicle_id': vehicle['vehicle_id'],
                    'items': vehicle['route'],
                    'step_count': vehicle.get('finish_time', 0),
                    'stack_clear_steps': vehicle.get('stack_clear_steps', 0),
                    'batch_count': sum(1 for batch in batches if batch.vehicle_id == vehicle['vehicle_id'])
                }
                for vehicle in vehicles
            ]

            end_time = time.perf_counter()
            execution_time = (end_time - start_time) * 1000

            result = BatchOptimizationResult(
                algorithm_name=algo_name,
                algorithm_type=algorithm.get_type(),
                total_batches=len(batches),
                batches=batches,
                total_steps=int(makespan),
                execution_time_ms=execution_time,
                total_items=len(all_items),
                vehicle_count=num_vehicles,
                total_travel_steps=int(total_travel_steps),
                workload_balance=workload_balance,
                vehicle_routes=vehicle_routes
            )

            results.append(result)

            if makespan < best_total_steps:
                best_total_steps = makespan
                best_algorithm = algo_name

        comparison = BatchOptimizationComparison(
            optimization_id=str(uuid.uuid4()),
            source_orders=[
                {
                    'id': order.get('id'),
                    'content': order.get('content'),
                    'items': order.get('items', [])
                }
                for order in source_orders
            ],
            results=results,
            best_algorithm=best_algorithm,
            best_total_steps=int(best_total_steps),
            timestamp=datetime.now(timezone.utc)
        )

        return comparison

# 全域單例
benchmark_service = BenchmarkService()
