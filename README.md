# KabuSys

KabuSys は日本株の自動売買システムのコアライブラリ群です。本リポジトリは注文実行、監視、ポートフォリオ構築、リサーチ（ファクター計算）および AI を用いたニュース解析等の機能を提供します。

以下はコードベースから抽出した README.md（日本語）です。

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要なコンポーネントをモジュール化したライブラリ／実行スクリプト群です。主な役割：

- 注文の作成・発注・状態管理（ExecutionEngine / OrderManager 等）
- システム稼働監視（SystemMonitor / MonitoringEngine / AlertManager 等）
- リスク監視（ドローダウン・ポジション上限等）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイジング）
- 研究用ファクター計算・特徴量解析（DuckDB を用いた計算）
- ニュースの NLP スコアリング / 市場レジーム判定（OpenAI を利用）
- Paper Trading 用の分離された DB と検証ツール

設計方針として、DB 操作は明確に分離され、DuckDB/SQLite に依存する処理と外部 API 呼び出し（kabu/station, OpenAI等）はレイヤで管理されています。

---

## 主な機能一覧

- Execution
  - 注文作成・送信、Order state machine、リコンシリエーション（Reconciler）
  - Paper Trading モード（実ブローカーと分離して MockBrokerClient を使用）
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、プロセス生存確認、データ鮮度チェック
  - TradeMonitor: 滞留注文、約定価格の異常検出
  - RiskMonitor: ドローダウン・ポジション上限の検出とリスクログ記録
  - MonitoringEngine: 各モニタを束ねるポーリングループ
  - AlertManager: LINE Push による通知（クールダウン制御）
  - Streamlit ダッシュボード（read-only）
- Portfolio
  - 候補選定、等配分・スコア加重配分、セクター上限適用、リスクベースのポジションサイジング
- Research
  - ファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン計算、IC（Information Coefficient）などの統計解析ユーティリティ
- AI
  - news_nlp: OpenAI によるニュースセンチメント評価（ai_scores へ書込み）
  - regime_detector: ma200 とマクロニュースの LLM 評価を組み合わせて日次レジーム判定

---

## セットアップ手順（開発・実行用）

前提：Python 3.9+ を想定します。

1. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージのインストール（最小）
   - pip install duckdb psutil requests openai streamlit

   ※ プロジェクトに requirements.txt がない場合は上記を参考にしてください。

3. 環境変数／.env
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（OS 環境変数が優先されます）。
   - 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   重要な環境変数（一部）：
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
   - KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
   - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector を使う場合）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: Monitoring SQLite（デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
   - PAPER_FILL_MODE: instant | partial | never | reject（Paper Trading の約定モード）
   - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト: 60）

   サンプル `.env`（例）
   ```
   KABUSYS_ENV=development
   JQUANTS_REFRESH_TOKEN=your_jquants_token
   KABU_API_PASSWORD=your_kabu_password
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   PAPER_FILL_MODE=instant
   MONITOR_POLL_INTERVAL=60
   LINE_CHANNEL_ACCESS_TOKEN=
   LINE_USER_ID=
   ```

4. データディレクトリ
   - スクリプトは `data/` 下のファイル（DB／flag／pid）を想定しています。必要に応じて作成してください。
   - 停止フラグ等: data/stop_requested.flag, data/kill.flag, data/execution.pid

5. DB 初期化
   - Monitoring 用の SQLite テーブルは `init_monitoring_db()` が起動時に自動で作成（冪等）します。特別な初期化は不要です。
   - DuckDB のテーブル（prices_daily / raw_financials / raw_news 等）はリサーチ・AI 機能で参照されます。これらは別途データ投入が必要です。

---

## 使い方（主要スクリプト）

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - もしくは python src/kabusys/run_monitoring.py
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）。
  - 監視は常に本番 sqlite_path（Settings.sqlite_path）を使用します（KABUSYS_ENV にかかわらず）。

- 実行エンジン起動（Execution）
  - python -m kabusys.run_execution
  - もしくは python src/kabusys/run_execution.py
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を用い、Paper Trading 専用 DB（PAPER_TRADING_SQLITE_PATH）に記録します。
  - 起動前に data/stop_requested.flag が存在する場合は起動を中止します。
  - 実行中に data/stop_requested.flag が作成されると安全に停止します。

