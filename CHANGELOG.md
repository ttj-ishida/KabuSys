# Changelog

すべての注目すべき変更を記録します。本ファイルは「Keep a Changelog」の形式に準拠しています。  
慣例に従い、バージョンはセマンティックバージョニングを使用します。

現在の日付: 2026-03-15

## [Unreleased]
（未リリースの変更はここに記載します）

## [0.1.0] - 2026-03-15
### Added
- 初回リリース: KabuSys — 日本株自動売買システムの基本パッケージを追加。
  - パッケージルート: `src/kabusys/__init__.py`
    - `__version__ = "0.1.0"` を定義。
    - `__all__ = ["data", "strategy", "execution", "monitoring"]` を公開APIとして設定。
    - パッケージの docstring に「KabuSys - 日本株自動売買システム」の説明を追加。
  - サブパッケージ（プレースホルダ）を追加:
    - `src/kabusys/data/__init__.py` — 市場データ取り込みや整形を担う想定のモジュール群。
    - `src/kabusys/strategy/__init__.py` — 売買戦略の定義と管理を担う想定のモジュール群。
    - `src/kabusys/execution/__init__.py` — 注文送信や取引執行の責務を担う想定のモジュール群。
    - `src/kabusys/monitoring/__init__.py` — 監視・ログ・稼働状態の可視化を担う想定のモジュール群。
  - 上記各サブパッケージの `__init__.py` は現時点では空のプレースホルダとして作成されており、今後の実装拡張を想定。

### Changed
- なし（初回リリースのため該当なし）

### Deprecated
- なし

### Removed
- なし

### Fixed
- なし

### Security
- なし

補足:
- 本リリースはプロジェクトの骨組み（スケルトン）を提供するもので、各サブパッケージの具体的な機能は今後のリリースで追加予定です。