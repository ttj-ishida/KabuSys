# Changelog

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは「Keep a Changelog」の慣習に従い、セマンティックバージョニングを使用します。

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更
- Deprecated: 非推奨
- Removed: 削除
- Fixed: バグ修正
- Security: セキュリティ修正

未リリースの変更は "Unreleased" セクションに記載します。

## [Unreleased]

- なし

## [0.1.0] - 2026-03-15

初期リリース。

### Added
- 新規パッケージ「KabuSys」を追加
  - パッケージ説明: "KabuSys - 日本株自動売買システム"（src/kabusys/__init__.py のモジュールドキュメンテーション文字列より）
  - バージョン情報: __version__ = "0.1.0"
  - パブリックAPIエクスポート: __all__ = ["data", "strategy", "execution", "monitoring"]
- 基本的なモジュール構成を作成
  - src/kabusys/data/__init__.py
  - src/kabusys/strategy/__init__.py
  - src/kabusys/execution/__init__.py
  - src/kabusys/monitoring/__init__.py
  - 各サブパッケージは初期プレースホルダ（空の __init__.py）として配置

### Changed
- なし

### Deprecated
- なし

### Removed
- なし

### Fixed
- なし

### Security
- なし

備考:
- このリリースはプロジェクトの骨格（パッケージ名、モジュール構成、バージョン管理、公開APIの宣言）を確立することを目的としています。各サブパッケージは現時点では実装が無いため、今後それぞれにデータ取得処理、売買戦略、注文実行、監視機能などの実装が追加される想定です。