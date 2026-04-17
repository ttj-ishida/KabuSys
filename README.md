# KabuSys

KabuSys は日本株自動売買システムのコアライブラリ群です。シグナルのポートフォリオ構築、ポジションサイズ計算、実際の注文発行・再同期、監視（モニタリング）や Research / AI 補助機能（ニュース NLP・レジーム判定）などを含みます。本リポジトリはライブラリ＋実行スクリプト群（モニタ、実行エンジン、ツール）で構成されています。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（起動コマンド例）
- ディレクトリ構成（主要ファイル解説）
- 環境変数 / 設定のポイント
- 注意事項

---

プロジェクト概要
- 日本株自動売買用の内部ロジックと運用用ユーティリティの集合。
- 主な責務：
  - ポートフォリオ構築（候補選定・重み計算・リスク調整・位置サイズ決定）
  - 注文管理・実行エンジン（ブローカー抽象化、再同期 / Reconciler）
  - 監視モジュール（システム監視、注文監視、リスク監視、アラート送信）
  - Research（ファクター計算・将来リターン・IC計算など）
  - AI 支援（ニュースのセンチメントスコアリング、マーケットレジーム判定）
  - 運用ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）

機能一覧（要約）
- Portfolio
  - select_candidates, calc_equal_weights, calc_score_weights
  - apply_sector_cap, calc_regime_multiplier
  - calc_position_sizes（リスクベース／Equal／Score ベースで株数算出、単元丸め、aggregate cap）
- Execution
  - OrderManager / ExecutionEngine（注文発行、状態遷移管理）
  - Reconciler（クラッシュ後の自動復旧）
  - Broker client ファクトリ（本番 / PaperTrading 用の分離）
- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク、データ鮮度、実行プロセス生存確認
  - TradeMonitor：滞留注文（stale orders）・約定異常価格の検出
  - RiskMonitor：ドローダウン・ポジション上限の監視、ダッシュボード永続化
  - AlertManager：LINE Push による通知（クールダウン管理）
  - KillSwitch：条件に応じて停止フラグを書き込み ExecutionEngine を止める
  - MonitoringEngine：各 Monitor を束ねるポーリングループ
  - Streamlit ダッシュボード（監視 UI）
- Research
  - calc_momentum / calc_volatility / calc_value（DuckDB を用いたファクター算出）
  - calc_forward_returns / calc_ic / factor_summary（特徴量・IC 計算）
- AI
  - news_nlp.score_news：raw_news をまとめて OpenAI に投げ、銘柄ごとの ai_score を ai_scores テーブルへ書き込み
  - regime_detector.score_regime：ETF の MA200 乖離＋マクロニュースセンチメントで日次レジーム判定
- Tools
  - paper_verification_report：Paper Trading DB を解析し PASS/FAIL を出す検証レポート生成
- ユーティリティ
  - config.Settings：環境変数 / .env 読み込み、各種設定プロパティを提供
  - utils.process_priority：プロセス優先度・CPU affinity 設定ユーティリティ
  - monitoring_db.MonitoringDB：監視用 SQLite テーブルの初期化と CRUD

---

セットアップ手順（開発 / 実行環境準備）
1. Python バージョン
   - Python 3.10 以上を推奨（PEP 563 的な型注釈や union 型表記を使用）。

2. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージ（代表的なもの）
   - pip install duckdb psutil requests openai streamlit
   - その他、依存関係はプロジェクトの要求に応じて追加してください。

   ※requirements.txt があればそれを使ってください（このコードベースでは示されていません）。

4. プロジェクトルートに .env を配置
   - .env.example を参考に必要な環境変数を設定してください（.env.example はこの抜粋には含まれていませんが、config モジュールのエラーメッセージに従って作成します）。
   - 自動ロード順序：OS 環境 > .env.local > .env 。
   - 自動ロードを無効化したい場合：環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

5. データディレクトリ
   - data/ ディレクトリを作成すると便利。デフォルトの SQLite / DuckDB パスは data 以下です。
   - 例:
     - data/monitoring.db
     - data/paper_trading.db
     - data/kabusys.duckdb
     - data/execution.pid, data/kill.flag 等

6. DB 初期化
   - Monitoring 系は起動時に init_monitoring_db() でテーブル作成（冪等）するため、特別なマイグレーションは不要です。
   - DuckDB に prices_daily や raw_financials などのテーブルをロードする処理は別途必要です（データパイプライン実装が前提）。

---

使い方（主要コマンド例）
- 実行スクリプトはモジュールとして起動できます（プロジェクトルートで実行）:

1) 監視プロセス起動（Monitoring）
   - python -m kabusys.run_monitoring
   - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可（デフォルト 60 秒）。
   - 停止: data/stop_requested.flag を作成するとループが検出して停止します。

