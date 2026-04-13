# KabuSys

日本株自動売買システムのモジュール群（ライブラリ＋起動スクリプト・監視・解析ツール）です。  
このリポジトリには、取引実行周りの管理、監視・アラート、ポートフォリオ構築ロジック、リサーチ用ファクター計算、ニュース NLP（OpenAI）連携などの機能が含まれます。

---

## プロジェクト概要

- 実運用を想定した自動売買プラットフォームのコンポーネント群
- 監視（SystemMonitor / TradeMonitor / RiskMonitor）とアラート（LINE）
- ExecutionEngine 起動スクリプト（paper_trading モードでの分離動作）
- DuckDB/SQLite を用いたデータ解析・永続化
- ニュースを LLM（OpenAI）でスコアリングする AI モジュール
- ポートフォリオ構築・リスク調整・ポジションサイジング関数群
- リサーチ用（ファクター計算・IC 計算・特徴量探索）モジュール
- Streamlit ベースの監視ダッシュボード
- 各種 CLI / モジュールはテストや再起動に耐えるよう設計されています

---

## 主な機能一覧

- 監視
  - SystemMonitor: CPU/メモリ/ディスクの監視、プロセス存在確認、データ鮮度チェック
  - TradeMonitor: 注文の滞留・約定異常価格検出
  - RiskMonitor: ドローダウン・ポジション上限チェック、ダッシュボード更新
  - MonitoringEngine: これらの監視を定期実行、KillSwitch と AlertManager 統合
  - AlertManager: LINE Messaging API によるプッシュ通知（クールダウン管理）
  - Streamlit ダッシュボード: 監視データ可視化（read-only）
- 実行（概念）
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - OrderManager / OrderRepository / Reconciler: 発注・状態管理・復旧処理
  - paper_trading モード: MockBroker を使用し、本番 DB と分離された SQLite を使用
- AI（OpenAI）
  - news_nlp.score_news: ニュース記事を集約し LLM で銘柄ごとにセンチメントを付与して ai_scores に保存
  - regime_detector.score_regime: ma200 乖離とマクロニュースから市場レジーム判定を行い market_regime に保存
- Portfolio（純粋関数）
  - 候補選定、等ウェイト/スコア重み、セクター上限適用、レジーム乗数、ポジションサイズ計算（lot 単位で丸め）
- Research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン・IC（Spearman）・統計サマリー等のユーティリティ
- ツール
  - paper_verification_report: Paper Trading の検証レポートを生成（稼働率／成功率／レイテンシ等）
- ユーティリティ
  - 環境変数ローダ（.env 自動ロード）、プロセス優先度／CPU affinity 設定

---

## 要求環境（主な依存）

（プロジェクトに requirements.txt が無い場合は下記パッケージをインストールしてください）

- Python 3.9+
- duckdb
- psutil
- requests
- openai
- streamlit
- （SQLite は標準ライブラリ）

例:
pip install duckdb psutil requests openai streamlit

---

## 環境変数（主要なもの）

Settings クラスで扱うキー（デフォルト値や必須の有無を併記）:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意, default: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能利用時に必要)
- LINE_CHANNEL_ACCESS_TOKEN (任意、AlertManager 用)
- LINE_USER_ID (任意、AlertManager 用)
- DUCKDB_PATH (任意, default: data/kabusys.duckdb)
- SQLITE_PATH (任意, default: data/monitoring.db) — 監視用 DB（Monitoring は環境に関係なく本番 sqlite_path を使用）
- PAPER_TRADING_SQLITE_PATH (任意, default: data/paper_trading.db) — paper_trading 用専用 DB
- PAPER_FILL_MODE (optional, default: "instant") — paper_trading の填埋モード (instant|partial|never|reject)
- PID_FILE_PATH (任意, default: data/execution.pid)
- KILL_FLAG_PATH (任意, default: data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (optional: "1" to enable)
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT（監視閾値）
- KABUSYS_ENV (development | paper_trading | live) — 環境モード
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)

その他:
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）。デフォルト 60。環境変数で上書き可能。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効化できます。

.example の記述例（.env）:
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
OPENAI_API_KEY=...
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install duckdb psutil requests openai streamlit

3. 環境変数を設定
   - 重要な秘密鍵は環境変数で設定する（またはプロジェクトルートに .env/.env.local を置く）
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
   - OpenAI を使う場合: OPENAI_API_KEY を設定

4. データディレクトリ作成（必要に応じて）
   - mkdir -p data

5. 初回起動時に監視 DB のテーブルは自動作成されます（init_monitoring_db を通じて）

---

## 使い方（起動方法 / コマンド例）

