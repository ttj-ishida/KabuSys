# KabuSys

KabuSys は日本株向けの自動売買・リサーチ・監視を行う小規模なシステムです。本リポジトリは以下の機能群を含み、ローカル SQLite / DuckDB をデータ層に採用しています。

- 注文管理・実行エンジン（ExecutionEngine）
- 監視（System / Trade / Risk）とアラート（LINE）
- Paper Trading（本番 DB と分離されたモード）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- 研究用ファクター計算・特徴量探索（DuckDB ベース）
- ニュース NLP（OpenAI を用いた銘柄センチメント）と市場レジーム判定
- Streamlit ベースの監視ダッシュボード
- Paper Trading の検証レポート生成ツール

---

## 主な機能一覧

- Execution
  - ブローカー抽象化（実ブローカー / モックを切替）
  - 発注状態管理、再起動時のリコンシリエーション
  - リスク管理（ポジション上限・ドローダウンなど）
- Monitoring
  - システム資源（CPU/Memory/Disk）監視
  - 注文滞留・約定異常監視
  - リスクイベントログ、ダッシュボード集計
  - Kill Switch（条件で停止フラグを書き込み、Execution を止める）
  - LINE によるアラート送信（AlertManager）
- Portfolio
  - 候補選定（スコア順）
  - 等金額 / スコア重み付け
  - リスク調整（セクターキャップ、レジーム乗数）
  - 株数決定（単元丸め、投下上限、集約キャップ）
- Research
  - Momentum / Volatility / Value ファクター計算（DuckDB）
  - 将来リターン、IC（Spearman）、統計サマリー
- AI
  - ニュース記事をまとめて OpenAI で銘柄ごとにセンチメントを算出（ai_scores に格納）
  - マクロニュース + ETF MA200 乖離から日次レジーム判定（bull/neutral/bear）
- Tools
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）
  - Streamlit ダッシュボード（監視データ可視化）

---

## 動作要件（想定）

- Python 3.10+
- パッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード使用時)
- SQLite は標準ライブラリで利用可能

requirements.txt は同梱されていません。次のようにインストールしてください（仮想環境推奨）:

pip install duckdb psutil requests openai streamlit

（実運用ではバージョン固定を推奨します）

---

## セットアップ手順（クイックスタート）

1. リポジトリをクローンして仮想環境を作成・有効化します。

   git clone <リポジトリURL>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate

2. 必要パッケージをインストールします。

   pip install duckdb psutil requests openai streamlit

3. 環境変数を設定します。
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただし OS 環境変数が優先されます）。
   - 自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

4. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
   - KABU_API_PASSWORD — kabuステーション API パスワード
   - （OpenAI 機能を使う場合）OPENAI_API_KEY
   - （LINE 通知を使う場合）LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID

5. データディレクトリ作成（必要に応じて）

   mkdir -p data

---

## 主な環境変数（例と説明）

- KABUSYS_ENV: execution の動作環境
  - 値: development, paper_trading, live
  - paper_trading の場合、MockBrokerClient を使用し DB は `data/paper_trading.db`（Settings.paper_sqlite_path）に分離されます
- SQLITE_PATH: Monitoring 用 SQLite（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の注文充足モード（instant|partial|never|reject）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必要）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
- KABUSYS_DISABLE_AUTO_ENV_LOAD: "1" を設定すると .env 自動読み込みを無効化

サンプル .env（プロジェクトルート）:

JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=xxxx
OPENAI_API_KEY=sk-...
KABUSYS_ENV=development
SQLITE_PATH=data/monitoring.db
DUCKDB_PATH=data/kabusys.duckdb
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=

---

## 使い方（主要スクリプト）

- 監視ループの起動

  python -m kabusys.run_monitoring

  オプション:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒数で上書き可能（例: export MONITOR_POLL_INTERVAL=30）
  - run_monitoring は常に Settings.sqlite_path（本番の monitoring DB）を使用します
  - 停止: プロジェクトルートの data/stop_requested.flag ファイルを作成すると監視ループが終了します

