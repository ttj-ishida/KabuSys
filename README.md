KabuSys — README
=================

概要
----
KabuSys は日本株の自動売買・調査・監視を目的とした Python パッケージです。本プロジェクトは以下の主要領域を含みます。

- 実取引／Paper Trading 用の ExecutionEngine（発注管理、リスク管理、リコンシリエーション）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算・セクター制限）
- 研究用モジュール（ファクター計算、特徴量探索、IC 等）
- AI モジュール（ニュースを LLM でスコアリング、レジーム判定）
- 監視（プロセス・リソース・注文滞留・ドローダウン監視）、および Streamlit ダッシュボード
- 運用支援ツール（Paper Trading 検証レポート生成 等）

主な特徴
--------
- ExecutionEngine と Monitoring はプロセス優先度設定（高優先）で起動
- Paper Trading と本番を完全に分離（デフォルトで別 SQLite ファイルを使用）
- DuckDB を使ったファクター計算・リサーチ（prices_daily 等のテーブル参照）
- OpenAI（gpt-4o-mini 等）を使ったニュースセンチメント & マクロセンチメント統合によるレジーム判定
- SQLite（monitoring.db）に監視ログを永続化。DB のスキーマ自動作成・マイグレーション対応
- LINE Push を用いたアラート配信（任意）
- Streamlit で稼働状況を可視化

セットアップ
-----------
1. Python バージョン
   - Python 3.10 以上（PEP 604 の型ヒント (|) などを使用）

2. 依存パッケージ（一例）
   - duckdb
   - psutil
   - requests
   - openai
   - streamlit
   - （環境によって他パッケージが必要になる場合があります）

   例:
   ```
   pip install duckdb psutil requests openai streamlit
   ```

   プロジェクトに requirements.txt がある場合はそれを使用してください:
   ```
   pip install -r requirements.txt
   ```

3. 環境変数 / .env
   - Settings クラスは .env/.env.local ファイルまたは環境変数を読み込みます。
   - 自動読み込みはプロジェクトルート（.git または pyproject.toml がある場所）を基準に行われます。
   - 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

   主要な環境変数（抜粋）
   - KABUSYS_ENV: 起動環境（development / paper_trading / live）
     - paper_trading の場合、MockBrokerClient を使用し、デフォルト DB は data/paper_trading.db
   - OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時に必須）
   - JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須の箇所あり）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須の箇所あり）
   - PAPER_FILL_MODE: paper_trading 時の約定挙動（instant | partial | never | reject）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
   - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
   - PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
   - KILL_FLAG_PATH: Kill Switch フラグ（デフォルト: data/kill.flag）
   - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）。1 未満の値は無効扱いされデフォルトにフォールバック。
   - LOG_LEVEL, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT 等のしきい値も設定可能
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（設定がない場合は通知は行われずログのみ）

   簡単な .env 例:
   ```
   KABUSYS_ENV=development
   OPENAI_API_KEY=sk-...
   SQLITE_PATH=data/monitoring.db
   DUCKDB_PATH=data/kabusys.duckdb
   ```

使い方（起動・実行コマンド）
--------------------------

- 監視ループ起動（SystemMonitor をポーリング）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト: 60）
  ```
  python -m kabusys.run_monitoring
  ```
  あるいは環境変数指定例:
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- 実行エンジン（ExecutionEngine）起動
  - Paper Trading に切り替える場合:
  ```
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```
  - 本番（live）や development 環境でも同様に KABUSYS_ENV を設定します。
  - Execution 起動時、プロセス優先度を「high」に設定します（成功しない場合は警告が出ます）。

- Streamlit 監視ダッシュボード
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - --db オプションで読み取り専用で DB を指定可能（デフォルト: data/monitoring.db）

- Paper Trading 検証レポート生成ツール
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - --db オプションで PAPER_TRADING_SQLITE_PATH を上書き可能

- AI モジュール（ニューススコアリング / レジーム判定）
  - OpenAI API キーを環境変数 OPENAI_API_KEY に設定してから呼び出します。
  - 例（スクリプトから直接呼ぶ）:
    from kabusys.ai import score_news
    # DuckDB の接続オブジェクトを作り score_news(conn, target_date) を呼ぶ
  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    # DuckDB 接続と target_date を渡して市場レジーム判定・DB 書き込みを行えます

