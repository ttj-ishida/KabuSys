CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" — https://keepachangelog.com/ja/1.0.0/

[0.1.0] - 2026-04-18
--------------------

Added
- 初回リリース。主要コンポーネントとユーティリティを追加。
  - コア実行スクリプト
    - run_execution.py
      - ExecutionEngine 起動用スクリプトを追加。
      - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と完全分離。
      - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、スレッド実行によるセッション管理を実装。
      - プロセス優先度を最初に "high" に設定（utils.process_priority）。
      - 停止フラグファイル (data/stop_requested.flag) による安全停止処理を備える。
    - run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプトを追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。不正な値はデフォルトにフォールバックして警告。
      - 監視（monitoring）用 DB は実行環境にかかわらず本番 sqlite_path を使用する設計。
      - 停止フラグによるループ終了、例外捕捉・ログ出力、最後に DB 接続をクローズ。

  - 設定関連
    - config.py
      - Settings クラスで環境変数経由の設定値アクセスを提供。
      - .env 自動読み込み機能を実装（プロジェクトルートの .env / .env.local をロード、OS 環境変数を保護）。
      - .env パース機構は export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの取り扱いなどに対応。
      - 各種設定プロパティ（DB パス、PID/kill flag パス、監視閾値、paper fill mode のバリデーション等）を用意。
    - config_setup.py
      - 対話式ウィザードで .env の初期作成・更新を支援する CLI を追加。
      - シークレットはマスク表示、選択肢・デフォルトのサポート、保存前確認を実装。
    - validate_config.py
      - 起動前に .env と config/*.yaml の設定不備を検出する検証ツールを追加。
      - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、PyYAML がある場合は YAML のパース検証を行う。
      - --strict オプションで警告を FAIL 扱いにできる。

  - ポートフォリオ構築（純関数群）
    - portfolio.portfolio_builder
      - select_candidates: BUY シグナルのスコア降順選定（タイブレークに signal_rank）。
      - calc_equal_weights: 等配分。
      - calc_score_weights: スコア加重。全スコアが 0 の場合は等配分にフォールバックして警告。
    - portfolio.risk_adjustment
      - apply_sector_cap: セクター集中制限（既存保有のセクター比率が上限を超える場合に新規候補を除外）。"unknown" セクターは上限適用除外。
      - calc_regime_multiplier: 市場レジーム ("bull"/"neutral"/"bear") に応じた投下資金乗数を返す（未知レジームは 1.0 にフォールバックし警告を出す）。
    - portfolio.position_sizing
      - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") をサポートする株数計算ロジックを実装。
      - 単元株（lot_size）丸め、per-position 上限（max_position_pct）、aggregate cap（available_cash）を考慮したスケーリング、cost_buffer による保守的コスト見積もり、残差に基づく追加配分アルゴリズムを実装。
      - 価格欠損時のスキップやログ出力を備える。

  - ユーティリティ
    - utils.logging_setup
      - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション・30日保持）を設定する共通ロギング設定を追加。
      - LOG_DIR / LOG_LEVEL の解決順を定義。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - utils.process_priority
      - Windows / POSIX（Linux/Mac 等）の差分を吸収してプロセス優先度 (high/normal/low) を設定するユーティリティを追加。
      - CPU affinity を最初 N コアに固定する set_cpu_affinity を提供（アクセス権限やプラットフォーム非対応時は警告を出してスキップ）。
    - その他パッケージ初期化 / バージョン定義（__version__ = "0.1.0"）

  - ツール・運用
    - tools.paper_verification_report
      - Paper Trading の検証レポート生成スクリプトを追加。
      - 稼働率、注文成功率（Fill Rate）、送信率（Send Rate）、リスク却下数、API レイテンシ（平均 / 最大 / P95）を計算してレポート出力。
      - コマンドライン引数 --from / --to / --db をサポート。PAPER_TRADING_SQLITE_PATH 環境変数から DB パスを取得可能。
      - デフォルトの合格基準（稼働率 >= 99.0%、fill_rate >= 90%、send_rate >= 95%、P95 latency <= 200 ms）を設定。

  - 研究用モジュール（duckdb によるファクター計算）
    - research.factor_research（モメンタム等のファクター計算を実装する設計。モメンタム算出のための定数と関数が追加されている（モジュール途中までの実装を含む））。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照してファクター計算を行う方針。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Security
- （初版のため該当なし）

Notes / Usage
- CLI の例
  - 環境設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - Execution 起動: python -m kabusys.run_execution
  - Monitoring 起動: python -m kabusys.run_monitoring
  - Paper レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

- 環境変数とデフォルト
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
  - SQLITE_PATH: data/monitoring.db（監視用 DB、デフォルト）
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
  - PAPER_FILL_MODE: instant | partial | never | reject（paper trading の約定モード。デフォルト: instant）
  - LOG_DIR / LOG_LEVEL: ログ出力設定

- 実装上の注意点（運用メモ）
  - .env の自動ロードはプロジェクトルート（.git または pyproject.toml を基準）が見つかった場合に限定して行われ、OS 環境変数は保護される。
  - process_priority や CPU affinity 設定は権限やプラットフォームにより失敗する可能性があり、その場合は警告してスキップする。
  - run_execution は停止フラグファイルを検出すると安全に停止する設計。run_monitoring は停止フラグ検出でループを抜ける。
  - portfolio の position sizing は単元株（lot_size）丸めと aggregate cap スケーリングを実装しており、手数料・スリッページ見積りのための cost_buffer パラメータを受け取る。

Acknowledgements
- 本リポジトリは初期設計段階のため、将来的に以下の点を改善予定:
  - stocks マスタから個別単元サイズを取得する設計への拡張
  - price 欠損時のフォールバック（前日終値等）処理の強化
  - research ファクター計算の完全実装とユニットテスト整備
  - エンドツーエンドの統合テスト・CI 設定の追加

<!-- END OF CHANGELOG -->