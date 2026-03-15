# CHANGELOG

すべての重要な変更をこのファイルに記録します。  
このプロジェクトは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用しています。

- フォーマットの詳細: https://keepachangelog.com/ja/1.0.0/
- バージョニング: https://semver.org/lang/ja/

## [Unreleased]

## [0.1.0] - 2026-03-15
### Added
- 初回リリース（スケルトン実装）。
  - パッケージ名: `kabusys`（説明: 日本株自動売買システム）。
  - ルートモジュール: `src/kabusys/__init__.py`
    - バージョン情報: `__version__ = "0.1.0"`
    - パッケージ公開 API: `__all__ = ["data", "strategy", "execution", "monitoring"]`
    - モジュール docstring に簡単な説明を追加。
  - サブパッケージ（プレースホルダとして空の初期化ファイルを含む）
    - `src/kabusys/data/__init__.py` — データ取得・管理用の名前空間
    - `src/kabusys/strategy/__init__.py` — 売買戦略ロジック用の名前空間
    - `src/kabusys/execution/__init__.py` — 注文実行・ブローカー連携用の名前空間
    - `src/kabusys/monitoring/__init__.py` — 監視・ログ・状態確認用の名前空間

### Notes（開発者向けメモ）
- 現時点ではサブパッケージはスケルトン（空の `__init__.py`）として配置されています。今後それぞれの責務に沿って機能を実装していく予定です。
- 公開 API はトップレベルで `data`, `strategy`, `execution`, `monitoring` を想定しており、将来的にこれらのモジュールを通じてシステム機能を利用できるように拡張します。