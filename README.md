KabuSys — 日本株自動売買システム（README）
=================================

概要
----
KabuSys は日本株の自動売買 / リサーチ / 監視機能を備えた小規模なトレーディング基盤です。  
主な設計方針はフェイルセーフ性・テスト容易性・本番/ペーパートレード分離で、DuckDB/SQLite をデータ層に利用します。

主な機能
--------
- ExecutionEngine（発注エンジン）
  - ブローカー抽象化（実口座 / モック切替）
  - OrderManager による注文状態管理、Reconciler による起動時リコンシリエーション
  - RiskManager によるシンプルな発注制御
- Monitoring（監視）
  - SystemMonitor：CPU/メモリ/ディスク/プロセス状態・データ鮮度監視
  - TradeMonitor：滞留注文 / 約定異常価格検出
  - RiskMonitor：ドローダウン / ポジション上限監視 + ダッシュボード更新
  - AlertManager：LINE Push による通知（任意）
  - KillSwitch：条件（例: ドローダウン）で ExecutionEngine を停止するフラグファイル
  - streamlit ベースの監視ダッシュボード
- Portfolio construction（シグナル→銘柄選定→株数決定）
  - 候補選定、等重 / スコア重み、リスク調整（セクターキャップ、レジーム乗数）、株数算出（単元丸め・aggregate cap）
- Research（ファクター計算 / 特徴量探索）
  - Momentum / Volatility / Value ファクター、将来リターン、IC 計算、統計サマリー
- AI（OpenAI）
  - news_nlp: ニュース記事を LLM でセンチメント化して ai_scores に格納
  - regime_detector: ETF の MA200 とマクロニュースの LLM 評価を合成して市場レジーム判定
- ユーティリティ
  - process_priority: プロセス優先度 / CPU affinity 設定
  - .env 自動ロード / Settings クラスによる環境変数抽象化
- ツール
  - paper_verification_report: ペーパートレード DB を集計して検証レポートを生成

セットアップ
-----------
前提
- Python 3.10+（型注釈に Union 演算子など使用）
- システムに応じた権限（プロセス優先度設定や psutil 操作で権限が必要な場合があります）

推奨手順（例）
1. 仮想環境を作る
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai requests streamlit
   （プロジェクトに requirements.txt がある場合はそれを使ってください）

3. プロジェクトルートに .env を配置（任意）
   - config.py はプロジェクトルート（.git または pyproject.toml があるディレクトリ）から .env を自動ロードします。
   - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

推奨 .env の例
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- OPENAI_API_KEY=...
- LINE_CHANNEL_ACCESS_TOKEN=...
- LINE_USER_ID=...
- KABUSYS_ENV=development  # development | paper_trading | live
- LOG_LEVEL=INFO
- PAPER_FILL_MODE=instant  # instant | partial | never | reject
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- SQLITE_PATH=data/monitoring.db
- DUCKDB_PATH=data/kabusys.duckdb

重要な環境変数（抜粋）
- KABUSYS_ENV: 動作環境（development / paper_trading / live）。paper_trading 時は MockBroker を使い DB を分離。
- OPENAI_API_KEY: AI 機能を使う際に必要。
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）。デフォルト 60。
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant / partial / never / reject）。
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 をセットで .env 自動ロードを無効化。

使い方（主要スクリプト）
-----------------------

1) 監視ループ（Monitoring）
- コマンド:
  - python -m kabusys.run_monitoring
- 概要:
  - Settings による DB パスを使って monitoring DB を初期化し、SystemMonitor をポーリングします。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 停止フラグ: data/stop_requested.flag を監視して存在すると終了します。
  - 監視は常に（環境にかかわらず）本番 sqlite_path を使用します。

2) 実行エンジン（Execution）
- コマンド:
  - python -m kabusys.run_execution
- 概要:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録（本番 DB と完全分離）。
  - 起動時に execution.pid（デフォルト: data/execution.pid） を作成／監視します。
  - 停止は data/stop_requested.flag を作成することで行えます（KillSwitch とは別の停止フラグ）。
  - ExecutionEngine は別スレッドで run_session を実行し、停止フラグを検出すると安全停止を試みます。

3) 監視ダッシュボード（Streamlit）
- コマンド:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 概要:
  - 監視 DB を読み取り専用で開いてダッシュボードを表示します。MonitoringEngine を先に起動してデータを作成してください。

