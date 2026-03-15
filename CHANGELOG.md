# Changelog

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトはセマンティックバージョニングに従います。  

フォーマットは「Keep a Changelog」準拠です。

## [Unreleased]

（未リリースの変更はここに記録してください）

## [0.1.0] - 2026-03-15

初期リリース

### 追加
- パッケージの初期骨格を追加
  - src/kabusys/__init__.py
    - パッケージのトップレベルモジュール。モジュールの説明ドキュメント文字列を追加（"KabuSys - 日本株自動売買システム"）。
    - バージョン情報を設定（`__version__ = "0.1.0"`）。
    - パブリックAPIとして公開するサブモジュール一覧を定義（`__all__ = ["data", "strategy", "execution", "monitoring"]`）。
  - サブパッケージのプレースホルダを追加（空の初期化ファイル）
    - src/kabusys/data/__init__.py
    - src/kabusys/strategy/__init__.py
    - src/kabusys/execution/__init__.py
    - src/kabusys/monitoring/__init__.py

### 備考
- 現時点では各サブパッケージはプレースホルダ（空の __init__.py）として構成されており、具体的な機能実装は今後追加予定です。
- パッケージは日本株自動売買システム（KabuSys）を想定したモジュール構成（データ取得、ストラテジー、注文実行、モニタリング）で設計されています。