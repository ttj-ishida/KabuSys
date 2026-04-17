KabuSys — README
=================

概要
----
KabuSys は日本株の自動売買・研究・監視を行うためのモジュール群です。  
主な機能は以下の通りです。

- 発注・約定管理を行う ExecutionEngine（本番 / ペーパー取引を分離）
- システム稼働・データ鮮度・注文異常などを監視する Monitoring
- ポートフォリオ構築（候補選定、重み付け、株数決定、セクター制約等）
- ファクター計算・特徴量探索などの Research ツール（DuckDB ベース）
- ニュースを LLM（OpenAI）で評価する AI モジュール（ニュース NLP、レジーム判定）
- Paper Trading 検証レポート生成、Streamlit ダッシュボードなどのユーティリティ

設計上の特徴
- 設定は環境変数（.env / .env.local の自動読み込みをサポート）
- DuckDB と SQLite を併用（履歴・分析用に DuckDB、監視ログやペーパー用に SQLite）
- Paper Trading は本番 DB から分離（PAPER_TRADING_SQLITE_PATH を使用）
- フェイルセーフ設計（API エラー時はフォールバック / 部分失敗時に他データ保護など）

主な機能一覧
- Execution
  - 起動スクリプト: run_execution.py（KABUSYS_ENV によってペーパー/本番切替）
  - Reconciler による起動時の自動復旧
  - OrderManager / OrderRepository による注文状態管理
  - RiskManager（制約・ドローン検出等）を組み込み可能
- Monitoring
  - run_monitoring.py によるポーリングループ（MONITOR_POLL_INTERVAL で間隔変更可）
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager
  - SQLite に監視ログを永続化（init_monitoring_db）
  - Streamlit ダッシュボード（src/kabusys/monitoring/streamlit_dashboard.py）
- Research
  - ファクター計算（momentum/value/volatility）
  - 将来リターン・IC 計算・統計サマリーなど
- AI
  - news_nlp.score_news: raw_news を OpenAI でスコア化し ai_scores に書き込み
  - regime_detector.score_regime: ma200 + マクロ記事センチメントでレジーム判定
- Tools
  - Paper Trading 検証レポート: kabusys.tools.paper_verification_report
  - Streamlit ダッシュボード

前提 / 必要環境
- Python 3.10+
- 必要なライブラリ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード利用時)
- SQLite（標準ライブラリで利用可）
- ネットワークアクセス（OpenAI / LINE API を利用する場合）

セットアップ手順
1. リポジトリをクローンして作業ディレクトリへ移動
   - 例: git clone ... && cd ...

2. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - (プロジェクトに requirements.txt がない場合は以下を例示)
     pip install duckdb psutil requests openai streamlit
   - ある場合:
     pip install -r requirements.txt

4. data ディレクトリ作成
   - mkdir -p data

5. 環境変数 / .env の用意
   - .env.example がある場合は参照して .env を作成してください。
   - 主要な環境変数（抜粋）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - JQUANTS_REFRESH_TOKEN: J-Quants API（必要時）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必要時）
     - OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時）
     - PAPER_FILL_MODE: paper_trading の約定モード（instant|partial|never|reject、デフォルト instant）
     - PAPER_TRADING_SQLITE_PATH: ペーパー用 SQLite（デフォルト data/paper_trading.db）
     - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
     - DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）
     - LOG_LEVEL: ログレベル（DEBUG/INFO/...）

   - 注意: Settings モジュールは自動でプロジェクトルートの .env と .env.local を読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

使い方（実行例）
- 監視ループの起動（Monitoring）
  - 環境変数でポーリング間隔を変更:
    - export MONITOR_POLL_INTERVAL=30  # 30秒間隔
  - 起動:
    - python -m kabusys.run_monitoring
  - 監視は常に本番用の sqlite_path を使用します（KABUSYS_ENV に無関係）。

