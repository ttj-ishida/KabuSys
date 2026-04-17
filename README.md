# KabuSys

日本株自動売買システムの部分実装（ライブラリ／ツール群）。  
本リポジトリにはポートフォリオ構築、ポジション決定、監視、実行エンジン周り、リサーチ／AI 補助モジュールなどが含まれます。

---

## プロジェクト概要

- 目的: 日本株の自動売買を支援するコンポーネント群（シグナル → 発注 → モニタリング → リコンシリエーション／レポート）。
- 設計方針の例:
  - DuckDB / SQLite を用いたローカルデータ処理（prices_daily, raw_financials 等）。
  - 実行（ExecutionEngine）は paper_trading（検証）と live（本番）を切替可能。
  - 監視（MonitoringEngine）はシステム状態、注文滞留、リスク（ドローダウン・ポジション上限）を監視し、LINE 通知・kill flag 発行を行う。
  - AI 機能（OpenAI）でニュースのセンチメントや市場レジーム判定を行う。

---

## 主な機能一覧

- ポートフォリオ構築
  - 候補選定、等金額／スコア重み計算（kabusys.portfolio）
  - ポジションサイズ決定（単元丸め、集約キャップ、コストバッファ対応）
  - セクター上限・レジーム乗数の適用

- 実行系
  - OrderManager, ExecutionEngine（発注、状態遷移、リスク制御）
  - Reconciler（再起動後の自動リコンシリエーション）
  - Broker クライアント抽象化（実運用・モックの切替）

- 監視（Monitoring）
  - SystemMonitor: CPU/MEM/Disk、データ鮮度、プロセス生存監視
  - TradeMonitor: 注文滞留、約定異常価格検知
  - RiskMonitor: ドローダウン、ポジション上限の監視と risk_logs 登録
  - MonitoringEngine: 各 Monitor を束ね定期実行。kill.flag 書き込みや LINE 通知連携
  - SQLite ベースの監視 DB（monitoring_db.py）

- AI / Research
  - ニュースの LLM センチメントスコアリング（kabusys.ai.news_nlp）
  - 市場レジーム判定（kabusys.ai.regime_detector）
  - ファクター計算 / 特徴量解析（kabusys.research）
  - DuckDB を用いた大量データ処理

- 運用ツール
  - run_execution.py / run_monitoring.py — 各プロセスの起動スクリプト
  - streamlit ダッシュボード（監視データ可視化）
  - paper_verification_report — Paper Trading の検証レポート生成

---

## 必要条件（依存）

主な Python パッケージ（pyproject.toml 等で管理されている前提）:
- python 3.10+
- duckdb
- psutil
- requests
- openai
- streamlit (ダッシュボード起動時)
- その他：標準ライブラリ（sqlite3, logging, threading 等）

OS: Windows / Linux / macOS（process priority はプラットフォーム差分を吸収する実装）

---

## セットアップ手順

1. リポジトリをチェックアウト
   - 例: git clone ...

2. 仮想環境作成と依存インストール
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
   - pip install -r requirements.txt  または pyproject.toml からインストール

3. 環境変数設定
   - プロジェクトルートに .env（または .env.local）を作成すると自動読み込みされます（自動ロードは既定で有効）。
   - 自動ロード無効化: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. 必須環境変数（主なもの）
   - JQUANTS_REFRESH_TOKEN — J-Quants API 用（Settings.jquants_refresh_token が必須）
   - KABU_API_PASSWORD — kabuステーション API パスワード（Settings.kabu_api_password が必須）
   - OPENAI_API_KEY — OpenAI を使う機能（news_nlp / regime_detector）を利用する場合
   - KABUSYS_ENV — 実行環境（development / paper_trading / live）デフォルト: development

5. データベース／データディレクトリ
   - デフォルト SQLite/ DuckDB パス:
     - monitoring.db (SQLite): data/monitoring.db
     - paper_trading.db (Paper 実行時): data/paper_trading.db
     - duckdb: data/kabusys.duckdb
   - 必要に応じて環境変数で上書き可能（SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, DUCKDB_PATH）

サンプル .env の例:
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=（省略）
KABU_API_PASSWORD=（省略）
OPENAI_API_KEY=（任意）
SQLITE_PATH=data/monitoring.db
DUCKDB_PATH=data/kabusys.duckdb
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=

---

## 実行方法（使い方）

基本はパッケージモジュールとして直接実行できます。各スクリプトは package 内にあり、python -m で実行可能です。

- 実行エンジン（ExecutionEngine）起動
  - 目的: 発注 / エンジン処理を実行
  - コマンド:
    - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）に完全分離して記録します。
    - 起動時に data/stop_requested.flag が存在する場合は起動せず終了します。
    - PID ファイル: data/execution.pid（Settings.pid_file_path でパス変更可能）
    - 停止: data/stop_requested.flag を作成すると実行中のループが検出して停止します。

