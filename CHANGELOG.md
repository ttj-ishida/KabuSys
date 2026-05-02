# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  

なお、この CHANGELOG はコードベースから機能・振る舞いを推測して作成しています。

## [0.1.0] - 2026-05-02

### Added
- 複数のコマンドラインエントリポイント（運用・監視・レポート用）を追加
  - run_execution: ExecutionEngine 起動スクリプト（本番 / ペーパートレード分離、起動時リコンシリエーション、起動サマリ出力、バックグラウンドスレッド駆動）
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL 環境変数対応、停止フラグ / PID ファイル管理）
  - run_intraday_monitor: ザラ場中監視 CLI（1回実行 / ウォッチモード、見やすい CLI サマリ出力）
  - run_position_reconciliation_report: Position Reconciliation View（1回実行 / ウォッチモード、JSON 出力・保存対応）
  - run_signal_queue_report: Signal Queue Confirmation View（対象日指定、JSON 出力・保存対応）
  - run_performance_report: 運用成績サマリーレポート（daily/weekly/monthly、env 指定、範囲指定、保存対応）
  - run_pre_market_report: Pre-Market Report（データ鮮度やタスクスケジューラ状態チェック、停止フラグ考慮、JSON/保存対応）
  - run_market_close_report: Market Close Summary（終値集計レポート、JSON/保存対応）
  - validate_config: 設定検証 CLI（.env と config/*.yaml の整合性・必須 env などのチェック、--strict オプション）
  - config_setup: 対話式環境設定ウィザード（.env の初期作成・更新を支援）
  - tools/paper_verification_report: Paper Trading 検証レポート生成スクリプト（稼働率・注文成功率・送信率・レイテンシ等の集計）
- 設定管理モジュールを追加
  - kabusys.config.Settings：環境変数 / .env 自動読み込み、各種設定プロパティを提供
  - .env 自動ロード（プロジェクトルート検出: .git / pyproject.toml 基準）、.env と .env.local の読み込み順序と保護（OS 環境変数の保護）を実装
  - 各種プロパティ（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID ファイルパス、kill/threshold 設定、KABUSYS_ENV / LOG_LEVEL 検証 等）
- .env ファイルのパース強化
  - export プレフィックス対応、クォート文字列（シングル/ダブル）のエスケープ処理、インラインコメントの扱いを考慮した堅牢なパーサを実装
- 複数の DB 連携を実装
  - SQLite（監視/実行用）と DuckDB（分析用）の接続を標準化して各レポート / エンジンで利用
  - Paper Trading モード時は専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離
- リスク設定の読み込みと検証を実装
  - config/risk_config.yaml の読み込み処理（yaml のエラー処理含む）、各種パラメータの型変換と範囲チェック（max_position_pct, max_utilization, max_drawdown, rate_limit_per_sec, circuit_breaker_* 等）
  - 不正値に対して明確な例外メッセージを発行
- 実行エンジン周りの初期処理/安全策を追加
  - プロセス優先度を "high" に設定する呼び出し（起動直後）
  - 起動時総資産の計算（現金 + 保有評価額）とそれに基づく RiskManager 初期化
  - 起動時のリコンシリエーション実行と Execution Startup Summary の出力・保存（生成失敗時も起動継続する堅牢性）
  - 停止フラグ（data/stop_requested.flag）を検知して安全にエンジン停止
- 監視（SystemMonitor）関連の改善
  - モニタリングループのポーリング間隔を環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）
  - 監視プロセス用 PID ファイルの出力と停止フラグ検知による優雅な終了処理
  - 監視 DB 初期化（init_monitoring_db）呼び出しで監視テーブルの冪等な準備
- CLI レポート系に共通の機能を多数追加
  - JSON 出力、Markdown/CLI フォーマット、ファイル保存（artifacts 下）対応
  - watch モード（定期ポーリング）と間隔指定オプションの追加
- ユーティリティ（logging_setup, process_priority 等）を各起動スクリプトで利用

### Changed
- .env 自動読込の仕様
  - OS 環境変数を保護しつつ .env、.env.local をプロジェクトルートから読み込む。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能
- Settings の挙動
  - KABUSYS_ENV, LOG_LEVEL の値チェックを厳格化
  - is_live / is_paper / is_dev のヘルパーを追加
  - paper_fill_mode の有効値検証を追加（instant/partial/never/reject）
- 起動/終了処理の堅牢化
  - DB 接続や外部クライアント（broker など）を finally ブロックで確実にクローズするよう改善
  - 起動時に停止フラグが立っている場合は起動を行わず早期終了する保護を追加
- エラーハンドリング
  - 監視ループ内の check_once() 呼び出しが例外を投げてもログ出力して次ポーリングへ継続するよう変更（監視の継続性向上）
  - 各 CLI で DB への読み取り専用接続（read_only）を使用することで安全性を向上

### Fixed
- 環境変数のパースで発生し得るエッジケース（引用符付き文字列内のバックスラッシュエスケープ、export プレフィックス、インラインコメント等）に対応して誤設定の解釈を改善
- RiskConfig 読み込み時の不整合チェック（パーサエラー、キー欠落、閾値の範囲外設定）に対する明示的な例外メッセージを追加
- run_intraday_monitor 等の CLI が DB に接続できなかった場合に適切にエラーメッセージを出して終了するよう修正

### Security
- .env ファイル取り扱いに関する注意を config_setup のヘッダに明記（.env を Git にコミットしない旨）
- OS 環境変数を保護する読み込みロジックを導入し、意図しない上書きを防止

### Notes
- 本リリースではアーキテクチャの土台（設定管理、プロセス管理、レポート生成、監視、実行起動フロー）を整備しました。ExecutionEngine や BrokerClientFactory、各種レポート生成ロジックは別モジュールとして分離されており、今後の改善・拡張（例: 詳細なメトリクス、外部通知、スケジューラ統合）を想定しています。
- config/*.yaml（特に risk_config.yaml）や .env の設定不備は validate_config で事前検出できるため、デプロイ前に実行することを推奨します。

---

（以降のリリースでは各機能の詳細な変更やバグフィックスを逐次追記してください。）