# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買・モニタリング基盤のコードベースです。戦略の研究・ファクター計算、ポートフォリオ構築、発注実行（本番 / ペーパー分離）、監視・アラート、LLM を用いたニュース解析など、運用に必要な主要コンポーネントを含みます。

---

## 概要

- 自動売買用の ExecutionEngine を中心に、ブローカー抽象化層、注文管理、リスク管理、起動時リコンシリエーションを提供します。
- 監視サブシステムはシステム状態・注文滞留・ドローダウン等を定期的にチェックし、SQLite にログを残します。LINE によるプッシュ通知や kill.flag による ExecutionEngine 停止シグナル送出をサポートします。
- 研究用モジュールは DuckDB を使ったファクター計算、将来リターン計算、IC などの解析機能を持ちます。
- AI モジュールは OpenAI を用いたニュースセンチメントやマクロセンチメント（市場レジーム判定）を実装しています。Paper Trading（シミュレーション）用に本番 DB と完全に分離した仕組みあり。
- 開発・運用で使う CLI / スクリプト類（実行 / 監視 / 検証レポート / Streamlit ダッシュボード）を同梱しています。

---

## 主な機能一覧

- Execution
  - ExecutionEngine（起動・セッション実行）
  - BrokerClientFactory（本番 / Mock 切替）
  - OrderManager / OrderRepository（注文ライフサイクル管理）
  - Reconciler（起動時リコンシリエーション）
  - RiskManager（ポジション上限・利用率など）
- Monitoring
  - SystemMonitor（CPU / メモリ / ディスク / プロセス / データ鮮度）
  - TradeMonitor（滞留注文・約定異常価格検出）
  - RiskMonitor（ドローダウン / ポジション数監視）
  - MonitoringDB（SQLite スキーマ / 永続化）
  - AlertManager（LINE 通知、クールダウン管理）
  - KillSwitch（flag ファイルで ExecutionEngine 停止指示）
  - MonitoringEngine（複数 Monitor の統合ポーリング）
  - Streamlit ダッシュボード（監視データ可視化）
- Portfolio construction
  - 候補選定、等金額 / スコア重み付け、リスク調整（セクターキャップ・レジーム乗数）、ポジションサイズ計算（単元丸め／aggregate cap）
- Research
  - ファクター計算（モメンタム・ボラティリティ・バリュー）
  - 将来リターン計算、IC（スピアマン）算出、統計サマリ
- AI / NLP
  - news_nlp: ニュース記事のセンチメントを OpenAI で算出し ai_scores に格納
  - regime_detector: ETF の MA とマクロニュースセンチメントを合成して日次レジーム判定
- Tools
  - Paper Trading 検証レポート生成（期間指定可）
- 環境管理
  - Settings（.env 自動ロード、環境変数による設定、ペーパー用 DB 分離）

---

## セットアップ手順（開発 / ローカル実行向け）

前提: Python 3.9+（typing の一部構文利用のため。環境に合わせて調整してください）

1. リポジトリをクローン / ワークディレクトリへ移動

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Unix/macOS)
   - .venv\Scripts\activate     (Windows)

3. 必要パッケージをインストール
   - 主要インポートを元にした推奨パッケージ:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit
   - 例:
     - pip install duckdb psutil requests openai streamlit

   （本リポジトリに requirements.txt がある場合はそちらを使用してください）

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に .env / .env.local を置くと自動読み込みされます（既存 OS 環境変数が優先）。
   - 自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 最低限設定すべき（用途に応じて）環境変数例:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...          (AI 機能を使う場合)
     - KABUSYS_ENV=development | paper_trading | live
     - PAPER_FILL_MODE=instant | partial | never | reject
     - LOG_LEVEL=INFO
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
   - Settings クラスは多くの値を環境変数から読み取ります。未設定の必須項目は起動時にエラーになります。

