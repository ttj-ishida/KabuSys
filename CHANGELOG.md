# Changelog

すべての注目すべき変更をここに記録します。  
このプロジェクトは Keep a Changelog の慣例に従って管理されています。  
非互換な変更は "Changed"、新機能は "Added"、バグ修正は "Fixed" に記載します。

## [Unreleased]

## [0.1.0] - 2026-03-15
初回リリース

### Added
- 初期パッケージ「KabuSys」を追加
  - トップレベルのパッケージ docstring: "KabuSys - 日本株自動売買システム"
  - バージョン情報を公開: `__version__ = "0.1.0"`
  - 公開 API: `__all__ = ["data", "strategy", "execution", "monitoring"]`
- 基本的なモジュール構成を追加（いずれも空の初期化ファイルを含む）
  - src/kabusys/data: 市場データの取得・管理を担うモジュール（骨格）
  - src/kabusys/strategy: 売買戦略を実装するための枠組み（骨格）
  - src/kabusys/execution: 注文発行・約定処理を行う実行層（骨格）
  - src/kabusys/monitoring: ログ・監視・メトリクス等の監視機能（骨格）
- プロジェクトレイアウトを `src/` 配下に配置（パッケージ化しやすい構成）

### Changed
- 該当なし（初回リリースのため）

### Fixed
- 該当なし（初回リリースのため）

---

（注）リポジトリ URL や比較リンクは本 CHANGELOG 作成時点で指定がなかったため記載していません。必要であれば追って追加してください。