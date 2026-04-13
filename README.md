KabuSys — README
=================

概要
----
KabuSys は日本株の自動売買・研究・監視を目的とした軽量なコードベースです。
主な機能は以下の通りです。

- シグナル → ポジション構築 → 注文発行の実行エンジン（ExecutionEngine 周辺）
- 注文状態のリコンシリエーション（再起動時の自動復旧）
- Paper Trading（モックブローカー）による検証環境分離
- 監視サブシステム（System / Trade / Risk Monitor）とアラート送信（LINE）
- kill.flag による外部停止（KillSwitch）
- DuckDB を利用したファクター計算・リサーチ用モジュール
- ニュースを用いた LLM（OpenAI）ベースのニュースセンチメント評価（ai モジュール）
- Paper Trading の検証レポート生成ツール（tools）
- streamlit ベースの監視ダッシュボード

主な機能一覧
-------------
- execution
  - 注文生成／送信／状態同期（OrderManager, Reconciler）
  - リスク管理（RiskManager）
- monitoring
  - システム状態監視（CPU/メモリ/ディスク、データ鮮度）
  - 注文滞留／約定異常検出
  - ドローダウン・ポジション上限監視（RiskMonitor）
  - アラート（LINE）・kill flag 制御
  - SQLite 監視 DB（monitoring_db.py）と Streamlit ダッシュボード
- portfolio
  - 候補選定 / 重み計算 / 単元丸め・ポジションサイズ計算
  - セクター制限やレジーム乗数の適用
- research
  - DuckDB を用いたファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）などの解析ユーティリティ
- ai
  - ニュース集約 → OpenAI によるセンチメントスコア化（score_news）
  - 市場レジーム判定（score_regime）
- tools
  - paper_verification_report: Paper Trading DB を読み検証レポートを出力

動作要件（推奨）
----------------
- Python 3.10+
- 必要な Python パッケージ（例）
  - duckdb
  - psutil
  - requests
  - streamlit (dashboard 実行時)
  - openai (AI 機能使用時)
  - そのほか：標準ライブラリ、sqlite3（標準）

セットアップ手順
----------------

1. リポジトリをクローン / コードを配置
   - ソースは src/kabusys 以下に配置されている想定です。

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Linux/Mac) または .venv\Scripts\activate (Windows)

3. 依存パッケージをインストール
   - 例:
     pip install duckdb psutil requests streamlit openai

   （requirements.txt があれば pip install -r requirements.txt）

4. 環境変数の準備
   - プロジェクトルートに .env（または .env.local）を置くと自動で読み込まれます（既存 OS 環境変数は保護）。
   - 自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

5. 主要な環境変数（代表例）
   - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - paper_trading の場合、実行エンジンは paper DB と MockBroker を使用します。
   - JQUANTS_REFRESH_TOKEN: （必須：J-Quants API を使う場合）
   - KABU_API_PASSWORD: （必須：kabuステーション API を使う場合）
   - OPENAI_API_KEY: OpenAI を使う場合
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知を有効にする場合
   - PAPER_FILL_MODE: instant | partial | never | reject （paper_trading の約定挙動）
   - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
   - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
   - PID_FILE_PATH / KILL_FLAG_PATH / その他しきい値（Settings クラスを参照）

   例 .env（最小例）
   ```
   KABUSYS_ENV=paper_trading
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   JQUANTS_REFRESH_TOKEN=...
   PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   SQLITE_PATH=data/monitoring.db
   DUCKDB_PATH=data/kabusys.duckdb
   LINE_CHANNEL_ACCESS_TOKEN=
   LINE_USER_ID=
   ```

使い方（主要なスクリプト）
-------------------------

- 実行エンジン（ExecutionEngine）を起動
  - 開発/本番/紙トレードを Settings.env で切替えます（KABUSYS_ENV）。
  - 実行:
    python -m kabusys.run_execution
  - 特記事項:
    - 起動時にプロセス優先度が "high" に設定されます（set_process_priority）。
    - KABUSYS_ENV=paper_trading の場合、paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と分離されます。
    - 設定に応じて MockBrokerClient が使われ、PAPER_FILL_MODE による約定挙動が変わります。

- 監視ループを起動（SystemMonitor 単体簡易版）
  - 実行:
    python -m kabusys.run_monitoring
  - オプション:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
    - 監視は常に本番の sqlite_path（Settings.sqlite_path）を使う設計になっています（環境に関係なく）。

