CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して日本語で記載します。

Unreleased
----------
（なし）

[0.1.0] - 2026-04-21
--------------------

Added
- 初回リリース: KabuSys v0.1.0 を追加。
  - コア CLI / 起動スクリプト
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。  
      - 起動時にプロセス優先度を "high" に設定。
      - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用して本番 DB と分離。
      - BrokerClientFactory によりブローカークライアントを作成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine をスレッドで起動。data/stop_requested.flag により安全に停止可能。
      - PID ファイル (data/execution.pid) のサポート。
    - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。  
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告のうえデフォルトにフォールバック。
      - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用（監視テーブル初期化済みで接続）。
      - stop フラグ検出でループを終了し、例外発生時はログを残して次ポーリングへ。
  - 設定管理 / ユーティリティ
    - config.py: Settings クラスを追加。環境変数の読み込み自動化、.env / .env.local の読み込み順序、必須キーチェック、各種プロパティ（PAPER_FILL_MODE、duckdb/sqlite パス、PID/kill flag パス、閾値、環境判定等）を提供。
      - .env パースは export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、コメント処理に対応。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - config_setup.py: 対話式 .env 作成ウィザードを追加。
      - 秘匿項目はマスク表示、既存 .env の読み込み、保存テンプレートの生成をサポート。
    - validate_config.py: 設定検証 CLI を追加。
      - 必須環境変数の存在チェック、KABUSYS_ENV/LOG_LEVEL の値チェック、DB パスの存在チェック、config/*.yaml の存在と（PyYAML があれば）パース検証、KABUSYS_ENV=live 時の追加警告を出す。
      - --strict オプションで警告を FAIL 扱いにする。
    - utils/logging_setup.py: ログ設定ユーティリティを追加。
      - stdout へ StreamHandler、日次ローテートの TimedRotatingFileHandler（デフォルト logs/<app_name>.log）をルートロガーに設定。既存ハンドラをクリアして二重設定を防止。
      - LOG_LEVEL / LOG_DIR / 引数で解決。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - utils/process_priority.py: プロセス優先度・CPU affinity のユーティリティを追加。
      - Windows と POSIX (Linux/Mac/FreeBSD) の差分を吸収して優先度設定を行う。失敗時は警告を出してスキップ。
      - set_cpu_affinity により最初の N コアにピン留め可能（権限不足や未実装時は警告を出してスキップ）。
  - ポートフォリオ構築（Portfolio）
    - portfolio/portfolio_builder.py:
      - select_candidates: スコア降順（同点は signal_rank 昇順）で候補を抽出。
      - calc_equal_weights / calc_score_weights: 等比重・スコア比重の重み計算。全スコアが 0 の場合は等金額配分にフォールバックし警告を出す。
    - portfolio/risk_adjustment.py:
      - apply_sector_cap: セクター集中制限で既存保有が上限を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。
      - calc_regime_multiplier: 市場レジーム (bull/neutral/bear) に対する乗数を返す。未知レジームは 1.0 でフォールバックして警告。
    - portfolio/position_sizing.py:
      - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に応じて株数を算出。単元株 (lot_size) に丸め、per-stock 上限と aggregate cap を適用。cost_buffer を考慮した保守的見積りとスケーリング／残差処理を実装。
  - research
    - research/factor_research.py: ファクター計算モジュールの骨組みを追加（モメンタム等の計算ロジックを実装予定）。DuckDB を使った prices_daily / raw_financials 参照設計。calc_momentum の実装開始（ファイル末尾で中断あり）。
  - tools
    - tools/paper_verification_report.py: Paper Trading 検証レポート生成 CLI を追加。
      - 稼働率（uptime）、注文成功率（fill rate）、送信率、P95 レイテンシ等を算出して PASS/FAIL を判定する。SQLite（PAPER_TRADING_SQLITE_PATH）を参照し、日付フィルタ／コマンドライン引数をサポート。
  - パッケージ情報
    - __init__.py によるパッケージ定義とバージョン宣言 __version__ = "0.1.0"。

Changed
- 初回公開のため該当なし（すべて新規追加）。

Fixed
- 初回公開のため該当なし。

Security
- 初回公開のため該当なし。

Notes / 実装上の重要な挙動
- run_monitoring は MONITOR_POLL_INTERVAL を整数で解釈し、1 未満や不正な文字列はログ警告のうえデフォルト 60 秒にフォールバックする。
- run_execution は paper_trading 環境時に mock/分離 DB を使い、本番データと完全分離する設計。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml）を起点に行われ、CWD に依存しない。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定する。
- validate_config は PyYAML 未導入環境では YAML 検証をスキップし、その旨を警告する。
- logging_setup はログディレクトリ作成失敗時にファイル出力を無効化しコンソール出力にフォールバックするため、権限のない環境でも動作継続する設計。
- position_sizing のスケーリングロジックは再現性のため残差ソートで安定した順序を採用している（fractional 残差の降順、同値は code を二次キーに）。

Environment variables (代表)
- 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
- 運用関連: KABUSYS_ENV (development | paper_trading | live), LOG_LEVEL, LOG_DIR
- DB 関連: DUCKDB_PATH (data/kabusys.duckdb), SQLITE_PATH (data/monitoring.db), PAPER_TRADING_SQLITE_PATH (data/paper_trading.db)
- その他: MONITOR_POLL_INTERVAL, PAPER_FILL_MODE, PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START

今後の予定（非破壊的な予定事項）
- research/factor_research の各ファクター計算（Momentum/Value/Volatility/Liquidity）を完遂し、DuckDB ベースの一貫したファクター生成パイプラインを整備。
- ExecutionEngine/Monitoring の追加テスト、異常時のより詳細な監視アラート実装（LINE 通知など）。
- 銘柄単位の lot_size を管理する stocks マスタを導入し position_sizing を拡張。

--------------------------------------------------------------------
この CHANGELOG はコードの内容から推察して作成しています。実際のリリースノートとの差分がある場合は適宜調整してください。