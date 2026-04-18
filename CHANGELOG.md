# CHANGELOG

すべての顕著な変更点を Keep a Changelog の形式で記録します。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-04-18

### 追加
- 基本パッケージ初期実装を追加（KabuSys v0.1.0）。
  - パッケージエントリポイント: `__version__ = "0.1.0"`。

- 環境設定関連
  - `kabusys.config`:
    - .env 自動ロード機能を実装（プロジェクトルートの検出基準: .git または pyproject.toml）。
    - `.env` と `.env.local` の読み込み順序をサポート。OS 環境変数は保護（上書き不可）。
    - 複数の .env 書式をパース可能（`export KEY=val`、シングル/ダブルクォート、エスケープ、行末コメント処理等）。
    - Settings クラスを実装し、環境変数の取得と基本的な妥当性検証を提供（例: KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE の検証）。
    - デフォルト値やパスを Path 型で扱うプロパティを提供（DUCKDB_PATH/SQLITE_PATH/PAPER_TRADING_SQLITE_PATH 等）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。

  - `kabusys.config_setup`:
    - 対話式ウィザードで .env を新規作成/更新する CLI を実装（`python -m kabusys.config_setup`）。
    - 各項目の説明・選択肢・シークレット入力・デフォルト値をサポート。
    - .env のテンプレート書き出し機能を実装（.env を誤って Git にコミットしない旨のヘッダを含む）。

  - `kabusys.validate_config`:
    - 起動前に環境変数・設定ファイルの妥当性を検証する CLI を実装（`python -m kabusys.validate_config`）。
    - 必須/任意の環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パス（親ディレクトリ存在確認）、config/*.yaml の存在・パース（PyYAML があればパース検証）を実施。
    - `--strict` オプションで警告を FAIL 扱いにする機能を提供。
    - 本番環境向けのガード（LINE 設定の未設定、KILL_FLAG_CLEAR_ON_START の警告等）を追加。

- ロギング・プロセス制御ユーティリティ
  - `kabusys.utils.logging_setup`:
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション）を設定するユーティリティを実装。
    - ログディレクトリ自動作成、作成失敗時はファイル出力をスキップしてコンソール出力のみで継続するフォールバック処理を実装。
    - ログレベル解決順（引数 > 環境変数 LOG_LEVEL > デフォルト）とログディレクトリ解決順（引数 > LOG_DIR > logs/）に対応。
  - `kabusys.utils.process_priority`:
    - クロスプラットフォームでプロセス優先度（high/normal/low）を設定するユーティリティを実装（psutil を利用）。
    - CPU affinity を最初の N コアに固定する `set_cpu_affinity` を提供。
    - 権限不足や非対応プラットフォームの際は安全にスキップし、警告ログを出す。

- 実行・監視プロセス起動スクリプト
  - `run_execution.py`:
    - ExecutionEngine 起動用スクリプトを提供。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と完全分離する実装。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、ExecutionEngine の起動（スレッド方式）と停止フラグ監視を実装。
    - プロセス優先度を起動時に "high" に設定。
  - `run_monitoring.py`:
    - SystemMonitor をポーリングで実行する監視ループ起動スクリプトを提供。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、0以下や不正値はデフォルトにフォールバックして警告を出す）。
    - Monitoring は環境にかかわらず本番の sqlite_path を使用する（監視データは本番監視 DB に記録）。
    - 停止フラグファイルの検知で安全にループを終了。

- Execution / Monitoring の DB 初期化
  - `kabusys.monitoring.monitoring_db` の init 呼び出しにより、必要な監視テーブルの存在を起動時に保証（冪等）。

- Portfolio 構築ロジック
  - `kabusys.portfolio.portfolio_builder`:
    - シグナル選定/重み算出の純粋関数を実装。
    - select_candidates: スコア降順・タイブレークとして signal_rank を使用。
    - calc_equal_weights / calc_score_weights: 等分配・スコア比率配分、全スコアが 0 の場合は等分配にフォールバックして警告。
  - `kabusys.portfolio.risk_adjustment`:
    - セクター集中制限（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）を実装。
    - apply_sector_cap は既存保有のセクター別時価算出（売却予定銘柄を除外可）に基づき、上限超過セクターの新規候補を除外するロジックを提供（"unknown" セクターは制限対象外）。
    - calc_regime_multiplier はレジーム(bull/neutral/bear) に応じた投下資金乗数を返す（未知レジームはフォールバック 1.0 として警告）。
  - `kabusys.portfolio.position_sizing`:
    - 各配分方法（risk_based / equal / score）に基づく発注株数計算を実装。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金を超える場合のスケールダウン）を実装。
    - cost_buffer による保守的コスト見積りを考慮してスケーリングや残余キャッシュでの追加配分を行うアルゴリズムを提供。
    - 入力データ欠損（価格がない等）についてはスキップしてログ出力。

- 解析・検証ツール
  - `kabusys.tools.paper_verification_report`:
    - Paper Trading 用の検証レポート生成スクリプトを追加（`python -m kabusys.tools.paper_verification_report`）。
    - system_status/trade_logs/risk_logs から稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）等の指標を算出し、PASS/FAIL 判定を行う。
    - CLI オプションで期間指定（--from/--to）と DB パス指定（--db）をサポート。
    - 既定の閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）を定義。
  - tools パッケージを追加（`kabusys.tools`）。

- リサーチ（分析）基盤（初期実装）
  - `kabusys.research.factor_research`:
    - ファクター計算モジュールの骨組みを追加（Momentum, Value, Volatility, Liquidity 設計に準拠）。
    - DuckDB 接続を受け取り、prices_daily / raw_financials を参照して日付ベースでファクターを計算する方針を実装開始（モメンタム関数の初期実装に着手。ファイル末尾で一部切れているため継続実装が必要）。

- パッケージ公開インターフェース
  - `kabusys.portfolio` で主要関数をまとめてエクスポート（select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier）。

### 変更
- ログ出力は stdout を優先して使用（cron/Task Scheduler 等との挙動を意識）。
- run_monitoring/run_execution 起動時にプロセス優先度を最初に設定するよう統一。

### 既知の注意点 / TODO
- apply_sector_cap 内で price が欠損（0.0）の場合にエクスポージャーが過少見積りされ得る旨を TODO コメントで指摘。将来的に前日終値等のフォールバックを検討する必要あり。
- position_sizing: 将来的には銘柄ごとの lot_size を持たせる設計へ拡張する予定（現在は全銘柄共通 lot_size を使用）。
- `kabusys.research.factor_research` はモメンタム計算の途中でファイルが切れており、完全実装が必要。
- monitoring は環境にかかわらず「本番 sqlite_path」を使用する設計のため、テスト環境で分離したい場合は設計上の注意が必要。

### セキュリティ
- .env に機密情報を格納する旨を明示し、.env を Git にコミットしないようにテンプレートに注記。

---

今後のリリースで以下を検討/追加予定:
- research モジュールの全面実装（Value/Volatility/Liquidity の算出）。
- ユニットテストの追加と CI の導入。
- BrokerClient のモック/インタフェース拡張および paper_trading 用シミュレーション強化。