KabuSys — 日本株自動売買システム
=============================

このリポジトリは日本株向けの自動売買（Execution）・監視（Monitoring）・リサーチ・AI アシスト機能を含む小規模なフレームワークです。  
下記はコードベース（src/kabusys 以下）に基づく README です。

概要
----
KabuSys は以下の責務を持ちます。

- ExecutionEngine: ブローカーとやり取りして注文を作成・管理し、リスク制御を行う。
- Monitoring: システム状態・注文状態・リスク（ドローダウン／ポジション上限）を定期監視してログ保存・アラート・Kill Switch を管理する。
- Portfolio / Strategy utilities: 候補選定、重み付け、ポジションサイズ計算、セクター制限などの純粋関数群。
- Research: DuckDB 上の株価・財務データからファクターや将来リターン、IC、統計要約を計算。
- AI 支援: ニュースのセンチメントスコアリング（OpenAI）や市場レジーム判定（LLM + ETF 指標の合成）。
- ツール: Paper Trading の検証レポート生成、Streamlit ダッシュボード等。

主な機能一覧
--------------
- 実行 (Execution)
  - ブローカー接続（実口座 / Paper Trading モードの分離）
  - OrderManager / OrderRepository / Reconciler による注文管理と起動時の自動リコンシリエーション
  - リスクマネージャ（position, utilization, drawdown 等）
- 監視 (Monitoring)
  - SystemMonitor: CPU/Mem/Disk、プロセス生存、データ鮮度チェック
  - TradeMonitor: 滞留注文、約定価格異常チェック
  - RiskMonitor: ドローダウン・ポジション上限監視（ダッシュボード更新、risk_logs 追加）
  - KillSwitch: 条件を満たせば data/kill.flag を出力して ExecutionEngine を停止させる
  - AlertManager: LINE へのプッシュ通知 (クールダウン管理)
  - MonitoringEngine / run_monitoring.py によるポーリングループ
  - Streamlit ダッシュボード（監視 DB の可視化）
- リサーチ / ポートフォリオ構築
  - ファクター計算（momentum/value/volatility）、forward returns、IC、統計サマリー
  - 候補抽出、重み算出、ポジションサイズ決定、セクター制限、レジーム乗数
- AI
  - news_nlp.score_news: raw_news をまとめて OpenAI に投げ、ai_scores に保存
  - regime_detector.score_regime: ETF とマクロニュースを組み合わせて日次レジーム判定
- ユーティリティ
  - process_priority: プラットフォームに依存しないプロセス優先度設定
  - .env 自動読み込み機構（プロジェクトルートの .env / .env.local、無効化フラグあり）

セットアップ手順
----------------

前提
- Python 3.10+（typing 表記から推測）
- DuckDB、psutil、requests、openai、streamlit（用途に応じて）などの依存パッケージ

推奨インストール（例）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（プロジェクトに requirements.txt があればそれを使用）
   - pip install duckdb psutil requests openai streamlit

3. データディレクトリ作成
   - mkdir -p data

環境変数（主なもの）
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 任意 / 推奨・設定可能
  - OPENAI_API_KEY — OpenAI 呼び出しに必要
  - KABUSYS_ENV — 実行環境: development / paper_trading / live  （デフォルト: development）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/...）
  - SQLITE_PATH — 監視用 sqlite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — paper_trading モード時の専用 sqlite（デフォルト: data/paper_trading.db）
  - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - PID_FILE_PATH — ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH — kill flag のパス（デフォルト: data/kill.flag）
  - MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト: 60）
  - PAPER_FILL_MODE — paper_trading の約定モード: instant | partial | never | reject（デフォルト: instant）
- .env 有効化
  - プロジェクトルート（.git または pyproject.toml を基準）に .env / .env.local を置くと自動で読み込まれます。
  - 自動ロードを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

使い方
------

起動スクリプト（パッケージモード）
- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - 動作: プロセス優先度を high に設定 → DB 接続（paper_trading なら専用 DB）→ ブローカー作成 → エンジン起動
  - 注意: data/stop_requested.flag が存在する場合は起動せず終了
  - PID ファイル: data/execution.pid（デフォルト）を作成

