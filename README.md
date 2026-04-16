# KabuSys

日本株自動売買システムの一部（監視 / 実行 / ポートフォリオ構築 / リサーチ / AI 連携など）。  
この README はリポジトリ内の主要コンポーネントから生成されています。

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 環境変数（.env）と設定
- 実行方法
  - 監視ループ（Monitoring）
  - 実行エンジン（Execution）
  - Paper Trading レポート生成ツール
  - Streamlit ダッシュボード
  - AI 関連（ニュース NLP / レジーム判定）
- 停止・キルスイッチの使い方
- ディレクトリ構成（主要ファイル一覧）
- 補足（依存関係・注意点）

---

## プロジェクト概要

KabuSys は日本株の自動売買を支えるモジュール群です。  
本リポジトリは監視（Monitoring）、実行（Execution）、ポートフォリオ構築（Portfolio）、リサーチ（Research）、AI（ニュースセンチメント・レジーム判定）などの機能を持つモジュールを提供します。  
SQLite / DuckDB を用いたローカルデータ管理、OpenAI API 連携、LINE 通知、プロセス優先度調整などを含みます。

---

## 主な機能一覧

- 監視
  - SystemMonitor: CPU/メモリ/ディスク、プロセス存在確認、データ鮮度チェック
  - TradeMonitor: 注文の滞留検出、約定価格の異常検出
  - RiskMonitor: ドローダウン監視、ポジション数監視、ダッシュボード更新
  - MonitoringEngine: 各 Monitor を周期的に呼ぶポーリングエンジン
  - AlertManager: LINE Messaging API による通知（クールダウン付き）
  - KillSwitch: しきい値超過時に停止フラグを書き込む
  - Streamlit ベースの監視ダッシュボード（読み取り専用）
  - monitoring DB 用の初期化ユーティリティ（init_monitoring_db）
- 実行（Execution）
  - ExecutionEngine（起動スクリプト run_execution.py 経由で実行）
  - Broker クライアント（実ブローカー／MockBroker 切替）
  - OrderManager / OrderRepository / Reconciler（再起動時の同期）
  - RiskManager（発注前の制約チェック）
- ポートフォリオ構築（純粋関数）
  - 候補選定、等配分・スコア配分、ポジションサイズ計算、セクターキャップ、レジーム乗数
- リサーチ
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン・IC 計算・統計サマリ
- AI（OpenAI）
  - news_nlp: raw_news を集約し OpenAI（gpt-4o-mini）で銘柄別センチメントを算出して ai_scores に書込
  - regime_detector: ETF（1321）の MA とマクロニュースの LLM センチメントを合成して market_regime に書込
- 開発用ツール
  - paper_verification_report: Paper Trading の検証レポート生成

---

## セットアップ手順

1. Python 仮想環境を作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール  
   （requirements.txt は本コードベースに含まれていませんが、主な依存は以下）
   - duckdb
   - psutil
   - openai
   - requests
   - streamlit
   - （その他、開発環境に応じて pytest 等）

   例:
   pip install duckdb psutil openai requests streamlit

3. .env の準備（プロジェクトルートに配置）
   - サンプルは次節「環境変数（.env）」を参照してください。

4. データディレクトリ作成
   - デフォルトでは data/ 配下に DB 等が置かれます。必要に応じて作成してください。
     mkdir -p data

5. （任意）自動的に .env を読み込む挙動を無効化する場合:
   - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

※ 注意: SQLite / DuckDB ファイルは実行時に必要に応じて作成・マイグレーションされます（init_monitoring_db が適用されます）。

---

## 環境変数（.env）と設定

自動ロード順は OS 環境 > .env.local > .env（プロジェクトルート）です。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

主な環境変数（抜粋・説明）:

- KABUSYS_ENV: 起動環境
  - 値: development | paper_trading | live
  - paper_trading の場合、MockBroker が使用され paper 専用 SQLite（PAPER_TRADING_SQLITE_PATH）に保存されます。

- DB / パス関連
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
  - PID_FILE_PATH (default: data/execution.pid)
  - KILL_FLAG_PATH (default: data/kill.flag)

- OpenAI / API
  - OPENAI_API_KEY (news/regime の API 呼び出しに使用)
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)

- LINE 通知
  - LINE_CHANNEL_ACCESS_TOKEN
  - LINE_USER_ID

- Paper Trading
  - PAPER_FILL_MODE: instant | partial | never | reject (default: instant)

- Monitoring
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用。デフォルト 60）
  - LOG_LEVEL: DEBUG/INFO/...

例（.env）:
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
OPENAI_API_KEY=...
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_USER_ID=...

---

## 実行方法

基本的にモジュールはパッケージエントリポイントとして実行できます（python -m kabusys.<module>）。

1) 監視ループ（Monitoring）
- スクリプト: src/kabusys/run_monitoring.py
- 起動例:
  - python -m kabusys.run_monitoring
- 挙動:
  - Settings を読み、指定された sqlite_path（monitoring DB）と duckdb を接続します。
  - init_monitoring_db() を呼び出し必要なテーブルを作成します（冪等）。
  - SystemMonitor を初期化して poll ループを開始します（デフォルト 60 秒）。
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書きできます（正の整数）。
  - 停止: プロジェクトルート data/stop_requested.flag の存在を検知するとループを終了します。

