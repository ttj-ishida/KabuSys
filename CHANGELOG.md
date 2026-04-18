# CHANGELOG

このファイルは Keep a Changelog の形式に準拠しています。  
既知の変更点はソースコードから推測して記載しています（実装意図や公開 API を元にまとめたものです）。

すべての変更は semver を前提としています。日付はリリース想定日です。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-18

Added
- 実行基盤と監視ツール群を追加
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV に応じて本番/ペーパートレードを切り替え、ペーパートレード時は専用 SQLite（data/paper_trading.db）を使用する。
    - BrokerClientFactory によるブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて Engine を構築し、別スレッドでセッションを実行。
    - 停止フラグ（data/stop_requested.flag）検知による安全なシャットダウン、実行 PID ファイル管理（data/execution.pid）。
    - RiskConfig によるデフォルトリスク制約（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等）を導入。
  - run_monitoring.py: SystemMonitor 用ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視 DB は環境にかかわらず本番 sqlite_path を使用（監視情報の一元化）。
    - 停止フラグ検知でループ終了、例外時でもログを残して次ポーリングへフォールバック。
- 設定管理
  - config.py: 環境変数ラッパー Settings を提供。
    - .env/.env.local の自動ロード機能（プロジェクトルート検出: .git または pyproject.toml）。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - .env の上書き制御（OS 環境変数の保護）や export 形式、クォート対応、インラインコメント処理を行う堅牢なパーサを実装。
    - デフォルト値や検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE など）の整合性チェックを備えたプロパティ群。
- 設定ユーティリティ / 検証
  - config_setup.py: 対話式 .env ウィザードを追加。既存値再利用、シークレットマスク、確認後のファイル書き込みをサポート。
  - validate_config.py: 起動前チェック CLI を追加。必須環境変数、KABUSYS_ENV 値、ログレベル、DB パス、config/*.yaml の存在と YAML パース（PyYAML が存在する場合）などを検証。--strict で警告を失敗扱いにできる。
- ポートフォリオ構築ライブラリ
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルのランク付け・上位 N 抽出（score 降順、signal_rank による tie-break）。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分ロジック（全スコア0時は等配分へフォールバック）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中度制限（既存保有を考慮）に基づく候補フィルタ。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear をサポート、未知レジームはフォールバック）。
  - portfolio.position_sizing:
    - calc_position_sizes: 各種配分方式（risk_based / equal / score）に対応した発注株数計算。単元株丸め、per-position 上限、aggregate cap（available_cash）でのスケールダウン、cost_buffer による保守的見積りを実装。lot_size の将来的拡張を見据えた設計。
- ロギング / プロセス管理ユーティリティ
  - utils.logging_setup: 統一的ログ設定ユーティリティを追加。stdout への StreamHandler と日次ローテートされた TimedRotatingFileHandler（logs/<app_name>.log、30日分保持）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続する耐性を持つ。
  - utils.process_priority: プラットフォーム差分を吸収してプロセス優先度（high/normal/low）と CPU affinity を設定するユーティリティを追加。Windows と POSIX（Linux/Mac/FreeBSD）をサポートし、権限不足や未対応 OS の場合は警告を出してスキップ。
- 解析 / レポート
  - tools.paper_verification_report.py: ペーパートレード検証用レポートを追加。system_status / trade_logs / risk_logs を集計して稼働率、注文成功率、送信率、P95 レイテンシなどを算出し PASS/FAIL 判定を行う。コマンドライン引数で期間指定可能（--from/--to、--db で DB 指定）。P95 計算や N/A の扱いに配慮。
- 研究用モジュール（部分実装）
  - research.factor_research: DuckDB を使ったファクター（Momentum / Value / Volatility / Liquidity）計算の基盤を追加。モメンタム計算（1M/3M/6M、MA200 乖離）などを想定した定数と関数シグネチャを実装（prices_daily / raw_financials を参照）。

Changed
- なし（初期リリース）

Fixed
- なし（初期リリース）

Security
- なし（初期リリース）

Notes / Implementation details
- run_monitoring は MONITOR_POLL_INTERVAL が不正（0 以下や整数以外）の場合にデフォルト 60 秒へフォールバックして警告ログを出力する。
- Settings は必須環境変数未設定時に明確な ValueError を投げる設計。環境変数やパスのデフォルトを多数定義しており、ローカル開発での起動を容易にする。
- config_setup により生成した .env ファイルは Git にコミットしないよう注意喚起を埋め込み。
- position_sizing の aggregate cap スケールダウンアルゴリズムは lot_size 単位での再配分を行い、残余キャッシュで端数を分配する安定化ロジックを実装。
- process_priority 系は権限不足やプラットフォーム差異に対して安全にフォールバックする（警告ログのみ）。

開発 / 次の予定（推測）
- research.factor_research の完全実装（SQL/DuckDB クエリ実装の続き）
- Strategy / Execution のユニットテスト整備、エンドツーエンドの mock-based テスト
- 銘柄別 lot_size や手数料・スリッページモデルの細分化対応
- UI/監視ダッシュボードやアラート連携（LINE）設定の強化

---

（この CHANGELOG はソースコードから推測してまとめたものです。実際のリリースノート作成時はコミット履歴や PR 説明と照合してください。）