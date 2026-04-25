# Changelog

すべての非互換性のある変更は明確に記載します。  
フォーマットは「Keep a Changelog」に準拠します。  

全般:
- 日付はリリース日です。
- 環境変数やデフォルトパスはコード内の説明に基づいて記載しています。

## [Unreleased]

## [0.1.0] - 2026-04-25

追加（Added）
- 基本パッケージ公開
  - パッケージバージョンを `__version__ = "0.1.0"` として初期リリース。
- 環境/設定管理
  - .env 自動読み込み機能
    - プロジェクトルート (.git または pyproject.toml) を基準に `.env` と `.env.local` を自動ロード（OS 環境変数が優先）。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env パーサ実装
    - export プレフィックス対応、シングル/ダブルクォート、エスケープ、インラインコメントの扱い等に対応。
  - Settings クラス（環境変数ラッパ）
    - J-Quants / kabuステーション / LINE / DB /監視閾値 / システム関連のプロパティを提供。
    - `env` プロパティは `development` / `paper_trading` / `live` を検証。
    - Paper Trading 用設定（`PAPER_FILL_MODE`, `PAPER_TRADING_SQLITE_PATH`）をサポート。
- 設定ウィザード CLI
  - `kabusys.config_setup` に対話式ウィザードを実装。
  - `.env` の初期作成・更新を対話的に行い、シークレット項目はマスク表示。
  - `.env` 書き出し時にテンプレートコメントを付与。
  - 実行例: `python -m kabusys.config_setup`
- 設定検証 CLI
  - `kabusys.validate_config` に起動前チェック機能を実装。
  - 必須環境変数未設定やプレースホルダ値、ログレベル・KABUSYS_ENV の検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML があれば）パース検証を行う。
  - `--strict` で警告をエラー扱いにするオプションを提供。
  - 実行例: `python -m kabusys.validate_config`
- 起動スクリプト
  - 実行エンジン起動スクリプト `run_execution.py`
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使い、Paper Trading 用 DB (`data/paper_trading.db` または `PAPER_TRADING_SQLITE_PATH`) に記録して本番 DB と分離。
    - プロセス優先度を最初に `high` に設定（`utils.process_priority.set_process_priority` を利用）。
    - 停止フラグ `data/stop_requested.flag` の存在を監視し、検知時にエンジン停止。
    - 実行中の PID を `data/execution.pid` に書き出す仕組み（Engine に引き渡す）。
  - 監視ループ起動スクリプト `run_monitoring.py`
    - `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下はデフォルトにフォールバック）。
    - Monitoring は KABUSYS_ENV にかかわらず本番 `sqlite_path` を使用（監視は本番 DB を見る設計）。
    - 停止フラグ `data/stop_requested.flag` の検出でループ終了。
- ロギング整備
  - `kabusys.utils.logging_setup.setup_logging`
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定するユーティリティを追加。
    - ログレベルは引数 > 環境変数 `LOG_LEVEL` > デフォルト("INFO") の順で決定。
    - ログ出力先ディレクトリは引数 > 環境変数 `LOG_DIR` > デフォルト("logs/") の順で決定。ディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみ継続。
- プロセス制御ユーティリティ
  - `kabusys.utils.process_priority`
    - Windows と POSIX (Linux/macOS/FreeBSD) に対して抽象化されたプロセス優先度設定（`high`/`normal`/`low`）を提供。psutil による実装で権限不足や未実装 API は警告してスキップ。
    - CPU affinity を最初の N コアに固定する `set_cpu_affinity` を提供（未指定は全コア使用）。権限不足等は警告してスキップ。
- 実行系コンポーネント（骨子）
  - ExecutionEngine を起動するための依存組み立て（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine の組立て）。
  - RiskManager のデフォルトパラメータ（max_position_pct, max_utilization, rate_limit_per_sec 等）を設定して初期化。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - kabusys.portfolio モジュールを追加:
    - portfolio_builder:
      - select_candidates: スコア降順・タイブレークは signal_rank、小数スコアを扱う。
      - calc_equal_weights: 等金額配分。
      - calc_score_weights: スコア正規化配分（全てのスコアが 0.0 の場合は等配分にフォールバックし WARNING）。
    - risk_adjustment:
      - apply_sector_cap: セクター別上限（max_sector_pct）を適用し、上限超過セクターの新規候補を除外。sector が不明 ("unknown") な銘柄は上限適用除外。
      - calc_regime_multiplier: market レジームに応じた投下資金乗数を返す（"bull":1.0, "neutral":0.7, "bear":0.3）。未知レジームは 1.0 にフォールバックして警告を出す。
    - position_sizing:
      - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づく株数決定。lot_size（単元）丸め、1銘柄上限、aggregate cap（available_cash） に基づくスケーリング、コストバッファ反映、残差配分ロジックを実装。
      - risk_based はリスク許容率 (risk_pct) と stop_loss_pct を使ってベース株数を計算。
- Paper Trading 検証ツール
  - `kabusys.tools.paper_verification_report`
    - Paper Trading 用 SQLite（デフォルト `data/paper_trading.db` / `PAPER_TRADING_SQLITE_PATH` で上書き可）から、システム稼働率・注文成功率・送信率・レイテンシ（avg/max/P95）・リスク却下数を集計し、PASS/FAIL 判定を出力するレポート機能を追加。
    - P95 の算出ロジックを実装。閾値はファイル内定数で設定（稼働率 99%、成功率 90%、送信率 95%、P95 latency 200ms）。
    - 実行例: `python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11`
- リサーチ / ファクター計算（骨子）
  - `kabusys.research.factor_research` を追加（設計と一部定数、calc_momentum の docstring と変数定義を含む）。DuckDB 経由で prices_daily / raw_financials を参照し、Momentum / Value / Volatility / Liquidity を計算する設計。実装は継続中（ファイル末尾で途中まで）。

変更（Changed）
- なし（初期リリース）

修正（Fixed）
- なし（初期リリース）

注記（Notes）
- run_monitoring は意図的に KABUSYS_ENV にかかわらず本番 sqlite_path を使用します。監視は本番 DB を参照する設計に注意してください。
- run_execution は paper_trading 環境で DB を切り離すことで本番データと完全分離することを意図しています。
- .env 管理と検証ツールにより、起動前に設定不備を検出しやすくなっています。
- 一部モジュール（リサーチの関数群など）は設計に基づく実装の拡張が予定されています（今後のリリースで追加実装予定）。

--- 

開発者向け補足（実装に基づく運用上のポイント）
- ログ: ファイル出力の失敗時は stdout のみで継続するため、cron 等での採用時は stdout をログにリダイレクトする運用を想定。
- process priority / cpu affinity は権限に依存するため、権限不足時は警告が出て処理は継続します。
- .env パーサはクォート内のバックスラッシュエスケープ対応や export プレフィックスに対応しており、一般的な .env フォーマットを堅牢に扱えます。