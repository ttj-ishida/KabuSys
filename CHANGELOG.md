# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

最新: 0.1.0 — 2026-04-17

---

## [0.1.0] - 2026-04-17

### Added
- 初回リリース。日本株自動売買システム KabuSys の基本コンポーネント一式を追加。
- 環境・設定関連
  - Settings クラスを追加し、環境変数経由での設定取得を統一（J-Quants / kabuステーション / DB パス / 環境種別など）。
  - .env 自動ロード機能を追加（プロジェクトルートの .env / .env.local を読み込み、OS 環境変数を保護）。
  - .env パース機能を実装（コメント、クォート、export 形式、エスケープ対応）。
  - config_setup CLI を追加（対話式ウィザードで .env を初期作成・更新）。
  - validate_config CLI を追加（起動前の設定検証：必須環境変数、パス、YAML ファイル、ライブ環境ガード等をチェック）。
- 実行関連
  - run_execution スクリプトを追加（ExecutionEngine の起動、paper_trading 環境では専用 SQLite を使用して本番 DB と分離）。
  - run_monitoring スクリプトを追加（SystemMonitor のポーリングループ、MONITOR_POLL_INTERVAL 環境変数で間隔変更可能、停止フラグ検出対応）。
  - 実行中の停止フラグ / PID ファイル取り扱いを実装（data/*.flag / *.pid を利用）。
- モニタリング / DB
  - 監視用 DB 初期化ユーティリティを追加（init_monitoring_db を利用して冪等に監視テーブルを確保）。
  - duckdb 接続サポート（分析用 DB として duckdb を利用）。
- Execution コンポーネント
  - BrokerClientFactory を導入し、環境に応じてモック/実ブローカークライアントを切り替え可能（paper_trading の完全分離）。
  - OrderRepository / OrderManager / Reconciler / RiskManager / ExecutionEngine の起動フローを追加。
  - RiskManager のデフォルト設定を実装（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。
- ポートフォリオ構築（純粋関数群）
  - portfolio_builder: 候補選定（select_candidates）、等重み（calc_equal_weights）、スコア重み（calc_score_weights）。
  - risk_adjustment: セクター集中制限（apply_sector_cap）、レジームに応じた乗数（calc_regime_multiplier）。
  - position_sizing: 株数計算ロジック（calc_position_sizes）。リスクベース / 等金額 / スコア方式、単元株丸め、aggregate cap スケーリング、コストバッファ考慮等を含む。
  - 上記モジュールを package-level でエクスポート。
- 研究モジュール
  - research.factor_research を追加（DuckDB を用いたモメンタム / ボラティリティ / 流動性ファクター計算。MA200、ATR、各種モメンタム指標等）。
- ユーティリティ
  - process_priority ユーティリティを追加（Windows / POSIX 差分を吸収してプロセス優先度と CPU affinity 設定機能を提供）。
  - ログ設定や警告出力を適宜実装。
- ツール
  - tools.paper_verification_report を追加（paper_trading 用 SQLite から稼働率、注文成功率、レイテンシ等を集計して PASS/FAIL 判定する CLI。P95 計算を含む）。
- パッケージ情報
  - パッケージ初期バージョンを __version__ = "0.1.0" として設定。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 環境変数の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。OS 環境変数は protected として上書きされない設計。

---

Notes / 備考
- run_monitoring は KABUSYS_ENV に関わらず「監視用の sqlite_path は本番パスを使用する」旨の挙動が実装されているため、テスト時は注意が必要（必要なら環境変数でパスを差し替えてください）。
- config_setup にて生成される .env ファイルは README 等で Git へのコミット禁止を明記しています（セキュアな運用を想定）。
- 一部関数や TODO コメントで将来的な拡張（銘柄別 lot_size のサポート、価格フォールバック等）が示されています。

今後の予定（例）
- 単体テストおよび CI パイプラインの整備
- 銘柄ごとの lot_size 対応、価格フォールバックの改善
- モニタリング / アラートの LINE 通知統合（現在は設定確認の警告のみ）