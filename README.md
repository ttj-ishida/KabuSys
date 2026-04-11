# KabuSys — README

このリポジトリは日本株自動売買システムの一部（コアロジック、実行エンジン、監視、研究・AIモジュールなど）を含む Python パッケージです。以下はコードベースから抽出した概要、機能、セットアップと使い方、ディレクトリ構成の説明です。

注意：本 README はソースコードのコメント・実装に基づいて作成しています。実行前に環境変数やデータベース等の設定を必ず確認してください。

## プロジェクト概要
KabuSys は日本株の自動売買を目的としたモジュール群です。主な役割は次のとおりです。

- シグナルに基づく発注（ExecutionEngine）
- 発注状態管理・永続化（OrderRepository / OrderManager）
- 再起動時のリコンシリエーション（Reconciler）
- リスク管理（RiskManager / RiskMonitor）
- 監視（SystemMonitor / TradeMonitor / MonitoringEngine）
- 監視ダッシュボード（Streamlit ベース）
- ポートフォリオ構築（候補選定、重み計算、枚数算出）
- 研究用ファクター計算（DuckDB を用いたファクター、将来リターン、IC 計算）
- ニュースの NLP によるセンチメント評価（OpenAI を利用する ai.news_nlp）
- 市場レジーム判定（ai.regime_detector）

設計上のポイント：
- DuckDB と SQLite を使い分ける（時系列データ等は DuckDB、監視ログ等は SQLite）
- Paper trading（KABUSYS_ENV=paper_trading）は本番 DB と分離して専用 SQLite を使用
- OpenAI（gpt-4o-mini）を用いる NLP 機能は API キーが必要
- プロセス優先度設定や CPU affinity 設定ユーティリティを提供

## 機能一覧（主要コンポーネント）
- kabusys.config
  - .env / 環境変数の読み込み・管理（Settings クラス）
  - KABUSYS_ENV（development / paper_trading / live）などの設定
- kabusys.execution
  - ExecutionEngine: シグナルの取り込み・発注ループ、push ドレイン処理
  - OrderManager: 発注フロー（create/send/sync/cancel）、クラッシュ耐性を考慮した永続化
  - Reconciler: 起動時の注文・ポジションの突合せ
- kabusys.monitoring
  - SystemMonitor: CPU/メモリ/ディスク使用率、データ鮮度、プロセス監視
  - TradeMonitor: 滞留注文や約定価格異常の検出
  - RiskMonitor: ドローダウン、ポジション上限監視
  - KillSwitch: 条件に応じて kill.flag を書き込み ExecutionEngine 停止を促す
  - AlertManager: LINE Push による通知（クールダウン管理）
  - MonitoringEngine: 上記モニタをまとめてポーリング
  - Streamlit ダッシュボード（監視用）
  - monitoring_db: 監視用 SQLite スキーマと永続化 API
- kabusys.portfolio
  - 銘柄選定（select_candidates）、等重・スコア重み付け
  - position sizing（枚数算出）、セクター制約、レジーム乗数
- kabusys.research
  - ファクター計算（momentum、volatility、value）
  - 将来リターン、IC（スピアマン）計算、統計サマリ
- kabusys.ai
  - news_nlp.score_news: raw_news を OpenAI に送り銘柄別センチメントを ai_scores に保存
  - regime_detector.score_regime: ETF MA とマクロニュースの LLM センチメントを合成して market_regime を生成
- kabusys.utils
  - process_priority: プロセス優先度 / CPU affinity 設定ユーティリティ

## セットアップ手順（開発環境向け、例）
1. 必要な Python バージョン
   - Python 3.10 以上を推奨（型注釈で PEP 604 の union 型（|）等を使用）

2. 仮想環境の作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール（代表的な依存）
   - pip install duckdb psutil requests openai streamlit
   - その他、プロジェクトに応じて追加パッケージが必要になる可能性があります。
   - 実際の requirements.txt があればそれを使ってください。

4. ソースを PYTHONPATH に通す / editable install
   - 開発時はプロジェクトルートで:
     - pip install -e .
     - または PYTHONPATH=src python -m kabusys.run_monitoring.py のように実行

5. データディレクトリ作成
   - デフォルトのパス (例): data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db
   - 必要に応じてディレクトリを作成: mkdir -p data

6. 環境変数設定
   - 推奨: プロジェクトルートに .env を作成
   - 主要なキー（.env.example を参照して作成してくださいが、代表例は以下）

代表的な環境変数（例）
- JQUANTS_REFRESH_TOKEN=（必須）
- KABU_API_PASSWORD=（必須）
- OPENAI_API_KEY=（ai モジュールを使う場合は必須）
- KABUSYS_ENV=development|paper_trading|live  （デフォルト: development）
- PAPER_FILL_MODE=instant|partial|never|reject  （paper_trading 時の挙動）
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PID_FILE_PATH=data/execution.pid
- KILL_FLAG_PATH=data/kill.flag
- KILL_FLAG_CLEAR_ON_START=0 または 1
- LOG_LEVEL=INFO
- LINE_CHANNEL_ACCESS_TOKEN=（AlertManager）
- LINE_USER_ID=（AlertManager）
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT（監視しきい値）

注意: Settings クラスは自動でプロジェクトルートの .env/.env.local をロードします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

## 使い方（起動例）
以下は主要な実行スクリプトの起動方法例です。プロジェクトをパッケージとしてインストールした場合は python -m で実行するのが推奨です。単純にファイルを直接実行することも可能です（PYTHONPATH の扱いに注意）。