4) Paper Trading 検証レポート
- コマンド例:
  - python -m kabusys.tools.paper_verification_report
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- 概要:
  - PAPER_TRADING_SQLITE_PATH（または --db オプション）で与えた DB を集計し、稼働率・注文成功率・レイテンシ等をレポート出力します。

5) AI 機能（プログラムからの呼び出し）
- 関数:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- 注意:
  - api_key が未指定の場合は環境変数 OPENAI_API_KEY を参照します。未設定時は ValueError を投げます。
  - LLM 呼び出しはフェイルセーフにしてあり、失敗時はスコアを 0 にして継続する箇所が多いですが、API キー自体は必須です（呼び出し側の要件による）。

停止 / キルフラグの動作
----------------------
- KillSwitch は条件成立時に Settings.kill_flag_path（デフォルト data/kill.flag）へ理由を記述したファイルを書いて ExecutionEngine に停止シグナルを送る仕組みです。
- run_monitoring / run_execution は data/stop_requested.flag を検知して終了します（run_execution 起動防止・実行停止のため）。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主要モジュールと簡単な説明です。

- kabusys/
  - __init__.py — パッケージ定義（__version__ 等）
  - config.py — Settings クラス（環境変数の読み込み・検証・デフォルト）
  - utils/
    - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成 CLI
  - monitoring/
    - monitoring_db.py — SQLite テーブル定義と MonitoringDB ラッパー
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - trade_monitor.py — 滞留注文 / 約定異常検知
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — フラグ書込による停止判定
    - alert_manager.py — LINE Push 通知ラッパー
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py — streamlit ダッシュボード
  - execution/
    - order_manager.py — OrderManager（外向け API）
    - reconciler.py — 起動時の再同期ロジック
    - ...（ブローカーファクトリ / engine / order_repository 等が存在）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py — 株数算出ロジック
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — Momentum/Volatility/Value 計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - ai/
    - news_nlp.py — ニュースの LLM によるセンチメント評価と ai_scores 書込み
    - regime_detector.py — ETF MA200 + マクロニュース LLM を合成してレジーム判定
  - data/（実行時に生成されることが想定）
    - monitoring.db（SQLite） — 監視ログ
    - paper_trading.db（SQLite） — ペーパートレード用 DB（paper_trading 環境）
    - kabusys.duckdb — DuckDB データ
    - execution.pid / stop_requested.flag / kill.flag など

データベース（監視 DB）について
------------------------------
init_monitoring_db により以下のテーブルを作成します（冪等）:
- system_status: CPU/メモリ/ディスク/プロセス OK の時系列
- trade_logs: 発注イベントログ（latency_ms カラムあり）
- positions: 保有株情報
- risk_logs: リスク関連イベント（重複抑止ロジックあり）
- dashboard: 集計（id=1 の単一行）

開発時のヒント / 注意事項
------------------------
- Settings は .env / .env.local を自動ロードします（ただし OS 環境変数が優先されます）。自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- paper_trading 環境は本番 DB と完全分離されるよう設計されています。実際の運用時は KABUSYS_ENV を誤らないよう注意してください。
- process_priority.set_process_priority はプラットフォーム差分（Windows vs POSIX）を吸収しますが、権限不足で警告が出る場合があります（例: nice 値変更の権限）。
- OpenAI 呼び出しは外部 API に依存するため、API レート制限やネットワーク障害に対して各所でリトライやフェイルセーフを実装しています。ローカルでテストする際は PATCH 等で _call_openai_api をモックしてください。
- DuckDB を使うリサーチ関数群は prices_daily / raw_financials / raw_news 等のテーブルを前提としています。テーブルスキーマに依存する箇所があるため、データ投入時はスキーマ整合を確認してください。

ライセンス・作者
----------------
（ここにライセンス・作者情報を追記してください）

問い合わせ / コントリビュート
----------------------------
バグ報告・機能提案・プルリクエストは README を置いているリポジトリの Issues/PR を利用してください。貢献の前に設計方針（フェイルセーフ・本番/ペーパートレード分離）を確認の上実装してください。

以上。必要があれば README に含める詳細（例: .env.example の完全なテンプレートや CLI オプション一覧、より詳細なディレクトリツリー）を追加します。