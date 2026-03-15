# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠し、セマンティック・バージョニングを使用します。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-15

### Added
- 初回リリース: KabuSys v0.1.0 を追加。
  - パッケージ名: `kabusys`
  - ソースレイアウト: `src/` 配下に実装
- トップレベル初期化モジュールを追加: `src/kabusys/__init__.py`
  - モジュールドキュストリング: "KabuSys - 日本株自動売買システム"
  - バージョン定義: `__version__ = "0.1.0"`
  - パブリックAPIのエクスポート指定: `__all__ = ["data", "strategy", "execution", "monitoring"]`
- サブパッケージのスケルトンを追加（現時点ではプレースホルダー）:
  - `src/kabusys/data/__init__.py`
  - `src/kabusys/strategy/__init__.py`
  - `src/kabusys/execution/__init__.py`
  - `src/kabusys/monitoring/__init__.py`
- 基本的なパッケージ構成を確立し、今後の機能追加（データ管理、戦略ロジック、実行エンジン、監視機能）に備える基盤を整備。

### Changed
- なし

### Fixed
- なし

---

メモ:
- サブパッケージは現状で空の `__init__.py` で定義されており、各コンポーネント（data, strategy, execution, monitoring）の実装はこれから追加される想定です。