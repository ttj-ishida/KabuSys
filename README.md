KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買／リサーチ／監視コンポーネント群を含むプロジェクトです。  
主要機能は以下の通り：

- 注文発行・状態管理を行う ExecutionEngine（本番 / ペーパートレード対応）
- 監視（System / Trade / Risk）とアラート（LINE Push）
- モニタリング DB（SQLite）と分析用 DuckDB
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制限）
- リサーチ用ファクター計算（モメンタム、バリュー、ボラティリティ）および特徴量解析
- ニュース NLP（OpenAI）を使った銘柄センチメント評価 / 市場レジーム判定
- ペーパートレード検証レポート出力ツール
- Streamlit ベースの監視ダッシュボード

機能一覧
--------
- 環境モード（KABUSYS_ENV）: development / paper_trading / live
  - paper_trading モードではブローカー呼び出しは Mock 実装を使用し、paper_trading 用 SQLite に記録（本番 DB と完全分離）
- Execution:
  - 注文作成 → ブローカー送信 → 状態同期（Reconciler による再起動時の自動復旧）
  - リスク管理（Position limit / Drawdown 等）
- Monitoring:
  - SystemMonitor: CPU/メモリ/Disk/プロセス死活・データ鮮度監視
  - TradeMonitor: 滞留注文・約定価格の異常検出
  - RiskMonitor: ドローダウンやポジション上限の監視とログ化
  - KillSwitch: 条件で flag ファイルを書き ExecutionEngine に停止シグナルを送信
  - AlertManager: LINE Messaging API による通知（クールダウン管理）
  - Streamlit ダッシュボード（読み取り専用で監視状態を表示）
- Research / AI:
  - DuckDB を用いたファクター計算（momentum/value/volatility）
  - 将来リターン・IC 計算、統計サマリ
  - news_nlp: OpenAI でニュースをまとめ銘柄ごとにセンチメントスコア化（ai_scoresへ保存）
  - regime_detector: ETF の MA200 とマクロニュースの LLM センチメントを合成して市場レジーム判定
- Utilities:
  - プロセス優先度 / CPU affinity 設定ユーティリティ（psutil ベース）
  - .env 自動読み込み（プロジェクトルートの .env / .env.local、OS env を上書きしない仕組み）
  - ペーパートレード検証レポート生成スクリプト（tools/paper_verification_report.py）

セットアップ手順
--------------
前提: Python 3.10 以上（typing の一部表記に依存）を想定しています。

1. リポジトリをクローンし、プロジェクトルートへ移動
   ```
   git clone <repo_url>
   cd <repo_root>
   ```

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   リポジトリに requirements.txt が無い場合は下記パッケージをインストールしてください（例）:
   ```
   pip install duckdb psutil openai requests streamlit
   ```
   実行環境に応じて他の依存が必要になる場合があります。

4. 環境変数 (.env) を用意
   プロジェクトルートに .env（または .env.local）を置くと自動で読み込まれます。主要な環境変数例:

   - KABUSYS_ENV=development|paper_trading|live
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - OPENAI_API_KEY=...
   - LINE_CHANNEL_ACCESS_TOKEN=...
   - LINE_USER_ID=...
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   - PAPER_FILL_MODE=instant|partial|never|reject
   - MONITOR_POLL_INTERVAL=60
   - LOG_LEVEL=INFO
   - PID_FILE_PATH=data/execution.pid
   - KILL_FLAG_PATH=data/kill.flag

   .env 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。

5. データディレクトリの作成（必要に応じて）
   ```
   mkdir -p data
   ```

使い方
------

- ExecutionEngine を起動する（本番/開発共通）
  - paper_trading モードでは PAPER_TRADING_SQLITE_PATH に書き込まれ、本番 DB とは分離されます。
  ```
  python -m kabusys.run_execution
  ```
  注意: 実行開始時にプロセス優先度を "high" に設定します（psutil 権限の制約により失敗する場合あり）。

- Monitoring（ポーリング）を起動する
  - MONITOR_POLL_INTERVAL 環境変数でポーリング秒数を変更可能（デフォルト 60 秒）。
  ```
  python -m kabusys.run_monitoring
  ```

