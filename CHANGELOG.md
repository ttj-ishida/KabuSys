# Changelog

すべての重要な変更をここに記録します。フォーマットは "Keep a Changelog" に準拠します。

注: 以下の内容はリポジトリ内のソースコードから推測して作成しています（コミット履歴そのままではありません）。

## [Unreleased]

- ドキュメントや小さな調整（将来のリリース向けの未反映事項）をここに記載します。

## [0.1.0] - 2026-04-18

### Added
- 基本アプリケーションパッケージ `kabusys` を追加
  - バージョン定義: `__version__ = "0.1.0"`

- 設定管理
  - `kabusys.config.Settings` クラスを実装。
    - 環境変数 / .env /.env.local の自動読み込み（プロジェクトルート自動検出: .git または pyproject.toml を基準）。
    - 必須値取得用 `_require()`、環境の妥当性チェック（KABUSYS_ENV, LOG_LEVEL 等）。
    - データベースパス、PID/kill フラグパス、閾値（CPU/Memory/Disk）などのプロパティを提供。
    - Paper Trading 向け設定（PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH）をサポート。

- .env 取り扱いユーティリティ
  - 高度な .env パーサ (`_parse_env_line`) を実装:
    - `export KEY=val` 形式対応、クォート文字列のバックスラッシュエスケープ処理、インラインコメント処理等。
  - 自動ロード時に OS 環境変数を保護（protected set）して上書きを制御。

- 設定ウィザード CLI
  - `kabusys.config_setup` を追加（対話式に .env を作成/更新するウィザード）。
  - シークレット項目はマスク表示、保存前に確認を促す。
  - デフォルト値・選択肢・説明文を含む設定項目群を提供。

