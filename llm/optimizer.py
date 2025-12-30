# llm/optimizer.py
import json
import math
import re
from typing import Any, Dict, List, Optional, Set, Tuple

class LLMContextOptimizer:
    """
    LLM向けにコンテキストを最適化するメインクラス
    """
    def __init__(self, token_budget=4000, focus_classes=None, focus_files=None):
        self.token_budget = token_budget
        self.focus_classes = focus_classes or []
        self.focus_files = focus_files or []
        self.token_manager = TokenBudgetManager()
        self.importance_scorer = ImportanceScorer()
        self.dependency_analyzer = DependencyAnalyzer()
        self.structure_extractor = CodeStructureExtractor()
    
    def optimize(self, code_analysis):
        """コード解析結果をLLM向けに最適化"""
        # 解析結果から構成要素を抽出
        directory_structure = code_analysis.get('directory_structure', [])
        classes = code_analysis.get('classes', [])
        functions = code_analysis.get('functions', [])
        imports = code_analysis.get('imports', [])
        call_graph = code_analysis.get('extended_analysis', {}).get('call_graph', {}).get('data', [])
        dependencies = code_analysis.get('extended_analysis', {}).get('dependencies', {})
        
        # 各セクションのサイズを計算
        dir_size = self._calculate_size(directory_structure)
        classes_size = self._calculate_size(classes)
        functions_size = self._calculate_size(functions)
        imports_size = self._calculate_size(imports)
        call_graph_size = self._calculate_size(call_graph)
        dependencies_size = self._calculate_size(dependencies)
        
        total_size = dir_size + classes_size + functions_size + imports_size + call_graph_size + dependencies_size
        
        # トークン予算に基づいて各セクションに割り当てるサイズを計算
        budget_allocation = self.token_manager.allocate_budget(
            self.token_budget, 
            {
                'directory': dir_size / total_size,
                'classes': classes_size / total_size,
                'functions': functions_size / total_size,
                'imports': imports_size / total_size,
                'call_graph': call_graph_size / total_size,
                'dependencies': dependencies_size / total_size
            }
        )
        
        # 各セクションを最適化
        optimized_directory = directory_structure
        
        # クラスの最適化（重要度に基づいて選択）
        scored_classes = []
        for cls in classes:
            score = self.importance_scorer.score_class(cls, self.focus_classes, dependencies)
            scored_classes.append((cls, score))
        
        sorted_classes = sorted(scored_classes, key=lambda x: x[1], reverse=True)
        
        # 予算に基づいてクラスを選択
        optimized_classes = []
        current_size = 0
        classes_budget = budget_allocation['classes']
        
        for cls, _ in sorted_classes:
            cls_size = self._calculate_size(cls)
            if current_size + cls_size <= classes_budget:
                optimized_classes.append(cls)
                current_size += cls_size
            else:
                # 予算を超えた場合、関連するクラスのみを追加
                if any(focus in cls['name'] for focus in self.focus_classes):
                    optimized_classes.append(cls)
        
        # 関数も同様に最適化
        scored_functions = []
        for func in functions:
            score = self.importance_scorer.score_function(func, dependencies)
            scored_functions.append((func, score))
        
        sorted_functions = sorted(scored_functions, key=lambda x: x[1], reverse=True)
        
        optimized_functions = []
        current_size = 0
        functions_budget = budget_allocation['functions']
        
        for func, _ in sorted_functions:
            func_size = self._calculate_size(func)
            if current_size + func_size <= functions_budget:
                optimized_functions.append(func)
                current_size += func_size
        
        # インポートも最適化
        optimized_imports = imports[:int(budget_allocation['imports'] / self._calculate_size(imports[0]) if imports else 0)]
        
        # コールグラフとその他の情報も最適化
        optimized_call_graph = call_graph[:int(budget_allocation['call_graph'] / self._calculate_size(call_graph[0]) if call_graph else 0)]
        
        # 依存関係も最適化する場合はここに追加
        
        # 最適化された解析結果を返す
        return {
            'directory_structure': optimized_directory,
            'classes': optimized_classes,
            'functions': optimized_functions,
            'imports': optimized_imports,
            'extended_analysis': {
                'call_graph': {'data': optimized_call_graph},
                'dependencies': dependencies  # 簡略化のため全依存関係を含める
            }
        }
    
    def _calculate_size(self, obj):
        """オブジェクトのトークンサイズを計算"""
        if isinstance(obj, str):
            return self.token_manager.estimate_tokens(obj)
        elif isinstance(obj, list):
            return sum(self._calculate_size(item) for item in obj)
        elif isinstance(obj, dict):
            return sum(self._calculate_size(key) + self._calculate_size(value) for key, value in obj.items())
        else:
            # その他の型は文字列に変換
            return self.token_manager.estimate_tokens(str(obj))
    
    def generate_optimized_prompt(self, code_analysis, template):
        """最適化されたプロンプトを生成"""
        # コード解析を最適化
        optimized_analysis = self.optimize(code_analysis)
        
        # JSONに変換
        optimized_json = json.dumps(optimized_analysis, indent=2, ensure_ascii=False)
        
        # テンプレートに挿入
        prompt = template.replace("[解析結果]", optimized_json)
        
        return prompt

