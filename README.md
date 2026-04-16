# KabuSys

KabuSys は日本株向けの自動売買システムのモジュール群です。注文実行エンジン・監視系・ポートフォリオ構築・ファクター計算・AI（ニュース NLP / レジーム判定）・リサーチユーティリティなどを含んでおり、実運用・ペーパートレード・研究用途を想定して設計されています。

バージョン: 0.1.0

---

## 概要

主な設計方針・特徴:

- 実取引（live）/ ペーパートレード（paper_trading） / 開発（development）環境を切替可能
- ExecutionEngine による発注フロー・OrderManager / Reconciler による再同期機能
- 監視スタック（SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine）
- 監視ログは SQLite（monitoring.db）へ永続化、リサーチ用データは DuckDB を使用
- ニュース記事を LLM（OpenAI）でスコアリングする ai.news_nlp、レジーム判定モジュール ai.regime_detector
- ポートフォリオ構築（候補選定、重み付け、リスク調整、ポジションサイズ算出）を純粋関数群として提供
- Streamlit による監視ダッシュボード、検証レポート生成ツールなどを付属
- .env / 環境変数ベースで設定を管理（自動ロード機能あり）

---

## 機能一覧

- Execution
  - ExecutionEngine（起動・セッション管理）
  - Broker クライアント抽象化（本番/モック切替）
  - OrderManager：発注 API 抽象と DB 保存
  - Reconciler：起動時の発注状態照合・ポジション差分検出

- Monitoring
  - SystemMonitor：CPU / メモリ / ディスク / プロセス生存チェック、データ鮮度チェック
  - TradeMonitor：滞留注文・約定異常価格検出
  - RiskMonitor：ドローダウン・ポジション数上限の検出とログ記録
  - KillSwitch：閾値超過時に data/kill.flag を書き込んで ExecutionEngine を停止
  - AlertManager：LINE Messaging API を用いたプッシュ通知（クールダウン管理）
  - MonitoringEngine：上記 Monitor を束ねてポーリング実行
  - Streamlit ダッシュボード（監視データ閲覧）

- Portfolio
  - 候補選定、等金額/スコア加重、セクター上限、レジーム倍率、株数計算（単元対応・集計キャップ）

- Research / Data
  - ファクター計算（momentum/value/volatility）
  - 将来リターン計算、IC（Information Coefficient）計算、特徴量探索ユーティリティ
  - DuckDB 接続ベースの SQL + Python 実装

- AI
  - news_nlp: raw_news を集約して OpenAI へ送信し ai_scores を更新
  - regime_detector: ETF（1321）MA200 とマクロニュースセンチメントを合成して日次レジーム判定

- Tools
  - paper_verification_report: ペーパートレード用 DB から検証レポートを生成
  - そのほか CLI / モジュール単位での実行エントリあり

---

## セットアップ手順

前提: Python 3.9+（プロジェクトで特定バージョン指定がない場合）。以下は一般的な手順です。

1. リポジトリをクローン
   - git clone <リポジトリURL>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  # macOS / Linux
   - .venv\Scripts\activate     # Windows

3. 必要パッケージのインストール
   - 必要な外部ライブラリ（コード内 import から推測）:
     - duckdb
     - psutil
     - openai
     - requests
     - streamlit
   - 例:
     - pip install duckdb psutil openai requests streamlit

   （実際の requirements.txt がある場合はそれを使用してください）

4. データディレクトリ作成
   - mkdir -p data

5. 環境変数設定 (.env ファイル)
   - プロジェクトルートに `.env` または `.env.local` を作成できます。
   - 自動ロードはデフォルトで有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 最低限設定が推奨される値:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...           # AI 機能を使う場合
     - KABUSYS_ENV=development|paper_trading|live
     - PAPER_FILL_MODE=instant|partial|never|reject
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - LINE_CHANNEL_ACCESS_TOKEN=...  # LINE通知を使う場合
     - LINE_USER_ID=...               # LINE通知を使う場合
     - LOG_LEVEL=INFO

   例（.env）:
   ```
   KABUSYS_ENV=development
   OPENAI_API_KEY=sk-...
   SQLITE_PATH=data/monitoring.db
   DUCKDB_PATH=data/kabusys.duckdb
   ```

6. DB の初期化
   - 監視 DB（monitoring.db）は run_monitoring または run_execution 実行時に自動でテーブル作成（init_monitoring_db）されます。
   - DuckDB のスキーマ / データは運用に応じて用意してください（prices_daily / raw_financials / raw_news 等）。

---

## 使い方

以下は代表的な実行方法です。

- 監視ループ起動（Monitoring）
  - デフォルトは本番の sqlite_path（Settings.sqlite_path）を使用して監視 DB を更新します。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 停止はプロジェクトルートの data/stop_requested.flag ファイルを作成することで次ポーリングで検知して停止します。
  - 実行:
    - python -m kabusys.run_monitoring

