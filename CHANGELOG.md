# Changelog

すべての注目すべき変更履歴はこのファイルに記録します。  
このファイルは Keep a Changelog（https://keepachangelog.com/ja/1.0.0/）の慣例に準拠します。  

※ 日付はリリース日を示します。

## [Unreleased]

（現時点では未リリースの変更はありません）

## [0.1.0] - 2026-03-15

初回リリース — 日本株自動売買システム（パッケージ骨格）

### Added
- パッケージ基盤を追加
  - src/kabusys/__init__.py
    - パッケージ名: KabuSys（説明コメントあり: "日本株自動売買システム"）
    - バージョンを __version__ = "0.1.0" に設定
    - パッケージ外部公開対象として __all__ = ["data", "strategy", "execution", "monitoring"] を定義
- サブパッケージのスケルトンを追加（現状は空の __init__.py）
  - src/kabusys/data/__init__.py （市場データ取得・管理用のサブパッケージ想定）
  - src/kabusys/strategy/__init__.py （売買ロジック・戦略実装用のサブパッケージ想定）
  - src/kabusys/execution/__init__.py （注文実行・API連携用のサブパッケージ想定）
  - src/kabusys/monitoring/__init__.py （監視・ロギング・メトリクス用のサブパッケージ想定）

### Notes / 開発メモ
- 現状はパッケージの骨格のみで、各サブパッケージはプレースホルダ（空ファイル）です。今後以下を実装予定：
  - data: 市場データ取得、時系列格納、キャッシュ
  - strategy: 戦略インターフェース、バックテスト用フック
  - execution: kabuステーション等の注文APIラッパー、注文管理
  - monitoring: ロギング、メトリクス、アラート
- 単体テスト、CI設定、ドキュメント（README 等）は未追加

---

（以降のリリースは上に新しいセクションを追加してください）