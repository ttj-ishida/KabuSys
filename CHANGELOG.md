# CHANGELOG

すべての重要な変更点はこのファイルに記録します。  
フォーマットは「Keep a Changelog」（https://keepachangelog.com/ja/1.0.0/）の指針に従います。  

※ このファイルはコードベース（src/kabusys 以下）の現状から推測して作成しています。実装の詳細が追加された場合は適宜更新してください。

## [Unreleased]

## [0.1.0] - 2026-03-15
初回リリース（骨格の作成）

### Added
- パッケージ「KabuSys」を初期作成
  - パッケージメタ情報を定義（src/kabusys/__init__.py）
    - __version__ = "0.1.0"
    - パブリックAPIを明示する __all__ = ["data", "strategy", "execution", "monitoring"]
    - 簡潔なパッケージドキュメンテーション（モジュールドックストリング）
- コアサブパッケージの骨格を追加（空パッケージとしての初期配置）
  - src/kabusys/data/__init__.py
  - src/kabusys/strategy/__init__.py
  - src/kabusys/execution/__init__.py
  - src/kabusys/monitoring/__init__.py
- プロジェクトのソース配置を src/ 配下に構成（src-layout の採用）

### Changed
- （該当なし）初回リリースのため変更履歴なし

### Fixed
- （該当なし）初回リリースのため修正履歴なし

### Removed
- （該当なし）

### Security
- （該当なし）

---

今後の予定例（今後のリリースで追加する想定の項目）
- data: 株価データの取得/キャッシュ機構の実装
- strategy: 取引戦略の基底クラスおよびサンプル戦略
- execution: 注文送信・約定管理インターフェース
- monitoring: ログ・メトリクス・監視ダッシュボード用のユーティリティ

変更を加えた際は、本CHANGELOGも更新してください。