1. ExecutionEngine を起動（リアル or paper_trading）
   - paper_trading（モックブローカー、DBを data/paper_trading.db に分離）:
     - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
     - または KABUSYS_ENV=paper_trading python src/kabusys/run_execution.py
   - live（本番ブローカー）:
     - KABUSYS_ENV=live python -m kabusys.run_execution

   実行時の挙動:
   - 起動時に process priority を "high" に設定する attempt を行います（権限不足だとログWarning）。
   - Settings に基づき SQLite/ DuckDB に接続します。
   - paper_trading の場合、MockBrokerClient 等（設定に依存）を使用し本番 DB と分離します。
   - ExecutionEngine.run_session() がセッションを実行します（ログを参照）。

2. Monitoring（監視ループ）を起動
   - python -m kabusys.run_monitoring
   - または python src/kabusys/run_monitoring.py

   環境変数:
   - MONITOR_POLL_INTERVAL: ポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
   - Monitoring は KABUSYS_ENV にかかわらず settings.sqlite_path（本番 sqlite_path）を使用します（設計上の注意点）

3. Streamlit ダッシュボード（監視 UI）
   - 起動コマンド:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - read-only モードで SQLite を開き、Positions / Orders / System / Overview を表示

4. AI モジュール
   - ニュース NLP（ai.news_nlp.score_news）や regime_detector.score_regime は OpenAI API を呼びます。
   - 実行例（Python から呼び出し）:
     - from kabusys.ai.news_nlp import score_news
     - score_news(duckdb_conn, target_date, api_key="...")  # api_key が None の場合は環境変数 OPENAI_API_KEY を使用
   - OpenAI の呼び出しはリトライやレスポンス検証を備えていますが、API キーは必須です。

5. kill.flag 管理
   - KillSwitch は条件が満たされると Settings.kill_flag_path（デフォルト data/kill.flag）に理由を書き込みます。
   - ExecutionEngine は起動時やループ内で kill.flag を検出した際に停止処理（kill_switch）を発動する設計です。
   - 手動でクリアする場合はファイルを削除するか、KillSwitch.clear() を利用します。

## 設定・運用上の注意点
- paper_trading を使うと実際の発注は行われず、paper 用 SQLite に記録されます（本番 DB と完全分離）。
- Monitoring は常に settings.sqlite_path を用いるため、環境にかかわらず監視ログは本番用の監視 DB に蓄積されます。
- OpenAI を使う機能は API キーが必須。API 呼び出しはレート制御や 5xx リトライを実装していますが、費用やレート制限に注意してください。
- process priority の変更や CPU affinity の設定は OS 権限に依存します。失敗しても警告を出し続行する設計です。
- .env ファイルの取り扱い:
  - 自動ロード順序: OS 環境 > .env.local > .env
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化できます。

## ディレクトリ構成（主要ファイル）
（src 配下を想定）

- src/kabusys/
  - __init__.py               — パッケージ定義（__version__ 等）
  - config.py                 — 環境変数 / Settings
  - utils/
    - __init__.py
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ
  - execution/
    - execution_engine.py     — ExecutionEngine（シグナル処理・push ドレイン）
    - order_manager.py        — OrderManager（発注ワークフロー）
    - order_repository.py     — （DB 永続化、コードから参照あり）
    - reconciler.py           — リコンシリエーション（起動時自動復旧）
    - risk_manager.py         — 発注前の Gate チェック等（設定で制御）
    - broker_factory.py       — ブローカークライアント生成（実装に依存）
    - broker_api.py           — ブローカー API の抽象プロトコル
    - order_record.py         — 注文状態・状態遷移ロジック
  - monitoring/
    - run_monitoring.py       — 監視ポーリング起動スクリプト
    - monitoring_db.py        — SQLite スキーマ & MonitoringDB API
    - system_monitor.py       — システム状態・データ鮮度監視
    - trade_monitor.py        — 注文滞留・約定異常監視
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — kill.flag 管理
    - alert_manager.py        — LINE Push 通知
    - monitoring_engine.py    — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py  — Streamlit 監視ダッシュボード
  - portfolio/
    - portfolio_builder.py    — 候補選定・スコアソート
    - position_sizing.py      — 枚数算出（lot rounding, caps, scaling）
    - risk_adjustment.py      — セクター制限・レジーム乗数
    - __init__.py
  - research/
    - factor_research.py      — momentum / value / volatility ファクター
    - feature_exploration.py  — 将来リターン・IC・統計サマリ
    - __init__.py
  - ai/
    - news_nlp.py             — ニュース記事の LLM センチメント評価と ai_scores 書込
    - regime_detector.py      — 市場レジーム判定（MA + マクロニュース）
    - __init__.py
  - data/                     — デフォルトデータパス（data/kabusys.duckdb 等）
  - run_execution.py          — ExecutionEngine 起動スクリプト（モジュール内）
  - run_monitoring.py         — Monitoring 起動スクリプト（モジュール内）

（上記はコードベースに現れる主要モジュールの要約です。実際には他にも補助的なモジュールが存在する想定です。）

## よくある運用コマンドまとめ
- 監視ループ起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 実行エンジン起動（Paper trading）:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

## 補足 / 注意事項
- 実行前に .env（または環境変数）で必須項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）を設定してください。Settings._require により未設定時は ValueError が発生します。
- DuckDB / SQLite のスキーマはコード内で生成・マイグレーション処理が含まれている箇所があります（例: init_monitoring_db）。
- AI 関連機能は外部 API（OpenAI）に依存します。テスト時には _call_openai_api をモックする実装（コメントでその旨が明記）があります。
- 実環境での運用は資金リスクを伴います。Paper trading で十分に動作確認を行ってからライブ運用してください。

---

不明点や README に追加したい項目（例: 実際の requirements.txt、.env.example、起動時のログ例、運用手順書など）があれば教えてください。必要に応じて README を拡張します。