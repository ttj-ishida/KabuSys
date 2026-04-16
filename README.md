# KabuSys

日本株向け自動売買基盤の内部モジュール群（ライブラリ／ランタイムスクリプト群）のリポジトリ。  
この README はソースツリー（src/kabusys 以下）に基づいて、概要・機能・セットアップ・実行方法・ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けのコンポーネント群を提供します。  
主な役割は以下の通りです。

- 注文管理・実行（ExecutionEngine、OrderManager、Broker クライアント抽象化）
- リコンシリエーション（起動時・障害復旧処理）
- 監視・アラート（SystemMonitor, TradeMonitor, RiskMonitor, AlertManager）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- 研究・ファクター計算（DuckDB を使ったファクター算出、IC 等の解析）
- AI 補助（ニュースセンチメント算出、レジーム判定、OpenAI API 経由）
- 運用ツール（Paper Trading 検証レポート生成、Streamlit ダッシュボード）

設計方針として、本番 DB と Paper Trading DB を分離し、LLM 呼び出しはフェイルセーフ（API 失敗時はスキップ・フォールバック）で実装しています。

---

## 主な機能一覧

- Execution
  - 注文作成・送信・状態同期（OrderManager）
  - 起動時のリコンシリエーション（Reconciler）
  - Paper Trading モード（MockBrokerClient、専用 SQLite を利用）
- Monitoring
  - システムメトリクス収集（CPU/メモリ/ディスク）
  - データ鮮度チェック（DuckDB の価格データ）
  - 注文滞留／約定異常検出
  - ドローダウン・ポジション上限の監視とリスクログ記録
  - LINE を用いたアラート送信（AlertManager）
  - kill.flag による ExecutionEngine 強制停止（KillSwitch）
  - Streamlit ベース監視ダッシュボード
- Portfolio
  - 候補選定・等重/スコア重み算出
  - セクターキャップ適用、レジーム乗数
  - ポジションサイズ計算（リスクベース、単元丸め、aggregate cap）
- Research
  - Momentum/Volatility/Value ファクター計算（DuckDB）
  - 将来リターン計算、IC（Spearman）計算、統計サマリ
- AI
  - ニュースのセンチメント評価（OpenAI GPT 系で銘柄別スコアを ai_scores に書込）
  - マクロニュース + ETF MA200 による市場レジーム推定と書込
- Tools
  - Paper Trading 検証レポート生成（src/kabusys/tools/paper_verification_report.py）
  - Streamlit ダッシュボード（src/kabusys/monitoring/streamlit_dashboard.py）

---

## 動作要件（主な依存）

最低限必要な Python パッケージ（抜粋）:

- Python 3.9+
- duckdb
- psutil
- requests
- openai
- streamlit (ダッシュボード利用時)
- (任意) sqlite3 は標準ライブラリ
- その他、環境に応じた broker client 実装など

推奨: 仮想環境（venv / pyenv）を使うこと。

requirements.txt がある場合はそれを利用してください。ない場合は手動でインストール例:

pip install duckdb psutil requests openai streamlit

注: psutil によるプロセス優先度設定は OS 権限が必要な場合があります（特に nice を下げる/Windows の高優先度設定など）。失敗しても警告を出してスキップする実装です。

---

## セットアップ手順（ローカル実行向け）

1. リポジトリをクローンし、ワークディレクトリへ移動
   - git clone <repo>
   - cd <repo>

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt  （存在する場合）
   - または上記の個別パッケージを pip install で導入

4. 環境変数（.env）
   - プロジェクトルートに `.env`（または `.env.local`）を置くことで自動読み込みされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 主要な環境変数例:
     - KABUSYS_ENV=development | paper_trading | live
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...  (AI 機能利用時)
     - PAPER_FILL_MODE=instant | partial | never | reject
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - PID_FILE_PATH=data/execution.pid
     - KILL_FLAG_PATH=data/kill.flag
     - MONITOR_POLL_INTERVAL=60  (監視ループの秒間隔)
   - .env のパースはシェル風（export 形式、クォート、コメント等）に対応しています。

5. データディレクトリを用意
   - デフォルトで data/ 以下を使用します。必要に応じて作成してください。
     - mkdir -p data

注: Settings クラスが環境変数を読み取り、Paper Trading モード（KABUSYS_ENV=paper_trading）では paper_sqlite_path を使って発注ログ等を分離します。

---

## 実行方法（主要なスクリプト）

以下はプロジェクト内のエントリポイントの実行例です。いずれもプロジェクトルート（.env がある場所）で実行してください。

1. ExecutionEngine（売買実行）の起動
   - スクリプト: src/kabusys/run_execution.py
   - 実行:
     - python -m kabusys.run_execution
   - 動作:
     - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、Paper Trading 用 SQLite（デフォルト data/paper_trading.db）へ記録します。
     - 起動時に data/stop_requested.flag が存在すると起動せずに終了します。
     - 実行中は pid ファイル（デフォルト data/execution.pid）を作成します。
     - プロセス優先度を "high" に設定しようとします（失敗しても継続）。

2. Monitoring（監視ループ）の起動
   - スクリプト: src/kabusys/run_monitoring.py
   - 実行:
     - python -m kabusys.run_monitoring
   - 動作:
     - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定可能（デフォルト 60 秒）。
     - Monitoring は常に本番 sqlite_path（Settings.sqlite_path）を使って監視ログを保存します（環境にかかわらず）。
     - stop_requested.flag を検知するとループを終了します。

