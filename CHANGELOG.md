# Changelog

すべての著しい変更はここに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

※ この CHANGELOG はリポジトリ内のソースコード（CLI、ユーティリティ、ポートフォリオ構築、監視/実行スクリプト等）を参照して推測・作成しています。

## [Unreleased]

- ドキュメント化・注釈の追加: 各モジュールに詳細な docstring / コメントを追加し、設計意図や使用方法を明確化。
- research/factor_research.py の実装途中（モメンタム計算などの処理が導入されているがファイル末尾で切れている旨を注記）。
- マイナーコード整理: import 順序やログメッセージの統一などコード内の細かい整形。

---

## [0.1.0] - 2026-04-25

Added
- 基本パッケージとバージョン
  - パッケージ初期バージョンを追加: `kabusys.__version__ = "0.1.0"`。

- 環境設定・読み込み
  - .env 自動読み込み機能を追加（プロジェクトルートを `.git` または `pyproject.toml` から探索）。
  - .env ファイルの行パーサ `_parse_env_line` を実装（コメント、エクスポート形式、クォート、エスケープを考慮）。
  - 環境変数読み込み関数 `_load_env_file` を実装し、OS 環境変数保護（protected）と上書き制御をサポート。
  - Settings クラスを実装してアプリ設定をプロパティ経由で安全に取得可能に。
    - J-Quants / kabu ステーション / LINE / DB / 監視閾値 / システム設定 等のプロパティを提供。
    - `env`（KABUSYS_ENV）のバリデーション、`is_live`/`is_paper`/`is_dev` 判定、`paper_fill_mode` の検証等を実装。
  - 自動 .env ロードを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。

- 環境設定支援 CLI
  - `kabusys.config_setup` ウィザードを追加。
    - 対話式で .env を作成・更新する機能を提供（秘密情報のマスク表示、選択肢、デフォルト値）。
    - `.env` 読み書きロジックを実装（既存値の読み込み、出力テンプレート）。

- 設定検証 CLI
  - `kabusys.validate_config` を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスや config/*.yaml 存在チェック。
    - PyYAML がない場合は YAML 検証をスキップして警告を出力。
    - `--strict` オプションで警告を失敗扱いにできる。

- ロギングユーティリティ
  - `kabusys.utils.logging_setup.setup_logging` を追加。
    - ルートロガーを統一的に設定（stdout StreamHandler と TimedRotatingFileHandler 日次ローテーション）。
    - LOG_DIR/LOG_LEVEL の優先解決、既存ハンドラのクリア、安全にファイルハンドラ作成失敗を扱う。

- プロセス優先度 / CPU 固定ユーティリティ
  - `kabusys.utils.process_priority` を追加。
    - `set_process_priority(level)`：Windows / POSIX を吸収し "high"/"normal"/"low" を設定（権限不足等は警告でスキップ）。
    - `set_cpu_affinity(cpu_count)`：最初の N コアへピンニング（権限不足等は警告でスキップ）。

- 実行 / 監視起動スクリプト
  - `run_execution.py`（ExecutionEngine 起動スクリプト）を追加。
    - 起動時にプロセス優先度を High に設定。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 専用 SQLite（`PAPER_TRADING_SQLITE_PATH`、デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory により本番/モックブローカーを切替え。
    - Engine の起動・監視ループと stop flag（data/stop_requested.flag）による停止機構、execution pid ファイル管理。
    - 依存コンポーネント（OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine）を組み立てて実行。
    - RiskManager の既定設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を導入。

  - `run_monitoring.py`（SystemMonitor ポーリングループ起動スクリプト）を追加。
    - `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告してデフォルトにフォールバック。
    - 監視（monitoring）は環境にかかわらず本番の sqlite_path を使用して監視 DB を初期化。
    - stop flag により安全にループを抜ける制御。

- 監視 DB 初期化
  - `monitoring_db.init_monitoring_db` を参照して監視テーブルの冪等初期化を呼び出す箇所を実装（スクリプト側で呼び出し）。

- Paper Trading / 検証ツール
  - `kabusys.tools.paper_verification_report` を追加。
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）からシステム稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）等を集計して人間向けレポートを出力。
    - Pass/Fail 基準を定義（稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 latency <= 200 ms）。
    - コマンドラインで期間指定（--from / --to）や DB パス指定（--db）に対応。

- ポートフォリオ構築ライブラリ
  - `kabusys.portfolio` 以下の純粋関数群を追加（DB 不要、メモリ内計算）。
    - portfolio_builder
      - select_candidates: スコア降順・タイブレークで上位 N を選択。
      - calc_equal_weights: 等金額配分の重み（1/N）。
      - calc_score_weights: スコア加重配分。全スコアが 0 の場合は等金額にフォールバック（警告）。
    - risk_adjustment
      - apply_sector_cap: セクター集中上限（max_sector_pct）に基づく候補除外ロジック。unknown セクターは上限適用外。
      - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは警告して 1.0 でフォールバック。
    - position_sizing
      - calc_position_sizes: 重み・候補・資産情報に基づいて銘柄ごとの発注株数を計算。
        - allocation_method: "risk_based" / "equal" / "score" をサポート。
        - 単元株丸め（lot_size、デフォルト 100）と per-stock 上限（max_position_pct）を考慮。
        - aggregate cap: 総投資額が available_cash を超えた場合のスケールダウン処理（スケール後に lot_size 単位で残差を大きい順に追加配分）。
        - cost_buffer による保守的見積りの考慮。
  - 上記関数群をパッケージエクスポート（kabusys.portfolio）として整理。

- 研究用ファクターモジュール（研究目的）
  - `kabusys.research.factor_research` を追加（モメンタム / Value / Volatility / Liquidity の設計を導入）。
    - calc_momentum のインターフェースと定数（horizons, MA200, ATR 等）を実装（DuckDB を受け取り prices_daily テーブルを参照する想定）。
    - 実装方針をドキュメント化（DuckDB ベース、外部 API にはアクセスしない等）。

Changed
- 監視・実行スクリプトのログ設定を統一（setup_logging を使用）。
- ファイル入出力・DB 接続における安全なクローズ処理を導入（finally で close）。

Fixed
- （初期リリース）基本動作の例外ハンドリングを追加（monitor.check_once() 実行時の例外キャッチ等）。

Security
- .env の取り扱いに関して注意書きを追加（.env を Git にコミットしないよう明記）。

Notes / Known issues
- research/factor_research.py がファイル末尾で未完了（calc_momentum の実装が途中で終わっている）。研究モジュールは追加の実装・テストが必要。
- position_sizing の price が欠損（0.0）だった場合の挙動について TODO コメントあり（フォールバック価格の採用を検討）。
- 一部の機能（BrokerClientFactory / ExecutionEngine / SystemMonitor / monitoring_db 等）は本 CHANGELOG 作成時点では本ファイル以外で実装済みと想定して利用されているが、その詳細実装は別ファイルに依存。

---

既知の互換性（Breaking Changes）
- 初期リリースのため Breaking Changes はありません。

References
- リポジトリ内の各モジュールの docstring / コメントを参照してください。