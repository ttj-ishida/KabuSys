# Changelog

すべての重要な変更はこのファイルに記録します。本ファイルは「Keep a Changelog」形式に準拠します。  
日付は推測に基づき記載しています。

## [Unreleased]
- 開発中の改善点・TODO をここに記載してください（例: research モジュールの未完機能、追加のテストなど）。

## [0.1.0] - 2026-04-18
初回リリース（コードベースから推測して作成）

### 追加 (Added)
- 全体
  - プロジェクトの初期実装を追加。パッケージ名は `kabusys`、バージョン `0.1.0`。
  - パッケージ構成: 実行・監視スクリプト、設定管理、ポートフォリオ構築ロジック、ユーティリティ群、検証・設定ウィザード、Paper Trading 検証ツール、研究用ファクター計算の骨子など。

- 起動スクリプト
  - `run_monitoring.py`
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔の上書き対応（デフォルト 60 秒）。
    - プロセス優先度を高に設定してから起動。
    - 停止はプロジェクトルートの `data/stop_requested.flag` により行う。
    - Monitoring は環境に依らず本番の `sqlite_path` を使用（監視テーブル初期化を実行）。
    - DuckDB 接続を組み合わせて利用。

  - `run_execution.py`
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は MockBroker を利用し、Paper Trading 用 DB（`data/paper_trading.db` デフォルト）で本番 DB と分離。
    - プロセス優先度を高に設定。
    - 停止フラグの監視と安全なシャットダウン処理（PID ファイル・stop フラグの使用）。
    - Execution 用コンポーネント（BrokerFactory、OrderManager、OrderRepository、RiskManager、Reconciler、ExecutionEngine）を組み立てるサンプル設定を含む。
    - デフォルトの RiskConfig を設定し、初期ポートフォリオ値はブローカから取得した現金を使用。

- 設定関連
  - `config.py`
    - 環境変数ベースの設定管理クラス `Settings` を実装。
    - `.env` 自動読み込み（`.env` → `.env.local`、ただし `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
    - `.env` のパースはシングル/ダブルクォート、`export KEY=val` 形式、インラインコメントに対応する堅牢な実装。
    - 各種設定プロパティ（DB パス、KABUSYS_ENV 判定、ログレベル、Paper Trading 用設定、監視しきい値など）を提供。
    - `settings = Settings()` で共通インスタンスを提供。

  - `config_setup.py`
    - 対話式の .env 設定ウィザードを追加。既存 .env の読み込み・更新、デフォルト値・選択肢表示、シークレットマスク表示に対応。
    - `.env` の書式ガイド付きでファイルを生成。

  - `validate_config.py`
    - 起動前に設定不備を検出する CLI を追加（必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と PyYAML があればパース検証、`live` 環境向けの追加ガードなど）。
    - `--strict` オプションで警告を失敗扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - `portfolio/portfolio_builder.py`
    - シグナル選定（スコア降順、タイブレークに signal_rank）と候補絞り込み。
    - 等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。スコアが全てゼロの場合は等分にフォールバックしログ警告。

  - `portfolio/risk_adjustment.py`
    - セクター集中制限（apply_sector_cap）。既存保有のセクターエクスポージャーに基づいて新規候補を除外。`unknown` セクターは制限の対象外。
    - レジームに応じた投下資金乗数（calc_regime_multiplier）を実装（"bull"=1.0, "neutral"=0.7, "bear"=0.3、未定義は 1.0 にフォールバック）。

  - `portfolio/position_sizing.py`
    - 株数算出ロジック（allocation_method: "risk_based" / "equal" / "score"）を実装。
    - 1 銘柄上限、lot_size（単元）丸め、aggregate cap（総投資額が利用可能現金を超える場合のスケーリングと残差処理）を実装。
    - cost_buffer を使った保守的見積りに対応。

  - `portfolio/__init__.py` で API を公開。

- ユーティリティ
  - `utils/logging_setup.py`
    - 統一ログ設定関数 `setup_logging` を実装。 stdout (StreamHandler) 出力と日次ローテーションファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリを自動作成し、作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - ログレベルは引数 > 環境変数 > デフォルト の優先度で決定。

  - `utils/process_priority.py`
    - クロスプラットフォーム（Windows / POSIX）でプロセス優先度設定と CPU affinity 設定ユーティリティを提供。
    - 標準的な例外（アクセス権限欠如など）発生時は警告を出して処理を継続する堅牢設計。

- Monitoring / DB
  - 監視テーブル初期化ユーティリティ呼び出し（`init_monitoring_db` を run スクリプトから呼ぶ形で、監視テーブルの冪等初期化を実施）。
  - DuckDB と SQLite を組み合わせて利用する設計。

- ツール
  - `tools/paper_verification_report.py`
    - Paper Trading 用 SQLite（`PAPER_TRADING_SQLITE_PATH`）から検証レポートを生成する CLI を追加。
    - 指標: 稼働率 (uptime_pct)、注文成功率 (fill_rate)、送信率 (send_rate)、P95 レイテンシ などを算出し、閾値に基づく PASS/FAIL を判定。
    - P95 計算、NULL 値の扱い、期間フィルタ（ISO8601 UTC 変換）に対応。

- 研究用
  - `research/factor_research.py`（骨子）
    - Momentum / Value / Volatility / Liquidity に関する設計と定数群を追加。DuckDB 接続を受けて prices_daily / raw_financials テーブルを参照する方針を記載。
    - モメンタム計算（calc_momentum）の実装を開始（ファイル末尾は一部未完成の可能性あり）。

### 変更 (Changed)
- 初回公開のため該当なし（初期実装）。

### 修正 (Fixed)
- 初回公開のため該当なし。

### 破壊的変更 (Removed / Deprecated)
- 初回公開のため該当なし。

### 既知の制約・注意点 (Notes / Known issues)
- research/factor_research.py の一部機能（calc_momentum などの実装の続き）が中途に見える（ファイル末尾が切れている／未完）。
- position_sizing、risk_adjustment 内に将来の拡張（銘柄別 lot_size のサポートや価格フォールバックの TODO コメント）が残っている。
- `.env` 自動読み込みはプロジェクトルート検出に .git または pyproject.toml を利用するため、配布後に動作しない環境がある場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して手動で環境を差し替える必要がある。
- `set_process_priority` / `set_cpu_affinity` は権限不足や未サポート OS でスキップされる場合がある（警告出力）。

---

参考: 主な実行方法（コード内 docstring / ログ出力に基づく）
- 設定ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- Paper Trading レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- 監視プロセス: python -m kabusys.run_monitoring
- 実行エンジン: python -m kabusys.run_execution

（上記はコードの docstring / エントリポイントの記述から推測して記載しています。）