- 監視ループ（MonitoringEngine）起動
  - 目的: システム・注文・リスク監視をポーリング
  - コマンド:
    - python -m kabusys.run_monitoring
  - 環境変数:
    - MONITOR_POLL_INTERVAL — ポーリング間隔（秒）。デフォルト 60 秒。0 または負値は無効でデフォルトにフォールバック。
  - 挙動:
    - 監視は本番 sqlite_path を使用（KABUSYS_ENV にかかわらず本番 DB を参照）。
    - data/stop_requested.flag が存在すると終了します。

- Streamlit ダッシュボード（監視 UI）
  - コマンド:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - DB は読み取り専用で開かれます（MonitoringEngine が生成する SQLite を参照）。

- Paper Trading 検証レポート生成
  - コマンド:
    - python -m kabusys.tools.paper_verification_report
    - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で変更可能）
  - 出力: 標準出力へ検証指標（稼働率、注文成功率、送信率、レイテンシ等）と PASS/FAIL 判定

- AI / レジーム・ニューススコア
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime は DuckDB 接続と target_date, api_key を受け取って実行します。
  - 例（スクリプト等から呼ぶ）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, date(2026,4,1), api_key="...")

---

## 主要な環境変数（まとめ）

- KABUSYS_ENV: development | paper_trading | live（default: development）
- JQUANTS_REFRESH_TOKEN: 必須（J-Quants API）
- KABU_API_PASSWORD: 必須（kabu API）
- OPENAI_API_KEY: OpenAI を使う場合に必要
- SQLITE_PATH: 監視用 SQLite（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（default: data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイル（default: data/kabusys.duckdb）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、default=60）
- PAPER_FILL_MODE: paper_trading 時の fill モード（instant|partial|never|reject）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（未設定なら通知は行われずログのみ）

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                — 環境変数 / 設定管理
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor 起動スクリプト
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- monitoring/
  - monitoring_db.py
  - monitoring_engine.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py
  - streamlit_dashboard.py
- execution/
  - order_manager.py
  - reconciler.py
  - (※ 他に broker_factory, execution_engine, order_repository 等が存在)
- research/
  - factor_research.py
  - feature_exploration.py
- ai/
  - news_nlp.py
  - regime_detector.py
- data/ (runtime に生成されることを想定)
  - monitoring.db
  - paper_trading.db
  - kabusys.duckdb
  - execution.pid
  - stop_requested.flag
  - kill.flag

（上記は主要ファイルのみ。実際のコードベースはさらに複数モジュールが含まれます。）

---

## 注意事項 / 運用メモ

- .env 自動読み込み:
  - config.Settings はプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）から .env/.env.local を自動で読み込みます。
  - 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

- stop フラグ:
  - run_execution.py / run_monitoring.py は data/stop_requested.flag を確認して安全に停止します。運用上はこのファイルの作成で各プロセスを停止できます。

- kill flag:
  - KillSwitch は条件により data/kill.flag（Settings.kill_flag_path）を作成し ExecutionEngine 停止を誘発します。kill.flag は明示的に削除しない限り残るため、起動前にクリアするオプション（Settings.kill_flag_clear_on_start）やツールで制御してください。

- Paper Trading:
  - KABUSYS_ENV=paper_trading の場合、実ブローカーへの発注は行われず、MockBrokerClient を使って挙動検証を行います。DB は PAPER_TRADING_SQLITE_PATH に分離されます。

- OpenAI 利用:
  - API 呼び出しは外部ネットワークに依存し、429 / ネットワーク断 / 5xx に対してリトライ実装がありますが、API キーが未設定のまま実行すると例外が発生します。運用では環境変数 OPENAI_API_KEY を設定してください。

- 権限・プラットフォーム:
  - process priority や cpu affinity の設定は OS により制限されることがあります（psutil による例外処理あり）。権限不足で警告が出ますが処理は続行されます。

---

## トラブルシューティング

- DB が見つからない / 読み取り不可:
  - Streamlit ダッシュボードは監視 DB を読み取り専用で開きます。MonitoringEngine を起動して DB が初期化されているか確認してください。

- 環境変数読み込まれない:
  - .env をプロジェクトルート（.git や pyproject.toml がある場所）に置くか、KABUSYS_DISABLE_AUTO_ENV_LOAD を確認してください。

- 実行中に停止したい:
  - data/stop_requested.flag を作成してください（実行スクリプトは定期に存在確認して安全に終了します）。
  - KillSwitch による停止は条件次第で kill.flag を置くため、起動前に file を確認・削除してください。

---

必要に応じて README を拡張して、起動オプション、より詳細な運用手順、CI テスト方法、開発向けユーティリティなどを追加できます。追加で盛り込みたい情報があれば教えてください。