# Changelog

すべての注目すべき変更点をここに記録します。  
このファイルは「Keep a Changelog」規約に従っています。  

- リリース日付はコミット時点の推測です。実際のリリース日付に合わせて調整してください。

## [Unreleased]

（現在の作業中の変更はここに記載します）

---

## [0.1.0] - 2026-04-19

最初の公開リリース。日本株自動売買システム KabuSys のコア機能群を実装しました。主な変更点は以下のとおりです。

### Added
- 全体構成・バージョン
  - パッケージの初期バージョンを `__version__ = "0.1.0"` として追加。

- 実行スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを追加。
    - 環境（KABUSYS_ENV）が `paper_trading` の場合は専用の paper trading SQLite DB を使用（本番 DB と分離）。
    - BrokerClientFactory によるブローカークライアント生成をサポート。
    - ExecutionEngine をデーモンスレッドで起動し、data/stop_requested.flag による外部停止をサポート。
    - プロセス優先度（"high"等）の設定、PID ファイル保持など運用周りの仕組みを提供。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔の上書き（デフォルト 60 秒）。
    - 監視は環境に関わらず本番の sqlite_path を使用する旨を実装。
    - 停止フラグ（data/stop_requested.flag）検知によるループ終了、KeyboardInterrupt の扱いを実装。

- 設定管理・ウィザード・検証
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルート検出: `.git` または `pyproject.toml` を基準）。
    - .env パースロジックは export 形式、クォート、インラインコメントを適切に処理。
    - 各種設定プロパティ（DB パス、API トークン、環境フラグ、閾値など）を提供。
    - env 値の検証（有効な KABUSYS_ENV / LOG_LEVEL 等）を実装。

  - config_setup.py
    - 対話式 .env 作成・更新ウィザードを追加。
    - デフォルト・選択肢・シークレット入力・確認・保存機能を備える。

  - validate_config.py
    - 起動前の設定検証 CLI を追加（必須環境変数、KABUSYS_ENV、DB パス、config/*.yaml の存在と YAML パース検証、ライブ環境向けガード等）。
    - `--strict` オプションで警告を fail 扱いにできる。

- データベース / 分析
  - DuckDB と SQLite の両対応を導入。duckdb は分析用（prices 等）、SQLite は監視・トレードログ用に利用する前提。
  - 監視用 DB 初期化ユーティリティ（init_monitoring_db）を起動時に呼び出して冪等にテーブルを保証。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選択（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - スコア合計が 0 の場合は等金額配分にフォールバックし警告を出す。

  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）を実装。既存保有のセクター比率が閾値を超える場合に新規候補を除外。
    - レジームに基づく投下資金乗数（calc_regime_multiplier）を実装（bull/neutral/bear のマッピング、未知レジームはフォールバック）。

  - portfolio/position_sizing.py
    - 各銘柄の発注株数を計算するアルゴリズムを実装（allocation_method: risk_based / equal / score）。
    - 単元株丸め、1 銘柄上限、aggregate cap（available_cash を超えた場合のスケールダウン）、cost_buffer（手数料/スリッページの見積もり）を考慮。
    - lot_size（単元）に基づく残余処理（端数を大きい順に再配分）を実装。

- ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに対する統一ログ設定を提供（stdout StreamHandler + 日次ローテートの TimedRotatingFileHandler）。
    - LOG_DIR / LOG_LEVEL の解決順を実装、ローテーション（30 日）とエラーハンドリングを備える。

  - utils/process_priority.py
    - プラットフォーム差（Windows/Linux/macOS）を吸収してプロセス優先度を設定するユーティリティを提供。
    - CPU affinity を最初 N コアへ固定する関数を提供（設定失敗時は警告でスキップ）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率 / 送信率、リスク却下数、レイテンシ（平均/最大/P95）を集計して PASS/FAIL を判定する（閾値はソース内で定義: 稼働率 99%、Filled 90%、送信 95%、P95 レイテンシ 200 ms）。
    - DB パスは引数または環境変数（PAPER_TRADING_SQLITE_PATH）で指定可能。

- リサーチ（ファクター計算）
  - research/factor_research.py（骨格）
    - Momentum / Value / Volatility / Liquidity に関する設計とモメンタム計算関数（calc_momentum）の骨格を追加。DuckDB 接続を受け、prices_daily / raw_financials を参照する設計。
    - 一部定数（MA/ATR 等）と P95 等のユーティリティが含まれる。calc_momentum 実装は継続。

### Changed
- .env 自動読み込みの挙動
  - プロジェクトルート検出を実装し、.env/.env.local を OS 環境変数に基づき安全に上書きする順序（OS > .env.local > .env）を採用。
  - テスト等のために KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードの無効化が可能。

- DB パスの扱い
  - run_monitoring は監視 DB に常に本番 sqlite_path を使用する（環境変数に依存しない旨をログ出力）。
  - run_execution は paper_trading 環境時に paper_sqlite_path を使用して本番 DB とは完全分離。

### Fixed
- 各 CLI/ユーティリティで起動時のファイル・ディレクトリ作成失敗やアクセス権限問題を安全に扱うように改善（ログ出力または警告でフォールバック）。

### Notes / Operational
- 停止制御
  - 実行中プロセスの停止は data/stop_requested.flag（プロジェクトルート直下の data ディレクトリ）を検知する方式を採用。外部からファイルを作成することで安全に停止できる。
  - ExecutionEngine は PID ファイルを保持し、run_execution は停止フラグ検知時に engine.stop() を呼ぶ。

- Paper Trading
  - Paper Trading は MockBroker を利用して発注処理をシミュレートし、専用の paper_trading.db に記録するため本番環境とは完全に分離される。

### Security
- 機密情報（API トークン等）は .env の "secret" 項目として扱い、config_setup の表示時にはマスクして表示。

---

今後の予定（候補）
- factor_research.calc_momentum の完全実装とユニットテスト追加。
- ExecutionEngine / SystemMonitor の詳細ログ拡張とより堅牢なエラーハンドリング。
- 各モジュール（portfolio, execution, monitoring）に対する単体テストの拡充。
- stocks マスタを用いた銘柄別 lot_size サポート等の拡張。

----- 

（この CHANGELOG はソースコードから推測して作成しています。細部の仕様や日付は実際のリリースノートに合わせて編集してください。）