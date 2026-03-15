# Changelog

すべての重要な変更はこのファイルに記録します。  
このファイルは「Keep a Changelog」の指針に従っています。  
参照: https://keepachangelog.com/（英語）

次の慣例を使用しています。  
- 追加 (Added) — 新機能  
- 変更 (Changed) — 既存機能の変更  
- 修正 (Fixed) — バグ修正  
- 削除 (Removed) — 既存機能の削除

## [Unreleased]

## [0.1.0] - 2026-03-15
### Added
- 初回リリース。KabuSys — 日本株自動売買システムのプロジェクトスケルトンを追加。
  - パッケージトップ: `src/kabusys/__init__.py`
    - パッケージ説明ドキュストリング: `"KabuSys - 日本株自動売買システム"`
    - バージョン情報: `__version__ = "0.1.0"`
    - 公開APIを定義する `__all__ = ["data", "strategy", "execution", "monitoring"]`
  - サブパッケージ（プレースホルダ）を追加:
    - `src/kabusys/data/__init__.py`
    - `src/kabusys/strategy/__init__.py`
    - `src/kabusys/execution/__init__.py`
    - `src/kabusys/monitoring/__init__.py`
  - 上記サブパッケージは現時点では空の初期化ファイルのみで、今後の実装（データ取得、取引戦略、注文実行、監視機能）を想定した構成になっています。

### Notes
- 本リリースはプロジェクトの骨組み（モジュール構成・公開API）を整備することを目的としています。各サブパッケージの具体的な実装は次バージョンで追加予定です。

[Unreleased]: #  
[0.1.0]: #