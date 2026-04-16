# KabuSys — README (日本語)

このリポジトリは日本株自動売買システムのモジュール群です。  
本 README ではプロジェクト概要、主な機能、セットアップ手順、使い方、ディレクトリ構成を簡潔にまとめます。

注意: 実行には外部ライブラリ（duckdb, psutil, requests, openai, streamlit など）や各種 API キーが必要です。AI 関連機能を使う場合は OpenAI API キーが必須です。

---

概要
----
KabuSys は日本株の自動売買を想定したパイプラインです。主要コンポーネントは以下の通りです。

- Execution: 注文生成、注文管理、ブローカーとの同期（実運用 / ペーパートレードを分離）
- Monitoring: システム状態 / 注文状況 / リスク監視、監視ログの永続化（SQLite）
- Research: ファクター計算、将来リターン、IC 計算などの研究向けモジュール（DuckDB を利用）
- AI: ニュース NLP によるセンチメント評価、マクロセンチメントを用いた市場レジーム判定
- Tools: ペーパートレードの検証レポート生成や簡易ダッシュボード（Streamlit）

設計上の特徴:
- DB: DuckDB（時系列ファクター等）と SQLite（監視ログ / 注文ログ）を併用
- 環境分離: KABUSYS_ENV に応じて paper_trading（ペーパー）と live（本番）を区別
- フェイルセーフ: API 呼び出し失敗時は安全側にフォールバックし、致命的な例外を抑える実装が施されています

主な機能一覧
--------------
- Execution
  - ExecutionEngine（起動・セッション実行）
  - OrderManager（注文生成・状態遷移）
  - Reconciler（起動時の自動復旧・ブローカー同期）
  - RiskManager（発注前リスク判定）
- Monitoring
  - SystemMonitor（CPU / メモリ / ディスク・プロセス監視、データ鮮度チェック）
  - TradeMonitor（滞留注文・約定異常検出）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - MonitoringEngine（複数モニタのポーリング、KillSwitch 評価）
  - AlertManager（LINE へ通知）
  - Streamlit ダッシュボード（監視データ可視化）
- Research
  - ファクター計算 (momentum / volatility / value)
  - 将来リターン・IC / 統計サマリ機能
- AI
  - news_nlp: raw_news を LLM（gpt-4o-mini など）へ渡し銘柄別センチメントを ai_scores に書き込む
  - regime_detector: MA と LLM センチメントを合成して market_regime を判定
- Tools
  - paper_verification_report: ペーパートレード DB を解析して Pass/Fail レポートを出力

セットアップ（ローカル）
---------------------
前提: Python 3.9+（型ヒント等に依存）。環境に合わせて仮想環境を作成することを推奨します。

1. リポジトリをクローン / 取得
   - git clone ... またはソースを配置

2. 仮想環境（例: venv）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール（例）
   - pip install duckdb psutil requests openai streamlit
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

4. 環境変数の設定
   - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 主要な環境変数（例・必須）:
     - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（使用箇所がある場合）
     - KABU_API_PASSWORD: kabuステーション API のパスワード
     - OPENAI_API_KEY: OpenAI API キー（AI 機能を使用する場合）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（paper_trading 時に使用、デフォルト: data/paper_trading.db）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager 用
     - PAPER_FILL_MODE: ペーパートレードの約定挙動（instant/partial/never/reject）
     - LOG_LEVEL: ログレベル（DEBUG/INFO/...）
   - サンプル .env（簡易）
     - KABUSYS_ENV=development
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - OPENAI_API_KEY=sk-...
     - KABU_API_PASSWORD=...
     - JQUANTS_REFRESH_TOKEN=...
     - LINE_CHANNEL_ACCESS_TOKEN=
     - LINE_USER_ID=

5. データディレクトリ
   - data/ 以下に DB ファイルやフラグファイルが作成されます:
     - data/kabusys.duckdb
     - data/monitoring.db
     - data/paper_trading.db
     - data/kill.flag（KillSwitch による停止指示）
     - data/stop_requested.flag（run_* スクリプトの外部停止用）
     - data/execution.pid（ExecutionEngine の PID 管理）

使い方（起動・主要コマンド）
----------------------------

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - 補足: KABUSYS_ENV=paper_trading にすると MockBroker を利用し、PAPER_TRADING_SQLITE_PATH に書き込まれます。
  - 起動前に data/kill.flag があると起動を行いません。kill.flag は KillSwitch 用の停止指示ファイルです。

