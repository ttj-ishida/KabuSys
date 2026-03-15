# Changelog

すべての注目すべき変更をここに記録します。  
このファイルは Keep a Changelog の形式に従い、セマンティック バージョニングを用いています。

## [Unreleased]
（現在未リリースの変更はここに記載します）

## [0.1.0] - 2026-03-15
### Added
- 初期リリース。パッケージ名: `kabusys`
  - パッケージのメタ情報:
    - `__version__ = "0.1.0"`
    - パッケージドキュメント文字列: "KabuSys - 日本株自動売買システム"
    - 公開 API: `__all__ = ["data", "strategy", "execution", "monitoring"]`
  - プロジェクト構成（src レイアウト）:
    - `src/kabusys/__init__.py`（パッケージのエントリポイント、バージョンとエクスポート定義）
    - `src/kabusys/data/__init__.py`（データ取得/管理用モジュールのプレースホルダ）
    - `src/kabusys/strategy/__init__.py`（トレーディング戦略用モジュールのプレースホルダ）
    - `src/kabusys/execution/__init__.py`（注文実行/API連携用モジュールのプレースホルダ）
    - `src/kabusys/monitoring/__init__.py`（監視/ログ/メトリクス用モジュールのプレースホルダ）
- 基本的なパッケージ骨組み（モジュールの空の初期化ファイルを含む）を追加。今後、各サブパッケージに機能を実装予定。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Security
- なし（初回リリース）

---

[Unreleased]: https://example.com/compare/v0.1.0...HEAD
[0.1.0]: https://example.com/releases/tag/v0.1.0

（上記リンクはリポジトリURLに応じて適宜置き換えてください）