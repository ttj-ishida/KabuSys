# KabuSys

小型日本株向け自動売買フレームワークの簡易実装です。  
このリポジトリは、シグナル → 発注 → 監視 → リコンシリエーション等の主要コンポーネントを備え、Paper Trading と Live の切替、監視ダッシュボード、AI を用いたニュースセンチメント評価などの機能を提供します。

---

## 概要

KabuSys は以下を目的としたモジュール群を含みます：

- ExecutionEngine（発注・注文管理・リスク管理・リコンシリエーション）
- Monitoring（システム状態・注文状況・リスク監視、LINE 通知・kill switch）
- Portfolio（銘柄選定、配分・ポジションサイズ計算）
- Research（ファクター計算、特徴量解析）
- AI（ニュースの NLP によるセンチメント計算、レジーム判定）
- Tools（レポート生成、ダッシュボード用スクリプト）

設計方針の一部：
- DB は SQLite（監視用 / paper_trading 用）と DuckDB（時系列・ファクター計算）を利用
- Paper Trading は本番 DB と分離（`data/paper_trading.db` を使用）
- OpenAI（gpt-4o-mini）を利用した NLP 機能あり（API キー必須）
- .env / .env.local による環境変数自動ロード（必要に応じて無効化可能）

---

## 主な機能一覧

- Execution
  - ExecutionEngine による発注セッション実行（run_execution.py）
  - Broker 抽象化（実運用 / モック切替）
  - リスク管理（利用率・最大ポジション・ドローダウン等）
  - リコンシリエーション（起動時にブローカーと注文/ポジションを突合）

- Monitoring
  - SystemMonitor（CPU/MEM/Disk、プロセス存在、データ鮮度）
  - TradeMonitor（滞留注文、約定異常価格検出）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - KillSwitch（条件達成時に `data/kill.flag` を書き込み Execution 停止）
  - AlertManager（LINE Push による通知）
  - Streamlit ベースの監視ダッシュボード（read-only で SQLite を参照）

- Portfolio / Research
  - 候補選定、等重・スコア重み、リスク基準でのポジションサイズ計算
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 上で SQL 実行）
  - 将来リターン・IC 計算等の研究用ユーティリティ

- AI
  - ニュース記事の銘柄別センチメント評価（OpenAI）
  - マクロニュース + MA200 を用いた市場レジーム判定（OpenAI と組合せ）

- Tools
  - Paper Trading 検証レポート生成（tools.paper_verification_report）
  - Streamlit ダッシュボード起動スクリプト

---

## 前提 / 必要環境

- Python 3.10+
- 必須パッケージ（主なもの）
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit（ダッシュボードを使う場合）
- SQLite（標準ライブラリで利用）
- ネットワーク接続（OpenAI / LINE API / ブローカー API を使う場合）

※ 実際の運用では requirements.txt を用意し pip install -r で管理してください（本リポジトリには含まれていません）。

---

## セットアップ手順（開発マシン向け例）

1. リポジトリをクローンし、仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb psutil openai requests streamlit

3. data ディレクトリ作成（スクリプト実行時に自動作成される場合もあります）
   - mkdir -p data

4. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くことで自動読み込みされます（OS 環境変数が優先）。
   - 自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. 重要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
   - KABU_API_PASSWORD: kabuステーション（ブローカー）パスワード（必須）
   - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合に必須）
   - KABUSYS_ENV: one of development | paper_trading | live（デフォルト: development）
   - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）
   - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）

6. （任意）.env の例
   - KABUSYS_ENV=development
   - JQUANTS_REFRESH_TOKEN=xxxxx
   - KABU_API_PASSWORD=xxxxx
   - OPENAI_API_KEY=sk-xxxxx
   - PAPER_FILL_MODE=instant

---

## 使い方（実行例）

- 監視ループ（SystemMonitor 単体を起動）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（例: MONITOR_POLL_INTERVAL=30）

