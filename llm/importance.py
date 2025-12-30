# llm/importance.py

class CodeElementScorer:
    """
    コード要素の重要度を評価するためのクラス
    異なる基準に基づいてクラス、関数、メソッドなどの重要度を計算する
    """
    def __init__(self):
        # 重み付け係数
        self.weights = {
            'reference_count': 3.0,      # 他の要素から参照されている回数
            'complexity': 2.0,           # 複雑さ（メソッド数、行数など）
            'name_importance': 1.5,      # 名前の重要さ（main, initなど）
            'docstring': 1.0,            # ドキュメント文字列の有無
            'inheritance': 2.5,          # 継承関係の有無
            'parameter_count': 1.0,      # パラメータの数
            'inner_element_count': 1.2,  # 内部要素（内部関数など）の数
            'is_focus': 10.0             # 明示的にフォーカスされた要素
        }
    
    def score_class(self, cls_info, focus_classes=None, dependencies=None):
        """クラスの重要度スコアを計算"""
        score = 0
        focus_classes = focus_classes or []
        dependencies = dependencies or {}
        
        # 明示的にフォーカスされたクラス
        if any(focus in cls_info['name'] for focus in focus_classes):
            score += self.weights['is_focus']
        
        # メソッド数に基づく複雑さ
        methods = cls_info.get('methods', [])
        score += len(methods) * self.weights['complexity']
        
        # 継承関係
        if cls_info.get('extends') or cls_info.get('base_classes'):
            score += self.weights['inheritance']
        
        # docstringの有無
        if cls_info.get('docstring'):
            score += self.weights['docstring']
        
        # 他の要素からの参照数
        reference_count = self._count_references(cls_info['name'], dependencies)
        score += reference_count * self.weights['reference_count']
        
        # 名前の重要さ
        if self._is_important_name(cls_info['name']):
            score += self.weights['name_importance']
        
        return score
    
    def score_function(self, func_info, focus_functions=None, dependencies=None):
        """関数の重要度スコアを計算"""
        score = 0
        focus_functions = focus_functions or []
        dependencies = dependencies or {}
        
        # 明示的にフォーカスされた関数
        if any(focus in func_info['name'] for focus in focus_functions):
            score += self.weights['is_focus']
        
        # パラメータの数
        parameters = func_info.get('parameters', [])
        score += len(parameters) * self.weights['parameter_count']
        
        # 内部関数の数
        inner_functions = func_info.get('inner_functions', [])
        score += len(inner_functions) * self.weights['inner_element_count']
        
        # docstringの有無
        if func_info.get('docstring'):
            score += self.weights['docstring']
        
        # 他の要素からの参照数
        reference_count = self._count_references(func_info['name'], dependencies)
        score += reference_count * self.weights['reference_count']
        
        # 名前の重要さ
        if self._is_important_name(func_info['name']):
            score += self.weights['name_importance'] * 2  # main関数などは特に重要
        
        return score
    
    def score_method(self, method_info, class_name, dependencies=None):
        """メソッドの重要度スコアを計算"""
        score = 0
        dependencies = dependencies or {}
        
        # パラメータの数
        parameters = method_info.get('parameters', [])
        score += len(parameters) * self.weights['parameter_count']
        
        # 内部関数の数
        inner_functions = method_info.get('inner_functions', [])
        score += len(inner_functions) * self.weights['inner_element_count']
        
        # docstringの有無
        if method_info.get('docstring'):
            score += self.weights['docstring']
        
        # 他の要素からの参照数
        full_name = f"{class_name}.{method_info['name']}"
        reference_count = self._count_references(full_name, dependencies)
        score += reference_count * self.weights['reference_count']
        
        # 名前の重要さ
        if self._is_important_method_name(method_info['name']):
            score += self.weights['name_importance']
        
        return score
    
    def _count_references(self, name, dependencies):
        """依存関係から参照回数を計算"""
        count = 0
        
        # 他の要素からの呼び出し
        for caller, callees in dependencies.items():
            for callee in callees:
                if name in callee:
                    count += 1
        
        return count
    
    def _is_important_name(self, name):
        """重要な名前かどうかを判定"""
        important_names = ['main', 'init', 'App', 'Manager', 'Controller', 'Service', 'run']
        return any(imp_name.lower() in name.lower() for imp_name in important_names)
    
    def _is_important_method_name(self, name):
        """重要なメソッド名かどうかを判定"""
        important_methods = ['__init__', 'main', 'run', 'execute', 'process', 'start', 'init', 'setup', 'create', 'build']
        return any(imp_method.lower() in name.lower() for imp_method in important_methods)

