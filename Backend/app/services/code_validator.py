import ast
from typing import List
from app.models.benchmark import CodeValidationResult
from app.services.interfaces import ICodeValidator


class CodeValidator(ICodeValidator):
    """程式碼驗證器"""
    
    # 禁止的模組導入
    FORBIDDEN_IMPORTS = [
        'os', 'sys', 'subprocess', 'socket', 'urllib', 'requests',
        'eval', 'exec', '__import__', 'importlib', 'pickle',
        'shelve', 'marshal', 'tempfile', 'shutil', 'glob',
        'pathlib', 'io', 'codecs', 'threading', 'multiprocessing'
    ]
    
    # 禁止的內建函數
    FORBIDDEN_BUILTINS = [
        'open', 'file', 'input', 'eval', 'exec', 'compile',
        '__import__', 'globals', 'locals', 'vars', 'dir',
        'getattr', 'setattr', 'delattr', 'hasattr'
    ]
    
    def validate_syntax(self, code: str) -> CodeValidationResult:
        """
        驗證程式碼語法
        
        Args:
            code: Python 程式碼字串
            
        Returns:
            驗證結果
        """
        errors = []
        warnings = []
        
        try:
            ast.parse(code)
        except SyntaxError as e:
            errors.append(f"語法錯誤：第 {e.lineno} 行 - {e.msg}")
            return CodeValidationResult(
                valid=False,
                errors=errors,
                warnings=warnings,
                forbidden_operations=[]
            )
        
        return CodeValidationResult(
            valid=True,
            errors=errors,
            warnings=warnings,
            forbidden_operations=[]
        )
    
    def check_security(self, code: str) -> List[str]:
        """
        檢查程式碼安全性
        
        Args:
            code: Python 程式碼字串
            
        Returns:
            禁止操作列表
        """
        forbidden_ops = []
        
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return forbidden_ops
        
        for node in ast.walk(tree):
            # 檢查導入語句
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in self.FORBIDDEN_IMPORTS:
                        forbidden_ops.append(f"禁止導入模組：{alias.name}")
            
            if isinstance(node, ast.ImportFrom):
                if node.module in self.FORBIDDEN_IMPORTS:
                    forbidden_ops.append(f"禁止導入模組：{node.module}")
            
            # 檢查內建函數呼叫
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in self.FORBIDDEN_BUILTINS:
                        forbidden_ops.append(f"禁止使用函數：{node.func.id}")
        
        return forbidden_ops
    
    def validate_algorithm_interface(self, code: str) -> bool:
        """
        驗證程式碼是否實作正確的演算法介面
        
        Args:
            code: Python 程式碼字串
            
        Returns:
            是否符合介面要求
        """
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return False
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if node.name == 'calculate_path':
                    return True
        
        return False
    
    def validate_code(self, code: str) -> CodeValidationResult:
        """
        驗證程式碼語法和安全性
        
        Args:
            code: Python 程式碼字串
            
        Returns:
            驗證結果
        """
        errors = []
        warnings = []
        forbidden_ops = []
        
        # 步驟 1: 語法檢查
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            errors.append(f"語法錯誤：第 {e.lineno} 行 - {e.msg}")
            return CodeValidationResult(
                valid=False,
                errors=errors,
                warnings=warnings,
                forbidden_operations=forbidden_ops
            )
        
        # 步驟 2: 安全性檢查
        forbidden_ops = self.check_security(code)
        
        # 步驟 3: 介面檢查
        has_calculate_path = False
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if node.name == 'calculate_path':
                    has_calculate_path = True
                    # 檢查參數
                    if len(node.args.args) < 2:
                        warnings.append("calculate_path 應該接受兩個參數：order_items 和 cargo_data")
        
        if not has_calculate_path:
            errors.append("程式碼必須包含 calculate_path 函數")
        
        # 步驟 4: 判定結果
        if len(forbidden_ops) > 0:
            errors.append("程式碼包含禁止的操作")
        
        valid = len(errors) == 0
        
        return CodeValidationResult(
            valid=valid,
            errors=errors,
            warnings=warnings,
            forbidden_operations=forbidden_ops
        )


# 全域單例
code_validator = CodeValidator()
