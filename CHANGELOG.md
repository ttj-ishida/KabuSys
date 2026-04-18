CHANGELOG
=========

すべての注目すべき変更点をここに記載します。  
（以下は与えられたコードベースの内容から推測して作成した ChangeLog です）

フォーマットは Keep a Changelog に準拠しています。
https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（なし）

[0.1.0] - 2026-04-18
-------------------

Added
- 初期リリースとして以下の主要機能・モジュールを追加
  - 起動スクリプト
    - run_execution.py
      - ExecutionEngine を起動するスクリプト。
      - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db をデフォルト）を使用し、MockBrokerClient を利用する想定。
      - 起動時にプロセス優先度を High に設定する。
      - stop フラグ（data/stop_requested.flag）や PID ファイル（data/execution.pid）に対応し、フラグ検知で安全に停止する仕組みを備える。
      - ExecutionEngine の組み立て時に OrderRepository, OrderManager, RiskManager, Reconciler などの依存コンポーネントを初期化。
      - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を設定し、initial_portfolio_value を broker.get_available_cash() で取得して初期化する。
    - run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプト。
      - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（monitoring 用 DB 初期化を実行）。
      - 停止フラグ（data/stop_requested.flag）検知でループ終了。
      - 例外発生時にもログを出力して次のポーリングへ継続するフェイルセーフを備える。

  - 設定管理
    - config.py
      - .env/.env.local の自動ロード機能を提供（プロジェクトルートが見つかれば自動読み込み。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
      - .env パース処理は引用符付き値、エスケープシーケンス、行コメント（条件付き）に対応。
      - Settings クラスを提供し、各種設定値（J-Quants, kabu API, DB パス, Paper Trading 設定、監視閾値、環境値検証など）をプロパティとして取得可能。値の検証（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）を行う。
    - config_setup.py
      - .env 生成／更新の対話式ウィザード CLI を提供。既存 .env 読み込み、シークレットのマスク表示、保存確認などをサポート。
    - validate_config.py
      - .env と config/*.yaml の事前検証 CLI。
      - 必須環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL、DB パスの親ディレクトリ存在確認、YAML ファイルの存在／パース（PyYAML がある場合）や本番時の追加ガードチェックを実施。
      - --strict オプションで警告も失敗扱いにできる。

  - ログ・プロセス管理ユーティリティ
    - utils/logging_setup.py
      - ルートロガーを統一的に設定するヘルパーを提供。
      - stdout 出力の StreamHandler と日次ローテート（TimedRotatingFileHandler）を設定。ログディレクトリは LOG_DIR / 引数 / デフォルト（logs/）で解決。30 日保持。
      - 既存ハンドラをクリアして二重登録を防止。
    - utils/process_priority.py
      - クロスプラットフォームでプロセス優先度と CPU affinity を設定するユーティリティ。
      - Windows と POSIX（Linux/Mac 等）に対応し、権限不足時は警告を出してスキップする安全化を実装。
      - set_process_priority("high"|"normal"|"low"), set_cpu_affinity(N) を提供。

  - ポートフォリオ構築（純粋関数群）
    - portfolio/portfolio_builder.py
      - select_candidates: score 降順、同点は signal_rank 昇順で上位 N を選択。
      - calc_equal_weights: 等金額配分（各銘柄 1/N）。
      - calc_score_weights: スコア正規化配分。全スコアが 0 の場合は等金額配分にフォールバックして WARNING を出力。
    - portfolio/risk_adjustment.py
      - apply_sector_cap: セクター集中制限。現有ポジションと価格情報からセクター別エクスポージャーを計算し、上限超過セクターの新規候補を除外（"unknown" セクターは除外対象外）。
      - calc_regime_multiplier: レジーム（"bull","neutral","bear"）に応じた投下資金乗数を返す（未定義は 1.0 でフォールバック）。
    - portfolio/position_sizing.py
      - calc_position_sizes: allocation_method("risk_based","equal","score") に基づく発注株数計算。lot_size（現行は 100）を考慮した丸め、per-stock 上限、aggregate cap（available_cash に基づくスケールダウン）、cost_buffer（手数料・スリッページ見積）を実装。
      - risk_based モードでは stop_loss_pct と risk_pct から株数を算出。
      - aggregate スケールダウン時は残余キャッシュで remainder に応じた単位追加配分ロジックを持つ。

  - 分析／トゥール
    - tools/paper_verification_report.py
      - Paper Trading 用の検証レポート生成 CLI。
      - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ、リスク却下数 などを SQLite のテーブル（system_status, trade_logs, risk_logs）から集計して出力。
      - デフォルトの閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を定義し、PASS/FAIL 判定を行う。
      - --from/--to/--db オプションで期間／DB を指定可能。DB ファイルが見つからない場合はエラーメッセージを表示。

  - 研究用モジュール（開発途中）
    - research/factor_research.py
      - ファクター計算（Momentum, Value, Volatility, Liquidity）を行うモジュールの骨組みを追加。DuckDB 接続を受けて prices_daily / raw_financials を参照し、各種期間のリターンや MA200 乖離、ATR、出来高等を計算する設計方針を記載。モメンタム計算関数のインターフェースが定義され始めている（実装は続く）。

Changed
- パッケージ初期構成として各モジュールを整理し、__init__.py にバージョン（0.1.0）と公開 API を設定。

Fixed
- （初回リリースにつき該当なし。またはコード内で既知の扱いを安全化する例外処理・フォールバックを多く導入）
  - 環境変数や外部依存（PyYAML, ログディレクトリ作成, psutil の特定定数等）がない場合のフォールバック／ワーニング出力を明確化。

Notes / Implementation details（実装上の注意点）
- .env パーサは引用符内部でのバックスラッシュエスケープに対応しており、クォートあり／なしでのコメント解釈を区別する実装になっている点が特徴。
- run_monitoring は MONITOR_POLL_INTERVAL に不正な値（0 や非数）が設定された場合にデフォルト 60 秒にフォールバックして警告を出す。
- Settings.paper_fill_mode は許容値チェックを行い、不正値は ValueError を送出する。
- ロギング設定は標準出力を stdout に出す設計（cron 等で stdout/stderr を一括リダイレクトする運用を想定）。
- process_priority の設定は環境によってアクセス権限がない場合があるため、AccessDenied 等を捕捉して警告に留める安全策が取られている。
- Paper Trading と本番 DB は明確に分離される設計（paper_trading 環境では paper_sqlite_path を使用）。

開発者向け備考（推奨ワークフロー）
- .env の初期化には python -m kabusys.config_setup を使用し、生成後に python -m kabusys.validate_config で設定検証を行うことを推奨。
- Paper Trading 検証は tools/paper_verification_report を用いて期間を指定してレポートを作成してください。

---

（注）上記の内容は提供されたソースコードの解析に基づく推測です。実際の変更履歴やリリースノートは、コミット履歴や開発者の意図に基づいて調整してください。