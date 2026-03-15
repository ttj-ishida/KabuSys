# Changelog

すべての注記は Keep a Changelog の形式に従い、安定版は Semantic Versioning に準拠します。日付はパッケージ初回リリース日です。

## [Unreleased]


## [0.1.0] - 2026-03-15
最初の公開リリース。

### 追加
- パッケージの初期構成を追加
  - パッケージ名: `kabusys`
  - パッケージ説明（docstring）: "KabuSys - 日本株自動売買システム"
  - バージョン情報: `__version__ = "0.1.0"`
  - パッケージ公開 API: `__all__ = ["data", "strategy", "execution", "monitoring"]`
- サブパッケージ（骨組み）を追加
  - `kabusys.data` — データ取得・整形関連モジュール用のプレースホルダ（現状は __init__.py のみ）
  - `kabusys.strategy` — 売買戦略ロジック用のプレースホルダ（現状は __init__.py のみ）
  - `kabusys.execution` — 注文執行・ブローカー連携用のプレースホルダ（現状は __init__.py のみ）
  - `kabusys.monitoring` — 監視・ログ・通知用のプレースホルダ（現状は __init__.py のみ）

### 備考
- 現状のサブパッケージはモジュールの骨組み（空の __init__.py）として追加されており、今後それぞれに具体的な機能（データ取得、戦略実装、注文執行、監視）が実装される予定です。
- パッケージの公開 API はサブパッケージ名で限定しているため、将来的に各サブパッケージ内に実装を追加することで利用者は `from kabusys import data, strategy, ...` のようにアクセスできます。