- 設定検証 CLI
  - `kabusys.validate_config` を追加（.env と config/*.yaml の起動前検証ツール）。
  - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスの親ディレクトリチェック、YAML ファイルのパースチェック（PyYAML がない場合はスキップ）を実装。
  - `--strict` オプションで警告を失敗扱いにできる。

- ログ設定ユーティリティ
  - `kabusys.utils.logging_setup.setup_logging` を実装。
    - stdout ストリームハンドラ + 日次ローテートファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - LOG_DIR/LOG_LEVEL の解決、既存ハンドラのクリーンアップ、ログディレクトリ作成失敗時のフォールバック処理を実装。

- プロセス優先度 / CPU affinity ユーティリティ
  - `kabusys.utils.process_priority` を実装。
    - 複数プラットフォーム（Windows / POSIX）に対応したプロセス優先度設定（`set_process_priority`）。
    - CPU コア固定 (`set_cpu_affinity`) を提供。
    - 権限不足や未対応 OS では警告を出して安全にスキップ。

- 実行 / 監視プロセス起動スクリプト
  - `run_execution.py`
    - ExecutionEngine 起動用スクリプト。
    - 環境に応じて paper_trading 用 DB と MockBroker を分離（paper_trading の場合は専用 DB に記録）。
    - プロセス優先度を High に設定、PID ファイルの利用、停止フラグ検知による安全停止。
    - ExecutionEngine の依存組み立て（OrderRepository, OrderManager, RiskManager, Reconciler 等）の初期化とスレッド管理。
    - RiskManager 向けの既定値を持つ `RiskConfig` を利用。
  - `run_monitoring.py`
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒、無効値は警告してデフォルトにフォールバック）。
    - 停止フラグファイル検知、例外発生時のログ処理、接続クローズ処理を実装。
    - Monitoring は環境に関わらず本番 sqlite_path を使用する旨の設計。

- データベース初期化 / DuckDB 統合
  - `init_monitoring_db`（参照）は呼び出し部分を追加（監視テーブルの冪等初期化を保証）。
  - DuckDB との接続を受け取る設計を採用（分析用途のための `duckdb` 統合）。

- Execution 周りの基盤（ファクトリ / エンジン / マネージャ等）
  - `BrokerClientFactory` を利用したブローカクライアント生成（Mock 対応）。
  - OrderRepository / OrderManager / Reconciler / RiskManager / ExecutionEngine の組み立て方をスクリプト側で実装。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`
    - 候補選定: `select_candidates`（スコア降順、同点は signal_rank でタイブレーク）。
    - 等金額配分: `calc_equal_weights`
    - スコア加重配分: `calc_score_weights`（全スコアが 0 の場合は等金額にフォールバック）
  - `kabusys.portfolio.risk_adjustment`
    - セクター集中制限: `apply_sector_cap`（既存保有のセクター露出を計算し、上限超過セクターの新規候補を除外）
    - レジーム乗数: `calc_regime_multiplier`（"bull"/"neutral"/"bear" に応じた乗数、未知レジームはフォールバック）
  - `kabusys.portfolio.position_sizing`
    - 株数決定ロジック: `calc_position_sizes`
      - allocation_method: "risk_based" / "equal" / "score" をサポート
      - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash を超える場合のスケールダウン）、cost_buffer を考慮した保守的コスト見積り。
      - スケーリング時の端数配分ロジックを実装（fractional remainder による優先付け）。

- 分析 / 研究ユーティリティ
  - `kabusys.research.factor_research`（ファクター計算の基礎実装）
    - モメンタム、MA200乖離、ATR、出来高系等を想定した定数と設計方針を実装（DuckDB の prices_daily / raw_financials テーブル参照）。
    - （注）ファイル末尾で関数実装が途中になっている箇所が見られるため、今後完成予定。

- Paper Trading 検証ツール
  - `kabusys.tools.paper_verification_report` を追加。
    - paper_trading DB から稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を算出してレポート出力。
    - 閾値（稼働率99%、成立率90%、送信率95%、P95レイテンシ200ms）を基に PASS/FAIL 判定を行う。
    - コマンドライン引数で期間指定 (--from / --to) と DB パス指定 (--db) をサポート。

### Changed
- ログ周りの堅牢化
  - ログディレクトリ作成に失敗した場合はファイルハンドラをスキップして stdout のみで継続するように変更（setup_logging）。
  - 既存ハンドラの flush/close を行ってから再設定することで二重出力を防止。

- .env 読み込み順序を明示
  - 自動ロード時の優先順を OS 環境変数 > .env.local > .env として明確化。

- 実行時の安全対策
  - run_execution と run_monitoring の起動前に停止フラグ (data/stop_requested.flag 等) をチェックして不要な起動を防止。
  - run_execution は paper_trading 環境で本番 DB と完全に分離するよう設計。

### Fixed
- .env パーサの堅牢化
  - クォート内のエスケープ、インラインコメントの判定、`export` プレフィックスの対応などを実装し、一般的な .env 記述に対応。

- 環境変数の不正値に対するフォールバック
  - `MONITOR_POLL_INTERVAL`、`PAPER_FILL_MODE`、`KABUSYS_ENV`、`LOG_LEVEL` 等の不正値に対して明示的な警告を出し、安全なデフォルトに戻す処理を追加。

### Deprecated
- なし（初期リリースのため該当なし）

### Removed
- なし（初期リリースのため該当なし）

### Security
- config_setup の出力で .env を生成する際、ファイルに含めるべきでないこと（絶対に Git にコミットしない旨）を明示。
- ウィザードではシークレット値をマスクして表示。

---

開発者向けメモ（推測）
- factor_research の一部関数が実装途中に見えるため、今後のリリースでファクター計算ロジックの完成・テスト追加が予定される可能性があります。
- DB 初期化関数 `init_monitoring_db` や SystemMonitor / ExecutionEngine の内部実装は本 changelog の作成時点では参照のみ（実装の変更点はソース全体を確認してください）。

もし詳細な差分（コミット単位）や特定モジュールごとの変更点を、ソースコードを元にさらに詳しく記載してほしい場合は、その旨を教えてください。