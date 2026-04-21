# Changelog

すべての重要な変更点をここに記載します。  
フォーマットは「Keep a Changelog」に準拠します。

最新: 未リリースの変更点は Unreleased に記載しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-21
初回リリース

### 追加 (Added)
- 基本アプリケーション情報
  - パッケージバージョンを導入: `kabusys.__version__ = "0.1.0"`。

- 起動スクリプト
  - 実行エンジン用起動スクリプト `run_execution.py` を追加。
    - KABUSYS_ENV が `paper_trading` の場合は専用のペーパートレード用 SQLite DB を使用（`PAPER_TRADING_SQLITE_PATH`、デフォルト: `data/paper_trading.db`）。
    - ブローカークライアントの生成を `BrokerClientFactory` に委譲。
    - `ExecutionEngine` をスレッドで実行し、プロジェクトルートの停止フラグファイル（`data/stop_requested.flag`）と PID ファイル（`data/execution.pid`）を用いて安全に停止可能。
    - リスク管理コンフィグのデフォルト値（max_position_pct, max_utilization 等）を定義し、起動時に `init_monitoring_db` を呼んで監視テーブルの整合性を担保。
  - 監視ループ起動スクリプト `run_monitoring.py` を追加。
    - `SystemMonitor` を用いたポーリングループを実装。
    - ポーリング間隔を環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - 監視は常に本番用の sqlite_path を使用する（環境に依存せず本番の監視 DB を参照）。
    - 停止フラグ検知および例外発生時のログ出力を実装。

- 設定管理
  - `kabusys.config.Settings` クラスを導入し、主要な環境設定をプロパティとして提供。
    - J-Quants / kabuステーション / LINE API / DB パス / 監視しきい値 / システムフラグ など多くの設定を環境変数から取得。
    - `env`（KABUSYS_ENV）は `development`, `paper_trading`, `live` をサポートし、不正値は例外を送出。
    - `paper_fill_mode` のバリデーション（"instant"|"partial"|"never"|"reject"）を実装。
    - `paper_sqlite_path`, `sqlite_path`, `duckdb_path` 等の Path 型での解決を提供。
  - 自動 .env 読み込み
    - プロジェクトルートを `.git` または `pyproject.toml` から探索して自動で `.env` / `.env.local` を読み込む機能を追加（`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能）。
    - `.env` パーサーは `export KEY=val` 形式、クォート（シングル/ダブル）内のエスケープ、インラインコメントの扱い等に対応。

- 設定ユーティリティ CLI
  - 対話式 .env 作成ウィザード `config_setup.py` を追加。
    - 一連の設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START 等）を対話的に収集して `.env` を生成。
    - シークレット項目はマスク表示、既存 `.env` の読み込み・再利用に対応。
  - 設定検証ツール `validate_config.py` を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、`config/*.yaml` の存在・パースチェック（PyYAML がない場合はスキップ）等を実行。
    - `--strict` オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築ライブラリ（portfolio モジュール）
  - 候補選定・重み計算: `portfolio.portfolio_builder`
    - `select_candidates`（スコア降順、同点タイブレーク）、
    - `calc_equal_weights`、`calc_score_weights`（スコア合計が 0 の場合は等金額にフォールバック）。
  - セクター集中制限・レジーム乗数: `portfolio.risk_adjustment`
    - `apply_sector_cap`（既存保有を考慮して同一セクター上限を越える候補を除外、"unknown" セクターは適用除外）、
    - `calc_regime_multiplier`（"bull"/"neutral"/"bear" マップ、未知レジームは警告を出して 1.0 でフォールバック）。
  - 株数決定・丸め処理: `portfolio.position_sizing`
    - `calc_position_sizes`（`risk_based` / `equal` / `score` の割当方式、単元株（lot_size）で丸め、per-stock と aggregate のキャップ、cost_buffer を用いた保守的見積もり、スケールダウン時の残差処理）。
  - 上記を package export に登録。

- 監視・検証ツール
  - `monitoring.monitoring_db.init_monitoring_db` を利用して監視テーブルの冪等初期化を行う（起動時の自動保証）。
  - Paper Trading 検証レポート生成スクリプト `tools/paper_verification_report.py` を追加。
    - 指定期間（--from/--to）または DB 全期間でのレポート生成。
    - 指標: 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を計算。
    - P95 計算、閾値（稼働率 >= 99.0%、fill_rate >= 90%、send_rate >= 95%、P95 <= 200 ms）に基づく PASS/FAIL 判定。
    - DB が存在しない場合やテーブルがない場合のフォールバック処理を実装。

- ロギング / プロセス制御ユーティリティ
  - `utils.logging_setup.setup_logging` を追加。
    - stdout への StreamHandler と日次ローテーションの FileHandler（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続する安全な実装。
    - ログレベル・ログディレクトリの解決順を定義（引数 > 環境変数 > デフォルト）。
  - `utils.process_priority` を追加。
    - Windows / POSIX（Linux/Mac/FreeBSD）での優先度設定（nice / HIGH_PRIORITY_CLASS 等）を抽象化。
    - CPU affinity を最初の N コアに固定する `set_cpu_affinity` を提供。
    - psutil による操作で権限不足や未実装 API を考慮し、失敗時は警告を出してスキップする。

- 研究用ファクターモジュール（research/factor_research）
  - DuckDB を用いたファクター計算の土台を追加（モメンタム、MA200、ATR、出来高等の定義と計算方針）。
  - （実装は一部まで含まれる。prices_daily / raw_financials を使う設計。）

### 変更 (Changed)
- .env 読み込みの挙動
  - プロジェクトルート探索を `.git` / `pyproject.toml` に基づく方法に変更し、CWD に依存しない自動ロードを実現。
  - `.env` と `.env.local` の読み込み順序（`.env.local` が上書き）と OS 環境変数の保護（protected set）を実装。

### 修正 (Fixed)
- 多数の外部条件に対する堅牢性向上
  - ログディレクトリ作成失敗、FileHandler 作成失敗、psutil の AccessDenied/NotImplemented による例外等を安全にハンドリングするよう修正（エラーで停止しない）。
  - 起動時に監視テーブルが存在しない場合でも `init_monitoring_db` を呼んで冪等に初期化することで起動失敗を回避。

### 注意事項 (Notes)
- Paper Trading と Live の DB は分離される設計（`Settings.paper_sqlite_path` を使用）。Monitoring は環境にかかわらず本番の `sqlite_path` を使用する点に注意。
- 将来的な拡張（TODO）として、銘柄ごとの lot_size 振り分けや価格フォールバックロジックなどがコメントとして残されています。
- `research.factor_research` は設計方針および一部実装を含むが、完全実装は今後の作業が必要。

---

この CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノートとして公開する前に、差分やコミットメッセージと照合して調整してください。