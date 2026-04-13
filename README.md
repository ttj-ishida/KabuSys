KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買を想定した軽量なトレーディングフレームワークです。  
主な目的は以下のとおりです。

- シグナル → オーダー管理（ExecutionEngine / OrderManager）
- 発注ログ・監視（SQLite ベースの monitoring DB）
- ポートフォリオ構築（候補選定・重み付け・株数算出）
- 研究用途のファクター計算（DuckDB を利用）
- AI を使ったニュースセンチメント評価・レジーム判定（OpenAI）
- 監視ダッシュボード（Streamlit）

小さなコンポーネント群（純粋関数・永続化層・監視・ツール）で構成され、実運用用の安全装置（kill flag / risk monitor / reconciler 等）を備えています。

主な機能
--------
- Execution
  - OrderManager による注文生成、送信、状態同期
  - Broker 抽象化（本番 / paper_trading の切り替え）
  - Reconciler による再起動時の自動リコンシリエーション
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク/プロセス状態・データ鮮度監視
  - TradeMonitor: 滞留注文・約定異常監視
  - RiskMonitor: ドローダウン・ポジション数監視とアラート記録
  - KillSwitch: 条件に応じた停止フラグ（data/kill.flag）生成
  - AlertManager: LINE へのプッシュ通知（クールダウン管理）
  - Streamlit ベースの監視ダッシュボード
- Portfolio（純関数）
  - 候補選定、等重/スコア加重、リスク調整（セクターキャップ・レジーム乗数）、株数算出（単元丸め・aggregate cap）
- Research（DuckDB）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（スピアマン）計算、統計サマリー
- AI
  - news_nlp.score_news: raw_news を OpenAI でセンチメント評価し ai_scores に書き込み
  - regime_detector.score_regime: ma200 とマクロニュースを合成して market_regime を書き込み
- ツール
  - paper_verification_report: Paper Trading DB を解析して検証レポート生成

セットアップ
-----------
前提
- Python 3.9+ を推奨（typing の記法や一部ライブラリに依存）
- DuckDB, psutil, requests, openai, streamlit などが必要

仮想環境と依存インストール（例）
- venv を使う例:
  python -m venv .venv
  source .venv/bin/activate  # Windows: .venv\Scripts\activate
  pip install --upgrade pip
  pip install duckdb psutil requests openai streamlit

（プロジェクトに requirements.txt があればそれを使ってください）

環境変数
- 自動読み込み: プロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を自動で読み込みします。  
  自動読み込みを無効化する場合:
  KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- 主要な環境変数（簡易一覧）
  - JQUANTS_REFRESH_TOKEN: （必須）J-Quants API 用トークン
  - KABU_API_PASSWORD: （必須）kabuステーション API パスワード
  - OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時）
  - KABUSYS_ENV: 起動モード ("development" | "paper_trading" | "live")。paper_trading 時は paper DB を使用。
  - PAPER_FILL_MODE: paper_trading の MockBroker 挙動 ("instant"|"partial"|"never"|"reject")（デフォルト: "instant"）
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - PID_FILE_PATH / KILL_FLAG_PATH / その他監視閾値（詳細は kabusys.config.Settings を参照）
- 注意
  - run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を使用します（監視 DB を本番と分離したい場合は運用側で管理してください）。
  - run_execution は KABUSYS_ENV=paper_trading の場合、PAPER_TRADING_SQLITE_PATH を使用して発注ログを分離します。

使い方（実行例）
----------------

1) Execution を起動（通常運用）
- 本番/開発/ペーパートレードの切り替え:
  export KABUSYS_ENV=paper_trading  # または development / live
- 実行:
  python -m kabusys.run_execution
  （プロセス開始時に PID ファイルを書き、Engine が注文処理を行います）

2) Monitoring を起動（ポーリング）
- MONITOR_POLL_INTERVAL でポーリング間隔秒を上書き可能（デフォルト 60 秒）。
  export MONITOR_POLL_INTERVAL=30