class CodeStructureImportanceAnalyzer:
    """
    コード構造全体の重要度を分析し、最適なフォーカスポイントを特定するクラス
    """
    def __init__(self):
        self.element_scorer = CodeElementScorer()
        self.dependency_graph = {}
    
    def analyze_code_structure(self, code_analysis):
        """コード構造全体を分析し、重要な要素を特定する"""
        # 依存関係グラフを構築
        self._build_dependency_graph(code_analysis)
        
        # クラスの重要度を評価
        classes = code_analysis.get('classes', [])
        scored_classes = []
        
        for cls in classes:
            score = self.element_scorer.score_class(cls, dependencies=self.dependency_graph)
            scored_classes.append((cls, score))
        
        # 関数の重要度を評価
        functions = code_analysis.get('functions', [])
        scored_functions = []
        
        for func in functions:
            score = self.element_scorer.score_function(func, dependencies=self.dependency_graph)
            scored_functions.append((func, score))
        
        # 重要度順にソート
        sorted_classes = sorted(scored_classes, key=lambda x: x[1], reverse=True)
        sorted_functions = sorted(scored_functions, key=lambda x: x[1], reverse=True)
        
        # 結果をまとめる
        top_classes = [cls['name'] for cls, _ in sorted_classes[:min(5, len(sorted_classes))]]
        top_functions = [func['name'] for func, _ in sorted_functions[:min(5, len(sorted_functions))]]
        
        return {
            'top_classes': top_classes,
            'top_functions': top_functions,
            'central_components': self._identify_central_components(),
            'entry_points': self._identify_entry_points(),
            'suggested_focus': self._suggest_focus_points(top_classes, top_functions)
        }
    
    def _build_dependency_graph(self, code_analysis):
        """コード分析結果から依存関係グラフを構築"""
        # 拡張解析の依存関係情報を取得
        dependencies = code_analysis.get('extended_analysis', {}).get('dependencies', {})
        
        # 依存関係グラフとして整理
        graph = {}
        
        for caller, callees in dependencies.items():
            if caller not in graph:
                graph[caller] = {'calls': set(), 'called_by': set()}
            
            for callee in callees:
                if callee not in graph:
                    graph[callee] = {'calls': set(), 'called_by': set()}
                
                graph[caller]['calls'].add(callee)
                graph[callee]['called_by'].add(caller)
        
        self.dependency_graph = graph
        return graph
    
    def _identify_central_components(self):
        """中心的なコンポーネントを特定（多くの呼び出しがあるもの）"""
        if not self.dependency_graph:
            return []
        
        # 呼び出しの多いコンポーネントを評価
        component_scores = {}
        
        for component, relations in self.dependency_graph.items():
            # スコア = 呼び出す数 + 呼び出される数
            score = len(relations['calls']) + len(relations['called_by'])
            component_scores[component] = score
        
        # スコアの高い順にソート
        sorted_components = sorted(component_scores.items(), key=lambda x: x[1], reverse=True)
        
        # 上位のコンポーネントを返す
        return [comp for comp, _ in sorted_components[:min(3, len(sorted_components))]]
    
    def _identify_entry_points(self):
        """エントリーポイントを特定（他から呼ばれないが、多くを呼び出すもの）"""
        if not self.dependency_graph:
            return []
        
        entry_points = []
        
        for component, relations in self.dependency_graph.items():
            # エントリーポイントの条件: 呼び出される数が0または少なく、呼び出す数が多い
            if len(relations['called_by']) <= 1 and len(relations['calls']) >= 3:
                # main関数や__main__ブロックを優先
                if 'main' in component.lower() or '__init__' in component:
                    entry_points.insert(0, component)
                else:
                    entry_points.append(component)
        
        return entry_points[:min(3, len(entry_points))]
    
    def _suggest_focus_points(self, top_classes, top_functions):
        """重要なクラスと関数を組み合わせて、推奨フォーカスポイントを提案"""
        suggested_focus = []
        
        # エントリーポイントを最優先
        entry_points = self._identify_entry_points()
        if entry_points:
            suggested_focus.extend(entry_points)
        
        # トップクラスを追加（エントリーポイントと重複しないもの）
        for cls in top_classes:
            if cls not in suggested_focus:
                suggested_focus.append(cls)
                if len(suggested_focus) >= 5:
                    break
        
        # 必要に応じてトップ関数も追加
        remaining_slots = 5 - len(suggested_focus)
        if remaining_slots > 0:
            for func in top_functions:
                if func not in suggested_focus:
                    suggested_focus.append(func)
                    remaining_slots -= 1
                    if remaining_slots <= 0:
                        break
        
        return suggested_focus