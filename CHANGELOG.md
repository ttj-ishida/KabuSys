# CHANGELOG

すべての注目すべき変更はここに記録します。  
このファイルは「Keep a Changelog」形式に準拠しています。詳細: https://keepachangelog.com/ja/1.0.0/

注: バージョン番号はセマンティックバージョニングに従います。

## Unreleased
- （今後の変更をここに記載）

## [0.1.0] - 2026-03-15
初期リリース。リポジトリの基本構造と公開APIの骨組みを追加しました。

### Added
- パッケージ「KabuSys」を追加
  - top-level モジュール `src/kabusys/__init__.py` を追加し、パッケージの説明ドキュメンテーション文字列を設定。
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。
  - パブリックAPIとして `__all__ = ["data", "strategy", "execution", "monitoring"]` を公開。
- サブパッケージのスケルトンを追加
  - `src/kabusys/data/__init__.py`（データ取得・管理用）
  - `src/kabusys/strategy/__init__.py`（取引戦略用）
  - `src/kabusys/execution/__init__.py`（注文実行用）
  - `src/kabusys/monitoring/__init__.py`（監視・ログ用）
  - 上記の各 `__init__.py` は現時点ではプレースホルダ（空）で、今後の実装拡張を想定。
- ソース配置に `src/` レイアウトを採用（将来的なパッケージ化・配布に適合）。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Removed
- なし（初回リリース）

### Security
- なし（初回リリース）

備考:
- 現バージョンは骨組み（スキャフォールド）にあたるため、各機能（データ取得、戦略実装、注文実行、監視）の具体的実装は今後追加予定です。