- 実行エンジン（ExecutionEngine）
  - python -m kabusys.run_execution
  - Paper Trading モードで起動する場合:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - paper_trading 時は MockBrokerClient を使用し、DB は `PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）に分離されます。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - `--db` オプションで別 DB を指定できます（環境変数 PAPER_TRADING_SQLITE_PATH より優先）。

- Streamlit ダッシュボード（監視画面）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは監視用 SQLite を read-only で参照します。MonitoringEngine が `data/monitoring.db` を更新していることが前提です。

- 停止制御 / フラグ
  - run_* スクリプトはいずれもプロジェクトルートの `data/stop_requested.flag` をチェックします。存在するとループを終了します。
    - 例えば一時停止・シャットダウン要求は `touch data/stop_requested.flag` で行えます（削除は手動で）。
  - ExecutionEngine を即時停止する安全スイッチ（KillSwitch）は `data/kill.flag` に理由を書き込むことで作動し、Engine 側で検出すると停止します。
    - KillSwitch の clear（起動時クリア）や手動での削除を行ってください。

---

## 設定（Settings）に関する注意

- 自動ロード順序:
  - OS 環境変数 > .env.local > .env
  - 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
  - プロジェクトルートは `.git` または `pyproject.toml` を上位ディレクトリから探索して決定します。見つからない場合は自動ロードをスキップします。

- 主要デフォルト値
  - KABUSYS_ENV: development
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - DUCKDB_PATH: data/kabusys.duckdb
  - PID_FILE_PATH: data/execution.pid
  - KILL_FLAG_PATH: data/kill.flag
  - MONITOR_POLL_INTERVAL: 60（秒）

- Paper Trading の挙動:
  - KABUSYS_ENV=paper_trading の場合、実行エンジンは MockBroker を使用し、paper_trading 用に別 SQLite を使います（本番 DB と完全分離）。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 配下の主要モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - ai/
    - __init__.py
    - news_nlp.py             — ニュース NLP（OpenAI）による銘柄別スコアリング
    - regime_detector.py      — レジーム判定（MA200 + マクロセンチメント）
  - monitoring/
    - __init__.py
    - monitoring_db.py       — SQLite スキーマ / DB ラッパー
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - alert_manager.py
    - kill_switch.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - reconciler.py
    - order_manager.py
    - (その他: broker_factory, execution_engine, order_repository などが存在)
  - portfolio/
    - portfolio_builder.py
    - risk_adjustment.py
    - position_sizing.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - process_priority.py     — psutil を使ってプロセス優先度 / CPU affinity を設定

---

## 運用上の注意 / トラブルシューティング

- psutil による優先度設定は権限が必要な場合があります。失敗すると警告が出力されますが、処理は継続します。
- OpenAI API 呼び出しはネットワーク・API レート制限の影響を受けます。news_nlp / regime_detector は複数回のリトライ・バックオフを実装していますが、API キーの設定と利用量に注意してください。
- DuckDB の接続先ファイル（DUCKDB_PATH）はファイルベースの DB です。データファイルのバックアップ・管理を行ってください。
- .env のロード順に注意してください。OS 環境変数が最優先で、.env.local が .env を上書きします。
- 監視 / 実行スクリプトは `data/stop_requested.flag` をチェックして安全にシャットダウンする仕組みがあります。CI / 管理操作でフラグを使ってプロセス制御可能です。

---

## 開発に関する補足

- テスト容易性のため、OpenAI 呼び出し等は内部で分離されており、ユニットテストから差し替え（モック）できます（例: news_nlp._call_openai_api を patch）。
- DB スキーマは monitoring_db.init_monitoring_db() によって冪等に作成 / マイグレーションが実行されます。起動時に自動で作られます。
- Research/Portfolio モジュールは外部 API に依存せず、DuckDB 上の prices_daily / raw_financials テーブルのみを参照する純粋関数群として実装されています。

---

必要であれば、README にサンプル .env.example、起動シェルスクリプト、requirements.txt の雛形、あるいは各モジュールの API 参照（関数一覧・引数説明）を追記できます。どの情報を優先して追加しますか？