- Streamlit ダッシュボード（監視 UI）
  - read-only モードで SQLite を開くため、監視データがあることを確認してください。
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- ペーパートレード検証レポート（コマンドライン）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または DB を明示:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI / リサーチ機能呼び出し（プログラムから）
  - news_nlp.score_news(conn, target_date, api_key=None) — DuckDB 接続を渡して実行
  - regime_detector.score_regime(conn, target_date, api_key=None)

  これらはライブラリ関数として呼び出す設計です。OpenAI API キーは引数か OPENAI_API_KEY 環境変数で指定します。

主要な環境設定の説明
-------------------
- KABUSYS_ENV
  - development / paper_trading / live のいずれか。Settings クラスで検証されます。
  - paper_trading 時は MockBroker を使用し、paper_trading 用の SQLite に記録します。

- PAPER_FILL_MODE
  - paper_trading 時の注文約定動作を制御: instant | partial | never | reject
  - 不正値は ValueError を発生させます。

- MONITOR_POLL_INTERVAL
  - Monitoring のポーリング間隔（秒）。0 以下や不正値はデフォルト 60 秒へフォールバック。

- PID / Kill flag
  - PID_FILE_PATH: ExecutionEngine が起動時に書く PID ファイルのパス（監視でプロセス死活判定に使用）
  - KILL_FLAG_PATH: KillSwitch が書き込む flag ファイル。存在すると ExecutionEngine は停止シグナルを受け取る運用想定。
  - kill flag を起動時に自動クリアするかは Settings.kill_flag_clear_on_start により制御可能。

- DB パス
  - DUCKDB_PATH: DuckDB（分析用）
  - SQLITE_PATH: 監視ログ用 SQLite（monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（分離用）

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                    — 環境変数 / .env の取り扱いと Settings
- run_execution.py             — ExecutionEngine 起動スクリプト
- run_monitoring.py            — SystemMonitor ポーリング起動スクリプト
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート
- execution/
  - order_manager.py
  - reconciler.py
  - ... (broker_factory, order_repository, execution_engine 等)
- monitoring/
  - monitoring_db.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py
  - monitoring_engine.py
  - streamlit_dashboard.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- ai/
  - news_nlp.py
  - regime_detector.py
- data/ (想定されるデータ配置: data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db)
- utils/
  - process_priority.py

運用上の注意点 / 補足
---------------------
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に行われます。CI／テスト等で自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Monitoring は環境にかかわらず本番用 sqlite_path を参照する設計の箇所があります。paper_trading を完全に分離したい処理では paper_sqlite_path を利用してください（run_execution は環境に応じて切り替えます）。
- OpenAI など外部 API の呼び出しはフェイルセーフを備えており、API エラー時は部分的にスキップして継続する設計です。ただし API キーは必須の機能（news_nlp / regime_detector）があります。
- process priority / cpu affinity の設定は psutil の権限に依存します。権限不足時は警告を出してスキップします。
- DuckDB や SQLite 側のテーブルスキーマ変更（マイグレーション）は init_monitoring_db 等にてある程度フォールバック／互換処理を含めていますが、バックアップを取ってから運用を開始することを推奨します。

開発 / 貢献
------------
- 新しい機能やバグ修正を行う場合は、まずローカルでユニットテストを追加・実行してください（テストフレームワークは任意です）。
- 環境変数や DB パスは .env / data ディレクトリでローカルに分離することで、本番データへの影響を避けてください。
- OpenAI を利用する機能をテストする場合は、API 呼び出し部をモック（unittest.mock.patch）して外部通信を行わない形でのテストができます（既に呼び出しラッパー関数を分離しています）。

ライセンス / 著作権
------------------
（リポジトリの LICENSE ファイルに従ってください）

問い合わせ
----------
不明点や実運用の相談はリポジトリの Issue またはプロジェクト内の担当へご連絡ください。

以上が README の概要です。必要であれば、実行例・.env.example のテンプレートや想定される requirements.txt を追記します。どの情報を追加しますか？