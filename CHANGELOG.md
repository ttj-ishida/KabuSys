# Changelog

すべての注目すべき変更をここに記録します。  
このファイルは Keep a Changelog のフォーマットに準拠しています。  

最新の変更は一番上に表示されます。

## [Unreleased]

- （現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-21

初回公開リリース（ベータ）。以下の主要機能と実装が含まれます。

### Added
- 全体
  - パッケージ初期リリース。モジュール構成、CLI、ユーティリティ、ポートフォリオ構築・リスク制御ロジック、Execution/Monitoring の起動スクリプト、Paper Trading 検証ツールなどを追加。
  - バージョン情報: `kabusys.__version__ = "0.1.0"` を設定。

- 起動スクリプト
  - run_execution: ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV が `paper_trading` の場合は paper-trading 用 SQLite（デフォルト `data/paper_trading.db`）を使用し、本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成。
    - OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の組み立てと起動ロジックを実装。
    - スレッド実行・停止フラグ（`data/stop_requested.flag`）による安全な停止処理をサポート。
    - 実行 PID の管理 (`data/execution.pid`)。
  - run_monitoring: SystemMonitor のポーリングループを起動するエントリポイントを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に関係なく本番用の sqlite_path を使用する挙動を明記。
    - 停止フラグ検出で優雅にループを抜ける処理を実装。

- 設定・環境管理
  - config.Settings クラスを導入。環境変数経由で設定を取得する共通 API を提供。
    - 各種環境変数（J-Quants トークン、kabu API パスワード、DB パス、ログレベルなど）をプロパティで公開。
    - `env`、`is_live` / `is_paper` / `is_dev` の判定ロジックを含む。
    - `PAPER_FILL_MODE` の検証（有効値: "instant","partial","never","reject"）を実装。
    - デフォルトパス: DuckDB=`data/kabusys.duckdb`、SQLite=`data/monitoring.db`、paper-trading 用 SQLite=`data/paper_trading.db`。
  - 自動 .env ロード機能を実装（プロジェクトルート検出: `.git` または `pyproject.toml` を基準）。
    - 優先順位: OS 環境変数 > .env.local > .env。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
  - config_setup CLI を追加。
    - 対話式ウィザードで .env を初期作成 / 更新。シークレット項目はマスク表示。
    - デフォルトや選択肢の提示、保存確認を実装。
  - validate_config CLI を追加。
    - .env と config/*.yaml の基本的な構成検証を行う。
    - `--strict` オプションで警告を失敗扱いにできる。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、ログレベルチェック、DB パスの親ディレクトリ存在チェック、YAML パース確認（PyYAML 未インストール時はスキップ）、本番環境向けガードなどを実装。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - 候補銘柄選定（スコア降順、同点時は signal_rank でタイブレーク）。
    - 等金額配分（equal weights）とスコア加重配分（score weights）。スコア合計が0の場合は等配分へフォールバック。
  - portfolio.risk_adjustment
    - セクター集中上限の適用（apply_sector_cap）。
    - 市場レジームに応じた投下資金乗数（calc_regime_multiplier）。"bull"/"neutral"/"bear" のマッピングを実装し、未知レジームは警告と共に 1.0 にフォールバック。
  - portfolio.position_sizing
    - 複数の配分方式（risk_based / equal / score）に対応した株数計算ロジックを実装。
    - 単元（lot_size）での丸め、1 銘柄上限、aggregate cap によるスケールダウン、cost_buffer（手数料・スリッページ見積り）を考慮。
    - スケールダウン時の端数処理（fractional remainder による追加割当て）を実装。

- ユーティリティ
  - logging_setup
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次・30日保持）を設定する共通ユーティリティを追加。
    - ログレベル・ログディレクトリの解決ロジック（引数 > 環境変数 > デフォルト）を実装。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - process_priority
    - クロスプラットフォームでのプロセス優先度設定（Windows の priority class / POSIX の nice）および CPU affinity 設定ユーティリティを追加。
    - 許容レベル: "high" / "normal" / "low"。失敗時は警告を出してスキップする堅牢性を確保。

- モニタリング / DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を用いて起動時に監視用テーブルの存在を保証（冪等）。
  - SystemMonitor の check_once 呼び出しを利用したポーリング監視ループを提供。

- Paper Trading 検証ツール
  - tools.paper_verification_report を追加。
    - paper_trading の SQLite（デフォルト `data/paper_trading.db`）から集計し、稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）等を算出してレポート出力。
    - パス/日付フィルタ、P95 計算、閾値に基づく PASS/FAIL 判定を実装。
    - 空データやテーブル未存在時に安全に N/A を扱うフォールバックを備える。

- 研究用モジュール（骨格）
  - research.factor_research の骨格を追加。DuckDB から価格／財務テーブルを参照してモメンタム / Value / Volatility / Liquidity 等のファクターを計算する設計方針を記載（実装は続きあり）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- .env パーサー
  - export プレフィックスやクォート内のバックスラッシュエスケープ、インラインコメントの扱いなどを正しく処理する堅牢なパーサーを実装し .env の読み込み精度を向上。
  - .env の読み込みで OS 環境変数を上書きしないよう protected set を導入（既存値保持／上書き制御を実装）。

### Security
- シークレット値（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD 等）は Settings 経由で直接取得し、config_setup では表示をマスクするなど取り扱いに配慮。

### Notes / Known limitations
- research.factor_research はファイルの途中で切れており、モメンタム計算の一部実装（関数実装継続）が必要。
- 一部 TODO コメントあり（例: price 欠損時のフォールバック、将来的な銘柄ごとの lot_size 拡張など）。
- process_priority / CPU affinity はプラットフォームや権限に依存し、失敗時は警告ログを出してスキップする設計になっている。
- ロギングでファイル出力に失敗した場合、標準エラーへ警告を出しつつコンソール出力のみで継続する。

---

作成者: KabuSys 開発チーム (コードベースから推測して自動生成)