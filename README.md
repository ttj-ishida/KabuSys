# KabuSys

日本株向け自動売買システムのコアライブラリ群。シグナル生成・ポートフォリオ構築・発注・監視・レポート生成・研究用ユーティリティを含みます。

以下はこのリポジトリの概要、機能、セットアップと利用方法、ディレクトリ構成の説明です。

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したモジュール群です。主な責務は次のとおりです。

- シグナル・ファクター計算（research/*）
- ポートフォリオ構築、ウェイト計算、ポジションサイズ決定（portfolio/*）
- 発注管理、ブローカー API 抽象化、再同期（execution/*）
- システム稼働監視、リスク監視、アラート（monitoring/*）
- ニュースに対する LLM ベースのセンチメント評価（ai/*）
- Paper Trading 用検証レポートや Streamlit ダッシュボード等の運用ツール（tools/、monitoring/streamlit_dashboard.py）

設計方針として、DB（SQLite / DuckDB）を用いたデータ永続化、外部 API（kabuステーション、J-Quants、OpenAI）を抽象化してテスト可能性を確保しています。

---

## 主な機能一覧

- 発注（ExecutionEngine、OrderManager、BrokerClientFactory）
- 起動時リコンシリエーション（Reconciler）
- リスク管理（RiskManager / RiskMonitor）: ドローダウン監視、ポジション上限等
- 監視（SystemMonitor / TradeMonitor / MonitoringEngine）
  - プロセス生存確認、CPU/メモリ/ディスク使用率、データ鮮度チェック
  - 注文の滞留・約定異常価格検出
- Kill Switch（kill.flag）による安全停止シグナル
- LINE を使ったアラート送信（AlertManager）
- Paper Trading 用の挙動分離（KABUSYS_ENV=paper_trading）と MockBroker
- Paper Trading 検証レポート生成ツール（kabusys.tools.paper_verification_report）
- ニュースの LLM センチメント評価（ai/news_nlp.py）
- 市場レジーム判定（ai/regime_detector.py）
- Research 用ファクター集計（research/*） — DuckDB を利用
- Streamlit ベースの監視ダッシュボード（monitoring/streamlit_dashboard.py）

---

## 要件

- Python 3.10 以降（型注釈で | を使用しているため）
- 主要依存パッケージ（例）
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit
- SQLite（標準 Python 実装で利用可能）

（requirements.txt はリポジトリに含まれていない場合があるため、実行環境に上記ライブラリをインストールしてください。）

例:
- pip install duckdb psutil openai requests streamlit

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境を作成して有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb psutil openai requests streamlit

4. 環境変数設定
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（OS 環境変数が優先）。
   - 自動ロードを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

5. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN — J-Quants トークン（必要に応じて）
   - KABU_API_PASSWORD — kabu API パスワード
   - OPENAI_API_KEY — OpenAI API キー（news_nlp/regime_detector 実行時に必要）
   - KABUSYS_ENV — "development" / "paper_trading" / "live"（デフォルト: development）
   - その他は Settings クラス（kabusys.config.Settings）で確認できます（DUCKDB_PATH、SQLITE_PATH 等）

6. data ディレクトリ
   - 実行時に data/ 配下に SQLite ファイルや PID/flag が作成されます。必要なら事前に作成してください（実行時に mkdir される箇所もあります）。

---

## 主な環境変数（代表）

- KABUSYS_ENV: execution の動作モード。development / paper_trading / live
  - paper_trading の場合、Paper Trading 専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、MockBroker を利用します。
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB データベース（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: Paper Trading の約定挙動（instant/partial/never/reject）
- OPENAI_API_KEY: OpenAI API キー（ai/* で使用）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60。無効値は 60 にフォールバック）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START: 実行管理用設定
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

詳細は kabusys.config.Settings を参照してください。

---

## 使い方（実行例）

基本的に Python のモジュール実行（-m）で起動します。

1. 監視ループ（Monitoring）
   - 目的: システム状態・注文状態・リスクを定期的にチェックしてログ/アラート/kill flag評価を行う
   - 実行:
     - python -m kabusys.run_monitoring
   - 補足:
     - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定可能（デフォルト 60 秒）。
     - run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用します。
     - 停止はプロジェクトルート/data/stop_requested.flag を作成することで検知されます（存在するとループを終了）。

2. Execution（発注エンジン）
   - 目的: ExecutionEngine を起動して発注セッションを実行
   - 実行:
     - python -m kabusys.run_execution
   - 補足:
     - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し、data/paper_trading.db に結果を記録して本番 DB と分離します。
     - 実行中は data/execution.pid に PID を書きます。停止は data/stop_requested.flag または data/kill.flag を利用します。
     - 起動時に kill.flag が既に存在する場合は起動を行いません。

3. Paper Trading 検証レポート（ツール）
   - 目的: Paper Trading のログ（trade_logs, system_status 等）を集計してレポートを作成
   - 実行:
     - python -m kabusys.tools.paper_verification_report
     - 期間指定例:
       - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     - DB 指定:
       - --db PATH で PAPER_TRADING_SQLITE_PATH を上書き可能
   - 出力: 標準出力にレポート（稼働率、注文成功率、レイテンシ等）と PASS / FAIL 判定を表示

4. Streamlit ダッシュボード（監視用）
   - 目的: 監視データを可視化する UI
   - 実行:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 補足: DB を read-only で開くため、MonitoringEngine が生成した SQLite を指定します。

5. AI 関連
   - News NLP（銘柄ごとのニュースセンチメント取得）
     - 関数: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
     - 実行には OPENAI_API_KEY が必要（引数で渡すことも可）。
   - Regime Detector（市場レジーム判定）
     - 関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
     - 同様に OPENAI_API_KEY が必要。

6. Kill / Stop フラグ
   - data/kill.flag: KillSwitch によって書き込まれる停止指示ファイル（Execution を安全に停止する目的）
   - data/stop_requested.flag: run_monitoring / run_execution が外部から停止指示として監視するフラグファイル
   - 手動で削除するには:
     - rm data/kill.flag
     - rm data/stop_requested.flag
   - KillSwitch クラスを使ってプログラムからクリアすることも可能（KillSwitch.clear()）。

---

## 注意点 / 動作仕様の要約

- Monitoring の DB 初期化: run_monitoring / run_execution どちらでも init_monitoring_db() を呼んでテーブルを冪等的に作成します。
- run_monitoring は MONITOR_POLL_INTERVAL 環境変数を読み、0 以下や不正な値は無視してデフォルト 60 秒を使用します。
- run_execution は KABUSYS_ENV=paper_trading の場合に paper_sqlite_path を使用し、MockBroker を用いることで本番 DB と完全に分離します。
- OpenAI 呼び出し（news_nlp / regime_detector）は再試行ロジックや JSON バリデーションを備えていますが、API キー未設定時は例外を出すか安全フォールバック（macro_sentiment=0.0）を行う実装があります。
- process priority や CPU affinity は utils/process_priority.py で抽象化されています。プロセス優先度は起動直後に High に設定されますが、権限がない場合は警告を出してスキップします。

---

## ディレクトリ構成（主要ファイル）

以下は主要なモジュール・ファイルの一覧（src/kabusys 以下）。実際のファイル数は多いため、代表的なものを抜粋しています。

- src/
  - kabusys/
    - __init__.py
    - config.py                         — 環境変数 / 設定管理
    - run_monitoring.py                 — Monitoring ポーリングループ起動スクリプト
    - run_execution.py                  — ExecutionEngine 起動スクリプト
    - tools/
      - paper_verification_report.py    — Paper Trading 検証レポート生成ツール
    - ai/
      - news_nlp.py                     — ニュースの LLM センチメント評価
      - regime_detector.py              — 市場レジーム判定
    - monitoring/
      - monitoring_db.py                — 監視用 SQLite 層（テーブル定義 / CRUD）
      - system_monitor.py               — システム状態監視
      - trade_monitor.py                — 注文滞留・価格異常監視
      - risk_monitor.py                 — ドローダウン・ポジション上限監視
      - kill_switch.py                  — kill.flag 管理
      - alert_manager.py                — LINE 通知
      - monitoring_engine.py            — 各 Monitor を束ねる
      - streamlit_dashboard.py          — Streamlit ダッシュボード
    - execution/
      - order_manager.py
      - order_repository.py
      - order_record.py
      - reconciler.py
      - execution_engine.py
      - broker_factory.py
      - broker_api.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - utils/
      - process_priority.py
    - data/ (実行時に生成される想定)
      - monitoring.db (デフォルト SQLITE_PATH)
      - kabusys.duckdb (デフォルト DUCKDB_PATH)
      - paper_trading.db (paper trading 用 DB)
      - execution.pid
      - kill.flag / stop_requested.flag

---

## 開発メモ / 拡張ポイント

- DuckDB はリサーチ / ファクター計算に使われます。prices_daily / raw_financials 等のテーブルを前提に処理が書かれているため、データ投入方法は別途用意してください。
- 発注フローのテスト時は BrokerClient のモックや paper_trading モードを活用してください。
- OpenAI を使う機能は API レスポンスの形式変化に注意（JSON Mode を期待する実装になっています）。
- streamlit ダッシュボードは監視 DB を read-only で開くため、実稼働での表示に適しています。

---

この README はリポジトリ内のコード（コメント・ドキュメンテーションストリング）に基づいて作成しています。詳細な API や引数、追加のユーティリティは各モジュールの docstring を参照してください。何か特定の使用例や補足ドキュメントが必要であれば教えてください。