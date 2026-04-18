CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従います。  
日付はリポジトリ内のバージョン情報とコードの実装状況に基づいて推定しています。

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-18
--------------------

Added
- 基本機能の初期実装（初回リリース）。
  - アプリケーションバージョンを `__version__ = "0.1.0"` として公開。
- 環境/設定管理
  - .env ファイル自動読み込み機能を追加（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - .env のパース機能を実装。以下に対応:
    - 空行・コメント行（#）の無視。
    - export KEY=val 形式のサポート。
    - シングル/ダブルクォート内のエスケープ処理。
    - インラインコメントの取り扱い（クォート外かつ直前が空白の `#` をコメントとみなす）。
  - 環境変数未設定時に例外を投げる `_require()` ユーティリティを追加。
  - Settings クラスを実装し、J-Quants / kabuステーション / LINE / DB /監視閾値 / システム設定等のプロパティを提供。
  - PAPER_FILL_MODE のバリデーション（"instant"|"partial"|"never"|"reject"）を実装。
  - 環境を `development` / `paper_trading` / `live` のいずれかに制限する検証を実装。
- 設定ウィザード CLI
  - `kabusys.config_setup` に対話式ウィザードを実装。`.env` の初期作成・更新を支援。
  - 既存 .env 読み込み、秘匿値のマスク表示、選択肢提示、保存確認、ファイル書き出しロジックを実装。
