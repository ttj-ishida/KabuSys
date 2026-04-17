README
======

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を目的とした小規模なシステム群です。本リポジトリは以下の主要機能を含みます:

- 実行エンジン（ExecutionEngine）の起動・発注管理・復旧ロジック
- 監視コンポーネント（System / Trade / Risk）のポーリングとログ保存
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算・リスク調整）
- リサーチ（ファクター計算・特徴量解析）
- AI 支援モジュール（ニュース NLP によるセンチメント評価、レジーム判定）
- 運用ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）

設計方針としては「副作用を最小化した純粋関数」「DB/外部API 呼び出しの明確な分離」「ルックアヘッドバイアス回避（日時参照の制約）」などを採用しています。

主な機能一覧
------------
- Execution
  - Execution エンジン起動スクリプト: run_execution.py
  - Broker クライアントを抽象化し paper_trading 環境時は MockBroker を使用（DB 分離）
  - 発注状態管理、リコンシリエーション（再起動時の自動復旧）
  - リスク管理（最大ポジション比率、利用率、回路遮断等のパラメータ）

- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor によるポーリング監視
  - 監視ログの永続化（SQLite）: system_status, trade_logs, positions, risk_logs, dashboard
  - KillSwitch（ドローダウンやポジション上限を検知すると Execution を停止するフラグ生成）
  - LINE によるアラート送信（AlertManager）
  - Streamlit ダッシュボード（read-only）: monitoring/streamlit_dashboard.py

- Research / Portfolio
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算・IC 計算・特徴量統計
  - 候補選定、等重・スコア重み付け、セクターキャップ、レジーム乗数、ポジションサイズ計算

- AI
  - news_nlp: raw_news を LLM（OpenAI）でセンチメント化して ai_scores に書き込み
  - regime_detector: ETF(1321) の MA とマクロニュースの LLM スコアを合成して市場レジーム判定

- Tools
  - Paper Trading 検証レポート生成スクリプト: kabusys.tools.paper_verification_report

セットアップ手順
----------------

前提
- Python 3.10 以上（型ヒントで | 演算子を使用しているため）
- OS: Linux / macOS / Windows のいずれでも動作するが一部機能（CPU affinity 等）は制限あり

1. リポジトリをクローン・移動
   - プロジェクトルートに移動（README のあるディレクトリ）

2. 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール（例）
   - pip install duckdb psutil requests openai streamlit
   - （プロジェクトで requirements.txt を用意する場合は pip install -r requirements.txt）

4. 環境変数 / .env
   - プロジェクトルートの .env または .env.local から自動読み込みします（デフォルト）。
   - 自動読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
   - 必須環境変数の例:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - OPENAI_API_KEY (AI モジュールを使う場合必須)
   - 任意かつ重要な設定:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（paper_trading 環境時）
     - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定挙動）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（LINE 通知）
     - LOG_LEVEL

   サンプル .env 内容:
   ```
   KABUSYS_ENV=development
   SQLITE_PATH=data/monitoring.db
   DUCKDB_PATH=data/kabusys.duckdb
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=...
   JQUANTS_REFRESH_TOKEN=...
   ```

使い方
------

1. 監視ループ起動（Monitoring）
   - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
   - 監視は常に settings.sqlite_path（本番監視 DB）を使用します（KABUSYS_ENV に依存しない）。
   - 起動コマンド:
     - python -m kabusys.run_monitoring
   - 停止:
     - プロセスに KeyboardInterrupt を送るか、プロジェクトルートの data/stop_requested.flag を作成するとループは検知して終了します。

2. 実行エンジン起動（ExecutionEngine）
   - KABUSYS_ENV が paper_trading の場合、MockBroker を使用し PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）に記録します（本番 DB と分離）。
   - 起動コマンド:
     - python -m kabusys.run_execution
   - 停止:
     - data/stop_requested.flag を作成するとエンジンは安全に停止を試みます。
   - 実行時に data/execution.pid に PID が書き込まれます。古い PID が残っていてプロセスが存在しない場合は stale PID を検知して削除します。

3. Paper Trading 検証レポート
   - コマンド:
     - python -m kabusys.tools.paper_verification_report
     - 期間指定例:
       python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     - DB 指定:
       --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

4. Streamlit ダッシュボード（監視可視化）
   - 起動:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - read-only で monitoring DB を読み取ります。DB が存在しない場合はエラーを表示します。

