CHANGELOG
=========
All notable changes to this project will be documented in this file.

フォーマットは「Keep a Changelog」に準拠し、重要な変更をバージョン単位で記載します。

Unreleased
----------
（なし）

[0.1.0] - 2026-04-12
--------------------
初回リリース。以下の主要機能・モジュールを追加しました。

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージ情報:
    - __version__ = "0.1.0"

- 設定 / 環境変数管理 (kabusys.config)
  - .env/.env.local の自動読み込み機能（プロジェクトルートを .git または pyproject.toml で検出）。
  - 読み込みを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 複雑な .env パースをサポート（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント扱い等）。
  - Settings クラスを通した中央集約的な設定取得。
  - サポートされる主要な環境変数とデフォルト:
    - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
    - LOG_LEVEL（デフォルト: INFO）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
    - PAPER_FILL_MODE（instant/partial/never/reject、デフォルト: instant）
    - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
    - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID

- 実行系スクリプト
  - run_execution.py
    - ExecutionEngine の起動エントリポイント。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用して本番 DB と完全分離。
    - BrokerClientFactory により実行時に適切なブローカークライアントを生成（MockBrokerClient 等を使用可能）。
    - OrderRepository, OrderManager, RiskManager, Reconciler の組み立てを行い ExecutionEngine.run_session() を実行。
    - RiskManager のデフォルト設定（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20 等）。initial_portfolio_value は broker.get_available_cash() を利用して初期化。
    - 起動時にプロセス優先度を "high" に設定（set_process_priority）。

  - run_monitoring.py
    - SystemMonitor（監視ループ）の起動エントリポイント。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値や 0 以下はデフォルトへフォールバックし警告を出力。
    - 監視は環境に関わらず本番 sqlite_path（設定の sqlite_path）を使用して監視テーブルを初期化。
    - check_once() 実行中の例外はログに出してループを継続するフェイルセーフ実装。
    - 起動時にプロセス優先度を "high" に設定。

- 監視 DB 初期化ユーティリティ
  - init_monitoring_db を介して monitoring 用テーブルの存在を保証（冪等）。

- プロセス制御ユーティリティ (kabusys.utils.process_priority)
  - set_process_priority(level) — Windows / POSIX を吸収した優先度設定（"high" / "normal" / "low"）。
  - set_cpu_affinity(cpu_count) — 指定コア数への CPU affinity 固定（アクセス権限がない場合は警告でスキップ）。
  - 権限や未サポート OS へのフォールバックを行い、例外を直接投げずにログで通知。

- ポートフォリオ構築モジュール (kabusys.portfolio)
  - portfolio_builder:
    - select_candidates — スコア降順 + signal_rank タイブレークで候補選定。
    - calc_equal_weights — 等金額配分。
    - calc_score_weights — スコア加重配分（全スコアが 0 の場合は等金額にフォールバック）。
  - risk_adjustment:
    - apply_sector_cap — 現有ポジションを考慮したセクター集中度チェック（max_sector_pct に基づき新規候補を除外）。"unknown" セクターは上限適用外。
    - calc_regime_multiplier — market regime に応じた投下資金乗数（bull/neutral/bear）。
  - position_sizing:
    - calc_position_sizes — allocation_method ("risk_based", "equal", "score") に基づく株数計算、単元株（lot_size）丸め、aggregate cap スケーリング、cost_buffer（手数料/スリッページ見積り）を考慮。

- 研究（Research）モジュール (kabusys.research)
  - factor_research:
    - calc_momentum, calc_volatility, calc_value — DuckDB の prices_daily / raw_financials を参照してファクターを計算（MA200, ATR20, various momentum horizons など）。
  - feature_exploration:
    - calc_forward_returns — 将来リターン（fwd_1d, fwd_5d, fwd_21d など）計算（任意ホライズン対応）。
    - calc_ic — スピアマンランク相関（IC）計算（rank を内部実装）。
    - factor_summary — 基本統計量（count, mean, std, min, max, median）。
  - research パッケージは zscore_normalize（kabusys.data.stats）を再エクスポート。

- AI ニュース NLP スコアリング (kabusys.ai.news_nlp)
  - raw_news / news_symbols を集約し OpenAI API（gpt-4o-mini）で銘柄別センチメントスコア（-1.0〜1.0）を生成して ai_scores に書き込む機能を実装。
  - バッチサイズ、API リトライ（429/ネットワーク/5xx の指数バックオフ）、レスポンス検証、結果クリッピング、部分失敗時のテーブル更新の安全化（対象コードのみ置換）などを実装。
  - OpenAI API キーは引数 api_key または環境変数 OPENAI_API_KEY から取得。未設定時は ValueError を送出。

- ツール
  - tools.paper_verification_report:
    - Paper Trading 検証用 CLI レポートを追加（--from/--to/--db）。
    - 指標: 稼働率(uptime_pct)、注文成功率(fill_rate_pct)、送信率(send_rate_pct)、P95 レイテンシ（ms）等。
    - 判定しきい値（Pass/Fail）:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - DB が存在しない場合やテーブルがない場合に安全に N/A を扱う。

Changed
- （初回リリースのため履歴なし）

Fixed
- （初回リリースのため履歴なし）

Deprecated
- なし

Removed
- なし

Security
- OpenAI API キーの取り扱いは環境変数または明示的引数に限定。API キー未設定時はエラーで通知。
- 機密情報保護のため .env ロード時に OS 環境変数は protected として扱われ上書きを制御。

Notes / Known issues / TODO
- apply_sector_cap:
  - price_map における price 欠損（0.0）があるとエクスポージャーが過少見積りされる問題があり、将来的に前日終値や取得原価でフォールバックすることを検討中（TODO コメントあり）。
- calc_position_sizes:
  - 今は全銘柄共通の lot_size（デフォルト 100）固定。将来的には銘柄別 lot_map を受け取る設計に拡張予定（TODO）。
- ai.news_nlp:
  - DuckDB で executemany に空パラメータが渡せない既知制約を考慮している実装がある（部分更新の安全化）。
  - 大量API呼び出しのコストやレート制限に注意。API失敗時はフェイルセーフでスキップする設計だが、部分的にスコアが欠落する可能性あり。
- run_monitoring:
  - MONITOR_POLL_INTERVAL に不正値が設定された場合はログ警告後にデフォルトにフォールバック（time.sleep の ValueError 回避）。
- process_priority / set_cpu_affinity:
  - 権限不足や未サポート OS では設定をスキップして警告ログを出力する。これによりコンテナや制約のある環境でもクラッシュしない挙動にしている。

Usage / 実行例
- 監視ループ起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 を設定するとポーリング間隔を 30 秒に変更可能。
- 実行エンジン起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定してペーパートレーディング専用 DB を利用。
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB を指定可能または PAPER_TRADING_SQLITE_PATH 環境変数を使用。

Upgrade notes
- 初期リリースのためアップグレード指示はありません。今後のバージョンで後方互換性を崩す変更を行う場合は明記します。

Authors
- 開発チーム（ソースコード内の docstring とコメントを基に本 CHANGELOG を作成）

References
- 内部の設計ドキュメント参照（PortfolioConstruction.md, StrategyModel.md 等がコードコメントで言及されています）。