- 実行エンジンの起動（ExecutionEngine）
  - Paper Trading（データ分離）を使う場合:
    - export KABUSYS_ENV=paper_trading
  - 起動:
    - python -m kabusys.run_execution
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
  - 実行中の PID は data/execution.pid に書き込まれます。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは環境変数 PAPER_TRADING_SQLITE_PATH または --db で指定可能。

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- AI モジュールの利用（プログラムから呼び出し）
  - from kabusys.ai import score_news
  - score_news(conn, target_date, api_key="...")  # conn は duckdb connection

重要ファイル・フラグ
- data/stop_requested.flag: 起動スクリプトがこのファイルを検知するとループを終了するための外部停止フラグ（run_monitoring/run_execution で使用）
- data/kill.flag: KillSwitch が書き込む停止フラグ（ExecutionEngine に停止を促す）
- data/execution.pid: 実行エンジンの PID（SystemMonitor がプロセス生存をチェック）
- デフォルト DB ファイル:
  - data/monitoring.db （監視ログ用 SQLite）
  - data/paper_trading.db （Paper Trading 用 SQLite）
  - data/kabusys.duckdb （分析用 DuckDB）

Settings（設定）について
- src/kabusys/config.py の Settings クラスを使って設定値を取得します。
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行い、OS 環境変数を上書きしないデフォルト挙動です。テストで自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

運用注意点 / ヒント
- Paper Trading を使う場合は PAPER_TRADING_SQLITE_PATH を確認して本番 DB と混同しないようにしてください。
- OpenAI を使う機能は API キー必須。料金やレートリミットに注意して運用してください（スロットリング＆リトライ実装あり）。
- Monitoring / KillSwitch / AlertManager により重大なリスク（ドローダウンやポジション上限超過等）を検出した際に自動で停止フラグを書き込む設計です。flag の管理（クリアや削除）は運用ルールを決めて行ってください。
- process priority 設定: 起動スクリプトは最初に set_process_priority("high") を呼びます。権限がない環境では警告が出ますが処理は継続します。

ディレクトリ構成（主要ファイル）
- src/
  - kabusys/
    - __init__.py
    - config.py  — 環境変数 / 設定管理
    - run_execution.py  — ExecutionEngine 起動スクリプト
    - run_monitoring.py — Monitoring 起動スクリプト
    - ai/
      - __init__.py
      - news_nlp.py       — ニュース NLP（OpenAI 呼び出し）
      - regime_detector.py— レジーム判定（ma200 + マクロセンチメント）
    - monitoring/
      - __init__.py
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py
      - streamlit_dashboard.py
    - execution/
      - order_manager.py
      - reconciler.py
      - ...（OrderRepository / ExecutionEngine 等は該当ファイル群に存在）
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - utils/
      - __init__.py
      - process_priority.py
    - data/  （実行時に作成される）
      - monitoring.db
      - paper_trading.db
      - kabusys.duckdb
      - kill.flag
      - stop_requested.flag
      - execution.pid

開発者向けメモ
- DuckDB クエリは conn.execute(...).fetchall() 形式で使われます。prices_daily / raw_financials / raw_news 等のテーブルに依存するため、研究機能のテストではダミーデータを用意してください。
- モジュールの多くは外部リソースアクセスを内包します（OpenAI, kabu API）。ユニットテストでは該当関数をモック化することを推奨します（コード中にも patch を想定した設計の箇所があります）。
- Settings は起動時に未設定の必須変数があると ValueError を投げます。開発時は .env を準備してください。

ライセンス / バージョン
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（現行: 0.1.0）。

問い合わせ / 貢献
- バグや改善提案は Issue を作成してください。プルリクエストは歓迎します。テスト・lint を整備してから PR を送るとマージがスムーズになります。

以上。README に不足している点や、特定機能（例: ExecutionEngine の詳細設定・OrderRepository のスキーマ等）について追加ドキュメントが必要であれば教えてください。