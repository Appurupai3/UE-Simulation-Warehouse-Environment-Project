from fastapi import APIRouter, HTTPException
from typing import List

from app.models.benchmark import (
    AlgorithmTemplate, CodeValidationRequest, CodeValidationResult,
    CodeExecutionRequest, CodeExecutionResult
)
from app.services.template_manager import template_manager
from app.services.code_validator import code_validator
from app.services.sandbox_executor import sandbox_executor


router = APIRouter(prefix="/algorithms", tags=["algorithms"])


@router.get("/templates", response_model=List[AlgorithmTemplate])
async def get_templates():
    """
    獲取所有演算法模板
    
    Returns:
        模板列表
    """
    try:
        templates = template_manager.list_templates()
        return templates
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取模板列表失敗: {str(e)}")


@router.get("/templates/{name}", response_model=AlgorithmTemplate)
async def get_template(name: str):
    """
    獲取特定演算法模板
    
    Args:
        name: 模板名稱
        
    Returns:
        模板物件
    """
    try:
        template = template_manager.get_template(name)
        
        if template is None:
            raise HTTPException(
                status_code=404,
                detail=f"模板 '{name}' 不存在"
            )
        
        return template
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取模板失敗: {str(e)}")


@router.post("/validate", response_model=CodeValidationResult)
async def validate_code(request: CodeValidationRequest):
    """
    驗證程式碼語法和安全性
    
    Args:
        request: 驗證請求
        
    Returns:
        驗證結果
    """
    try:
        # 檢查程式碼長度
        if len(request.code) > 10000:
            raise HTTPException(
                status_code=400,
                detail="程式碼長度超過限制（最多 10000 字元）"
            )
        
        result = code_validator.validate_code(request.code)
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"驗證程式碼失敗: {str(e)}")


@router.post("/execute", response_model=CodeExecutionResult)
async def execute_code(request: CodeExecutionRequest):
    """
    執行程式碼
    
    Args:
        request: 執行請求
        
    Returns:
        執行結果
    """
    try:
        # 檢查程式碼長度
        if len(request.code) > 10000:
            raise HTTPException(
                status_code=400,
                detail="程式碼長度超過限制（最多 10000 字元）"
            )
        
        # 檢查訂單項目數量
        if len(request.order.items) > 100:
            raise HTTPException(
                status_code=400,
                detail="訂單項目數量超過限制（最多 100 項）"
            )
        
        # 先驗證程式碼
        validation_result = code_validator.validate_code(request.code)
        
        if not validation_result.valid:
            return CodeExecutionResult(
                success=False,
                error_message="程式碼驗證失敗: " + ", ".join(validation_result.errors),
                error_type="ValidationError"
            )
        
        # 執行程式碼
        result = await sandbox_executor.execute_code(
            code=request.code,
            order=request.order,
            timeout=request.timeout or 5
        )
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"執行程式碼失敗: {str(e)}")
