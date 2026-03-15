# Changelog

すべての重要な変更をここに記録します。本プロジェクトは「Keep a Changelog」の形式に従います。  
<https://keepachangelog.com/ja/1.0.0/>

※ 日付はリリース日を示します。

## [Unreleased]

## [0.1.0] - 2026-03-15
### 追加
- 初期リリースのパッケージ骨格を追加。
  - `src/kabusys/__init__.py`
    - パッケージのドキュメンテーション文字列を追加（"KabuSys - 日本株自動売買システム"）。
    - バージョン情報 `__version__ = "0.1.0"` を定義。
    - 公開モジュールリスト `__all__ = ["data", "strategy", "execution", "monitoring"]` を定義。
  - サブパッケージのプレースホルダを追加（現在は空の初期化ファイル）。
    - `src/kabusys/data/__init__.py`
    - `src/kabusys/strategy/__init__.py`
    - `src/kabusys/execution/__init__.py`
    - `src/kabusys/monitoring/__init__.py`

### 備考
- 現時点では機能実装は行われておらず、サブパッケージは将来的な実装のための構造（プレースホルダ）として配置されています。今後、データ取得（data）、売買戦略（strategy）、注文実行（execution）、監視（monitoring）に関する具体的な実装を追加していく予定です。