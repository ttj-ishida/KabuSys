CHANGELOG
=========

すべての変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) 準拠で記載しています。

[unreleased]: #unreleased

0.1.0 - 2026-04-19
------------------

Added
- 初期リリース: KabuSys 基本機能群を実装。
- 設定管理:
  - .env 自動読み込み機能（プロジェクトルートの検出: .git または pyproject.toml を基準）。
  - 高機能な .env パーサ（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントの取り扱いに対応）。
  - Settings クラスで環境変数をプロパティ化（J-Quants / kabu API / DB パス / 監視しきい値 / 実行環境など）。
  - 環境変数自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。.env と .env.local の読み込み順を実装（.env.local が上書き）。
- 設定ウィザード CLI:
  - kabusys.config_setup: 対話式ウィザードで .env を初期作成・更新する機能。シークレット入力のマスク表示、デフォルト・選択肢対応、保存確認を実装。
- 設定検証 CLI:
  - kabusys.validate_config: 必須環境変数、KABUSYS_ENV 値、ログレベル、DB パス、config/*.yaml の存在とパース検証（PyYAML がない場合は YAML 検証をスキップ）。--strict オプションで警告を FAIL 扱いにできる。
- 起動スクリプト:
  - run_execution: ExecutionEngine の起動スクリプト。KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（data/paper_trading.db）を使用して本番 DB と完全分離。停止フラグ / pid ファイルの扱いを実装。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用。
- 実行系コンポーネント統合:
  - BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager の組立てと起動ロジック（ExecutionEngine.run_session を別スレッドで実行し、停止フラグを監視して安全に停止）。
  - RiskConfig 初期設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を Engine 起動時に設定。
- 監視基盤:
  - monitoring_db の初期化呼び出しを起動スクリプトに組込（冪等に監視テーブルを保証）。
- ロギングユーティリティ:
  - kabusys.utils.logging_setup: ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション・30日保持）を設定。ログレベル/ログディレクトリ解決ロジックを実装。既存ハンドラの二重設定を防止するためクリアして再設定。
- プロセス優先度 / CPU affinity:
  - kabusys.utils.process_priority: set_process_priority(level)（Windows / POSIX の差分吸収）、set_cpu_affinity(cpu_count) を提供。権限不足や未対応 OS を考慮して安全にスキップする挙動を実装。
- ポートフォリオ構築ライブラリ:
  - portfolio_builder: 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights)。全スコアが 0 の場合は警告を出して等配分にフォールバック。
  - risk_adjustment: セクター集中制限の apply_sector_cap、マーケットレジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear とフォールバック動作）。
  - position_sizing: calc_position_sizes を実装（allocation_method: "risk_based"/"equal"/"score" 対応）。単元株（lot_size）で丸め、1 銘柄上限・利用率上限を考慮。aggregate cap 超過時のスケーリングと端数処理（fractional remainder に基づく追加配分）を実装。手数料・スリッページ見積り用 cost_buffer 引数あり。
- Paper Trading 検証ツール:
  - tools/paper_verification_report: SQLite（デフォルト data/paper_trading.db）から system_status / trade_logs / risk_logs を集計し、稼働率・注文成功率・送信率・P95 レイテンシ等を計算して PASS/FAIL 判定のレポートを出力。閾値を定数化（稼働率 99%、成立率 90%、送信率 95%、P95 200ms）。
- リサーチ（ファクター計算）:
  - research/factor_research: Momentum / Value / Volatility / Liquidity を計画したモジュール骨子。DuckDB 接続を受け取り prices_daily / raw_financials を参照してファクターを算出する設計。

Changed
- n/a 初期リリースのため該当なし。

Fixed
- n/a 初期リリースのため該当なし。

Deprecated
- n/a

Removed
- n/a

Security
- 環境変数の必須チェックを validate_config で実装し、README 相当の .env 生成を支援することで運用ミスによる誤発注リスクを低減。

Known issues / Notes
- research/factor_research.calc_momentum の実装が途中で途切れており（ソース末尾が切れている）、モメンタム計算の完全実装が未完。
- apply_sector_cap 内に price が 0.0 の場合のフォールバックに関する TODO があり、price 欠損時にエクスポージャーが過少評価される可能性がある。将来的に前日終値や取得原価へのフォールバックを推奨。
- ログディレクトリ作成に失敗した場合はファイル出力をスキップして標準出力のみで継続する設計（意図的なフォールバック。ただしディスクや権限の問題の通知は必要）。
- run_monitoring は MONITOR_POLL_INTERVAL に不正な値が設定された場合にデフォルトへフォールバックするロジックを持つ（0 以下や非数値は警告 → 60 秒）。
- Process priority / CPU affinity の設定は権限不足や未対応環境では警告を出してスキップするため、期待どおりに優先度調整されないケースがある。
- Version: __version__ = "0.1.0"

今後の予定（例）
- research/factor_research の完成（calc_momentum 等の実装補完）。
- 価格欠損時のフォールバックロジック実装（apply_sector_cap の TODO 解消）。
- テストカバレッジの追加（各 pure function と CLI のユニット / 結合テスト）。
- 実行/監視系の integration テスト（paper_trading と live の挙動確認）。

---
（この CHANGELOG はリポジトリの現在コードベースから推測して作成しています。運用上の変更やコミット履歴に基づく詳細は実際の VCS ログを参照してください。）