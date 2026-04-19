# Changelog

すべての変更は Keep a Changelog の形式に従います。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-04-19
初回リリース。日本株自動売買フレームワーク「KabuSys」の基本機能を実装しました。主な追加点は以下の通りです。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として追加。
  - パッケージ公開用のエクスポート（portfolio, execution, monitoring 等）を `kabusys.__init__` で定義。

- 環境設定 / 設定管理
  - Settings クラスを実装し、環境変数から各種設定を取得（`kabusys.config`）。
  - 自動 `.env` ロード機能を追加（プロジェクトルートの検出: `.git` または `pyproject.toml` を基準）。環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
  - `.env` のパースロジックを強化：
    - `export KEY=val` 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理対応
    - インラインコメント処理のルール（クォートなしの場合の `#` 扱い）を実装
  - 各種設定プロパティを実装（例: DB パス、Paper Trading 関連、監視閾値、ログレベル等）。`KABUSYS_ENV` の妥当性チェック、`PAPER_FILL_MODE` の有効値チェック等を実施。

- 対話式設定ウィザード
  - `.env` を対話式に作成/更新する CLI を追加（`kabusys.config_setup`）。
  - デフォルト値の表示、シークレット値のマスク、選択肢の検証、保存前の確認等を実装。

- 設定検証 CLI
  - `.env` および `config/*.yaml` の基本チェックを行う `kabusys.validate_config` を追加。
  - 必須環境変数チェック、`KABUSYS_ENV` / `LOG_LEVEL` の検証、DB パスの親ディレクトリチェック、YAML のパース検証（PyYAML が存在する場合）、本番環境向けガード（LINE 設定・KILL_FLAG_CLEAR_ON_START）を実装。
  - `--strict` オプションで警告を失敗扱いにできる。

- 起動スクリプト
  - 監視プロセス用起動スクリプト `run_monitoring.py` を追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒、値検証あり）。
    - 監視は常に本番用の SQLite パス（Settings.sqlite_path）を使用して DB 初期化（`init_monitoring_db`）を行う。
    - 停止フラグファイル `data/stop_requested.flag` を検知してループを抜ける。
    - `SystemMonitor` の単発チェック `check_once()` をポーリングループで実行。例外時はログを出して次ポーリングへ継続。
  - 実行エンジン起動スクリプト `run_execution.py` を追加。
    - 起動時にプロセス優先度を High に設定。
    - `KABUSYS_ENV=paper_trading` の場合、Paper 専用 SQLite（デフォルト `data/paper_trading.db`）を使用して本番 DB から完全分離。
    - ブローカークライアント生成（`BrokerClientFactory.create`）により MockBroker の利用を可能にする。
    - OrderRepository、OrderManager、RiskManager（`RiskConfig` を含む）、Reconciler、ExecutionEngine の組み立てと実行スレッド化を実装。
    - 停止フラグ検知でエンジン停止処理を行う（`engine.stop()`）。

- DB / 分析基盤
  - DuckDB 接続サポートを追加（Settings.duckdb_path）。
  - 起動スクリプトで DuckDB 接続を確立し、分析用に利用可能に。

- 監視 DB 初期化ユーティリティ
  - 監視用テーブルを作る `init_monitoring_db` を起動時に呼び出し、冪等に監視テーブルの存在を保証（実装箇所は monitoring パッケージ内）。

- ロギング設定ユーティリティ
  - `kabusys.utils.logging_setup.setup_logging` を追加。
    - コンソール出力は stdout を使用する StreamHandler と、日次ローテーション（TimedRotatingFileHandler）でログファイルへ出力（デフォルト `logs/<app_name>.log`、30 日分保持）。
    - ログディレクトリの自動作成、作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - 引数または環境変数 `LOG_LEVEL` / `LOG_DIR` による設定。

- プロセス優先度 / CPU affinity ユーティリティ
  - `kabusys.utils.process_priority` を追加。
    - Windows（psutil の優先度クラス使用）と POSIX（nice 値）を吸収してプラットフォーム非依存に優先度を設定（"high" / "normal" / "low"）。
    - `set_cpu_affinity` による CPU コア固定（最初の N コア）機能を追加。
    - アクセス権限不足等の失敗はログ警告で安全にフォールバック。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - 候補選定 / 重み付け（`kabusys.portfolio.portfolio_builder`）
    - select_candidates: スコア降順の上位 N 抽出、同点タイブレークは signal_rank による。
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコア加重配分。全スコアが 0 の場合は等金額にフォールバック（警告ログ）。
  - リスク調整（`kabusys.portfolio.risk_adjustment`）
    - apply_sector_cap: 1 セクターの時価比率が閾値を超える場合、新規候補を除外（売却予定銘柄は除外して計算、"unknown" セクターは適用除外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（"bull":1.0, "neutral":0.7, "bear":0.3、未知は 1.0 でフォールバックし警告）。
  - 株数決定・丸め（`kabusys.portfolio.position_sizing`）
    - calc_position_sizes: `allocation_method`（"risk_based" / "equal" / "score"）に基づき発注株数を計算。
    - 単元株（lot_size）で丸め、1 銘柄上限（max_position_pct）、全体投下上限（available_cash）を念頭にスケールダウンするアグリゲートキャップ実装。
    - cost_buffer を考慮した保守的コスト見積り、残余配分のための fractional remainder 処理（再現性のため安定ソート）。

- Paper Trading 検証ツール
  - `kabusys.tools.paper_verification_report` を追加。Paper Trading 用 SQLite（`PAPER_TRADING_SQLITE_PATH` 環境変数または `--db` で指定）から各種指標を集計してレポート出力:
    - 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等を算出。
    - P95 計算ユーティリティと各種閾値（稼働率 99%、fill_rate 90%、send_rate 95%、P95 200ms）を実装。
    - 期間フィルタ（`--from` / `--to`）対応。
    - DB テーブルが存在しない場合のフォールバック（OperationalError を捕捉して N/A を出力）。

- 研究用ファクターモジュール（スケルトン）
  - `kabusys.research.factor_research` を追加。DuckDB の `prices_daily` / `raw_financials` を対象にモメンタム / Value / Volatility / Liquidity 等を計算する設計。モジュールは関数インターフェースと定数を含む骨格実装を追加（メモ: ファイル末尾は一部未完の形でスケルトンが入っています）。

### Changed
- 起動シーケンスの改善
  - 監視・実行スクリプトは起動直後にプロセス優先度を「High」に設定するよう統一。
  - 監視用 DB 初期化はどの環境でも本番の sqlite_path を使用して監視データを一元化。

### Fixed
- 環境変数パースの堅牢化
  - `.env` 行のパースでクォート内のエスケープやコメント処理などの不整合を修正し、実運用での `.env` 設定ミスに対して寛容に動作するようにした。

### Notes / Operational details
- kill/stop フラグはプロジェクトルート以下の `data/stop_requested.flag`（監視）および `data/stop_requested.flag`（実行）を使ってプロセスを外部から停止できます。Execution は `data/execution.pid` を PID ファイルとして使用します。
- ログはデフォルトで `logs/` ディレクトリに保存されますが、作成に失敗した場合はコンソールのみで継続します。
- Paper Trading（シミュレーション）と本番 DB は明確に分離される設計（Paper は `PAPER_TRADING_SQLITE_PATH` を使用）。

### Security
- 機密情報（トークン・パスワード等）は `.env` で管理することを前提としており、`config_setup` での .env 生成時に「絶対に Git にコミットしない」注意書きを出力します。

---

変更点の詳細や未実装 / TODO はソースコード中のコメントを参照してください。質問やリリースノート追記の希望があれば教えてください。