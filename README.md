プロジェクト: KabuSys
====================

プロジェクト概要
----------------
KabuSys は日本株向けの自動売買・リサーチ・監視コンポーネント群を集めた Python パッケージです。  
主な目的はアルゴリズムトレードの実行（ExecutionEngine）、監視（MonitoringEngine）、リサーチ（ファクター計算 / 特徴量探索）、および Paper Trading 検証を行うことです。  
モジュール設計は次の点を重視しています: 冪等性／フェイルセーフ、DB 分離（本番 vs paper）、外部 API 呼び出しの明確化（OpenAI 等）、および単一責務の純粋関数化（ポートフォリオ計算等）。

主な機能一覧
-------------
- 実行（ExecutionEngine）
  - ブローカークライアント抽象化（実運用／モック切替）
  - 注文管理（OrderManager / OrderRepository）
  - リコンシリエーション（Reconciler）
  - リスク管理（RiskManager）
- 監視（MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor）
  - システムリソース、プロセス監視、データ鮮度チェック
  - 注文の滞留検出、約定価格異常検出
  - ドローダウン・ポジション上限監視と kill.flag による停止シグナル
  - LINE による通知（AlertManager）
  - Streamlit ダッシュボード（リアルタイム確認）
- Paper Trading 検証
  - データから検証レポート生成ツール（tools.paper_verification_report）
- リサーチ
  - ファクター計算（momentum / volatility / value）
  - 将来リターン、IC（Information Coefficient）等の統計解析
- AI 支援モジュール
  - ニュースの LLM センチメント評価（ai.news_nlp）
  - 市場レジーム判定（ai.regime_detector）
- ユーティリティ
  - 設定管理（config.Settings）：.env の自動ロード・検証
  - プロセス優先度・CPU affinity 設定（utils.process_priority）
  - DuckDB / SQLite を用いた DB 層ユーティリティ

セットアップ手順
----------------
前提:
- Python 3.9+（型ヒントに依存。環境に合わせて動作を確認してください）
- SQLite は標準ライブラリで利用可能
- 必要パッケージ（例）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit
これらは pip でインストールします（requirements.txt がない場合は手動で）:

例:
- 仮想環境作成:
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
- パッケージインストール:
  - pip install duckdb psutil requests openai streamlit

環境変数 / .env:
- プロジェクトルートに .env / .env.local を置くと自動でロードされます（CWD に依存せず、ソース位置からプロジェクトルートを探索）。
- 自動ロードを無効化する場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- 主要な環境変数（一部）:
  - KABUSYS_ENV: development | paper_trading | live（必須ではないが検証あり）
  - SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
  - DUCKDB_PATH: DuckDB（デフォルト data/kabusys.duckdb）
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 sqlite（デフォルト data/paper_trading.db）
  - OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 外部 API 用（未設定時は Settings が例外を投げます）
  - PID_FILE_PATH, KILL_FLAG_PATH 等の監視パス
  - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒。デフォルト 60）

DB 初期化:
- 各起動スクリプトは init_monitoring_db() を呼び DB テーブルを作成／マイグレーションを実行します。手動で作成する必要は通常ありません。

使い方（実行例）
----------------

1) 監視ループを起動（Monitoring）
- デフォルトのポーリング間隔 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書き可。
  - 簡易起動:
    - python -m kabusys.run_monitoring
  - or
    - python src/kabusys/run_monitoring.py
- 実行内容:
  - pid ファイル・プロセス優先度設定
  - monitoring DB（SQLite）接続と初期化
  - DuckDB 接続（価格データ参照用）
  - SystemMonitor.check_once() を定期実行してログ・リスクイベントを永続化

2) 実行エンジン起動（ExecutionEngine）
- 本番・Paper の切替:
  - KABUSYS_ENV=paper_trading を指定すると MockBrokerClient を使用し、data/paper_trading.db に記録（本番 DB と完全分離）
- 起動:
  - python -m kabusys.run_execution
- 実行内容:
  - ブローカークライアント生成（BrokerClientFactory）
  - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て
  - ExecutionEngine.run_session() によるセッション実行

3) Streamlit ダッシュボード（監視可視化）
- 起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 機能:
  - ダッシュボード、ポジション一覧、最近の注文、最新システム状態、最近のリスクイベントを表示

4) Paper Trading 検証レポート生成
- コマンドライン:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- オプション:
  - --db PATH: DB パス（未指定時は PAPER_TRADING_SQLITE_PATH 環境変数 → data/paper_trading.db）

