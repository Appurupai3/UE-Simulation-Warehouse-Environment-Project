from fastapi import APIRouter, HTTPException
from typing import List, Optional
from pydantic import BaseModel, Field

from app.models.benchmark import BenchmarkOrder, BenchmarkResult, BenchmarkComparison
from app.services.benchmark_service import benchmark_service


router = APIRouter(prefix="/benchmark", tags=["benchmark"])


class RunBenchmarkRequest(BaseModel):
    """執行 Benchmark 請求"""
    order: BenchmarkOrder
    algorithms: List[str] = Field(..., description="演算法名稱列表")


class CompareBenchmarkRequest(BaseModel):
    """比較演算法請求"""
    algorithms: List[str] = Field(..., description="演算法名稱列表")
    test_orders: List[BenchmarkOrder] = Field(..., description="測試訂單列表")


@router.post("/run", response_model=BenchmarkResult)
async def run_benchmark(request: RunBenchmarkRequest):
    """
    執行 Benchmark 測試
    
    Args:
        request: Benchmark 請求
        
    Returns:
        Benchmark 結果
    """
    try:
        result = await benchmark_service.run_benchmark(
            order=request.order,
            algorithm_names=request.algorithms
        )
        
        # 透過 WebSocket 廣播結果
        # Note: WebSocket broadcast is handled in main.py
        # We'll import it dynamically to avoid circular imports
        try:
            from app.main import broadcast_to_all
            await broadcast_to_all({
                "type": "benchmark_completed",
                "result": result.model_dump(mode='json')
            })
        except Exception as broadcast_error:
            # Log but don't fail the request if broadcast fails
            import logging
            logging.getLogger(__name__).warning(f"Failed to broadcast benchmark result: {broadcast_error}")
        
        return result
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"執行 Benchmark 失敗: {str(e)}")


@router.get("/history", response_model=List[BenchmarkResult])
async def get_history(
    limit: int = 50,
    algorithm: Optional[str] = None
):
    """
    獲取歷史 Benchmark 結果
    
    Args:
        limit: 返回結果數量限制
        algorithm: 演算法名稱過濾器（可選）
        
    Returns:
        歷史結果列表
    """
    try:
        results = await benchmark_service.get_history(
            limit=limit,
            algorithm_filter=algorithm
        )
        return results
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取歷史結果失敗: {str(e)}")


@router.post("/compare", response_model=dict)
async def compare_algorithms(request: CompareBenchmarkRequest):
    """
    比較多個演算法的效能
    
    Args:
        request: 比較請求
        
    Returns:
        演算法比較結果
    """
    try:
        comparisons = await benchmark_service.compare_algorithms(
            algorithm_names=request.algorithms,
            test_orders=request.test_orders
        )
        
        # 轉換為可序列化的格式
        result = {
            name: comp.model_dump(mode='json')
            for name, comp in comparisons.items()
        }
        
        return result
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"比較演算法失敗: {str(e)}")



@router.get("/cargo-layout", response_model=dict)
async def get_cargo_layout():
    """提供前端 2D 模擬畫布使用的倉庫原始佈局資料"""
    try:
        cargo = benchmark_service.get_cargo_layout()
        return {"cargo": cargo, "total": len(cargo)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得 cargo layout 失敗: {str(e)}")


class OptimizeOrdersRequest(BaseModel):
    """批次優化請求"""
    algorithms: List[str] = Field(default=["greedy", "sequential", "reverse"], description="演算法列表")
    max_items_per_batch: int = Field(default=20, gt=0, description="每批次最大項目數")
    num_vehicles: int = Field(default=2, gt=0, description="可並行作業的車輛數")


@router.post("/optimize-orders", response_model=dict)
async def optimize_all_orders(request: OptimizeOrdersRequest):
    """
    批次優化所有訂單
    
    讀取所有現有訂單，合併項目，使用不同演算法進行批次優化
    
    Args:
        request: 批次優化請求
        
    Returns:
        批次優化比較結果
    """
    try:
        result = await benchmark_service.optimize_all_orders(
            algorithm_names=request.algorithms,
            max_items_per_batch=request.max_items_per_batch,
            num_vehicles=request.num_vehicles
        )
        
        return result.model_dump(mode='json')
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批次優化失敗: {str(e)}")