3. Paper Trading 検証レポート生成
   - スクリプト: src/kabusys/tools/paper_verification_report.py
   - 実行例:
     - python -m kabusys.tools.paper_verification_report
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
   - 説明:
     - SQLite 内のテーブル（system_status, trade_logs, risk_logs 等）を参照して稼働率・成功率・レイテンシ等の指標を算出し、PASS/FAIL 判定を表示します。

4. Streamlit 監視ダッシュボード
   - スクリプト: src/kabusys/monitoring/streamlit_dashboard.py
   - 実行:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 説明:
     - ダッシュボードは読み取り専用で SQLite DB を開き、ダッシュボード表示・ポジション一覧・注文ログ・最新システムステータスを見られます。

5. AI 機能（ニューススコア／レジーム判定）
   - ニューススコア:
     - 関数: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
     - 概要: raw_news と news_symbols を集約し OpenAI API（gpt-4o-mini）で銘柄別スコアを ai_scores テーブルに書き込みます。
   - レジーム判定:
     - 関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
     - 概要: ETF 1321 の MA200 乖離とマクロニュースの LLM 評価を合成して market_regime に書き込みます。
   - いずれも OPENAI_API_KEY（または api_key 引数）必須。API 呼び出しはリトライ・フェイルセーフ実装です。

---

## 運用上の注意

- Paper Trading と本番は DB を分離しているため、Paper Trading での検証が本番に影響しないようになっています（Settings.paper_sqlite_path）。
- kill.flag（Settings.kill_flag_path）は ExecutionEngine に対する停止シグナルです。KillSwitch は条件を満たすとファイルを書き込みます。ExecutionEngine 側は stop_requested.flag / kill.flag の存在をチェックして安全に停止します。
- プロセス優先度設定や CPU affinity 設定はプラットフォーム依存・権限依存です。失敗した場合は警告ログが出力されますが処理は継続します。
- OpenAI API 利用には API キーと利用制限の考慮が必要です。429 等のエラーはエクスポネンシャルバックオフでリトライしますが、利用量に注意してください。
- SQLite / DuckDB のファイルはファイルロックや同時書き込みに注意してください（特に複数プロセスで同じファイルにアクセスする場合）。

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（Paper Trading の約定挙動）
- PID_FILE_PATH: ExecutionEngine PID ファイル（デフォルト data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト data/kill.flag）
- MONITOR_POLL_INTERVAL: 監視ループ間隔（秒、デフォルト 60）

Settings クラス（src/kabusys/config.py）にすべてのプロパティとデフォルト値／バリデーションが定義されています。実運用前に .env.example を参考に .env を作成してください。

---

## ディレクトリ構成（主要ファイルの概観）

src/kabusys/
- __init__.py — パッケージ定義（バージョンなど）
- config.py — 環境変数 / 設定読み込み・Settings クラス
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

src/kabusys/execution/
- order_manager.py — 注文管理の外向き API
- order_repository.py — SQLite ベースの注文永続化（参照）
- reconciler.py — 起動時のリコンシリエーション
- reconciler などの各種実行コンポーネント（Engine 等は省略ファイル参照）

src/kabusys/monitoring/
- monitoring_db.py — 監視用 SQLite の初期化と CRUD（MonitoringDB）
- system_monitor.py — システム状態・データ鮮度監視
- trade_monitor.py — 注文滞留・約定異常監視
- risk_monitor.py — ドローダウン・ポジション上限監視
- kill_switch.py — kill.flag 制御
- alert_manager.py — LINE 通知
- monitoring_engine.py — 監視コンポーネント統合
- streamlit_dashboard.py — Streamlit ダッシュボード

src/kabusys/portfolio/
- portfolio_builder.py — 候補選定・重み計算
- position_sizing.py — 株数決定・リスク制限
- risk_adjustment.py — セクター制限・レジーム乗数

src/kabusys/research/
- factor_research.py — Momentum/Value/Volatility 等のファクター計算（DuckDB）
- feature_exploration.py — 将来リターン・IC・統計サマリ

src/kabusys/ai/
- news_nlp.py — ニュースセンチメント算出（OpenAI）
- regime_detector.py — 市場レジーム判定（MA200 + マクロセンチメント）

src/kabusys/tools/
- paper_verification_report.py — Paper Trading 検証レポート生成スクリプト

src/kabusys/utils/
- process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

data/
- （実行時に使用されるデフォルト DB / PID / フラグファイル）  
  例: data/monitoring.db, data/paper_trading.db, data/kabusys.duckdb, data/execution.pid, data/kill.flag, data/stop_requested.flag

---

## 開発・デバッグのヒント

- DB スキーマ初期化は init_monitoring_db() により冪等に実行されます（run_monitoring / run_execution で呼ばれます）。
- Streamlit ダッシュボードは SQLite を読み取り専用で開くようにしているため、監視プロセスと同時に見ても安全なケースが多いです（URI に mode=ro を付与）。
- AI 周りは外部 API 呼び出しなので、ユニットテストでは _call_openai_api をパッチしてモックする設計になっています（ソース内に注記あり）。
- MONITOR_POLL_INTERVAL に負や 0 を与えるとデフォルトにフォールバックします（安全装置）。

---

問題や追加してほしいドキュメント（例：API 契約、Broker クライアントの実装ガイド、requirements.txt）などがあれば教えてください。必要に応じて README を拡張します。