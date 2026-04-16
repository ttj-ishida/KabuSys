KabuSys — 日本株自動売買システム
================================

本リポジトリは日本株向けの自動売買／リサーチ／監視コンポーネント群を含むライブラリ兼実行スクリプト群です。
README はソースコード（src/kabusys 以下）をもとに作成しています。

要点
- Python パッケージとして動作（モジュール名: kabusys）
- 実行用スクリプト（ExecutionEngine・Monitoring 等）は python -m kabusys.<module> で起動
- DuckDB/SQLite を利用したローカル DB（時系列データ・監視ログ・paper trading ログ等）
- OpenAI（gpt-4o-mini）を用いたニュース NLP / レジーム判定機能（任意）

機能一覧
- 実行エンジン（ExecutionEngine 起動スクリプト）
  - 本番 / Paper Trading の切替（KABUSYS_ENV）
  - Broker クライアント抽象化、Order 管理、Reconciler によるリコンシリエーション
- 監視（Monitoring）
  - SystemMonitor: CPU / メモリ / ディスク / プロセス生存チェック、データ鮮度チェック
  - TradeMonitor: 滞留注文・約定価格異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視（KillSwitch と組合せ）
  - MonitoringEngine: 各 Monitor を束ねてポーリング、LINE 通知（AlertManager）
  - streamlit ダッシュボード（監視 DB の可視化）
- Portfolio 構築ユーティリティ
  - 候補選択、等金額／スコア加重配分、セクター上限適用、ポジションサイズ決定（丸め等）
- Research（ファクター計算・特徴量探索）
  - momentum / volatility / value 等のファクター計算（DuckDB 上の prices_daily / raw_financials を参照）
  - 将来リターン、IC（Information Coefficient）計算、ファクターサマリ
- AI 関連
  - ニュース NLP（raw_news -> ai_scores へ格納。OpenAI 使用）
  - Regime Detector（ETF MA とマクロ NLP を合成し日次の market_regime を作成）
- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

セットアップ手順（ローカル開発向け）
- 前提
  - Python 3.9+（duckdb / psutil 等ライブラリが必要）
  - sqlite3 は標準モジュール
- 手順（例）
  1. リポジトリをクローン
     - git clone <repo_url>
  2. 仮想環境を作成・有効化
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
  3. 必要パッケージをインストール（プロジェクトに requirements.txt がないため代表的なパッケージを例示）
     - pip install duckdb psutil openai requests streamlit
     - （必要に応じて開発系パッケージを追加）
  4. 環境変数の設定
     - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（読み込みはデフォルトで有効）
     - 自動読み込みを無効化する場合:
       - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  5. データディレクトリ
     - デフォルトでは data/ 以下に DB や PID/flag ファイルを作成します。必要に応じてディレクトリ作成:
       - mkdir -p data

主な環境変数（主要なもの）
- KABUSYS_ENV (development | paper_trading | live) — 動作モード（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト: 60）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を利用する際に必要）
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD — 外部 API 用の必須トークン・パスワード（Settings 参照）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — AlertManager（LINE通知）用
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START など（監視／停止制御関連）

起動・使い方（代表例）
- ExecutionEngine 起動（本番 or paper_trading）
  - デフォルト（development）:
    - python -m kabusys.run_execution
  - Paper Trading モード（MockBroker を使用し paper DB に書く）:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
  - 停止制御:
    - run_execution はプロジェクトルート data/stop_requested.flag を監視します。停止するには stop_requested.flag を作成してください（または KillSwitch により data/kill.flag を作成）。
- Monitoring 起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書きできます（例: export MONITOR_POLL_INTERVAL=30）
- streamlit 監視ダッシュボード
  - 起動例（コード内にも起動方法が記載されています）:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを明示する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
- AI バッチ処理（プログラムから）
  - ニュース NLP スコア付け:
    - Python API: from kabusys.ai.news_nlp import score_news
      - conn = duckdb.connect("data/kabusys.duckdb")
      - score_news(conn, target_date, api_key="YOUR_OPENAI_KEY")
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
      - score_regime(conn, target_date, api_key="YOUR_OPENAI_KEY")
  - 注意: OpenAI API 呼び出しはネットワーク/課金を伴います。APIキーは環境変数 OPENAI_API_KEY に指定するか、関数に直接渡してください。