- Streamlit ダッシュボード（監視データ可視化）
  - 起動例:
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは監視 DB を読み取り専用で開きます。MonitoringEngine がデータを書き込んでいることが前提です。

- Paper Trading 検証レポート生成
  - 実行:
    python -m kabusys.tools.paper_verification_report
  - 期間指定:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 関連（OpenAI を使った処理）
  - ニューススコアリング:
    - 関数: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
    - API キーは引数または環境変数 OPENAI_API_KEY で指定
  - 市場レジーム判定:
    - 関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

監視と停止（KillSwitch / kill.flag）
-----------------------------------
- KillSwitch は Settings.kill_flag_path（デフォルト data/kill.flag）を用いて ExecutionEngine に停止信号を送ります。
- RiskMonitor 等が条件を満たすと kill.flag ファイルが書かれ、ExecutionEngine 側で検知して安全に停止できます。
- ExecutionEngine 起動時に kill.flag を消去する挙動は Settings.kill_flag_clear_on_start で制御できます。

DB とマイグレーション
---------------------
- 監視用 SQLite（monitoring.db）は init_monitoring_db() によって必要テーブルを冪等で作成します（起動スクリプトが自動で呼び出します）。
- DuckDB は分析・リサーチ用に使用。デフォルトパスは data/kabusys.duckdb。
- Paper Trading 用 SQLite は data/paper_trading.db（KABUSYS_ENV=paper_trading 時に使用される想定）。

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py
- config.py                    — 環境変数/設定読み込みロジック（.env 自動読み込み含む）
- run_execution.py             — ExecutionEngine 起動スクリプト
- run_monitoring.py            — SystemMonitor ポーリングループ起動スクリプト

subpackages / ファイル:
- ai/
  - news_nlp.py                 — ニュースの LLM スコアリング
  - regime_detector.py          — 市場レジーム判定
  - __init__.py
- monitoring/
  - monitoring_db.py            — SQLite 永続化レイヤ（system_status/trade_logs/positions/...）
  - system_monitor.py           — CPU/メモリ/ディスク/データ鮮度監視
  - trade_monitor.py            — 注文滞留・約定異常監視
  - risk_monitor.py             — ドローダウン・ポジション上限監視
  - kill_switch.py              — kill.flag 書き込みロジック
  - alert_manager.py            — LINE 通知
  - monitoring_engine.py        — 各 Monitor を束ねる実行エンジン
  - streamlit_dashboard.py      — Streamlit ダッシュボード
  - __init__.py
- portfolio/
  - portfolio_builder.py        — 候補選定・重み計算
  - position_sizing.py          — 株数決定・丸め・キャップ適用
  - risk_adjustment.py          — セクターキャップ・レジーム乗数
  - __init__.py
- research/
  - factor_research.py          — Momentum/Volatility/Value のファクター計算（DuckDB）
  - feature_exploration.py      — 将来リターン・IC・統計サマリー
  - __init__.py
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
  - __init__.py
- utils/
  - process_priority.py         — プロセス優先度 / CPU affinity ユーティリティ
  - __init__.py
- execution/
  - reconciler.py               — 再起動時の注文・ポジション整合化
  - order_manager.py            — 注文状態遷移の外向き API
  - order_repository.py         — （参照）SQLite に対する注文 CRUD（コードベースに依存）
  - その他 execution 関連ファイル...

補足 / 実運用上の注意
---------------------
- OpenAI / 外部 API を使う機能は API キーが必須です。API 失敗時は多くの箇所でフォールバック（0.0 等）やスキップが実装されていますが、運用前に十分なテストを行ってください。
- process priority / cpu affinity の設定は OS に依存し、権限不足で失敗する場合はログが出てスキップされます。
- Paper Trading（モック）と本番 DB を明確に分離する設計になっていますが、環境変数の設定ミスに注意してください。
- LINE 通知は channel token・user ID が未設定だとログのみでスキップされます。過度な通知を防ぐためにクールダウンを内部で管理しています。

ライセンス
----------
（このコードベースのライセンス情報が別途あればここに記載してください）

以上
----
この README はソースコードのコメント・構成に基づいてまとめています。追加で「デプロイ手順」「CI」「テストの実行方法」などが必要であれば教えてください。