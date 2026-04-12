# KabuSys

日本株自動売買システムの一部サブモジュール群を集めたリポジトリ。戦略のリサーチ/ファクター計算、ポートフォリオ構築、発注実行、監視（モニタリング）、ニュースのAI評価などのユーティリティを含みます。

## 概要（Project overview）

KabuSys は日本株向けの自動売買システムを想定したモジュール群です。本コードベースには以下の主要機能が含まれます。

- リサーチ / ファクター計算（momentum, value, volatility など）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイジング）
- 発注周りのロジック（OrderManager, Reconciler, ExecutionEngine 起動スクリプト）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor）とアラート送信（LINE）
- AI を用いたニュースのセンチメント評価（OpenAI）
- Paper Trading 検証レポート生成スクリプト
- Streamlit ベースの監視ダッシュボード

本 README はローカル環境でのセットアップ・起動方法、主要構成の説明をまとめたものです。

---

## 機能一覧（Features）

- リサーチ
  - calc_momentum / calc_volatility / calc_value：DuckDB 上の株価・財務データからファクター算出
  - feature_exploration：将来リターン計算・IC（情報係数）・統計サマリ
- ポートフォリオ構成
  - 候補選定（score ソート）、等金額／スコア加重の重み計算
  - セクターキャップ適用、レジーム乗数（bull/neutral/bear）
  - 株数の決定（risk_based / equal / score）、単元株丸め、投下資金スケーリング
- 実行（Execution）
  - OrderManager / OrderRepository / Reconciler：注文ステート管理・リコンシリエーション
  - BrokerClientFactory を通した本番/モックブローカー分離（KABUSYS_ENV により切替）
  - run_execution.py：ExecutionEngine の起動スクリプト（paper_trading 環境では専用 DB を使用）
- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor：定期ポーリングによる状態記録とリスク検知
  - MonitoringDB：SQLite に対する永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - MonitoringEngine / run_monitoring.py：監視ループの起動（ポーリング間隔は環境変数で調整可能）
  - AlertManager：LINE Push による通知（クールダウン管理あり）
  - KillSwitch：条件に応じて `data/kill.flag` を書き込み ExecutionEngine を停止させる
  - streamlit_dashboard.py：監視ダッシュボード（Streamlit）
- AI
  - news_nlp.score_news：ニュース記事を OpenAI でセンチメント評価し ai_scores に保存
  - regime_detector.score_regime：ETF（1321）の MA とマクロニュースの LLM 評価を合成して市場レジーム判定
- ツール
  - tools/paper_verification_report.py：Paper Trading DB を対象に各種指標（稼働率、約定率、レイテンシなど）を集計・レポート出力

---

## 必要条件（Requirements）

最低限必要な Python ライブラリ（代表例）:

- Python 3.9+
- duckdb
- psutil
- requests
- openai（AI 機能を使う場合）
- streamlit（ダッシュボードを使う場合）

インストール例:
```
pip install duckdb psutil requests openai streamlit
```

SQLite は標準ライブラリで利用可能です。

---

## 環境変数（重要な設定）

Settings クラスで読み取る主な環境変数（デフォルトを含む）:

- KABUSYS_ENV: 起動環境（development | paper_trading | live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: （必須）J-Quants API 用トークン
- KABU_API_PASSWORD: （必須）kabuステーション API パスワード
- KABU_API_BASE_URL: kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN: LINE Push 用トークン（任意）
- LINE_USER_ID: LINE Push 宛先ユーザーID（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: Monitoring SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: Paper Trading のフィルモード（instant | partial | never | reject）デフォルト: instant
- PID_FILE_PATH: ExecutionEngine 用 PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアする場合は "1"
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値（パーセント）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: run_monitoring で監視ポーリング間隔（秒、デフォルト 60 秒）

.env 自動ロード:
- プロジェクトルート（.git または pyproject.toml を基準） にある `.env` と `.env.local` が自動で読み込まれます。
- OS 環境 > .env.local > .env の優先順位。自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順（Setup）