2) 実行エンジン起動（ExecutionEngine）
   - python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading を設定して起動すると、MockBrokerClient を使用して data/paper_trading.db に記録（本番 DB と分離）。
   - 実行中の停止は data/stop_requested.flag または kill.flag により制御されます。

3) Streamlit 監視ダッシュボード（読み取り専用）
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

4) Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report
   - オプション:
     - --from YYYY-MM-DD  （開始日）
     - --to YYYY-MM-DD    （終了日）
     - --db PATH          （SQLite DB パス。省略時: env または data/paper_trading.db）

5) AI / Research 実行
   - AI 機能は OpenAI API キーが必要:
     - 環境変数 OPENAI_API_KEY を設定するか、該当関数に api_key を渡してください。
   - news_nlp.score_news(conn, target_date, api_key=None)
   - regime_detector.score_regime(conn, target_date, api_key=None)
   - Research 関数は DuckDB 接続を要求します（prices_daily, raw_financials 等が必要）。

---

主要な環境変数（抜粋）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: 必須（Settings.jquants_refresh_token を使用する場合）
- KABU_API_PASSWORD: 必須（kabuステーション API 連携時）
- OPENAI_API_KEY: OpenAI を利用する機能で必要
- PAPER_FILL_MODE: paper trading の約定モード（instant|partial|never|reject）
- PAPER_TRADING_SQLITE_PATH: Paper trading 用 SQLite（デフォルト data/paper_trading.db）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, LOG_LEVEL など
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）

設定は .env / .env.local や OS 環境変数で与えられます。config.Settings が設定の取得・バリデーションを行います。

---

ディレクトリ構成（主要ファイルの説明）
- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数の読み込み・Settings クラス（.env 自動ロード機能含む）
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト（paper_trading 用 DB 分離）
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算（等配分・スコア重み）
    - position_sizing.py — 発注株数計算（risk_based / equal / score）
    - risk_adjustment.py — セクターキャップ / レジーム乗数
  - monitoring/
    - monitoring_db.py — SQLite による監視用テーブルの初期化 & MonitoringDB（CRUD）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常検知
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — 停止フラグ書き込みユーティリティ
    - alert_manager.py — LINE Push 通知クライアント
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py — Streamlit 監視ダッシュボード（起動方法はファイル内コメント参照）
  - execution/
    - order_manager.py — 注文発行・状態管理の外向き API（OrderManager）
    - reconciler.py — 起動時の自動復旧・ポジション差分照合
    - 他（broker 関連や repository 等は抜粋に一部あり）
  - research/
    - factor_research.py — momentum / volatility / value ファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン計算・IC・統計サマリ
  - ai/
    - news_nlp.py — raw_news を OpenAI に投げるニュース NLP スコアリング
    - regime_detector.py — マーケットレジーム判定（ETF MA200 + マクロ NLP）
  - data/（実行時に利用するフラグ・DB ファイル等。リポジトリに含めないことを想定）
    - monitoring.db, paper_trading.db, kabusys.duckdb, stop_requested.flag, kill.flag, execution.pid

---

注意事項 / 運用上のポイント
- Paper Trading と Live の DB は明確に分離してください。run_execution.py は KABUSYS_ENV=paper_trading 時に paper_sqlite_path を使用します。
- AI（OpenAI）を利用する機能は API コストとレートリミットに注意してください。news_nlp・regime_detector は再試行ロジックを持ちますが、失敗時は安全側フォールバック（0 またはスキップ）します。
- monitoring の kill.switch はドローダウンやポジション上限を検出して自動的に停止フラグ（data/kill.flag）を書き込みます。kill.flag のクリアは ExecutionEngine 起動時の設定で制御できます（Settings.kill_flag_clear_on_start）。
- config.Settings はプロジェクトルートの .env / .env.local を自動ロードします。テスト環境などで自動ロードを止める場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Streamlit ダッシュボードは DB を読み取り専用で開きます（URI + mode=ro）。MonitoringEngine が DB を作成/更新している前提です。
- DuckDB / SQLite テーブル（prices_daily / raw_financials / raw_news / ai_scores / market_regime など）は Research / AI 機能で使用されます。これらのデータパイプラインは別途実装が必要です。

---

問い合わせ / 貢献
- バグ報告や機能改善リクエストは Issue を通してください。
- コードスタイル・テスト追加の PR は歓迎します。

---

簡単な起動例（まとめ）
- 仮想環境 & 依存インストール
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install duckdb psutil requests openai streamlit

- 環境変数設定（例）
  - export KABUSYS_ENV=development
  - export OPENAI_API_KEY=sk-...
  - export SQLITE_PATH=data/monitoring.db
  - export DUCKDB_PATH=data/kabusys.duckdb

- 監視プロセス起動
  - python -m kabusys.run_monitoring

- 実行エンジン（Paper Trading）
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

以上。README の補足や特定ファイルの詳しい説明が必要であれば、教えてください。