重要な運用点
------------
- Monitoring は KABUSYS_ENV に依存せず、常に本番用 sqlite_path（デフォルト data/monitoring.db）を使用します。
- ExecutionEngine が paper_trading の場合、Paper Trading 用 SQLite（data/paper_trading.db）に記録され、本番 DB とは完全に分離されます。
- PID ファイル（デフォルト data/execution.pid）を使って ExecutionEngine の稼働有無を監視／検出します。SystemMonitor は stale PID を検出した場合に削除し、ログに残します。
- Kill Switch: RiskMonitor が閾値を超えた場合（ドローダウンやポジション上限など）に data/kill.flag を書き込んで ExecutionEngine に停止シグナルを送ります。flag の既存チェック・クリアは KillSwitch が担当します。
- init_monitoring_db() はテーブル作成と簡易マイグレーション（列追加）を行います。既存 DB に対して安全に何度でも呼べます（冪等）。

ディレクトリ構成（主要ファイル）
------------------------------
以下は主要なソース配置（src/kabusys 以下）。実際のリポジトリでは pyproject.toml 等がプロジェクトルートにあります。

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / .env ロードと Settings クラス
  - run_monitoring.py             — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート生成ツール
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュースを LLM でスコアリングして ai_scores へ
    - regime_detector.py           — マクロ + MA200 を使った市場レジーム判定
  - monitoring/
    - __init__.py
    - monitoring_db.py            — SQLite 永続化層（テーブル作成 / MonitoringDB クラス）
    - system_monitor.py           — CPU/Memory/Disk/プロセス/データ鮮度の監視
    - trade_monitor.py            — 注文滞留・約定異常監視
    - risk_monitor.py             — ドローダウン・ポジション上限監視
    - kill_switch.py              — kill.flag 管理
    - alert_manager.py            — LINE 通知
    - monitoring_engine.py        — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py      — Streamlit ダッシュボード
  - portfolio/
    - __init__.py
    - portfolio_builder.py        — 候補選定・重み計算
    - risk_adjustment.py          — セクターキャップ・レジーム乗数
    - position_sizing.py          — 株数計算・スケールダウンロジック
  - research/
    - __init__.py
    - factor_research.py          — Momentum / Volatility / Value 等のファクター計算
    - feature_exploration.py      — 将来リターン / IC / 統計サマリー
  - execution/
    - order_manager.py           — OrderManager（発注ワークフロー）
    - reconciler.py              — 起動時リコンシリエーション（Order / Position 突合）
    - ...（Broker クライアントや OrderRepository 等の実装がここに含まれます）
  - utils/
    - __init__.py
    - process_priority.py        — プロセス優先度 / CPU affinity ユーティリティ

開発・拡張メモ
---------------
- DuckDB を使った分析モジュールは SQL と Python を組み合わせて実装しており、大量データに対して高速に処理できます。
- AI モジュールは OpenAI の Chat Completions（JSON Mode）を前提に実装されています。API レスポンスに対する堅牢なバリデーションとリトライロジックを備えています。
- ポートフォリオ構築関係は純粋関数群として実装されており、ユニットテストが書きやすい構造になっています。
- MonitoringDB は読み書きのみ（ビジネスロジック無し）で設計されているため、他コンポーネントから容易に利用できます。

よくある質問（FAQ）
------------------
Q: Paper Trading と本番の DB は混ざりますか？
A: いいえ。KABUSYS_ENV=paper_trading を指定すると paper_sqlite_path（デフォルト data/paper_trading.db）へ記録され、本番 sqlite_path とは分離されます。

Q: MONITOR_POLL_INTERVAL を 0 に設定してもよいですか？
A: 0 以下は無効です。1 未満の値や非整数はデフォルトの 60 秒にフォールバックします（ログに警告が出ます）。

Q: OpenAI キーが無いと何ができませんか？
A: news_nlp（ニューススコアリング）や regime_detector（レジーム判定）は OpenAI API を使うため、API キーが必要です。キーが無い場合、これらの機能は実行できませんが、監視・実行エンジン等の他機能は動作します（API 呼び出し箇所は例外やフォールバック処理を持たせています）。

サポート・貢献
--------------
バグ報告や機能リクエスト、プルリクエストはリポジトリの Issue / Pull Request を通してください。開発にあたってはユニットテスト（特に純粋関数群）を重視してください。

付記
----
本 README はコードベースに含まれる docstring と実装を基に作成しています。運用前に .env の設定、DB の初期化（data ディレクトリ作成等）および必要な外部 API キーの準備を行ってください。