- 実行:
  python -m kabusys.run_monitoring

3) Streamlit ダッシュボード（監視ビュー）
- 実行例:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

4) Paper Trading 検証レポート生成
- 実行:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- または DB を明示:
  python -m kabusys.tools.paper_verification_report --db /path/to/data/paper_trading.db

5) AI モジュールの利用（コードから呼び出す例）
- ニューススコア取得（DuckDB 接続を渡す）:
  from kabusys.ai import score_news
  n = score_news(conn, target_date, api_key="...")

- レジーム判定:
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date, api_key="...")

注意: 上記はモジュール関数を直接呼び出す例です。API キー指定は引数または環境変数 OPENAI_API_KEY で行えます。API 呼び出しはリトライ、フォールバック処理を備えています。

設定・運用上のポイント
---------------------
- PID / kill.flag
  - Execution は PID ファイル（デフォルト data/execution.pid）を書きます。SystemMonitor は PID ファイルの存在／実体プロセス確認を行い、stale PID を検出するとファイルを削除して risk_logs に記録します。
  - KillSwitch は条件が満たされると data/kill.flag を書き、ExecutionEngine 側でこれを検知して安全停止することを想定しています。
- Paper Trading
  - KABUSYS_ENV=paper_trading のとき、発注は MockBrokerClient を使い、paper DB（PAPER_TRADING_SQLITE_PATH）へ記録します。本番 DB を完全に分離できます。
- .env の読み込みルール
  - OS 環境 > .env.local > .env の優先順位。OS 環境を保護したい場合は .env.local を利用してください。
- ログレベルは LOG_LEVEL 環境変数で制御可能（Settings.log_level）。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py (バージョン等)
- config.py — 環境変数 / .env 読み込み / Settings
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリング起動スクリプト

サブパッケージ
- ai/
  - news_nlp.py — ニュースセンチメント取得（OpenAI）
  - regime_detector.py — 市場レジーム判定（ma200 + マクロニュース）
- execution/
  - order_manager.py, reconciler.py, order_repository.py, execution_engine.py, broker_factory.py, broker_api.py, ...（発注関連）
- monitoring/
  - monitoring_db.py — SQLite スキーマ & CRUD
  - system_monitor.py, trade_monitor.py, risk_monitor.py, kill_switch.py
  - monitoring_engine.py, alert_manager.py, streamlit_dashboard.py
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
- research/
  - factor_research.py, feature_exploration.py
- tools/
  - paper_verification_report.py
- utils/
  - process_priority.py (プロセス優先度 / CPU affinity ユーティリティ)
- data/ （デフォルトの DB ファイル置き場、実運用では外部ボリューム推奨）
  - kabusys.duckdb (DuckDB)
  - monitoring.db (SQLite 監視 DB)
  - paper_trading.db (Paper Trading 用 SQLite)

開発に関する補足
----------------
- DuckDB を用いた分析系関数は外部 API に依存せず、prices_daily / raw_financials 等のテーブルを前提として計算します。研究目的でローカル DuckDB を利用して検証できます。
- Unit テストやモックを用いたテストが容易なように、OpenAI/requests への直接呼び出しは関数化され、テスト時に差し替え可能です（例: unittest.mock.patch）。
- logging を利用した詳細なデバッグ情報を出力します。LOG_LEVEL を DEBUG にすると内部動作を追いやすくなります。

ライセンス / 責任
-----------------
本リポジトリは学習目的のサンプル実装を想定しています。実運用での使用は自己責任で行ってください。実際の証券取引に利用する場合は適切なテスト・監査・法令遵守を行ってください。

問い合わせ
----------
コードや設定について不明点があれば、該当するモジュールの docstring を参照してください。モジュール内部には挙動や前提（例えば時間ウィンドウの定義、フォールバックポリシー、冪等性の扱いなど）が詳述されています。README にない運用ルールや拡張方法はソースを参照のうえ質問してください。