- 監視ループを起動（SystemMonitor のポーリングのみの簡易起動）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で変更可能（デフォルト 60）
  - run_monitoring 実行時はプロセス優先度を "high" に設定し、monitoring 用 SQLite（Settings.sqlite_path）を使用します

- 実行エンジンを起動（取引実行）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使用され、PAPER_TRADING_SQLITE_PATH（data/paper_trading.db）に記録されます（本番 DB と分離）
  - 実行時にプロセス優先度を "high" に設定します

- Paper Trading 検証レポート（コマンドライン）
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH より優先）
  - 出力: 稼働率、注文成功率、送信率、レイテンシ P95 などのレポートと PASS/FAIL 判定

- Streamlit ダッシュボード（監視データ閲覧）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用（URI with mode=ro）で開きます。MonitoringEngine が書き込んでいることが前提

- AI 機能（ニュース NLP / レジーム判定）
  - kabusys.ai.score_news および kabusys.ai.regime_detector.score_regime を呼び出して使用
  - 実行には OPENAI_API_KEY が必要
  - API 呼び出しはリトライ・バックオフやレスポンス検証等の安全策を備えています

注意:
- 監視（Monitoring）はいずれの環境でも Settings.sqlite_path（通常 data/monitoring.db）を使用してログを保存します。paper_trading モードでも監視は本番 monitoring DB を使う点に留意してください（run_execution は paper_trading 時に発注 DB を別ファイルに分離）。

---

## 実装上のポイント / 動作仕様（抜粋）

- 環境の自動読み込み:
  - プロジェクトルート（.git / pyproject.toml を基準）から .env/.env.local を自動ロード（OS 環境変数が優先、.env.local は上書き）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能

- DB 初期化:
  - init_monitoring_db() により監視用 SQLite のテーブルと必要なマイグレーション（列追加）を冪等に作成します

- プロセス優先度:
  - 起動スクリプトは psutil を用いてプロセス優先度を "high" に設定しようとします（失敗時は警告でスキップ）

- Kill Switch / 停止フラグ:
  - KillSwitch は KILL_FLAG_PATH に理由テキストを記したファイルを書き込むことで ExecutionEngine 停止シグナルを与えます（既存の flag は上書きしない）

- Paper Trading:
  - PAPER_FILL_MODE によりモックの約定動作を制御（instant, partial, never, reject）
  - Paper Trading は実際のブローカーを用いず、発注結果は専用 SQLite に記録されます

- AI（OpenAI）連携:
  - LLM の結果は JSON で受け取り検証後に DuckDB のテーブルへ保存します
  - レートリミットや 5xx などの一時的エラーは指数バックオフでリトライ
  - API の失敗はフェイルセーフとしてスコア 0 またはスキップで続行される設計

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                          — 環境変数/.env 管理
- run_monitoring.py                  — SystemMonitor ポーリング起動スクリプト
- run_execution.py                   — ExecutionEngine 起動スクリプト
- utils/
  - __init__.py
  - process_priority.py               — プロセス優先度 / CPU affinity ユーティリティ
- monitoring/
  - __init__.py
  - monitoring_db.py                  — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
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
  - (その他: broker_factory, execution_engine, order_repository, order_record など。起動ロジックは run_execution から組み立てられる)
- portfolio/
  - __init__.py
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- tools/
  - __init__.py
  - paper_verification_report.py

その他: data/ ディレクトリ（DuckDB/SQLite ファイル等を置く想定）

---

## 開発メモ / 注意事項

- 実行スクリプトはプロセス優先度設定を試みますが、環境依存で失敗する可能性があります（権限が必要）。失敗しても動作継続します。
- DuckDB 接続はリサーチ/AI モジュールで大量の SQL を実行します。テーブル（prices_daily, raw_financials, raw_news など）は事前にロードしておく必要があります。
- Monitoring の DB（monitoring.db）は監視ログ用に常に存在する想定です。初回は run_monitoring/run_execution が init_monitoring_db を呼び出してテーブルを作成します。
- OpenAI API を用いる機能は API キーと使用料が必要です。開発時はモック化してテストすることを推奨します（モジュール内で API 呼び出し関数を差し替え可能）。
- Paper Trading 用の DB は本番 DB と明確に分離されます。paper_trading モードでの検証に利用してください。

---

## よくある起動例

- 監視開始（60秒間隔）:
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring

- Execution 起動（paper_trading）:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Paper 検証レポート（2026-04-01〜2026-04-11）:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

もし README をプロジェクトのルートに合わせて調整（依存の固定化、requirements.txt や setup.py/pyproject.toml 追加、より詳細な環境変数一覧の表記など）が必要であれば、その情報を教えてください。README をそれに合わせて更新します。