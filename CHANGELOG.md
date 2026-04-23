# Changelog

すべての重要な変更は Keep a Changelog 準拠で記載しています。  
フォーマット: https://keepachangelog.com/ja/

## [Unreleased]

## [0.1.0] - 2026-04-23
初回リリース。

### Added
- 基本アーキテクチャと起動スクリプト
  - run_execution.py: ExecutionEngine 起動用スクリプトを追加。スレッドでエンジンを起動し、data/execution.pid に PID を管理。data/stop_requested.flag による停止監視に対応。
  - run_monitoring.py: SystemMonitor 用ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を制御可能（デフォルト 60 秒）。Monitoring は環境に関わらず本番 sqlite_path を使用する仕様。

- 設定・環境変数管理
  - config.py: .env 自動読み込み（.env / .env.local、OS 環境変数優先）を実装。プロジェクトルートを .git または pyproject.toml を基準に探索してロード。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化に対応。
  - Settings クラスを導入し、J-Quants / kabuAPI / LINE / DB / 監視閾値 / 実行環境等の取得をプロパティ化。
  - PAPER_FILL_MODE（paper_trading 用のモック約定モード）や PAPER_TRADING_SQLITE_PATH（ペーパートレード専用 DB）のサポート。
  - PID / Kill Flag 関連の設定プロパティ（pid_file_path, kill_flag_path, kill_flag_clear_on_start）を追加。

- CLI ユーティリティ
  - config_setup.py: 対話式ウィザードで .env を初期作成・更新するツールを追加。シークレット項目はマスク表示。デフォルト・選択肢指定あり。
  - validate_config.py: 起動前に .env と config/*.yaml を検査する CLI を追加。必須環境変数チェック、KABUSYS_ENV／LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、YAML の存在／パース検証（PyYAML が存在する場合）。--strict オプションで警告も失敗扱いにできる。
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、P95 レイテンシなどを集計して PASS/FAIL 判定を表示。PAPER_TRADING_SQLITE_PATH 環境変数および --db オプションで DB 指定可能。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定(select_candidates)・等分配(calc_equal_weights)・スコア加重(calc_score_weights)を実装。
  - portfolio/risk_adjustment.py: セクター集中制限の適用(apply_sector_cap)、市場レジームに応じた投下資金乗数(calc_regime_multiplier)を実装（regime: bull/neutral/bear）。
  - portfolio/position_sizing.py: position sizing ロジックを実装。risk_based / equal / score の配分方式に対応。単元株（lot_size）丸め、aggregate cap によるスケールダウン、cost_buffer による保守的見積り等を実装。

- リサーチ / ファクター計算基盤
  - research/factor_research.py: DuckDB を使ったファクター計算モジュールの骨格を追加。モメンタム（1M/3M/6M、MA200乖離）、ATR（ボラティリティ）、流動性指標などを計算する設計。DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計方針。

- DB / 分析基盤
  - DuckDB と SQLite 両方への接続をサポート（起動スクリプトで接続して初期化）。monitoring 用テーブル初期化関数 init_monitoring_db を使用して冪等的に監視用テーブルを保証。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテート、30日保持）をルートロガーに設定。LOG_LEVEL / LOG_DIR / app_name 指定で出力制御。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみ継続。
  - utils/process_priority.py: プラットフォーム差分（Windows / POSIX）を吸収してプロセス優先度を設定するユーティリティを追加。set_process_priority("high" | "normal" | "low")、CPU affinity 設定用 set_cpu_affinity を提供。権限不足時は警告でスキップ。

- Execution 周りの初期構成・安全装置
  - 実行エンジン起動前にプロセス優先度を high に設定。
  - paper_trading 環境では BrokerClientFactory が MockBrokerClient を返却し、ペーパートレード用 DB（data/paper_trading.db など）を使用して本番 DB と分離。
  - RiskManager のデフォルト構成を実装（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）および初期ポートフォリオ値に broker.get_available_cash() を使用。

### Changed
- N/A（初回リリースのため既存の変更履歴なし）

### Fixed
- N/A（初回リリースのためバグ修正履歴なし）

### Notes / Implementation details
- .env パーサーはシングル/ダブルクォートやバックスラッシュエスケープ、行内コメントの扱いを考慮しており、export KEY=val 形式にも対応しています。
- run_monitoring は MONITOR_POLL_INTERVAL の不正値（0 以下や非整数）を検知してデフォルト値にフォールバックする実装になっています。
- apply_sector_cap のエクスポージャー計算では price が欠損（0.0）だと過少見積りになる旨の注記があり、将来的なフォールバック価格導入を検討しています（TODO）。
- logging_setup はログディレクトリ作成に失敗した場合にファイルハンドラの設定をスキップし、stdout への出力のみで継続する堅牢化を行っています。
- paper_verification_report は DB テーブルが存在しない場合に例外を握り潰して N/A 等で扱うフォールバック実装を行っています。

### Known issues / TODO
- portfolio.position_sizing: 銘柄ごとの lot_size を将来的にサポートするための拡張注記あり（現状は一律の lot_size を使用）。
- risk_adjustment.apply_sector_cap: 価格欠損時のフォールバックロジック未実装（TODO コメントあり）。
- research/factor_research.py: ファイル末尾で実装が途中（コード断片）になっている箇所が存在するため、ファクター計算の完全実装は今後の作業。

---

今後のリリースでは以下を想定しています:
- research/factor_research の完全実装とパフォーマンス最適化
- ExecutionEngine・OrderManager・Reconciler 等の詳細実装とテストカバレッジ追加
- ドキュメント（README、運用手順、デプロイ手順）の整備

----- 

注: 上記 CHANGELOG は提供されたコードベースから推測して作成しています。実際の変更履歴やリリース日付はプロジェクト運用ルールに従って調整してください。