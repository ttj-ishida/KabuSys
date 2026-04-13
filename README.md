KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を目的としたモジュール群です。本コードベースには以下の主要機能が含まれます:

- 発注エンジン（ExecutionEngine）と注文管理（OrderManager / OrderRepository）
- 監視・アラート（MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor）
- ポートフォリオ構築（候補選定・重み付け・株数決定・セクター制約）
- リサーチ（ファクター計算、将来リターン、IC 等）
- AI 系機能（ニュースセンチメントによるスコアリング・市場レジーム判定）
- 開発用/検証ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）
- プラットフォーム横断のプロセス優先度設定ユーティリティ

主な特徴
--------
- 明確に分離された「本番 / paper_trading / development」動作（Settings により切替）
- Paper Trading 時は MockBrokerClient を用い、本番 DB と分離（data/paper_trading.db）
- DuckDB を用いたリサーチ（prices_daily / raw_financials 等に対して高速 SQL 処理）
- OpenAI（gpt-4o-mini）を用いたニュース NLP（スコアリング）とレジーム判定（リトライ等を含む堅牢な実装）
- 監視ログは SQLite（monitoring.db）へ永続化、Streamlit で可視化
- kill.flag による安全停止（ExecutionEngine 停止シグナル）とアラート経路（LINE push）

セットアップ
-----------
前提
- Python 3.10 以上（ソースで X | Y 型アノテーションを使用しているため）
- SQLite（標準ライブラリ）
- 必要な Python パッケージ（下記参照）

依存パッケージ（例）
- duckdb
- openai
- psutil
- requests
- streamlit

インストール例
1. 仮想環境作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb openai psutil requests streamlit

（プロジェクトに requirements.txt がある場合は pip install -r requirements.txt を使用）

環境変数（.env）
- .env / .env.local をプロジェクトルートに置くことで自動読み込み（OS 環境変数が優先）
- 自動読み込みを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主な環境変数（代表例とデフォルト）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（monitoring）デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant | partial | never | reject. デフォルト: instant）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE Push）用

使い方
------

1) 監視ループを起動（Monitoring）
- 目的: SystemMonitor をポーリングして system_status / risk_logs / trade_logs 等を更新
- 実行例:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL を設定してポーリング間隔を変更（秒）
    - 例: export MONITOR_POLL_INTERVAL=30

- 動作メモ:
  - Monitoring は KABUSYS_ENV の値に関係なく production 用の sqlite_path（Settings.sqlite_path）を使用します
  - 起動時にプロセス優先度を "high" に設定しようとします（psutil の権限に依存）

2) ExecutionEngine を起動（発注・実行）
- 実行例:
  - python -m kabusys.run_execution
- 動作メモ:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して paper_sqlite_path（data/paper_trading.db）へ記録し、本番 DB と分離します
  - 起動時に PID ファイルを作成し、kill.flag の存在で停止判定を行う設計になっています
  - Settings によりリスク制約 (RiskConfig) 等の初期設定が適用されます

3) Paper Trading 検証レポート生成ツール
- 目的: paper_trading DB のログから稼働率/注文成功率/レイテンシ等の指標レポートを生成
- 実行例:
  - python -m kabusys.tools.paper_verification_report
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション --db で DB パスを指定可能（優先順位: --db > 環境変数 PAPER_TRADING_SQLITE_PATH > デフォルト）

4) Streamlit ダッシュボード（監視可視化）
- 実行例:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- ダッシュボードではポートフォリオ値、開いているポジション、最近の注文、最新システムステータス、リスクログ等を確認できます

5) AI 機能（プログラム的に呼び出す）
- ニュースセンチメント（ai.score_news）およびレジーム判定（ai.regime_detector.score_regime）は DuckDB 接続と target_date、OPENAI_API_KEY を与えて呼び出します。
  - 例（概念）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key="...")

注意点・運用上のポイント
- Paper Trading では本番 DB と完全に分離される設計です（settings.is_paper をチェック）
- kill.flag の存在は ExecutionEngine 停止の合図です。KillSwitch はリスク閾値（ドローダウン等）を満たした際に flag を書き込みます
- Settings はプロジェクトルートの .env/.env.local を自動ロードします（ただし OS 環境変数が優先）
- OpenAI API 呼び出しはリトライとサニタイズ（JSON parse 回復処理）を含む堅牢な処理を実装しています
- Process priority / CPU affinity の設定はプラットフォームや権限に依存し、失敗した場合は警告を出してスキップします

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py — 環境変数 / Settings 管理（.env 自動ロード機能含む）
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

サブパッケージ（主なファイル）
- ai/
  - news_nlp.py — ニュース文章の LLM によるセンチメント付与 / ai_scores 書込処理
  - regime_detector.py — マクロセンチメント + ETF ma200 による市場レジーム判定
- monitoring/
  - monitoring_db.py — SQLite による監視ログ永続化 / MonitoringDB API
  - system_monitor.py — システム状態・データ鮮度検査
  - trade_monitor.py — 注文滞留・約定価格異常の監視
  - risk_monitor.py — ドローダウン / 保有上限の監視とダッシュボード更新
  - kill_switch.py — kill.flag 書き込みロジック
  - alert_manager.py — LINE Push による通知（クールダウン管理）
  - monitoring_engine.py — 各 Monitor を束ねるループ
  - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード
- execution/
  - reconciler.py — 起動時の注文／ポジション照合・自動復旧
  - order_manager.py — 発注フロー（状態遷移・Broker API との連携）
  - order_repository.py, order_record.py, broker_factory.py, execution_engine.py ...（発注関連）
- portfolio/
  - portfolio_builder.py — 候補選定・等重／スコア重み計算
  - position_sizing.py — 株数計算（リスクベース / 等分配等）
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- research/
  - factor_research.py — Momentum / Volatility / Value ファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン計算・IC・統計サマリ
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

補足（開発者向け）
-----------------
- DuckDB を使う設計上、prices_daily / raw_financials / raw_news 等のテーブル整備が前提です
- MonitoringDB の init_monitoring_db() は冪等でテーブル作成・簡単なマイグレーション（列追加）を行います
- AI 呼び出しは OpenAI の SDK（OpenAI クライアント）を使用します。キーは OPENAI_API_KEY に設定してください
- 重要な設定や閾値は Settings クラス（kabusys.config.Settings）に集約されています。必要に応じて .env に設定を追加してください

ライセンス・作者
----------------
（この README にはライセンス情報は含まれていません。プロジェクトのライセンスや作者情報は別途追加してください。）

以上。セットアップや運用で不明点があれば、どの部分について詳しく知りたいか教えてください。