class TokenBudgetManager:
    """トークン使用量を管理するクラス"""
    def __init__(self):
        pass
    
    def estimate_tokens(self, text):
        """テキストのトークン数を推定"""
        # 簡易的な推定: 平均的な英語では1トークンが約4文字
        # 日本語の場合はもう少し複雑ですが、ここでは簡易的に実装
        return len(text) / 4
    
    def allocate_budget(self, total_budget, section_ratios):
        """各セクションに割り当てるトークン予算を計算"""
        # 全体の比率の合計を1.0に正規化
        total_ratio = sum(section_ratios.values())
        normalized_ratios = {k: v/total_ratio for k, v in section_ratios.items()}
        
        # 予算を比率に基づいて配分
        allocation = {k: total_budget * v for k, v in normalized_ratios.items()}
        
        # 最小予算を確保（非常に小さなセクションにも最低限のスペースを）
        min_budget = total_budget * 0.05  # 全体の5%
        
        for section, budget in allocation.items():
            if budget < min_budget:
                allocation[section] = min_budget
        
        # 最大予算を超えないように調整
        if sum(allocation.values()) > total_budget:
            # 超過分を均等に減らす
            excess = sum(allocation.values()) - total_budget
            excess_per_item = excess / len(allocation)
            
            for section in allocation:
                allocation[section] = max(min_budget, allocation[section] - excess_per_item)
        
        return allocation

class ImportanceScorer:
    """コード要素の重要度を評価するクラス"""
    def __init__(self):
        pass
    
    def score_class(self, cls, focus_classes, dependencies):
        """クラスの重要度をスコアリング"""
        score = 0
        
        # フォーカスクラスに指定されている場合は高いスコアを付ける
        if any(focus in cls['name'] for focus in focus_classes):
            score += 100
        
        # メソッド数が多いほど重要度を上げる
        score += len(cls.get('methods', [])) * 2
        
        # 他のクラスから参照されている回数に基づいてスコアを付ける
        for caller, callees in dependencies.items():
            for callee in callees:
                if cls['name'] in callee:
                    score += 3
        
        # 継承関係がある場合はスコアを上げる
        if cls.get('extends'):
            score += 5
        
        return score
    
    def score_function(self, func, dependencies):
        """関数の重要度をスコアリング"""
        score = 0
        
        # 引数の数が多いほど重要度を上げる
        params = func.get('parameters', [])
        score += len(params) * 1.5
        
        # 他の関数から呼び出されている回数に基づいてスコアを付ける
        for caller, callees in dependencies.items():
            for callee in callees:
                if func['name'] in callee:
                    score += 2
        
        # 'main'関数や'init'関数は重要
        if func['name'] == 'main' or 'init' in func['name']:
            score += 10
        
        # 内部関数があれば重要度を上げる
        score += len(func.get('inner_functions', [])) * 1.5
        
        return score

class DependencyAnalyzer:
    """コード間の依存関係を分析するクラス"""
    def __init__(self):
        self.dependency_graph = {}
    
    def build_dependency_graph(self, dependencies):
        """コール関係からグラフを構築"""
        graph = {}
        
        for caller, callees in dependencies.items():
            if caller not in graph:
                graph[caller] = set()
            
            for callee in callees:
                graph[caller].add(callee)
                if callee not in graph:
                    graph[callee] = set()
        
        self.dependency_graph = graph
        return graph
    
    def find_related_components(self, component_name, distance=2):
        """指定コンポーネントに関連するコンポーネントを特定"""
        if not self.dependency_graph:
            return []
        
        if component_name not in self.dependency_graph:
            return []
        
        # 関連コンポーネントを見つける
        related = set([component_name])
        current = set([component_name])
        
        for _ in range(distance):
            next_level = set()
            
            # 現在のノードから呼び出されるコンポーネント
            for comp in current:
                next_level.update(self.dependency_graph.get(comp, set()))
            
            # 現在のノードを呼び出すコンポーネント
            for caller, callees in self.dependency_graph.items():
                if any(comp in callees for comp in current):
                    next_level.add(caller)
            
            current = next_level - related
            related.update(current)
        
        return list(related - {component_name})

class CodeStructureExtractor:
    """コード構造を抽出するクラス"""
    def extract_key_components(self, code_analysis, importance_threshold=0.7):
        """最も重要なコンポーネントを抽出"""
        # 簡易実装: クラス名とその上位メソッド、重要な関数のみを抽出
        classes = code_analysis.get('classes', [])
        functions = code_analysis.get('functions', [])
        
        # クラスの構造データのみ抽出
        class_structures = []
        for cls in classes:
            methods = []
            if cls.get('methods'):
                # メソッド数の多いクラスほど重要と仮定し、上位のメソッドのみ抽出
                sorted_methods = sorted(cls['methods'], key=lambda m: len(m.get('inner_functions', [])), reverse=True)
                top_methods_count = max(1, int(len(sorted_methods) * importance_threshold))
                methods = sorted_methods[:top_methods_count]
            
            class_structures.append({
                'name': cls['name'],
                'extends': cls.get('extends', ''),
                'method_count': len(cls.get('methods', [])),
                'top_methods': [m['name'] for m in methods]
            })
        
        # 関数も同様に絞り込み
        function_structures = []
        if functions:
            # 内部関数の多い関数ほど重要と仮定
            sorted_functions = sorted(functions, key=lambda f: len(f.get('inner_functions', [])), reverse=True)
            top_functions_count = max(1, int(len(sorted_functions) * importance_threshold))
            function_structures = [{'name': f['name']} for f in sorted_functions[:top_functions_count]]
        
        return {
            'classes': class_structures,
            'functions': function_structures
        }