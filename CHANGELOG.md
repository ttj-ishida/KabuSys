# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
この変更履歴は「Keep a Changelog」の形式に準拠しています。  
慣例としてセマンティック バージョニングを使用します。

現在のリリース:
- Unreleased: 今後の変更を記載
- 0.1.0: 初期リリース（2026-03-15）

## [Unreleased]
（未リリースの変更はここに記載します）

## [0.1.0] - 2026-03-15
### 追加 (Added)
- 初期公開リリースを追加。
- パッケージ構成を追加:
  - src/kabusys/__init__.py
    - パッケージドキュメンテーション: "KabuSys - 日本株自動売買システム"
    - バージョン情報: `__version__ = "0.1.0"`
    - パブリックAPIとして `__all__ = ["data", "strategy", "execution", "monitoring"]` を定義
  - サブパッケージ（スケルトン）を追加:
    - src/kabusys/data/__init__.py
    - src/kabusys/strategy/__init__.py
    - src/kabusys/execution/__init__.py
    - src/kabusys/monitoring/__init__.py
  - 上記サブパッケージは現時点では初期プレースホルダ（空の __init__.py）として実装されており、今後詳細な機能（データ取得/保管、取引戦略、注文実行、監視/ログ/アラート等）を実装予定。

### 変更 (Changed)
- 該当なし（初期リリースのため）

### 修正 (Fixed)
- 該当なし

### 非推奨 (Deprecated)
- 該当なし

### 削除 (Removed)
- 該当なし

### セキュリティ (Security)
- 該当なし

---

メモ:
- このリポジトリはソースルートが `src/` 配下にあり、パッケージ名は `kabusys` です。
- 今後のリリースでは、各サブパッケージに対する具体的な機能追加（API、データモデル、取引ロジック、実行エンジン、監視機能など）を個別に記載します。

[Unreleased]: #  
[0.1.0]: #