1. リポジトリをクローン／取得
2. 仮想環境を作成して依存パッケージをインストール
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
   （requirements.txt が無ければ手動で duckdb, psutil, requests, openai, streamlit などをインストール）

3. 環境変数を設定
   - プロジェクトルートに `.env` を作成するか、環境変数で設定します。
   - 例: `.env` に必要なキー（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD 等）を記述。

4. データディレクトリ作成
   ```
   mkdir -p data
   ```
   初回は MonitoringDB の初期化（スクリプト起動時に自動で作成されます）。

---

## 使い方（Usage）

以下は代表的な実行例です。

- 監視ループを起動（MonitoringEngine）
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を秒単位で上書きできます（デフォルト 60）。
  - 監視は常に本番の sqlite_path を使用します（KABUSYS_ENV に依らず）。

- ExecutionEngine を起動（発注実行）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、`data/paper_trading.db` に記録します（本番 DB と完全分離）。
  - 起動時に PID ファイルが `PID_FILE_PATH` に書かれます。KillSwitch により `KILL_FLAG_PATH` にフラグを書き出すと ExecutionEngine の停止を促せます。

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB: `data/paper_trading.db`。`--db` オプションや `PAPER_TRADING_SQLITE_PATH` 環境変数で変更可能。

- Streamlit ダッシュボード（監視）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - read-only モードで SQLite を開きます。MonitoringEngine を先に起動してデータを蓄積してください。

- AI ニュース評価（関数呼び出し）
  - news_nlp.score_news / regime_detector.score_regime は DuckDB 接続と target_date、OpenAI の API key を渡して呼び出す関数です。CLI ではなく、別スクリプトやスケジューラから呼ぶことを想定しています。
  - 例（簡易）:
    ```
    from kabusys.ai.news_nlp import score_news
    import duckdb, datetime
    conn = duckdb.connect('data/kabusys.duckdb')
    score_news(conn, datetime.date(2026,4,10), api_key='sk-...')
    ```

注意事項:
- OpenAI を利用する機能は API キー（OPENAI_API_KEY）の設定が必須です。
- Streamlit はブラウザで表示されます。ローカル環境ファイアウォール等に注意してください。

---

## 重要な実装上の挙動（補足）

- Settings はプロジェクトルートの `.env` / `.env.local` を自動読込しますが、OS 環境変数は保護され上書きされません。
- run_monitoring のポーリングループは例外処理を内包しており、check_once 内での例外はログ出力のうえ次ループへ継続します。
- MonitoringDB の初期化（init_monitoring_db）は冪等で、既存 DB に対するマイグレーション（カラム追加）も行います。
- KillSwitch は条件に合致すると `kill.flag` を書き込みます。既に存在する場合は再書き込みしません。
- PSUtil を使ってプロセス優先度や CPU affinity を設定しますが、権限不足で失敗する場合は警告を出してスキップします。

---

## ディレクトリ構成（Directory structure）

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/設定管理
  - run_monitoring.py        — MonitoringEngine ポーリング起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py
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
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他 Broker 関連・Engine の実装ファイル...)
  - utils/
    - process_priority.py

---

## トラブルシューティング（Tips）

- DB ファイルが見つからない / 開けない：
  - Monitoring の SQLite は通常 `data/monitoring.db`。パスが違う場合は `SQLITE_PATH` を設定するか、Streamlit 実行時に `-- --db path` を指定してください。
- OpenAI 呼び出しで 429 / 接続エラーが発生：
  - ニュース評価 / レジーム判定は内部でリトライ（指数バックオフ）を実装していますが、API 制限下では失敗することがあります。API キー・レート上限を確認してください。
- プロセス優先度設定で PermissionError が発生：
  - 高優先度の設定は権限が必要な場合があります。失敗時はログに警告が出て処理は継続されます。
- .env 自動ロードを無効にしたい場合：
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に便利です）。

---

以上がこのコードベースの概要と使い方です。具体的な各モジュールの詳細（関数仕様や引数の意味など）は各ファイル内の docstring に記載されています。必要であれば README にサンプルコードや運用フロー（起動順序、cron/scheduler 例など）を追記します。ご希望があれば教えてください。