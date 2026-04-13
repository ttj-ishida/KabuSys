KabuSys — 日本株自動売買システム
=============================

概要
----
KabuSys は日本株自動売買のためのミニマルなフレームワークです。本プロジェクトは取引実行・リスク管理・監視・研究（ファクター計算）・ニュース NLP を含む複数コンポーネントで構成されています。  
設計方針として以下を重視しています。

- 本番とテスト（paper trading）を明確に分離する設定
- DuckDB / SQLite を用いたデータ処理と監視ログの永続化
- LLM（OpenAI）を使ったニュースセンチメント・レジーム判定機能（フェイルセーフ実装）
- シンプルな監視エンジンとダッシュボード（Streamlit）

主な機能
--------
- ExecutionEngine 起動と再実行時のリコンシリエーション（reconciler）
- OrderManager を介した注文生成・送信・状態同期
- RiskManager / RiskMonitor によるドローダウン・ポジション上限監視
- MonitoringEngine によるシステム・注文・リスクの定期チェック
- monitoring DB（SQLite）へのログ永続化（system_status / trade_logs / positions / risk_logs / dashboard）
- Streamlit ベースの監視ダッシュボード
- Paper Trading 検証レポート生成ツール（tools.paper_verification_report）
- ファクター計算 / 研究用ユーティリティ（research）
- ニュース NLP（OpenAI）による銘柄単位センチメントスコア生成（ai.news_nlp）
- 市場レジーム判定（ai.regime_detector）

動作環境・前提
--------------
- Python 3.10+（typing の | 記法を使用）
- 必要パッケージ（代表的なもの）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード利用時)
- SQLite（標準ライブラリで利用）
- ネットワークアクセス（ブローカー API / OpenAI / LINE API 利用時）

セットアップ手順
----------------
1. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate (Linux/macOS) または .venv\Scripts\activate (Windows)

2. 必要ライブラリをインストール（例）
   - pip install duckdb psutil requests openai streamlit

   ※ 実際の requirements.txt がある場合はそれを使ってください。

3. 環境変数設定
   - プロジェクトルートに .env/.env.local を置くと自動で読み込まれます（OS 環境変数が優先）。自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
   - 必須（実行モードにより必要性が変わる場合があります）:
     - JQUANTS_REFRESH_TOKEN — J-Quants 用トークン（research 等で必要）
     - KABU_API_PASSWORD — kabuステーション API 用パスワード
   - OpenAI を使う機能を利用する場合:
     - OPENAI_API_KEY — OpenAI API キー（ai.score_news / score_regime で使用）
   - その他主要な環境変数（Settings クラスで扱う）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
     - PAPER_FILL_MODE: paper_trading のマッチング挙動（instant | partial | never | reject）
     - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START など

4. データベース初期化
   - run_monitoring.py や run_execution.py は起動時に監視用テーブルの初期化（init_monitoring_db）を行います。明示的に初期化する場合は簡単な Python スクリプトで init_monitoring_db を呼び出せます。

使い方（実行例）
----------------

- 監視ループを起動（SystemMonitor 単体）
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定できます（デフォルト 60）。
  - 実行例:
    - python -m kabusys.run_monitoring
    - またはパッケージ未インストール/ソースから: python src/kabusys/run_monitoring.py
  - 挙動:
    - プロセス優先度を high に設定
    - monitoring DB（Settings.sqlite_path）へ接続してテーブルを作成
    - DuckDB に接続してデータ鮮度チェックなどを実行

- 実行エンジンを起動（Order 実行）
  - paper_trading モードでは MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に分離して記録します。
  - 実行例:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - python -m kabusys.run_execution  （デフォルトは development または live に応じた挙動）
  - 挙動:
    - プロセス優先度設定、DB 接続、BrokerClient の生成、ExecutionEngine の起動（run_session）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 引数:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH より優先）
  - 出力: 稼働率・注文成功率・送信率・レイテンシ等のサマリと PASS/FAIL 判定

- Streamlit ダッシュボード起動
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードでは dashboard、positions、recent orders、最新 system_status、risk_logs を参照可能（読み取り専用 URI を使用）

- AI（ニュース）スコア生成（プログラムから呼ぶ場合）
  - 例（簡略）:
    - import duckdb
      from kabusys.ai.news_nlp import score_news
      conn = duckdb.connect("data/kabusys.duckdb")
      score_news(conn, target_date=date(2026,4,1), api_key="sk-...")

設定・挙動のポイント
--------------------
- .env 自動ロード
  - プロジェクトルートを .git または pyproject.toml から検出して .env/.env.local を自動読み込みします。
  - OS 環境変数は保護され、.env.local は .env 上書きする挙動になっています。
- KABUSYS_ENV による振る舞い分岐
  - development / paper_trading / live のいずれか。paper_trading 時は実マーケットに影響を与えないよう DB やブローカーを分離します。
- MONITOR_POLL_INTERVAL
  - run_monitoring のポーリング間隔（秒）を環境変数で上書きできます。不正値や 0 以下の値はデフォルト（60秒）にフォールバックします。
- PID / kill flag
  - ExecutionEngine / SystemMonitor 間で PID ファイル management と data/kill.flag を使った停止シグナルをやり取りします。KillSwitch はドローダウンやポジション上限アラート時に kill.flag を書き込みます。

ディレクトリ構成（主要ファイル）
------------------------------
以下は本リポジトリ内の主要なモジュール構成（概要）です。実際のファイル数はさらに多いですが、代表的なファイルを示します。

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / 設定読み込みロジック（.env の自動ロード、Settings クラス）
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading の検証レポート生成
  - ai/
    - __init__.py
    - news_nlp.py — ニュースの LLM スコアリング（ai_scores への書込み）
    - regime_detector.py — 市場レジーム判定（ma200 + マクロセンチメント）
  - monitoring/
    - __init__.py
    - monitoring_db.py — SQLite 用の永続化レイヤ（テーブル作成 / CRUD）
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - trade_monitor.py — 注文滞留 / 約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限チェック
    - kill_switch.py — kill.flag 管理
    - alert_manager.py — LINE Push 通知（クールダウン付き）
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py — Streamlit ダッシュボード（起動スクリプト）
  - execution/
    - order_manager.py — 注文状態遷移・broker 呼び出しラッパ
    - reconciler.py — 再起動時のオーダー・ポジション照合
    - （その他：broker_factory, execution_engine, order_repository, order_record 等を想定）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数算出・キャップ処理
    - risk_adjustment.py — セクター制限・レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value 等のファクター計算（DuckDB 使用）
    - feature_exploration.py — 将来リターン計算・IC・統計サマリ
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

開発メモ / 注意事項
------------------
- DuckDB / SQLite のスキーマ変更は init_monitoring_db 内の冪等処理で一部マイグレーションを行いますが、大きな変更は手動で対応してください。
- OpenAI など外部 API 呼び出しはリトライ・フェイルセーフを組み込んでいます。API キー未設定時は明示的に例外を投げる箇所があります（ai.* の一部）。
- テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して .env 自動ロードを無効化できます。
- 実運用では KABUSYS_ENV=live で動かし、LINE の通知や kill.flag の監視運用を検討してください。

お問い合わせ / 貢献
------------------
この README はコードベースから抽出した主要ポイントをまとめたものです。機能追加・バグ修正・ドキュメント改善は PR を歓迎します。README の補足やチュートリアルが必要であればお知らせください。