5) AI モジュール（プログラム利用）
- ニュースセンチメントを得て ai_scores に書き込む:
  - from kabusys.ai.news_nlp import score_news
  - score_news(duckdb_conn, target_date, api_key="...")  # api_key を省略すると OPENAI_API_KEY を参照
- レジーム判定:
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(duckdb_conn, target_date, api_key="...")

設定と挙動の注意点
------------------
- Settings クラスは環境変数の検証を行います。無効な値や必須変数未設定時は ValueError を投げます。
- .env のパースは shell ライクな書式（export KEY=val、引用符、インラインコメント等）に対応します。
- run_monitoring / run_execution は起動時にプロセス優先度を set_process_priority("high") しようとします（psutil を使用）。権限がないとワーニングでスキップされます。
- Monitoring はどの KABUSYS_ENV でも本番の sqlite_path を使用します（監視ログは環境に依存せず共通で運用可能）。
- kill.flag による停止シグナル: KillSwitch がトリガー条件を満たすと flag ファイルを書き、ExecutionEngine 側で検出して停止できます。ExecutionEngine 起動時にクリアする挙動は Settings.kill_flag_clear_on_start に依存します。

ディレクトリ構成（主要ファイル）
--------------------------------
src/kabusys/
- __init__.py                     — パッケージ定義（__version__ 等）
- config.py                       — Settings: .env 自動読み込み・環境変数管理
- run_monitoring.py               — Monitoring ポーリングループ起動スクリプト
- run_execution.py                — ExecutionEngine 起動スクリプト

src/kabusys/monitoring/
- monitoring_db.py                — SQLite 用永続化レイヤ（テーブル定義・MonitoringDB）
- system_monitor.py               — システム/データ鮮度監視
- trade_monitor.py                — 注文滞留・約定異常監視
- risk_monitor.py                 — ドローダウン / ポジション上限監視
- kill_switch.py                  — kill.flag の作成/評価
- alert_manager.py                — LINE Push 通知ラッパ
- monitoring_engine.py            — 各 Monitor を束ねるエンジン
- streamlit_dashboard.py          — Streamlit ベースの監視ダッシュボード

src/kabusys/execution/
- order_manager.py                — 注文管理ロジック / ステートマシン外向き API
- reconciler.py                   — 起動時自動復旧（注文/ポジション照合）
- その他（broker_factory, execution_engine, order_repository など） — 実行関連（省略されたファイルあり）

src/kabusys/portfolio/
- portfolio_builder.py            — 候補選定・重み計算（等配分・スコア加重）
- risk_adjustment.py              — セクターキャップ・レジーム乗数
- position_sizing.py              — 株数算出・単元丸め・利用可能現金スケール

src/kabusys/research/
- factor_research.py              — Momentum/Volatility/Value のファクター計算（DuckDB）
- feature_exploration.py          — 将来リターン計算、IC、統計サマリー

src/kabusys/ai/
- news_nlp.py                     — ニュースを LLM でセンチメント化して ai_scores に保存
- regime_detector.py              — MA + マクロセンチメントで市場レジーム判定

src/kabusys/tools/
- paper_verification_report.py    — Paper Trading レポート生成 CLI

src/kabusys/utils/
- process_priority.py             — プロセス優先度・CPU affinity 設定ユーティリティ

デフォルトのデータファイルパス
------------------------------
- DuckDB: data/kabusys.duckdb
- 監視 SQLite: data/monitoring.db
- Paper Trading SQLite: data/paper_trading.db
- PID ファイル: data/execution.pid
- Kill flag: data/kill.flag

開発上のメモ / 注意事項
-----------------------
- DuckDB 接続はリサーチ/AI モジュールで利用します。prices_daily / raw_financials / raw_news 等のテーブル構成に依存します。
- monitoring_db.init_monitoring_db() は既存 DB へマイグレーション（列追加）を行います。破壊的変更は避ける設計です。
- OpenAI API 呼び出し部分はリトライ・バックオフ・レスポンス検証を備えていますが、API キー・利用制限には注意してください。
- process priority / cpu affinity の設定はプラットフォーム依存で、権限不足や未サポート環境ではスキップされます。

ライセンスや貢献方法
-------------------
（このリポジトリのライセンスやコントリビュートルールがあればここに追記してください）

以上が README に含める主要情報です。README の補足や具体的な起動例（systemd サービス定義や Docker 化、CI 設定など）を追加希望であれば、利用想定環境に合わせて追記します。