5. データディレクトリ作成
   - data/ 配下に DB 等を配置する想定です（例: data/monitoring.db, data/paper_trading.db, data/kabusys.duckdb）。必要に応じて作成してください。

---

## 使い方（主要スクリプト）

- 監視ループを開始
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60）
  - 例:
    - python -m kabusys.run_monitoring
    - 実行時にプロセス優先度を "high" に設定し、監視テーブルを初期化してポーリングを開始します。

- ExecutionEngine を起動（本番 / ペーパー切替）
  - Paper Trading:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
      - Paper 実行時は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）へ記録します（本番DBと分離）。
  - Live:
    - KABUSYS_ENV=live python -m kabusys.run_execution

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション:
    - --db PATH    : SQLite ファイルを指定（デフォルト PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）

- Streamlit ダッシュボード（監視データ閲覧）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 読み取り専用で SQLite DB を開き、Overview / Positions / Orders / System タブを表示します。

- AI 系スコアリング・レジーム判定（ライブラリ API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続を受け取り、ai_scores / market_regime などのテーブルに書き込みます。OPENAI_API_KEY を渡すか環境変数で提供してください。

その他、各モジュールはライブラリとして直接インポートしてユニットテストやバッチ処理から使用できます。

---

## 主要な構成設定（主な環境変数）

- KABUSYS_ENV: development | paper_trading | live（Settings.env）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用
- KABU_API_PASSWORD: kabuステーション API 用
- OPENAI_API_KEY: OpenAI API 用（AI 機能に必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（ペーパーフィルモード）
- PID_FILE_PATH / KILL_FLAG_PATH: pid / kill.flag ファイルパス
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）

（詳細は src/kabusys/config.py を参照）

---

## ディレクトリ構成

（抜粋 / 主要ファイルのみ）

- src/
  - kabusys/
    - __init__.py                 — パッケージ定義 (version 0.1.0)
    - config.py                   — 環境変数 / Settings 管理（.env 自動読み込み）
    - run_execution.py            — ExecutionEngine 起動スクリプト
    - run_monitoring.py           — SystemMonitor ポーリング起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト
    - execution/
      - order_manager.py
      - reconciler.py
      - (Broker, Engine 等他モジュール)
    - monitoring/
      - monitoring_db.py          — SQLite スキーマ / 永続化層
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py
      - monitoring_engine.py
      - streamlit_dashboard.py
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
    - utils/
      - process_priority.py        — プロセス優先度・CPU affinity 設定ユーティリティ
    - data/ (想定)
      - （DuckDB, SQLite 等の DB ファイルを置く既定の場所）
  - pyproject.toml / setup や CI 設定（プロジェクトルート）

---

## 運用上の注意 / 補足

- .env 自動読み込み: プロジェクトルートが特定できる場合、.env（→OS 環境変数より優先度低）および .env.local（上書き可）を自動で読み込みます。自動読み込みを停止するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading と本番 DB は完全に分離されています（PAPER_TRADING_SQLITE_PATH を使用）。ペーパー実行時は MockBrokerClient を使います。
- 実行スクリプトは起動時にプロセス優先度を "high" に設定しようとします（psutil を利用）。権限不足などで失敗した場合は警告を出して継続します。
- kill.flag による停止: KillSwitch により data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送れます。Execution 側はこのフラグを監視して停止処理を行う想定です。
- DuckDB / SQLite のバージョン差異に注意（executemany の空リストバインドなど互換性処理あり）。
- AI（OpenAI）呼び出しは API エラー時にリトライやフォールバック処理を内包しますが、APIキーの管理・コスト・レイテンシには注意してください。

---

## 参考コマンドまとめ

- 監視の開始:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Execution 起動（Paper）:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Paper 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

README に記載のない内部 API / 詳細な仕様は各ソースファイルの docstring / コメントを参照してください。必要に応じて README を拡張しますので、追加で含めたい情報（例えば要求される Python バージョン、CI 手順、具体的な .env.example）を教えてください。