- 監視ループ（SystemMonitor を単体で実行する場合）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定できます（デフォルト 60 秒）。
  - 監視は常に本番用 sqlite_path（Settings.sqlite_path）を使用します（環境にかかわらず）。

- Streamlit ダッシュボード（監視状況の可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で開きます（起動中の MonitoringEngine が DB を更新します）。

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH より優先）

- AI 関連（スクリプト API）
  - ニューススコアリング（プログラムから呼ぶ）
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")  # api_key を渡すか OPENAI_API_KEY を設定
  - レジーム判定
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

運用に関する注意
----------------
- KABUSYS_ENV が paper_trading の場合、Execution はペーパートレード専用 DB（PAPER_TRADING_SQLITE_PATH）へ記録します。本番 DB と分離されます。
- Monitoring は常に Settings.sqlite_path（デフォルト data/monitoring.db）を使用します（ログ・監視は一元管理）。
- KillSwitch / kill.flag を書くことで ExecutionEngine に停止を指示できます。KillSwitch は主に RiskMonitor の判定結果でフラグを作ります。
- PID ファイルや stop_requested.flag により外部からの停止検知や stale PID の検出が行われます。
- OpenAI など外部 API はレート制限・障害を考慮してリトライや安全フォールバックが実装されていますが、API キーの保護とコスト管理は利用者側で行ってください。

主要ファイル・ディレクトリ構成
------------------------------
（src/kabusys 以下を抜粋して説明）

- src/kabusys/__init__.py
  - パッケージ定義（version 等）

- src/kabusys/config.py
  - 環境変数のロード / Settings クラス（アプリ設定取得）
  - .env 自動読み込み（プロジェクトルート検出）機構を持つ

- src/kabusys/run_execution.py
  - ExecutionEngine を立ち上げるスクリプト（thread ベースの実行）

- src/kabusys/run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト

- src/kabusys/execution/
  - broker_factory, execution_engine, order_manager, order_repository, reconciler, risk_manager など
  - 注文フロー・ブローカー連携・リコンシリエーションの実装場所

- src/kabusys/monitoring/
  - monitoring_db.py: SQLite テーブル初期化・読み書きラッパ
  - system_monitor.py, trade_monitor.py, risk_monitor.py: 各種監視ロジック
  - monitoring_engine.py: 複数モニタの組み合わせ・ポーリング
  - alert_manager.py: LINE push 実装
  - kill_switch.py: kill.flag の生成・評価
  - streamlit_dashboard.py: Streamlit ダッシュボード

- src/kabusys/research/
  - factor_research.py: momentum/volatility/value 等のファクター計算（DuckDB）
  - feature_exploration.py: 将来リターン / IC / 統計サマリ
  - __init__.py: 研究用 API エクスポート

- src/kabusys/ai/
  - news_nlp.py: raw_news を LLM に送り銘柄別スコアを ai_scores に書き込む
  - regime_detector.py: マクロニュース＋MA200 を合成して market_regime を計算

- src/kabusys/portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py: ポートフォリオ構築ロジック

- src/kabusys/tools/
  - paper_verification_report.py: ペーパートレード検証レポート
  - __init__.py

- src/kabusys/utils/
  - process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティ

補足（重要な挙動）
-----------------
- Settings クラスにより KABUSYS_ENV, LOG_LEVEL, DB パス等を集中管理しています。値が不正な場合は ValueError を投げます。
- .env のパースはシェル風記法に対応（export 付き、クォート、コメントなど）。
- MonitoringDB.init_monitoring_db() は冪等でテーブルを作成し、簡単なマイグレーション（カラム追加）にも対応しています。
- AI モジュールは OpenAI SDK（OpenAI class）経由で Chat Completions を呼び出す設計です。レスポンスの検証やリトライ戦略が実装されています。
- process_priority.set_process_priority("high") を run_* スクリプト先頭で呼び出しており、可能ならプロセス優先度を上げようとします（権限不足時は警告でスキップ）。

ライセンス・貢献
----------------
この README ではライセンス情報を示していません。実運用や公開時は適切な LICENSE をリポジトリに追加してください。  
バグ報告や改善提案は issue / pull request を送ってください。

---

この README はコード内の docstring と実装に基づいてまとめています。実際に運用する際は環境固有の設定（API キー、DB パス、LINE トークン等）を必ず確認してください。必要であれば README をローカル運用向けにカスタマイズします。必要な追加情報（例: requirements.txt の提案、docker-compose 例、運用チェックリストなど）があれば教えてください。