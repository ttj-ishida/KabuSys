# Changelog

すべての重要な変更をここに記載します。フォーマットは Keep a Changelog に準拠します。  

このリポジトリの初期リリース (v0.1.0) をコードベースから推測してまとめています。

## [Unreleased]


## [0.1.0] - 2026-04-18
### Added
- 基本アプリケーション構成
  - パッケージのバージョンを `__version__ = "0.1.0"` として設定。
  - パッケージエクスポート: data, strategy, execution, monitoring など主要モジュールを公開。

- 環境設定関連
  - Settings クラス（`kabusys.config`）を実装。環境変数からアプリ設定を安全に取得する API を提供。
  - 自動 .env ロード機能を実装（プロジェクトルートの検出: .git または pyproject.toml 基準）。OS 環境変数を保護して `.env` / `.env.local` を読み込む仕組み。
  - .env 解析器を実装（クォート、エスケープ、export 形式、インラインコメントの取り扱いなどを考慮）。
  - 各種設定プロパティを提供（J-Quants トークン、kabu API、DB パス、ログレベル、モニタ閾値、ペーパートレード切替等）。
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD` で自動読み込みを無効化可能。

- 設定支援 CLI
  - 対話式ウィザード `kabusys.config_setup` を追加（`.env` の生成・更新を支援）。
    - シークレット項目はマスク表示。
    - デフォルト値・選択肢を提示して安全に .env を作成可能。
  - 設定検証 CLI `kabusys.validate_config` を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性検証、DB パスの親ディレクトリ確認。
    - config/*.yaml の存在確認と（PyYAML があれば）パース検証。
    - 本番環境（KABUSYS_ENV=live）向けの追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の注意喚起）。

- 実行・監視ランナー
  - Execution 起動スクリプト `run_execution.py` を追加。
    - `KABUSYS_ENV=paper_trading` の場合は paper 専用 SQLite（デフォルト `data/paper_trading.db`）を使用し、本番 DB と分離。
    - BrokerClientFactory を使用してブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで実行。PID ファイル・停止フラグに対応。
    - デフォルトの RiskConfig を設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。
  - Monitoring 起動スクリプト `run_monitoring.py` を追加。
    - ポーリング間隔を環境変数 `MONITOR_POLL_INTERVAL` から上書き可能（デフォルト 60 秒、無効値はフォールバック）。
    - Monitoring は環境に依らず本番用 `sqlite_path` を使用する設計（監視データを一元管理）。
    - 停止フラグファイル検出で安全にループ終了。

- ポートフォリオ構築（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`
    - シグナルから候補選定（score 降順、タイブレークは signal_rank）および等金額・スコア重みの計算を実装。
    - スコア全てが 0 の場合は等配分にフォールバック（警告ログ）。
  - `kabusys.portfolio.risk_adjustment`
    - セクター集中上限の適用（既存ポジションのセクター比率に基づき候補を除外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear にマッピング。未知レジームはフォールバックで 1.0）。
  - `kabusys.portfolio.position_sizing`
    - allocation_method = "risk_based" / "equal" / "score" をサポート。
    - 損切り・リスクベースの単位株数計算、単元株（lot_size）丸め、1 銘柄上限・総投下キャッシュに基づくスケーリング（aggregate cap）を実装。
    - cost_buffer を考慮した保守的見積りと、スケールダウン後の端数処理（lot 単位での追加配分ロジック）を実装。

- 取引実行・監視用 DB / 分析基盤
  - DuckDB を分析用途に使用（duckdb_path を設定可能）。
  - 監視用 SQLite 初期化ヘルパー（`init_monitoring_db` を参照して各ランナーで実行）。

- ロギング・プロセス制御ユーティリティ
  - `kabusys.utils.logging_setup`
    - ルートロガーの初期化ユーティリティを提供。Console (stdout) と TimedRotatingFileHandler（日次・30日保存）を設定。
    - LOG_DIR / LOG_LEVEL の決定ロジック、ハンドラ二重設定防止、ファイル作成失敗時のフォールバックを実装。
  - `kabusys.utils.process_priority`
    - Windows / POSIX（Linux/Mac など）の差分を吸収してプロセス優先度設定を提供（high/normal/low）。
    - CPU affinity 設定ヘルパも提供（最初の N コアに固定）。
    - 権限不足や未サポート環境では警告を出してスキップ。

- Paper Trading 検証ツール
  - `kabusys.tools.paper_verification_report`
    - ペーパートレード用 SQLite（デフォルト `data/paper_trading.db`）からレポートを生成。
    - システム稼働率・注文成功率・送信率・P95 レイテンシ・リスク却下数などを集計。
    - PASS/FAIL 基準値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を定義し判定。
    - P95 計算、日付フィルタ（--from/--to）、CLI 用オプションを提供。

- リサーチ（骨格）
  - `kabusys.research.factor_research` の骨格を追加。DuckDB を用いたファクター計算（Momentum / Value / Volatility / Liquidity）を想定する設計で、一部定数とモメンタム計算関数のシグネチャを整備（実装途中の箇所あり）。

### Changed
- （初版リリースのため該当なし）

### Fixed
- （初版リリースのため該当なし）

### Removed
- （初版リリースのため該当なし）

### Security
- config_setup の表示時にシークレット値をマスク（表示保護）。
- `.env` の自動読み込み時に OS 環境変数を保護する仕組みを導入（protected set）。

### Notes / Known limitations
- 一部モジュール（例: research.factor_research の詳細実装、monitoring.monitoring_db / system_monitor / execution エンジンの内部実装詳細）は本スナップショットでは参照のみで、完全実装は別ファイルに依存している可能性があります。
- position_sizing の価格欠損時のフォールバック処理については TODO コメントが残っており、将来的に前日終値等のフォールバック実装が想定されています。
- プロセス優先度や CPU affinity の設定は環境（権限や OS）によって失敗する場合があり、その際は警告ログを発行してスキップします。
- monitoring は説明どおり本番用 sqlite_path を使用する設計（環境に依存しない集中監視）。紙上での想定に基づくため、運用ポリシーに注意してください。

---

（この CHANGELOG は現在のコードベースから推測して作成しています。実際のコミット履歴やリリースノートと差異がある場合があります。）