- 実行エンジン（ExecutionEngine）起動

  python -m kabusys.run_execution

  注意:
  - KABUSYS_ENV=paper_trading を設定すると Paper Trading 専用 DB（PAPER_TRADING_SQLITE_PATH）と MockBrokerClient を使用します（本番 DB と完全分離）
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します
  - 実行中に停止したい場合は同ファイルを作成すると安全に停止要求を送れます

- Streamlit 監視ダッシュボード

  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

  読み取り専用で SQLite を開く（存在しない場合はエラーを出します）。MonitoringEngine を先に起動しておくこと。

- Paper Trading 検証レポート

  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  --db オプションで DB を指定可能。デフォルトは data/paper_trading.db。

- AI / リサーチ機能（ライブラリ呼び出し）
  - ニュース NLP（銘柄センチメント）: kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 研究関数（例）: kabusys.research.calc_momentum(duckdb_conn, date)
  これらは Python から直接呼び出して利用します。OpenAI API を使う場合は OPENAI_API_KEY を渡すか環境変数に設定してください。

---

## 停止・制御フロー

- stop_requested.flag: run_monitoring / run_execution が監視している停止フラグ（data/stop_requested.flag）
- kill.flag: KillSwitch が書き込む停止指示（ExecutionEngine に停止を促すために利用）
- PID ファイル: Execution 起動時に data/execution.pid（デフォルト）に PID を書く設計（SystemMonitor はこの PID を参照してプロセス生存をチェックする）

---

## DB・マイグレーション

- Monitoring の DB 初期化は init_monitoring_db(conn) により冪等に作成されます。起動時に自動で必要なテーブル・カラムが作られます。
- 監視データは SQLite（Settings.sqlite_path）に、時系列・ログ・dashboard 集計が保存されます。
- DuckDB は時系列・価格データ・raw_financials などの研究用テーブルを格納する想定です（Settings.duckdb_path）。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                     — 環境変数 / 設定読み込みロジック（.env 自動ロード）
- run_monitoring.py             — SystemMonitor ポーリング起動スクリプト
- run_execution.py              — ExecutionEngine 起動スクリプト
- utils/
  - process_priority.py         — プロセス優先度・CPU affinity ユーティリティ
- monitoring/
  - __init__.py
  - monitoring_db.py            — SQLite 永続化層（テーブル作成・読み書き）
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - monitoring_engine.py
  - kill_switch.py
  - alert_manager.py
  - streamlit_dashboard.py
- execution/
  - order_manager.py
  - reconciler.py
  - (その他 execution 関連モジュール)
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
  - __init__.py
- research/
  - factor_research.py
  - feature_exploration.py
  - __init__.py
- ai/
  - news_nlp.py
  - regime_detector.py
  - __init__.py
- tools/
  - paper_verification_report.py

（省略されたファイル群は上記一覧に含まれる責務を参照してください）

---

## 補足・運用上の注意

- Paper Trading モードは本番 DB と完全分離される旨に注意してください（PAPER_TRADING_SQLITE_PATH）。
- OpenAI を使う処理は API 呼び出しがあるためレート制限やネットワークエラーに注意。モジュールはリトライやフェイルセーフ（失敗時に中立値を使う等）を備えていますが、API キー管理には注意してください。
- psutil によるプロセス優先度設定や CPU affinity の変更は OS 権限やプラットフォーム依存で失敗することがあります（警告を出してスキップされます）。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）から行われます。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- SQLite / DuckDB のファイルを別プロセスで直接書き換えると整合性に影響する可能性があるため同時書き込みは注意してください（読み取り専用で開く等の配慮を行ってください）。

---

必要であれば、README に設定可能な環境変数一覧をより詳しく追記したり、各モジュールの API 使用例（短いコードスニペット）を追加できます。どの情報を優先して追記しますか？