- 設定検証 CLI
  - `kabusys.validate_config` に設定検証ツールを実装。
  - 必須/任意環境変数チェック、KABUSYS_ENV / LOG_LEVEL の検証、DB パス存在有無チェック、config/*.yaml の存在と（PyYAML がある場合は）パース検証、本番環境用ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）を実装。
  - `--strict` オプションで警告を失敗扱いにする機能を追加。
- ログ設定ユーティリティ
  - `kabusys.utils.logging_setup.setup_logging` を実装。
    - stdout 出力用 StreamHandler（stdout）と日次ローテーションの TimedRotatingFileHandler をルートロガーに設定。
    - ログディレクトリ自動作成。作成に失敗した場合はファイル出力を無効化してコンソールのみで継続。
    - 既存ハンドラをクリアして二重登録を防止。
- プロセス優先度 / CPU affinity ユーティリティ
  - `kabusys.utils.process_priority.set_process_priority` と `set_cpu_affinity` を実装。
    - Windows / POSIX（Linux, Darwin, FreeBSD）差分を吸収。
    - psutil の例外（AccessDenied など）を安全にハンドリングして警告に落とす。
- 実行・監視用の起動スクリプト
  - `run_execution.py`
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は Paper 用専用 SQLite（環境変数/デフォルト: `data/paper_trading.db`）を使用し、本番 DB と分離する設計。
    - BrokerClientFactory によるブローカークライアント生成（mock を含めて切り替え可能）。
    - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立てと起動シーケンスを実装。
    - PID ファイル管理、停止フラグ（data/stop_requested.flag）検知による安全停止処理を実装。
    - ExecutionEngine を別スレッドで実行し、停止フラグでエンジン停止を呼び出すループを実装。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec 等）を定義し、初期ポートフォリオ値に broker.get_available_cash() を使用。
  - `run_monitoring.py`
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境にかかわらず「本番の」sqlite_path を監視 DB として使用する設計（監視は本番 DB を参照）。
    - ポーリング間隔を環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。不正値時はデフォルトにフォールバックして警告。
    - 停止フラグ検知でループを終了、例外発生時はログに例外情報を出して次ポーリングへ継続する耐障害性を実装。
- 監視 DB 初期化
  - `monitoring.monitoring_db.init_monitoring_db`（呼び出しを両スクリプトに追加）により、監視用テーブルの冪等初期化を保証。
- Paper Trading 検証ツール
  - `kabusys.tools.paper_verification_report` を追加。
    - Paper Trading 用 SQLite のログ（trade_logs / system_status / risk_logs 等）から検証指標（稼働率、注文成功率、送信率、レイテンシ等）を集計してレポート出力。
    - P95 計算、閾値による PASS/FAIL 判定、コマンドライン引数で期間指定（--from/--to/--db）をサポート。
    - デフォルト閾値: 稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms。
- ポートフォリオ構築ライブラリ
  - `kabusys.portfolio` パッケージを追加し、純粋関数群を実装:
    - portfolio_builder: 候補選定（select_candidates）、等配分（calc_equal_weights）、スコア重み（calc_score_weights: スコア全ゼロ時は等配分にフォールバック）。
    - risk_adjustment: セクターキャップ適用（apply_sector_cap: 既存ポジションのセクター比率に基づき候補を除外）、レジーム乗数計算（calc_regime_multiplier: bull/neutral/bear マップと未知レジームのフォールバック）。
    - position_sizing: 各銘柄の株数算出（calc_position_sizes）。allocation_method = "risk_based" / "equal" / "score" をサポート。単元株（lot_size）丸め、per-stock 上限、aggregate cap によるスケールダウンと端数配分ロジックを実装。cost_buffer パラメータで手数料/スリッページを保守的に見積もる。
  - 上記関数は DB 非依存の純粋関数として実装（メモリ内計算）。
- 研究用ファクター計算骨格
  - `kabusys.research.factor_research` にモメンタム等ファクター計算の設計と一部実装（定数・関数シグネチャ・設計方針）を追加。DuckDB 接続を受け prices_daily / raw_financials を参照する想定。

Changed
- ロギング設定の挙動を標準化:
  - stdout を利用することで cron 等からのリダイレクト運用に適するようにした。
  - 既存ハンドラを自動クリアすることで多重出力を防止。

Fixed / Robustness
- ファイル/ディレクトリ作成の失敗に対してフェイルセーフを導入:
  - ログディレクトリ作成失敗時はファイルハンドラの追加をスキップし、コンソールログのみで継続。
  - .env 読み込み失敗時は警告を発して続行。
- psutil / プラットフォーム非対応機能（nice/affinity/Windows 定数）が存在しない場合でもモジュールロードや実行が失敗しないようにフォールバックと例外ハンドリングを追加。
- Execution / Monitoring スクリプトで DB 接続（sqlite3 / duckdb）を finally ブロックで確実にクローズするように修正（リソースリーク防止）。
- Paper 検証レポートで対象テーブルが存在しない場合の sqlite3.OperationalError を捕捉して耐障害的にレポートを生成。

Notes / Usage
- 起動スクリプト例:
  - 監視: python -m kabusys.run_monitoring
  - 実行エンジン: python -m kabusys.run_execution
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - Paper レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- 主要な環境変数とデフォルト:
  - KABUSYS_ENV: development (選択肢: development, paper_trading, live)
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - LOG_LEVEL: INFO
  - MONITOR_POLL_INTERVAL: 60（秒、監視ループ）
  - PAPER_FILL_MODE: instant（paper_trading の注文約定動作を制御）
  - KILL_FLAG_CLEAR_ON_START: 0（本番では 0 推奨）
- Paper Trading と本番 DB は分離:
  - KABUSYS_ENV=paper_trading の場合は paper_sqlite_path を使用し、本番の monitoring.db とデータを混ぜない設計。
- 設定ファイル config/*.yaml は PyYAML がインストールされている場合のみ内容検証を行う。未インストール時は存在チェックのみ行う。

Deprecated
- なし

Removed
- なし

Security
- なし

今後の予定（例）
- factor_research の完全実装（Momentum / Value / Volatility / Liquidity の計算ロジック）。
- ExecutionEngine 内部のテストカバレッジ強化・Broker クライアントの抽象化拡張。
- 単体銘柄ごとの lot_size を銘柄マスタから取得する拡張（現行は全銘柄共通 lot_size）。
- monitoring のアラート通知（LINE 連携）実装の強化。