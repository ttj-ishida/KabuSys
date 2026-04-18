# CHANGELOG

すべての注目すべき変更を記録します。本ファイルは「Keep a Changelog」の慣例に準拠します。

## [0.1.0] - 2026-04-18

初回リリース。日本株自動売買フレームワーク「KabuSys」の基本機能を実装しました。

### Added
- コア起動スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイント。KABUSYS_ENV が `paper_trading` の場合はペーパートレード用の専用 SQLite（デフォルト: data/paper_trading.db）と MockBrokerClient を利用して本番 DB と完全に分離します。エンジンは別スレッドで動作し、data/stop_requested.flag により安全に停止可能。PID ファイル出力をサポート。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する設計。

- 設定管理
  - config.py: Settings クラスを実装。環境変数読み込み、検証ロジック、各種パス/閾値（duckdb/sqlite パス、PID/kill flag、CPU/メモリ/ディスク閾値など）を提供。PAPER_FILL_MODE の入力検証、KABUSYS_ENV/LOG_LEVEL のバリデーションを含む。
  - 自動 .env ロード: プロジェクトルート（.git または pyproject.toml）を探索して .env/.env.local を自動読み込み（OS 環境変数は保護）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

- ユーティリティ
  - utils/logging_setup.py: 統一ロギング設定ユーティリティ。StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、デフォルト logs/、30 日保持）をルートロガーに設定。LOG_LEVEL / LOG_DIR 解決。既存ハンドラをクリアして二重設定を防止。
  - utils/process_priority.py: プロセス優先度／CPU アフィニティ設定ユーティリティ。Windows と POSIX 系を吸収し、psutil を用いた設定とフォールバック処理を実装。set_process_priority, set_cpu_affinity を提供（権限不足時は警告でスキップ）。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py: シグナルの候補選定（select_candidates）、等配分（calc_equal_weights）、スコア加重（calc_score_weights。全スコアが 0 の場合は等配分へフォールバック）。
  - portfolio/risk_adjustment.py: セクター集中制限の適用（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier。既知レジームのマップ、未知時は 1.0 を返す）。
  - portfolio/position_sizing.py: 各銘柄の購入株数算出。allocation_method により "risk_based" / "equal" / "score" をサポート。単元株（lot_size）丸め、1 銘柄上限・aggregate cap（利用可能現金を超える場合のスケールダウン）処理、cost_buffer による保守的見積りを実装。

- ツール・CLI
  - config_setup.py: .env の対話式ウィザード。初期作成・更新支援。シークレット項目はマスクして表示。生成された .env に関する注意（Git にコミットしないなど）を含む。
  - validate_config.py: 起動前の設定検証 CLI。必須環境変数の確認、KABUSYS_ENV/LOG_LEVEL/DB パスの検証、config/*.yaml の存在と（PyYAML があれば）パース検証。本番環境用の追加ガード（LINE トークン未設定や KILL_FLAG_CLEAR_ON_START の危険設定を警告）を実装。--strict オプションで警告も失敗扱いにできる。
  - tools/paper_verification_report.py: ペーパートレード検証レポート生成スクリプト。system_status / trade_logs / risk_logs を参照して稼働率、注文成功率（fill/send）、リスク却下数、レイテンシ（avg/max/P95）などを集計し PASS/FAIL 判定を生成。P95 計算、日付フィルタ、DB パス指定 (--db, 環境変数 PAPER_TRADING_SQLITE_PATH) に対応。

- 研究用モジュール（部分実装）
  - research/factor_research.py: DuckDB 接続を受け取りファクター（Momentum / Value / Volatility / Liquidity）を計算する基盤を追加（モメンタム計算などを含む。prices_daily / raw_financials を参照する設計）。（実装は継続中、将来的に完全なファクター計算を提供）

- パッケージ情報
  - __init__.py にて __version__ = "0.1.0" を設定。

### Changed
- （初回リリースのため該当なし）

### Fixed
- .env パーサの堅牢化（config._parse_env_line）
  - export 形式のサポート、シングル／ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理（クォートあり/なしでの取り扱い差分）を実装し、より現実的な .env フォーマットに対応。
- init_monitoring_db を各起動スクリプトで冪等に呼び出し、監視テーブルの存在を保証（テーブルがない状態での起動失敗を防止）。

### Security
- .env ファイルに関する注意書きを config_setup に明示（.env を絶対に Git にコミットしないこと）。
- 環境変数読み込みでは OS 環境変数を保護（.env 自動ロード時に上書きしない実装）。

### Notes / Known issues・留意点
- run_monitoring.py は「監視目的の DB 接続」において、KABUSYS_ENV にかかわらず settings.sqlite_path（本番の monitoring DB）を使用する設計となっています。意図的な挙動なので運用時は注意してください。
- apply_sector_cap:
  - price_map に価格が欠損（0.0 等）だとエクスポージャーが過小見積りされ、想定よりブロックが緩くなる可能性があります（TODO コメントあり）。将来的にフォールバック価格導入を検討。
- process_priority / set_cpu_affinity:
  - psutil による優先度設定は権限やプラットフォームに依存します。設定に失敗した場合は警告を出してスキップします。
- position_sizing:
  - 現状 lot_size はグローバルな単一値（デフォルト 100）で処理。将来的に銘柄毎の lot_size をサポートする予定（stocks マスタへの拡張想定）。
- validate_config の YAML 検証は PyYAML 未インストール時はスキップし警告となります。
- tools/paper_verification_report の集計はテーブル存在や列の有無に弱い箇所があり、OperationalError を捕捉して N/A 相当で処理するように配慮しています。

---

(補足) 初回リリースのため BREAKING CHANGES はありません。今後のバージョンで API/設定の互換性に変更を加える場合は明示的に記載します。