- Streamlit ダッシュボード（監視）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を read-only で開き、Overview / Positions / Orders / System を表示します。

- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH より優先）
  - レポート指標: 稼働率、注文成功率、送信率、P95 レイテンシ等。閾値越えで FAIL を出力します。

- AI（ニューススコア / レジーム判定）
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を使って手動で呼び出すことができます（OpenAI API キー必須）。
  - score_news は DuckDB の raw_news / news_symbols / ai_scores テーブルを参照・更新します。
  - API 呼び出しは 429 / タイムアウト / 5xx に対して指数バックオフを実装していますが、API キーが必要です。

- Kill Switch（手動停止）
  - data/kill.flag を作成すると、ExecutionEngine に停止シグナルを送る仕組みが用意されています（KillSwitch）。
  - kill.flag は既存の場合は上書きされません。削除は手動で行うか、KillSwitch.clear() を呼び出してください。

---

## 主要設定（Settings）

設定は `kabusys.config.Settings` でラップされています。主なプロパティ：

- env: KABUSYS_ENV（development / paper_trading / live）
- duckdb_path / sqlite_path / paper_sqlite_path
- pid_file_path / kill_flag_path / kill_flag_clear_on_start
- paper_fill_mode（instant/partial/never/reject）
- cpu_threshold_pct / memory_threshold_pct / disk_threshold_pct
- log_level（DEBUG/INFO/...）

.env ファイルの自動読み込みルール：
- OS 環境変数 > .env.local > .env の順でマージされます。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化できます。

---

## ディレクトリ構成（抜粋）

リポジトリの主要モジュールを示します（src/kabusys 以下）。

- kabusys/
  - __init__.py
  - config.py
  - run_monitoring.py
  - run_execution.py
  - data/ (※データファイルはここに格納される想定: DB / flag / pid)
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - alert_manager.py
    - kill_switch.py
    - streamlit_dashboard.py
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - broker_api.py
    - order_record.py
    - ...（ブローカー関連インターフェース）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - tools/
    - paper_verification_report.py
  - utils/
    - process_priority.py

（上記は主要ファイルの抜粋です。詳細はソースツリーを参照してください。）

ツリー（例）
```
src/kabusys/
├─ ai/
│  ├─ news_nlp.py
│  └─ regime_detector.py
├─ monitoring/
│  ├─ monitoring_db.py
│  ├─ monitoring_engine.py
│  └─ streamlit_dashboard.py
├─ execution/
│  ├─ run_execution.py
│  ├─ order_manager.py
│  └─ reconciler.py
├─ portfolio/
│  ├─ portfolio_builder.py
│  └─ position_sizing.py
├─ research/
│  ├─ factor_research.py
│  └─ feature_exploration.py
├─ tools/
│  └─ paper_verification_report.py
├─ utils/
│  └─ process_priority.py
├─ config.py
├─ run_monitoring.py
└─ __init__.py
```

---

## 運用上の注意 / ヒント

- Paper Trading と Production DB は分離して運用してください（Settings.is_paper を利用）。
- Monitoring は常に monitoring DB (Settings.sqlite_path) を使用します。監視ログは起動時に自動でテーブル作成されます。
- 停止フラグ（data/stop_requested.flag）を置くことで run_monitoring/run_execution を安全に停止できます。
- Execution 起動時に PID ファイル（data/execution.pid）を書き込み、システムモニタがプロセス生存をチェックします。PID ファイルが古くなった場合は自動削除してアラート記録します。
- OpenAI を利用する機能は API キーが必要です。API のレート制限や課金に注意してください。
- process_priority.set_process_priority() は起動直後に呼ばれ、実行プロセスの優先度を設定します（OS 権限によっては失敗する場合があります）。
- DuckDB のテーブル（prices_daily / raw_financials / raw_news 等）はリサーチ・AI 機能で前提として参照されます。事前にデータを投入してください。

---

## よく使うコマンドまとめ

- 監視を起動:
  - python -m kabusys.run_monitoring

- エンジン（実行）を起動:
  - python -m kabusys.run_execution

- Streamlit ダッシュボード起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading レポート生成:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - もしくは `--db` オプションで DB パスを指定

---

必要であれば、README にサンプルの .env.example、requirements.txt、起動スクリプトの systemd unit 例や Dockerfile のテンプレートを追加できます。どの情報を優先して追記しますか？