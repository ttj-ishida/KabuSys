KabuSys — 日本株自動売買システム (README)
========================================

概要
----
KabuSys は日本株向けの自動売買・研究・監視ツール群です。  
主な機能は市場データを使ったファクター計算・ポートフォリオ構築、発注エンジン、監視（システム／注文／リスク）、および AI を使ったニュースセンチメント/レジーム判定です。  
コードはモジュール化されており、運用（live）・ペーパートレーディング（paper_trading）・開発（development）を環境切替して利用できます。

主な機能
--------
- 取引実行
  - ExecutionEngine を中心とした発注フロー（ブローカ抽象化、OrderManager、OrderRepository）
  - 再起動時のリコンシリエーション（Reconciler）
  - paper_trading 環境では MockBroker を使用し本番 DB と分離

- ポートフォリオ構築
  - 候補選定、等配分 / スコア配分、リスクベース配分
  - セクターキャップ、レジームに応じた投下比率調整
  - 単元株丸めや aggregate cap の調整

- リサーチ機能
  - Momentum / Volatility / Value 等のファクター計算 (DuckDB を利用)
  - 将来リターン計算、IC（スピアマン）や統計サマリー

- AI 機能
  - ニュースを LLM（OpenAI）でスコアリングして ai_scores テーブルへ書き込み
  - マクロニュース + MA200 を組み合わせた市場レジーム判定

- 監視（Monitoring）
  - SystemMonitor: CPU/メモリ/ディスク、プロセス死活、データ鮮度監視
  - TradeMonitor: 滞留注文・約定異常の検出
  - RiskMonitor: ドローダウン / ポジション上限の検出
  - KillSwitch: 条件に応じてフラグファイルを書き ExecutionEngine 停止指示
  - AlertManager: LINE Messaging API による通知（オプション）
  - Streamlit ベースの監視ダッシュボード

セットアップ手順
----------------
1. リポジトリをクローンして作業ディレクトリへ移動（例）
   - git clone ... && cd <repo>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   - （必要に応じてその他パッケージを追加）

   注意: system 依存で libsqlite3 等が必要な場合があります。OS に合わせて事前にインストールしてください。

4. 環境変数（.env）を用意
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 主要な環境変数（例）:
     - KABUSYS_ENV: development | paper_trading | live  (デフォルト: development)
     - JQUANTS_REFRESH_TOKEN: J-Quants トークン（必須の処理で使う）
     - KABU_API_PASSWORD: kabuステーション API パスワード
     - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用（任意）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
     - PID_FILE_PATH, KILL_FLAG_PATH など（必要に応じて）

5. データディレクトリを作成（初回）
   - mkdir -p data

使い方（主要エントリポイント）
-----------------------------

- 監視プロセス（Monitoring）
  - ポーリングを開始して system/trade/risk を定期的にチェックします。
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可（デフォルト 60 秒）。
  - 実行例:
    - python -m kabusys.run_monitoring

  - 監視は Settings から読み取った sqlite_path（monitoring DB）を使用します。Monitoring は環境にかかわらず本番 sqlite_path を使用する設計です。

- 実行エンジン（Execution）
  - 発注フローを実行するメインエントリポイント。
  - KABUSYS_ENV=paper_trading の場合、MockBroker を使い PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録し本番 DB と分離されます。
  - 実行例:
    - python -m kabusys.run_execution

- Streamlit ダッシュボード
  - 監視結果をブラウザで可視化します（読み取り専用）。
  - 実行例:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - MonitoringEngine が監視 DB を作成・更新していることが前提です。

- Paper Trading 検証レポート
  - data/paper_trading.db の履歴を集計してレポートを標準出力へ出します。
  - 実行例:
    - python -m kabusys.tools.paper_verification_report
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - オプション --db で DB パス指定可（環境変数 PAPER_TRADING_SQLITE_PATH でも可）

- AI 機能（プログラムから呼び出す）
  - ニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key="...")
  - レジームスコア:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key="...")

設定と挙動に関する重要ポイント
------------------------------
- Settings（kabusys.config.Settings）
  - .env / .env.local をプロジェクトルートから自動読込（OS 環境変数優先）。プロジェクトルートは .git や pyproject.toml を基準に探索します。
  - KABUSYS_ENV は "development", "paper_trading", "live" のいずれか。無効値は例外になる。
  - PAPER_FILL_MODE（paper_trading の MockBroker の挙動）: instant | partial | never | reject

- DB
  - デフォルト DuckDB: data/kabusys.duckdb
  - デフォルト monitoring SQLite: data/monitoring.db
  - Paper trading 用 SQLite（分離）: data/paper_trading.db

- プロセス優先度／CPU affinity
  - 実行時に set_process_priority("high") を呼び出します（psutil 利用）。権限や OS によって設定失敗することがありますがログでスキップされます。

- KillSwitch
  - リスク条件を満たすと Settings.kill_flag_path（デフォルト data/kill.flag）へ理由を書き込み、ExecutionEngine に停止指示を与えます。既存のフラグは上書きしません。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                    — 環境変数/設定管理
- run_monitoring.py            — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py             — ExecutionEngine 起動スクリプト

kabusys/ai/
- news_nlp.py                  — ニュースセンチメント（OpenAI）
- regime_detector.py           — レジーム判定（MA200 + マクロセンチメント）

kabusys/data/                    — （外部）データパイプライン / DuckDB と連携（実装ファイルは別）
kabusys/research/
- factor_research.py           — ファクター計算（momentum/volatility/value）
- feature_exploration.py       — 将来リターン・IC・統計サマリー

kabusys/portfolio/
- portfolio_builder.py         — 候補選定・重み計算
- position_sizing.py           — 発注株数計算
- risk_adjustment.py           — セクター制限・レジーム乗数

kabusys/execution/
- order_manager.py
- reconciler.py
- ...（brokerFactory, order_repository, order_record 等が含まれる）

kabusys/monitoring/
- monitoring_db.py             — 監視 DB（SQLite）読み書き層
- system_monitor.py
- trade_monitor.py
- risk_monitor.py
- kill_switch.py
- alert_manager.py
- monitoring_engine.py
- streamlit_dashboard.py

kabusys/tools/
- paper_verification_report.py — Paper Trading 検証レポート生成

注意点・トラブルシューティング
------------------------------
- OpenAI API キーが未設定だと AI を使用する関数は ValueError を投げます。環境変数 OPENAI_API_KEY を設定してください。
- paper_trading モードは本番 DB を破損しないよう分離された SQLite を使います。実運用前に env の設定を必ず確認してください。
- Monitoring は監視用 SQLite を使用します。streamlit ダッシュボードは読み取り専用で DB が存在しないと起動できません。
- psutil を使ったプロセス優先度設定は権限不足や未対応 OS で失敗します（ログでスキップ）。
- DuckDB / SQLite のファイルパスは Settings で上書き可能です。複数プロセスから同一ファイルへ書き込む場合は排他や接続方式に注意してください。
- ロギングは基本 INFO レベルで初期化されています。詳細デバッグが必要な場合は LOG_LEVEL を設定してください。

最後に
------
この README はコードベースから主要な使い方・設計意図をまとめた概要ドキュメントです。各モジュールの詳細な仕様や API はソースコメント（docstring）を参照してください。追加のセットアップや運用手順（Docker/CI/運用 runbook 等）が必要な場合は別途ドキュメント化することを推奨します。