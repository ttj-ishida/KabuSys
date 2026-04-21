# Changelog

すべての重要な変更点は Keep a Changelog の形式に従って記載します。  
このファイルはコードベースの現状（リポジトリ内の実装）から推測して作成した変更履歴です。

フォーマット:
- Unreleased: 今後の変更（現時点では空）
- 各リリース: そのリリースで追加・変更・修正された機能の要約

---

## [Unreleased]
（現在未リリースの変更はありません）

---

## [0.1.0] - 2026-04-21

初期リリース。本リリースではシステムのコア機能、運用ユーティリティ、監視・実行スクリプト、ポートフォリオ構築ロジック、設定管理・検証ツールなどを実装しています。

### Added
- 基本アプリケーションメタ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として導入。

- 設定管理
  - `kabusys.config.Settings` クラスを追加。環境変数経由で各種設定を取得・検証可能。
    - J-Quants / kabuステーション / LINE / DB / 監視閾値 / システム設定などをプロパティで提供。
    - `KABUSYS_ENV` の値検証（有効値: `development`, `paper_trading`, `live`）。
    - `LOG_LEVEL` 値検証。
    - `PAPER_FILL_MODE` の導入（有効値: `"instant" | "partial" | "never" | "reject"`）。
    - paper_trading 用 DB パス (`PAPER_TRADING_SQLITE_PATH`) と通常用 sqlite パスの区別。
  - .env 自動読み込み機能を導入:
    - プロジェクトルートを `.git` または `pyproject.toml` から探索し、`.env` → `.env.local` の順で読み込む。OS 環境変数は保護される。
    - 自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env パーサーが改善:
    - `export KEY=val` 形式に対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理などをサポート。

- CLI / 運用ユーティリティ
  - `kabusys.config_setup`:
    - 対話式ウィザードで `.env` を作成・更新する CLI を提供。
    - 複数の設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE_* 等）を対話的に編集可能。
    - シークレット項目はマスク表示、保存前の確認、書き込みを実装。
  - `kabusys.validate_config`:
    - 起動前チェック CLI を提供。必須環境変数・パスの存在・YAML ファイル（存在する場合は PyYAML によりパース確認）・本番ガード（LINE 設定や KILL_FLAG_CLEAR_ON_START の危険性）などを検証。
    - `--strict` オプションで警告をエラー扱いにできる。
  - `kabusys.tools.paper_verification_report`:
    - ペーパートレード用 SQLite（デフォルト: `data/paper_trading.db`）から統計を抽出しレポートを出力するツール。
    - 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等を計算・判定する。
    - CLI 引数で期間指定（`--from`, `--to`）と DB パス指定（`--db`）に対応。
    - 判定基準（閾値）が定義済み（稼働率 >= 99%、注文成功率 >= 90% 等）。

- 実行・監視スクリプト
  - `run_execution.py`:
    - ExecutionEngine の起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、paper_trading 用 DB（data/paper_trading.db）に記録して本番 DB と分離する設計。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止用フラグファイル（data/stop_requested.flag）を監視し、検出時にエンジンを停止。
    - PID ファイルの取り扱い（`data/execution.pid`）。
    - コンポーネント群を組み立て:
      - BrokerClientFactory, OrderRepository, OrderManager, RiskManager（デフォルト設定を提供）, Reconciler, ExecutionEngine。
    - スレッドでエンジンを実行し、停止フラグ検出時に安全に停止する処理を実装。
  - `run_monitoring.py`:
    - SystemMonitor をポーリングで実行する起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL`（デフォルト 60 秒）でポーリング間隔を設定可能。無効値はデフォルトにフォールバックし警告を出力。
    - 監視は環境にかかわらず本番 sqlite_path を使用する旨が明示（監視データは本番 DB を参照する設計）。
    - 起動時にプロセス優先度を "high" に設定。停止フラグ検出でループ終了。
    - SQLite / DuckDB 接続を確立し、監視 DB の初期化を行う処理を実装。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`:
    - 候補選定（select_candidates: スコア降順、同点は signal_rank 昇順）。
    - 等分配（calc_equal_weights）・スコア加重（calc_score_weights）を実装。全スコアが 0 の場合は等分配にフォールバックして警告。
  - `kabusys.portfolio.risk_adjustment`:
    - セクター集中制限（apply_sector_cap）: 既存ポジションのセクター暴露を計算し上限超過のセクターの新規候補を除外するロジックを実装。未登録セクター ("unknown") は上限適用対象外。
    - レジーム乗数（calc_regime_multiplier）: "bull"=1.0, "neutral"=0.7, "bear"=0.3。未知レジームは 1.0 にフォールバックして警告。
  - `kabusys.portfolio.position_sizing`:
    - 株数計算ロジック（calc_position_sizes）を実装:
      - allocation_method による分岐 ("risk_based", "equal", "score")。
      - lot_size（単元株）丸め、1銘柄上限、aggregate cap によるスケーリング、cost_buffer（手数料・スリッページの保守的見積）を考慮した配分。
      - スケールダウン時の端数配分（fractional remainders）を取り扱って残余キャッシュで lot 単位を順次配分。
      - 価格欠損時のログ出力とスキップ処理。

- 研究/因子モジュール（部分実装）
  - `kabusys.research.factor_research`:
    - モメンタム、MA、ATR、ボリューム等の因子計算を目標とした設計。DuckDB 接続を受け prices_daily/raw_financials を参照する想定。
    - モメンタム計算関数（calc_momentum）の実装に着手（ターゲット日ベースで 1M/3M/6M などを計算する設計）が含まれる（ファイル末尾で途中実装の箇所あり）。

- ロギング・プロセスユーティリティ
  - `kabusys.utils.logging_setup`:
    - 統一ログ設定ユーティリティを提供。StreamHandler を stdout に出力し、TimedRotatingFileHandler（ディレクトリ: `logs/`、日次ローテーション、30日保持）を設定。
    - 既存ハンドラのクリア、ログレベル解決順（関数引数 > 環境変数 LOG_LEVEL > デフォルト）。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - `kabusys.utils.process_priority`:
    - クロスプラットフォームのプロセス優先度設定を提供（Windows と POSIX の差分を吸収）。
    - `set_process_priority(level)`（"high" | "normal" | "low"）と `set_cpu_affinity(cpu_count)` を実装。
    - 権限不足や未対応 OS の場合は警告を出してスキップする安全な実装。

### Changed
- なし（初回リリースのため既存機能の変更履歴は無し）

### Fixed
- なし（リリース時点で既知のバグ修正履歴は無し）

### Security
- 環境変数や .env の取り扱いに関して注意喚起をドキュメント（config_setup のヘッダー）に記載（.env を Git にコミットしないこと等）。

---

注記 / 実装上の重要ポイント（運用や将来の注意点）
- run_monitoring は説明文にある通り監視用 DB に本番 sqlite_path を使用するため、監視環境では DB の扱いに注意が必要です。
- `PAPER_FILL_MODE` と paper_trading 用 DB を用いた分離設計により、ペーパートレードと本番の記録が明確に分かれます。
- `.env` パーサーは多くのケースに対応しているものの、特殊ケース（複雑なネストクォート等）では想定外の振る舞いとなる可能性があるため、重要なシークレットは運用で厳重に管理してください。
- `kabusys.research.factor_research` は複雑な時系列処理を行う設計ですが、ファイル末尾に実装途中の断片があります（今後の完成が必要）。

---

作成: 自動生成（コード内容から推測による CHANGELOG）  
日付: 2026-04-21

（必要であれば各変更項目をさらに詳細に分割し、今後の Unreleased に対するタスクや既知の issue を追記します。）