- Monitoring を起動（ポーリングループ）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL で間隔を秒単位で上書き可能（デフォルト 60）
  - 監視は本番 sqlite_path を使う（環境にかかわらず本番 DB を参照する設計）

Paper Trading（切り離し）
- KABUSYS_ENV=paper_trading を設定すると、Execution 側で MockBrokerClient が使用され paper_trading 用 SQLite に記録されます（data/paper_trading.db がデフォルト）。

ストップ / キル
- 実行を外部から停止したい場合:
  - data/stop_requested.flag を作成すると run_execution/run_monitoring のループが検知して終了します。
  - KillSwitch は条件を満たすと data/kill.flag を書き込み、ExecutionEngine 停止をトリガーします（ファイルパスは Settings.kill_flag_path）。

Streamlit ダッシュボード
- 監視 DB を read-only で可視化する UI:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

Paper Trading 検証レポート
- CSV ではなく SQLite を参照して集計を出力するツール:
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH  （PAPER_TRADING_SQLITE_PATH 環境変数を上書き）
  - 例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

AI モジュールの利用
- ニューススコアリング: kabusys.ai.score_news(conn, target_date, api_key=None)
  - conn: DuckDB 接続（raw_news / news_symbols / ai_scores テーブルが必要）
  - api_key 未指定なら環境変数 OPENAI_API_KEY を使用
- レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 同様に OpenAI API キーが必要

注意点 / 運用メモ
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml がある階層）を基準に行われます。CWD に依存しないためパッケージ化後も機能します。
- Monitoring は常に本番 sqlite_path を用いる設計なので、paper_trading モードでも監視 DB を共有する点に注意してください（run_execution は paper_trading 時に別 DB を使う）。
- PID ファイルや flag ファイルは data/ 以下に作成されます。これらを操作することで外部からの停止制御が可能です。
- OPENAI 呼び出しは外部 API に依存するため、API エラー時はフェイルセーフ（多くは 0.0 等でフォールバック）になっていますが、API キーは必須の操作があります（例: score_news, score_regime）。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py — パッケージ定義、バージョン
- config.py — 環境変数 / Settings 管理（.env 自動読み込み、各種パス・閾値定義）
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor のポーリング起動スクリプト

subpackages:
- ai/
  - news_nlp.py — ニュースの LLM センチメントスコアリング（ai_scores 書込）
  - regime_detector.py — ETF + マクロニュースで市場レジーム判定
- monitoring/
  - monitoring_db.py — SQLite テーブル初期化 & 永続化 API（MonitoringDB）
  - system_monitor.py / trade_monitor.py / risk_monitor.py — 各モニタ実装
  - monitoring_engine.py — 個別モニタを束ねるエンジン
  - kill_switch.py — kill.flag 作成ロジック
  - alert_manager.py — LINE Push 送信
  - streamlit_dashboard.py — Streamlit ベースの監視 UI
- execution/
  - order_manager.py / reconciler.py / ... — 注文管理・再同期等
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py — ポートフォリオ構築ロジック
- research/
  - factor_research.py, feature_exploration.py — ファクター計算・統計
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート（CLI）
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
- data/ （実行時に作成される想定）
  - monitoring.db (default)
  - paper_trading.db (paper_trading 用)
  - kabusys.duckdb (DuckDB データ)
  - execution.pid, kill.flag, stop_requested.flag などの制御ファイル

補足（開発時のヒント）
- DB スキーマ初期化: run_execution / run_monitoring の起動時に init_monitoring_db が呼ばれます。手動で初期化したい場合は MonitoringDB の init_monitoring_db を呼ぶか、上記スクリプトを実行してください。
- ログレベル: LOG_LEVEL 環境変数で調整可能（Settings.log_level）。
- テスト時: .env の自動読み込みを抑止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

以上がコードベース（src/kabusys）に基づく README の概要です。必要であれば、具体的な実行例（systemd サービス、Dockerfile、requirements.txt の例）や API 使用方法の章を追加できます。どの情報を優先して拡張しますか？