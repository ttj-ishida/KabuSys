Keep a Changelog
================

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトはセマンティックバージョニングに従います。

フォーマットの詳細: https://keepachangelog.com/ja/1.0.0/

[Unreleased]


0.1.0 - 2026-03-15
------------------

Added
- 初期リリース: 日本株自動売買システム "KabuSys"
  - パッケージ名: `kabusys`
  - パッケージ説明（パッケージルートのdocstring）: "KabuSys - 日本株自動売買システム"
  - バージョン情報: `src/kabusys/__init__.py` に `__version__ = "0.1.0"` を定義
  - 公開API: `__all__ = ["data", "strategy", "execution", "monitoring"]`
- モジュール構成（スキャフォールド）
  - `src/kabusys/data/__init__.py` — データ取得・管理に関するモジュール（プレースホルダ）
  - `src/kabusys/strategy/__init__.py` — 取引戦略に関するモジュール（プレースホルダ）
  - `src/kabusys/execution/__init__.py` — 注文実行（ブローカー連携等）に関するモジュール（プレースホルダ）
  - `src/kabusys/monitoring/__init__.py` — 監視・ログ・状態管理に関するモジュール（プレースホルダ）
- パッケージのソース構成を明確化（`src/` 配下にパッケージ配置）

Notes
- 現状はパッケージの骨組み（__init__.py によるモジュール公開とメタ情報の定義）が作成された状態です。各サブパッケージ（data, strategy, execution, monitoring）はプレースホルダとして存在しており、今後それぞれの機能実装が追加される想定です。