2) 実行エンジン（Execution）
- スクリプト: src/kabusys/run_execution.py
- 起動例:
  - python -m kabusys.run_execution
- 挙動:
  - KABUSYS_ENV が paper_trading の場合、MockBrokerClient を使用して PAPER_TRADING_SQLITE_PATH に記録し本番 DB と分離します。
  - 各コンポーネント（Broker, OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）を組み立て、別スレッドで実行します。
  - data/execution.pid に PID を書き込みます（設定で変更可）。
  - 起動時に data/stop_requested.flag が既に存在すると起動を中止します。
  - 停止: data/stop_requested.flag を作成するとエンジンに停止を指示します（監視側や手動で作成）。

3) Paper Trading 検証レポート
- スクリプト: src/kabusys/tools/paper_verification_report.py
- 実行例:
  - python -m kabusys.tools.paper_verification_report
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パス指定可（優先順: --db > 環境変数 PAPER_TRADING_SQLITE_PATH > data/paper_trading.db）
- 出力: 稼働率、注文成功率、送信率、レイテンシ指標、PASS/FAIL 判定

4) Streamlit 監視ダッシュボード（読み取り専用）
- ファイル: src/kabusys/monitoring/streamlit_dashboard.py
- 起動例:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 説明: monitoring DB を読み取り専用で開き、Overview / Positions / Orders / System タブを表示します。

5) AI 関連（ニュース NLP / レジーム判定）
- news_nlp.score_news(conn, target_date, api_key=None)
  - DuckDB 接続と対象日を渡すことで raw_news -> ai_scores に書き込みます。
  - OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY を使用します。
- regime_detector.score_regime(conn, target_date, api_key=None)
  - ETF 1321 の MA200 とマクロニュースの LLM スコアを合成して market_regime に書き込みます。
- 注意: API 呼び出し時はリトライ/フォールバックが実装されていますが、API キー未設定の場合は ValueError になります。

---

## 停止・キルフラグの使い方

- data/stop_requested.flag
  - run_monitoring.py と run_execution.py はこのファイルの存在を監視し、存在するとメインループを終了またはエンジンを停止します。
  - 監視ループやエンジンの安全停止用に使用できます。

- data/kill.flag
  - KillSwitch（Monitoring 側）の判定により書き込まれるフラグで、ExecutionEngine に対する停止シグナルの意味を持ちます。
  - ExecutionEngine 側では KILL_FLAG_PATH（Settings.kill_flag_path）を参照して挙動を制御できます。
  - KillSwitch はドローダウンやポジション上限超過などの条件でファイルを生成します。

- PID ファイル
  - ExecutionEngine はデフォルトで data/execution.pid を作成しプロセスの存在確認に使用します（SystemMonitor が stale PID を検出して削除する仕組みあり）。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py — 環境変数・設定管理（.env の自動ロード・Settings）
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト

modules:
- ai/
  - news_nlp.py — ニュースを LLM でスコアリングして ai_scores に書き込む
  - regime_detector.py — 市場レジーム判定と書込み
- monitoring/
  - monitoring_db.py — monitoring SQLite の初期化 & DB 操作ラッパー
  - system_monitor.py — システム状態・データ鮮度監視
  - trade_monitor.py — 注文滞留・約定異常監視
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - monitoring_engine.py — 各 Monitor の束ね
  - alert_manager.py — LINE 通知送信
  - kill_switch.py — kill.flag の作成/管理
  - streamlit_dashboard.py — Streamlit ダッシュボード
- execution/
  - reconciler.py — 再起動時の注文・ポジション同期間合
  - order_manager.py — 注文作成 / 同期 / 状態遷移の制御
  - （その他 execution 関連ファイルは省略：BrokerFactory 等）
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - risk_adjustment.py — セクター制限・レジーム乗数
  - position_sizing.py — 株数決定・投下資金のスケール
- research/
  - factor_research.py — モメンタム/ボラ/バリューなどのファクター計算
  - feature_exploration.py — 将来リターン・IC・統計サマリ
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート
- utils/
  - process_priority.py — クロスプラットフォームの優先度 / CPU affinity 設定

ドキュメントファイル（リポジトリにあれば）
- PortfolioConstruction.md, StrategyModel.md など（コード中に参照あり）

---

## 補足・注意点

- Paper Trading と本番 DB は分離されています（KABUSYS_ENV=paper_trading 時は paper_sqlite_path を使用）。
- Settings は起動時に .env / .env.local を自動で読み込みます（OS 環境変数を上書きしない挙動、.env.local は上書き可）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
- OpenAI API の呼び出しはリトライ・フォールバック（タイムアウト・429・5xx 等に対して指数バックオフ）を行いますが、API キーは必須です（未設定だと ValueError を送出）。
- プロセス優先度設定（set_process_priority）はプラットフォーム依存の制限（権限・OS 非対応）により失敗する場合があります。ログで警告されますが実行は継続します。
- DuckDB/SQLite のアクセスは同時実行やバージョンによる差に注意（例: DuckDB executemany の空リスト制約など、コード中で考慮済みのケースあり）。
- テストや CI の際は KABUSYS_DISABLE_AUTO_ENV_LOAD を検討してください。

---

もし README に追加したい具体的なインストール手順（requirements.txt を含めた例）や運用手順（systemd ユニット例、Dockerfile など）があれば、その情報を教えてください。README をその要件に合わせて追記します。