5. AI 関連（ニュース NLP / レジームスコア）
   - OpenAI API キーが必要です（OPENAI_API_KEY 環境変数または関数引数で指定）。
   - ニューススコアリング:
     - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=...)
   - レジーム判定:
     - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)
   - これらは DuckDB コネクションを受け取り、ai_scores / market_regime テーブル等へ書き込みます。

重要なランタイム挙動
-------------------
- .env 自動ロード:
  - プロジェクトルート（.git または pyproject.toml を基準）から .env を読み込みます。.env.local があれば上書きします。ただし既存の OS 環境変数は保護されます。
- Monitoring DB 初期化:
  - run_monitoring と run_execution のいずれも起動時に init_monitoring_db() を呼び、必要なテーブルと簡易マイグレーション（カラム追加）を行います（冪等）。
- Kill / Stop フラグ:
  - kill.flag（Settings.kill_flag_path：デフォルト data/kill.flag）は KillSwitch が書き込む停止要求専用のファイルです（ExecutionEngine を停止させるために外部ツールが書き込む想定）。
  - stop_requested.flag（data/stop_requested.flag）は run_monitoring / run_execution のループ停止用フラグとして利用されます。
- プロセス優先度:
  - 起動時に set_process_priority("high") を呼んで優先度を上げようとします（権限がない場合は警告を出して継続）。

ディレクトリ構成
----------------
以下は主要ファイル・モジュールの概観（src/kabusys 以下）:

- __init__.py
  - バージョン定義など

- config.py
  - 環境変数読み込みロジックと Settings クラス。.env 自動ロード、必須キーチェックを実装。

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト。

- run_execution.py
  - ExecutionEngine 起動スクリプト。paper_trading モードでの DB 分離と MockBroker 利用。

- ai/
  - news_nlp.py — ニュースを LLM でスコアリングし ai_scores に保存
  - regime_detector.py — 市場レジーム判定と market_regime 書込

- monitoring/
  - monitoring_db.py — SQLite 用の永続化 API（テーブル作成・読み書き）
  - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/実行プロセス監視
  - trade_monitor.py — 滞留注文・約定異常監視
  - risk_monitor.py — ドローダウン・ポジション上限監視とリスクイベント記録
  - kill_switch.py — フラグファイルによる停止制御
  - alert_manager.py — LINE への通知送信
  - monitoring_engine.py — 各 Monitor を束ねる実行ループ
  - streamlit_dashboard.py — Streamlit による可視化

- execution/
  - order_manager.py, reconciler.py, order_repository.py, execution_engine.py, broker_factory など
  - 発注ロジック・リポジトリ・復旧ロジックを含む

- portfolio/
  - portfolio_builder.py — 候補選定・重み付け
  - position_sizing.py — 株数決定・丸め・aggregate cap
  - risk_adjustment.py — セクターキャップ・レジーム乗数

- research/
  - factor_research.py — Momentum/Volatility/Value 計算（DuckDB 使用）
  - feature_exploration.py — 将来リターン・IC・統計サマリー

- tools/
  - paper_verification_report.py — Paper Trading の運用検証レポート生成

- utils/
  - process_priority.py — クロスプラットフォームのプロセス優先度 / CPU affinity ユーティリティ

データディレクトリ（デフォルト）
- data/kabusys.duckdb (DuckDB)
- data/monitoring.db (監視 SQLite)
- data/paper_trading.db (paper_trading 用 SQLite)
- data/execution.pid, data/stop_requested.flag, data/kill.flag

追加メモ / 推奨
---------------
- 本番運用時は KABUSYS_ENV=live を設定し、適切な API キー・パスワード管理・ログ設定を行ってください。
- Paper Trading の検証は paper_trading 環境で分離 DB を使って実行してください。
- OpenAI 等の API 呼び出しを利用する機能はネットワークエラーや API 制限に耐えるように設計されていますが、API キー・コストに注意して運用してください。
- 開発時は LOG_LEVEL=DEBUG を指定すると内部のデバッグログが出力されます。

ライセンス / 貢献
-----------------
（ここにライセンス情報や貢献ルールを記載してください。リポジトリに該当ファイルがあれば参照を追加してください。）

問い合わせ
---------
問題報告や質問はリポジトリの issue を使用してください。