# Changelog

すべての重要な変更は Keep a Changelog の慣習に従って記載します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

注: 以下は提供されたソースコードから推測して作成した変更履歴です。実際のコミット履歴ではありません。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-19

### Added
- プロジェクト初期リリース。パッケージバージョンは `kabusys.__version__ = "0.1.0"`。
- 実行スクリプト
  - run_execution: ExecutionEngine 起動スクリプトを追加。プロセス優先度設定、SQLite/DuckDB 接続、BrokerClient の生成、OrderManager / RiskManager / Reconciler の組立て、別スレッドでエンジンを実行する仕組みを提供。停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）に対応。KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB を使用。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する設計。停止フラグファイルで安全終了。
- 設定関連
  - config.Settings: 環境変数をラップする Settings クラスを追加。J-Quants / kabu / LINE / DB / 監視閾値 / システム設定等をプロパティとして提供。KABUSYS_ENV の検証、LOG_LEVEL の検証、paper_trading 用設定（PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH）をサポート。
  - 自動 .env ロード機能: プロジェクトルート（.git または pyproject.toml）を探索して `.env` / `.env.local` を自動読み込み（OS 環境変数優先）。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - validate_config: .env と config/*.yaml の事前検証用 CLI を追加。必須環境変数チェック、KABUSYS_ENV・LOG_LEVEL の検証、DB パスの親ディレクトリチェック、YAML パースチェック（PyYAML がない場合はスキップ）、本番環境向けの追加ガード、`--strict` モードをサポート。
  - config_setup: 対話式ウィザードで .env を作成・更新する CLI を追加。シークレット項目はマスク表示、既存 .env の取り込み、保存前の確認などを実装。
  - .env パーサ実装: export 付き行、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いなどに対応する堅牢なパーサを提供。読み込み時の override / protected（OS 環境変数保護）オプションあり。
- ロギング / プロセス管理ユーティリティ
  - utils.logging_setup.setup_logging: stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler, 30日保持）をルートロガーに設定する共通ユーティリティを追加。既存ハンドラをクリアして二重設定を防止。ログディレクトリ作成失敗時はファイル出力をスキップして警告。
  - utils.process_priority: psutil を用いたプロセス優先度（high/normal/low）設定と CPU affinity 固定関数を追加。Windows / POSIX (Linux, Darwin, FreeBSD) の違いを抽象化し、権限不足や未対応 OS の場合は警告を出してスキップ。
- ポートフォリオ構築ライブラリ
  - portfolio.portfolio_builder: シグナルの候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
  - portfolio.risk_adjustment: セクター集中上限チェック（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。未知レジームや "unknown" セクターのフォールバックロジックを備える。
  - portfolio.position_sizing: allocation_method（"risk_based", "equal", "score"）に基づく株数決定ロジックを実装。単元株（lot_size）での丸め、個別・総合の投下上限（max_position_pct, max_utilization）、コストバッファ適用、投資合計が利用可能現金を超える場合のスケーリングと残差処理を含む。
  - portfolio パッケージエクスポートを整備（select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier）。
  - position_sizing 内に将来の拡張 TODO（銘柄別 lot_size の導入）を明記。
- Execution 側の初期 RiskManager 設定値を実装例として提供（max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）。初期ポートフォリオ値は broker.get_available_cash() から取得。
- Monitoring DB 初期化ユーティリティ（monitoring.monitoring_db.init_monitoring_db）を参照して、起動時に監視テーブルの存在を保証する処理を追加（冪等）。
- tools.paper_verification_report: ペーパートレード用検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均 / 最大 / P95）を算出し、閾値に対する PASS/FAIL 判定を出力。日付範囲指定（--from/--to）と DB パス指定（--db）をサポート。
  - P95 計算ユーティリティ、閾値定義（稼働率99%, 成立率90%, 送信率95%, P95 <= 200ms）を含む。
- research.factor_research の基盤を追加（ファクター計算モジュール）。DuckDB の prices_daily/raw_financials を参照して Momentum / Value / Volatility / Liquidity を計算する方針が記載されている（モジュール実装は一部未完）。

### Changed
- なし（初回リリースに相当するため主に追加）。

### Fixed
- なし（新規実装）。

### Deprecated
- なし。

### Removed
- なし。

### Security
- なし（特記なし）。

---

補足（実装上の注意・既知の制約・今後の改善）
- config の自動 .env 読み込みはプロジェクトルートの検出に依存するため、配布パッケージ環境では自動ロードがスキップされる可能性がある（設計上の意図）。
- portfolio.risk_adjustment.apply_sector_cap: price が欠損（0.0）の場合にエクスポージャが過少見積もられる点が TODO として指摘されている。将来的に前日終値や取得原価などのフォールバック価格を導入することが想定される。
- research.factor_research は大枠が実装されているが（関数定義や定数）、一部関数が未完（ソースが途中で切れている）。追加実装が必要。
- process_priority の設定は権限やプラットフォームに依存するため、権限不足時は警告を出して処理をスキップする安全設計になっている。
- run_monitoring は監視 DB として sqlite_path（本番用）を常に使用する設計のため、テスト／開発環境で使う際は注意が必要。

もし実際のコミットや変更日付、より詳細な差分情報があれば、それを元に CHANGELOG を改訂します。必要であれば英語版やセクション分割（例: CLI, ライブラリ, ツール等）も作成します。