- ExecutionEngine 起動（注文実行）
  - KABUSYS_ENV=paper_trading にすると MockBrokerClient を使用し、paper_trading 用 SQLite（data/paper_trading.db）に書き込みます（本番 DB と完全分離）。
  - Execution 側も data/stop_requested.flag をチェックして停止します。execution は data/execution.pid に PID を出力します。
  - 実行:
    - python -m kabusys.run_execution
  - ペーパートレード例:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution

- Streamlit 監視ダッシュボード
  - 起動:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ローカルで monitoring.db を読み取り専用で開き、Overview / Positions / Orders / System を表示します。

- Paper Trading 検証レポート
  - SQLite（ペーパートレード DB）から指標を集計してレポートを標準出力に出します。
  - 実行例:
    - python -m kabusys.tools.paper_verification_report
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - --db オプションで DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI 機能（ニューススコア / レジーム判定）
  - OpenAI API キーが必要（環境変数 OPENAI_API_KEY）。キー未設定だと関連関数はエラーになります。
  - news_nlp.score_news(conn, target_date, api_key=None) — ai_scores を書き換え
  - regime_detector.score_regime(conn, target_date, api_key=None) — market_regime に書き込み

- Kill / Stop
  - 手動で ExecutionEngine を停止したい場合は data/kill.flag を書く仕組み（KillSwitch）や data/stop_requested.flag により監視・実行プロセスが検知して停止します。
  - kill.flag の削除は手動で rm data/kill.flag するか、KillSwitch.clear() を呼び出すことで行います。

---

## 環境変数と設定（主な項目）

- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- PAPER_FILL_MODE: instant | partial | never | reject（デフォルト instant）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START など（Settings にプロパティあり）
- MONITOR_POLL_INTERVAL: run_monitoring スクリプトのポーリング間隔（秒）

Settings クラスに多数のプロパティ（cpu/memory/disk の閾値、ログレベル等）が定義されています。自動読み込みはプロジェクトルートの `.env` / `.env.local` を検出して行われます（OS 環境変数が優先）。

---

## ディレクトリ構成

（主要ファイル/ディレクトリのみ抜粋）

src/
└── kabusys/
    ├── __init__.py
    ├── config.py                      # 環境変数 / 設定管理
    ├── run_execution.py               # ExecutionEngine 起動スクリプト
    ├── run_monitoring.py              # SystemMonitor 起動スクリプト
    ├── tools/
    │   ├── __init__.py
    │   └── paper_verification_report.py
    ├── ai/
    │   ├── __init__.py
    │   ├── news_nlp.py                 # ニュース NLP（OpenAI）
    │   └── regime_detector.py
    ├── monitoring/
    │   ├── __init__.py
    │   ├── monitoring_db.py            # SQLite テーブル定義 / Persistence
    │   ├── system_monitor.py
    │   ├── trade_monitor.py
    │   ├── risk_monitor.py
    │   ├── monitoring_engine.py
    │   ├── alert_manager.py
    │   ├── kill_switch.py
    │   └── streamlit_dashboard.py
    ├── execution/
    │   ├── order_manager.py
    │   ├── reconciler.py
    │   └── ...（broker / order_repository 等の実装が含まれるはずです）
    ├── portfolio/
    │   ├── __init__.py
    │   ├── portfolio_builder.py
    │   ├── risk_adjustment.py
    │   └── position_sizing.py
    ├── research/
    │   ├── __init__.py
    │   ├── factor_research.py
    │   └── feature_exploration.py
    ├── utils/
    │   ├── __init__.py
    │   └── process_priority.py         # プロセス優先度 / CPU affinity ユーティリティ
    └── data/ (推奨)
        ├── monitoring.db (SQLite)
        ├── paper_trading.db (SQLite, ペーパートレード)
        └── kabusys.duckdb

注意: 上記はソースツリーの一部抜粋です。実際の repo にはさらに execution/broker 実装や data pipeline 等のモジュールが存在する想定です。

---

## 運用メモ / トラブルシューティング

- 監視 DB が存在しない場合、run_monitoring / run_execution の起動時にテーブルが作成されます（init_monitoring_db）。
- run_monitoring は KABUSYS_ENV にかかわらず本番の sqlite_path を使用する設計なので、監視 DB が本番を指していることに注意してください（環境変数で上書き可能）。
- Execution は paper_trading モード時に paper_sqlite_path（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離します。
- OpenAI 関連機能を使う場合、API キーのレート制限やネットワークエラーに備えてリトライやフェイルセーフが組まれています。API キーが未設定だと明示的に例外が出ます。
- line 通知が届かない場合は LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID の設定を確認してください。設定が空の場合は送信をスキップします。
- プロセス優先度設定（set_process_priority）は psutil を使用しています。権限不足や非対応 OS の場合は warning を出してスキップされます。
- 停止フラグ:
  - data/stop_requested.flag: run_* スクリプトが定期的にチェックする停止フラグ
  - data/kill.flag: KillSwitch が書き込む「強制停止」フラグ（ExecutionEngine に停止を促す）
  - 必要に応じてこれらのファイルを手動で作成 / 削除してください

---

必要であれば、実際の requirements.txt の推定作成、systemd サービス定義、Dockerfile、CI 設定例などの追加ドキュメントも作成できます。どの情報を優先して出力しますか？