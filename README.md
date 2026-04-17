# KabuSys

日本株自動売買システムの一部（ライブラリ・運用ツール群）。  
この README はソースツリー（src/kabusys/*）を基にした利用・運用向けの概要ドキュメントです。

---

## プロジェクト概要

KabuSys は以下の機能を持つ自動売買プラットフォーム向けコンポーネント群を提供します。

- 注文作成・管理・再同期（ExecutionEngine / OrderManager / Reconciler）
- リスク管理（RiskManager、RiskMonitor）
- 監視（SystemMonitor、TradeMonitor、MonitoringEngine）
- 監視ログ永続化（SQLite）
- ファクター／リサーチ（ファクター計算、特徴量探索）
- ポートフォリオ構築（候補選定・重み算出・ポジションサイズ計算・セクター制限）
- AI連携（OpenAI を用いたニュースセンチメント、レジーム検出）
- 運用補助ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）
- プロセス優先度や CPU affinity 設定ユーティリティ

設計上の特徴：
- DuckDB / SQLite をデータ層に利用（価格・財務・ニュースは DuckDB、監視ログは SQLite）
- Paper Trading (= `KABUSYS_ENV=paper_trading`) 時は本番 DB と分離して `data/paper_trading.db` を使用
- .env / 環境変数経由で設定を注入（自動ロード機構あり）
- OpenAI API 呼び出しはフェイルセーフ実装（リトライやフォールバックあり）

---

## 主な機能一覧

- 実行（Execution）
  - ExecutionEngine（起動スクリプト: run_execution.py）
  - Broker クライアントファクトリ（本番／Mock 切替）
  - OrderManager / OrderRepository / Reconciler（再起動後の同期）
- 監視（Monitoring）
  - SystemMonitor（CPU/Memory/Disk・データ鮮度・実行プロセス監視）
  - TradeMonitor（滞留注文・約定異常価格検出）
  - RiskMonitor（ドローダウン・ポジション上限検出）
  - MonitoringEngine（複数監視を束ねたポーリング）
  - AlertManager（LINE Push 通知）
  - streamlit_dashboard（監視ダッシュボード）
- ポートフォリオ構築（純粋関数）
  - 候補選定、等分配・スコア重み、リスク調整、ポジションサイズ計算
- リサーチ
  - ファクター計算（momentum/value/volatility）
  - 未来リターン、IC 計算、統計サマリ
- AI モジュール
  - news_nlp（ニュースから銘柄別センチメント算出・ai_scores へ保存）
  - regime_detector（MA200 とマクロニュースで market_regime を判定）
- 運用ツール
  - paper_verification_report（Paper Trading 用検証レポート生成）

---

## セットアップ手順

前提
- Python 3.10 以上（型注釈の構文や union 型などを利用）
- Git 等でリポジトリをチェックアウト済み

1. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   主要依存（例）:
   - duckdb
   - psutil
   - requests
   - openai
   - streamlit
   - （標準ライブラリの sqlite3 は Python に同梱）
   例:
   - pip install duckdb psutil requests openai streamlit

   実運用では requirements.txt を用意して pip install -r requirements.txt を推奨します。

3. 環境変数 / .env
   リポジトリルートに `.env` / `.env.local` を置くと自動ロードされます（OS 環境変数が優先）。自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須（実行時に参照される主な環境変数）
   - JQUANTS_REFRESH_TOKEN（J-Quants API）
   - KABU_API_PASSWORD（kabuステーション API）
   - OPENAI_API_KEY（AI 機能を使う場合）
   - そのほか（オプション／デフォルト有り）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
     - PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（通知用）
     - LOG_LEVEL（DEBUG/INFO/...）
     - MONITOR_POLL_INTERVAL（監視ループポーリング秒数、デフォルト 60）
     - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START 等（監視制御）

4. 初期データディレクトリ作成（必要に応じて）
   - mkdir -p data

5. DB 初期化
   - 一部スクリプトは起動時に `init_monitoring_db()` を実行して必要テーブルを作成します。DuckDB 側の prices 等は別途データパイプラインで投入してください。

---

## 使い方（主要スクリプト・コマンド）

パッケージとしてモジュールを直接実行可能です（src 配下を PYTHONPATH に含めるかパッケージインストール後）。

- 監視プロセスを起動（ポーリングループ）
  - python -m kabusys.run_monitoring
  - 環境変数:
    - MONITOR_POLL_INTERVAL（秒、デフォルト 60）
  - 備考: Monitoring は `Settings.sqlite_path`（デフォルト: data/monitoring.db）を使用します。モニタは KABUSYS_ENV にかかわらず本番 sqlite_path を参照します。

- 実行エンジンを起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker が使用され、paper_trading 用 DB（デフォルト: data/paper_trading.db）へ記録され、本番 DB と分離されます。
  - 実行中は PID が `data/execution.pid` に書かれ、外部から `data/stop_requested.flag`（停止）や `data/kill.flag`（停止トリガ）を扱う設計です。

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視データを読み取り専用で可視化します。MonitoringEngine を先に実行してログを貯めてください。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to   YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数の代替）

- AI 機能
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API キーは引数で渡すか OPENAI_API_KEY 環境変数を設定してください。

運用上のフラグファイル（デフォルト path は Settings で指定可）
- data/stop_requested.flag : 実行スクリプトが監視している停止フラグ（外部から作成するとプロセスが停止）
- data/kill.flag : KillSwitch によって書き込まれる（ExecutionEngine 停止シグナル）
- data/execution.pid : 実行エンジンの PID 管理

例（バックグラウンド起動）
- nohup python -m kabusys.run_monitoring &

ログレベルは LOG_LEVEL 環境変数で制御可能（INFO デフォルト）。

---

## 設定（主な環境変数）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabu API のパスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時）
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 用の約定モード）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視ログ用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH: 実行エンジン PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動で消す場合は "1"
- MONITOR_POLL_INTERVAL: 監視ループ間隔（秒、デフォルト: 60）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

Settings クラスにより環境変数は静的プロパティで取得され、値の検証（有効な列挙値チェック等）が行われます。

---

## ディレクトリ構成（主要ファイルと説明）

src/kabusys/
- __init__.py
  - パッケージメタ情報（__version__ 等）
- config.py
  - 環境変数/.env の読み込みロジックと Settings 定義
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL に対応）
- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading に応じて DB / broker を切替）
- execution/
  - broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py ...（発注・注文管理・リコンシリエーション）
- monitoring/
  - monitoring_db.py : SQLite による永続化層（テーブル定義・アップサート等）
  - system_monitor.py : CPU/MEM/DISK・データ鮮度・PID監視
  - trade_monitor.py : 滞留注文・約定異常価格検出
  - risk_monitor.py : ドローダウン・ポジション上限監視
  - kill_switch.py : フラグファイルによる Engine 停止判定
  - alert_manager.py : LINE へプッシュ通知
  - monitoring_engine.py : 各 monitor を束ねる
  - streamlit_dashboard.py : 監視ダッシュボード
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py（候補選定・重み・株数算出）
- research/
  - factor_research.py, feature_exploration.py（ファクター計算、IC、統計）
- ai/
  - news_nlp.py（ニュースを LLM でスコアリング）、regime_detector.py（市場レジーム判定）
- tools/
  - paper_verification_report.py（Paper Trading の検証レポート）
- utils/
  - process_priority.py（プロセス優先度 / CPU affinity ユーティリティ）

（詳細なファイル一覧はリポジトリ内の src/kabusys 配下を参照してください）

---

## 運用上の注意

- Paper Trading は本番 DB と分離されていますが、設定ミスで上書きしないよう `.env` を慎重に管理してください。
- OpenAI API 等の外部 API 利用時はキーの管理とコストに注意してください。AI 呼び出しはバッチ・リトライ・クリップ等の保護が入っていますが、想定外のトラフィックに注意。
- Monitoring は `Settings.sqlite_path` を使っており、環境（development/live/paper）によらず同じ監視 DB を参照します（設計上の意図）。
- kill.flag / stop_requested.flag による外部停止制御をサポートしています。意図しない削除/書き込みに注意してください。
- プロセス優先度や CPU affinity の変更はプラットフォーム依存です（psutil に委任）。権限不足や未対応 OS の場合は警告を出してスキップします。

---

## 開発・拡張のヒント

- DuckDB 上の prices_daily / raw_financials / raw_news 等のテーブルを充実させることで、research / ai / regime の精度が向上します。
- 新しい通知チャネルを追加する場合は AlertManager を拡張してください（現在 LINE）。
- テスト時に .env の自動ロードが邪魔な場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して無効化できます。
- AI 呼び出しのテストは公開関数のモック（例: unittest.mock.patch）で API 呼び出し部を置き換えると容易です（score_news, score_regime など）。

---

README は以上です。必要があれば以下を追記できます：
- 具体的な .env.example のテンプレート
- requirements.txt の推奨内容
- よくある運用コマンドやトラブルシュート集（PID / kill.flag / DB マイグレーション等）