停止 / Kill 指示
- run_execution / run_monitoring は data/stop_requested.flag の存在を監視して終了します（run_execution は起動時に既にフラグがある場合は起動せず終了）。
- KillSwitch（監視側）は data/kill.flag を書き込み、ExecutionEngine 側での停止トリガーとして使われます。
- ExecutionEngine の PID は data/execution.pid に保存されます（pid ファイルの stale 検出は SystemMonitor が行い、必要に応じて削除・アラートを出します）。

注意点 / 運用メモ
- process priority / CPU affinity
  - 起動時に psutil を使ってプロセス優先度（high/normal/low）を設定します。権限により失敗する場合があります（警告ログのみ）。
- DB マイグレーション
  - monitoring DB は起動時に init_monitoring_db() によりテーブル・必要カラムを作成します（冪等）。
- Paper Trading 分離
  - KABUSYS_ENV=paper_trading の場合、発注情報や実行ログは paper_trading.db に保存され、本番 DB と分離されます（設定でパスを変更可能）。
- LLM 呼び出しの耐障害処理
  - OpenAI 呼び出しはレート制限や 5xx、タイムアウトに対してリトライ実装がありますが、最終的に失敗した場合はフォールバック動作（スコア 0.0 など）で継続する設計です。

ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定読み込みロジック（.env 自動読み込み含む）
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — Monitoring ポーリング起動スクリプト
  - ai/
    - news_nlp.py                — ニュースセンチメント解析（OpenAI 利用）
    - regime_detector.py         — 市場レジーム判定（MA + マクロ NLP）
    - __init__.py
  - monitoring/
    - monitoring_db.py           — 監視用 SQLite 永続化層
    - system_monitor.py          — システム状態・データ鮮度監視
    - trade_monitor.py           — 注文滞留・約定異常監視
    - risk_monitor.py            — ドローダウン / ポジション上限監視
    - kill_switch.py             — kill.flag 書き出し（Execution 停止）
    - alert_manager.py           — LINE 通知ラッパー
    - monitoring_engine.py       — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py     — Streamlit ダッシュボード
  - execution/
    - order_manager.py           — Order 管理（発注フロー）
    - reconciler.py              — 起動時同期・リコンシリエーション
    - ... (broker_factory, execution_engine, order_repository などが存在)
  - portfolio/
    - portfolio_builder.py       — 候補選択・重み計算
    - position_sizing.py         — 株数決定・丸め・資金配分
    - risk_adjustment.py         — セクター上限・レジーム乗数
  - research/
    - factor_research.py         — ファクター計算（momentum/volatility/value）
    - feature_exploration.py     — 将来リターン、IC、統計サマリなど
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト
  - utils/
    - process_priority.py        — psutil を使った優先度 / CPU affinity ユーティリティ
  - data/  (運用時に作成される想定: DB / pid / flag 等を配置)
    - monitoring.db (default)
    - kabusys.duckdb (default)
    - paper_trading.db (paper trading 用 default)
    - execution.pid / kill.flag / stop_requested.flag

開発者向けヒント
- 単体関数群（portfolio / research）には DB 参照を必要としない純粋関数が多く含まれており、ユニットテストが容易です。
- DuckDB 接続を引数にとる research/ai モジュールは I/O を分離しているため、テスト用に小さな DuckDB ファイルを用意して検証できます。
- .env ファイル読み込み:
  - 優先順位: OS 環境変数 > .env.local > .env
  - 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

ライセンス / 責任範囲
- 本 README はコードベースの解析に基づく要約です。実運用では外部 API キー管理、シークレット管理、監視・アラートの確実な設定、PEP8 等のコード品質チェック、テストを必ず行ってください。

もし README に追記して欲しい内容（例: 実際の requirements.txt の生成、systemd 用のユニットファイル例、運用チェックリスト、主要 API の使用例スニペットなど）があれば教えてください。必要に応じて具体的なコマンド例や systemd ユニットのテンプレートも作成します。