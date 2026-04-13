CHANGELOG
=========

All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠します。セマンティックバージョニングを使用します。

[0.1.0] - 2026-04-13
--------------------

Added
- 初回リリース: 基本機能群を追加。
  - パッケージメタ情報
    - kabusys/__init__.py にバージョン 0.1.0 を追加。

  - 設定/環境変数管理 (src/kabusys/config.py)
    - .env / .env.local 自動読み込み機能を追加（プロジェクトルートを .git または pyproject.toml で検出）。
    - OS 環境変数を保護して .env.local で上書き可能な仕組みを実装。
    - .env パーサを実装：コメント、クォート、export 形式に対応。無効行を無視。
    - Settings クラスを実装し、アプリケーション設定をプロパティ経由で取得できるようにした。
    - 環境変数の妥当性チェックを導入:
      - KABUSYS_ENV: 有効値 = development / paper_trading / live
      - LOG_LEVEL: 有効値 = DEBUG/INFO/WARNING/ERROR/CRITICAL
      - PAPER_FILL_MODE: instant / partial / never / reject（不正値で ValueError）
    - デフォルトパス／設定値を提供:
      - DUCKDB_PATH: data/kabusys.duckdb
      - SQLITE_PATH: data/monitoring.db
      - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
      - PID_FILE_PATH: data/execution.pid
      - KILL_FLAG_PATH: data/kill.flag
      - 各種閾値（CPU/MEM/DISK）など

  - 実行ユーティリティ (src/kabusys/utils/process_priority.py)
    - set_process_priority(level) を実装して Windows / POSIX の差を吸収して優先度設定を行う。
      - Windows は psutil の優先度クラス、POSIX は nice 値を使う。
      - 未対応 OS や権限不足時は警告を出してスキップするフェイルセーフを実装。
    - set_cpu_affinity(cpu_count) を実装（指定が None の場合は何もしない）。

  - 監視（Monitoring）ランナー (src/kabusys/run_monitoring.py)
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、1 未満は無効扱いしてデフォルトにフォールバック）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して接続し、監視用 DB 初期化を行う（init_monitoring_db）。
    - 起動時にプロセス優先度を "high" に設定。

  - 実行（Execution）ランナー (src/kabusys/run_execution.py)
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_sqlite_path（data/paper_trading.db 等）を使用して本番 DB と完全分離。
    - 起動時にプロセス優先度を "high" に設定。
    - BrokerClientFactory 経由でブローカークライアントを作成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - RiskManager のデフォルト構成値を設定（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20, initial_portfolio_value を broker.get_available_cash() から取得）。

  - 監視 DB 初期化フック（init_monitoring_db を使用して監視テーブルが存在することを保証）

  - Portfolio 構築ライブラリ (src/kabusys/portfolio/*.py)
    - 候補選定: select_candidates — スコア降順、signal_rank をタイブレークに使用。
    - 重み計算:
      - calc_equal_weights — 等金額配分（1/N）。
      - calc_score_weights — スコア正規化配分、すべてのスコアが 0 の場合は等金額にフォールバック（警告ログ）。
    - セクター制約: apply_sector_cap — 既存保有のセクター比率が上限を超える場合に当該セクターの新規候補を除外（"unknown" セクターは制限対象外）。
      - 売却予定銘柄（sell_codes）をエクスポージャー計算から除外する機能あり。
    - レジーム乗数: calc_regime_multiplier — regime ラベルに応じて乗数を返す（bull=1.0, neutral=0.7, bear=0.3、未知は 1.0 にフォールバックして警告）。
    - ポジションサイズ決定: calc_position_sizes — risk_based / equal / score の各配分方式に対応。単元株（lot_size）丸め、per-stock 上限、aggregate cap（available_cash）に基づくスケールダウン、cost_buffer を用いた保守的推定を実装。

  - 研究（Research）モジュール (src/kabusys/research/*.py)
    - factor_research: calc_momentum, calc_volatility, calc_value を実装。DuckDB 接続を受け、prices_daily/raw_financials テーブルからファクター値を算出。
      - モメンタム/MA200/ATR/平均売買代金等を計算。必要行数が不足する場合は None を返す仕様。
      - 各関数は target_date を引数に取り、date=target_date のレコードを返す。
    - feature_exploration:
      - calc_forward_returns — 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算（ホライズンの妥当性チェックあり）。
      - calc_ic — スピアマンランク相関（IC）を計算（有効レコード < 3 の場合は None）。
      - rank / factor_summary — ランク付けと基本統計量の集計を実装（外部ライブラリに依存しない純 Python 実装）。
    - research/__init__.py で主要関数を再エクスポート。

  - News NLP（AI スコアリング） (src/kabusys/ai/news_nlp.py)
    - raw_news を OpenAI（gpt-4o-mini）でセンチメント分析し、銘柄ごとの ai_scores テーブルへ書き込む機能を実装。
    - 処理フロー:
      - 指定 target_date に対するニュースウィンドウ（前日 15:00 JST 〜 当日 08:30 JST を UTC に変換）を算出する calc_news_window。
      - 記事を銘柄ごとに集約し、1銘柄あたり最大記事数と最大文字数でトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
      - 最大 20 銘柄単位でバッチ送信（_BATCH_SIZE=20）、OpenAI の JSON Mode を期待し厳密な JSON のレスポンスを検証。
      - 429・ネットワークエラー・タイムアウト・5xx は指数バックオフでリトライ（最大 _MAX_RETRIES 回）。
      - スコアは ±1.0 にクリップして保存。
      - API キーは引数 api_key または環境変数 OPENAI_API_KEY から取得（未設定時は ValueError）。

  - ツール: Paper Trading 検証レポート (src/kabusys/tools/paper_verification_report.py)
    - paper_trading DB を走査して検証レポートを標準出力に生成する CLI を追加。
    - 検証指標と閾値:
      - 稼働率 (uptime) >= 99.0%
      - 注文成功率 (fill_rate) >= 90.0%
      - 送信率 (send_rate) >= 95.0%
      - P95 レイテンシ <= 200 ms
    - P95 計算、日付フィルタ (--from / --to)、DB パスの引数/環境変数指定 --db / PAPER_TRADING_SQLITE_PATH をサポート。
    - DB が存在しない場合はエラーメッセージを表示して終了。
    - 各クエリは system_status / trade_logs / risk_logs テーブルを参照し、テーブルが存在しない場合は安全にフォールバック（OperationalError を捕捉）。

  - モジュールエクスポート
    - portfolio/__init__.py / research/__init__.py で主要 API をエクスポートし使いやすくした。

Changed
- 設計方針の明確化（ソース内ドキュメント）
  - research / portfolio / ai モジュールは原則として DB 参照または DuckDB 接続のみを受け、外部の実行環境や本番口座にはアクセスしない方針を明記。
  - ランタイムでの datetime.today()/date.today() 参照を避ける設計（ルックアヘッドバイアス防止）をドキュメント化。

Fixed
- n/a（初回リリース）

Security
- n/a（初回リリース）

Removed
- n/a（初回リリース）

Notes / Migration
- 実行方法（代表例）
  - 監視ループ: python -m kabusys.run_monitoring
  - 実行エンジン: python -m kabusys.run_execution
  - Paper レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- 重要な環境変数（主なもの）
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト: 60）
  - SQLITE_PATH: 本番監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 DB（デフォルト: data/paper_trading.db）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - OPENAI_API_KEY: News NLP 用 OpenAI API キー
  - PAPER_FILL_MODE: paper_trading の MockBroker の約定モード（instant|partial|never|reject）
  - PID_FILE_PATH / KILL_FLAG_PATH 等の監視関連パス
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効化

- 注意点
  - run_monitoring は監視用に「常に本番 sqlite_path を使用する」設計（KABUSYS_ENV に依存しない）。
  - run_execution は paper_trading 環境では paper_sqlite_path を使用して本番 DB と分離する。
  - process priority / cpu affinity の設定は権限不足や未対応プラットフォームで安全にスキップされる。
  - ai/news_nlp の OpenAI 呼び出しはレスポンス形式の厳密検証を行うため、API の互換性に注意。

今後の予定（抜粋）
- BrokerClient の具象実装（実ブローカー/モック）の補完とテストカバレッジ拡充
- エラー監視・メトリクスの DB 書き込み強化（監視側の retry やメトリクスの詳細化）
- position_sizing の lot_size を銘柄別に扱う拡張（stocks マスタ導入）
- ai/news_nlp のバッチ処理の堅牢化（部分失敗時のロールバックやトランザクション制御）

----- End of CHANGELOG -----