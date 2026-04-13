KabuSys — 日本株自動売買システム
=============================

この README はこのコードベース（src/kabusys）を使い始めるための簡潔なガイドです。設計思想や内部実装の詳細はコード内コメントを参照してください。

プロジェクト概要
--------------
KabuSys は日本株の自動売買プラットフォームの雛形です。主要機能は以下を含みます。

- ExecutionEngine: シグナルを受けてブローカーへ発注／状態管理を行うエンジン（本番/ペーパートレード対応）
- Monitoring: システム稼働・注文状況・リスク（ドローダウン・ポジション上限など）を周期的に監視しログ／アラートを出す
- Portfolio construction: 候補選定、重み計算、ポジションサイジング、セクター制限などの純粋関数群
- Research: DuckDB 上の価格／財務データに基づくファクター計算・特徴量解析
- AI モジュール: ニュースセンチメント（OpenAI を利用）や市場レジーム判定
- Tools: Paper Trading 検証レポート生成、Streamlit ダッシュボードなど

主な機能一覧
--------------
- 実行（Execution）
  - ブローカー抽象化（実ブローカー / MockBroker で切替）
  - 発注管理（OrderManager）、リコンシリエーション（Reconciler）
  - リスク管理（RiskManager）と注文リポジトリ（SQLite）
- 監視（Monitoring）
  - SystemMonitor: CPU/メモリ/ディスク、プロセス PID チェック、データ鮮度チェック
  - TradeMonitor: 滞留注文、約定異常価格検知
  - RiskMonitor: ドローダウン・ポジション数監視、kill flag 発行
  - AlertManager: LINE へ一方向プッシュ通知（任意）
  - Streamlit ベースの監視ダッシュボード
- ポートフォリオ構築
  - 候補選定（スコア／ランク基準）
  - 等分配／スコア加重／リスクベースのポジション決定
  - セクター集中制限、レジーム乗数
- リサーチ
  - Momentum / Volatility / Value ファクター計算（DuckDB）
  - 将来リターン、IC（Information Coefficient）計算、統計サマリー
- AI
  - ニュース記事のセンチメントスコア化（OpenAI）
  - マクロニュース + ETF MA200 を用いた市場レジーム判定
- ツール
  - paper_verification_report: Paper Trading DB を解析して検証レポート出力
  - streamlit_dashboard: 監視 DB を可視化

セットアップ手順
----------------
1. Python 環境
   - 推奨: Python 3.10 以上（typing に | を使用）
   - 仮想環境を作ることを推奨します:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール
   - 主要依存（抜粋）:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit (ダッシュボードを使う場合)
   - 例:
     - pip install duckdb psutil requests openai streamlit

   （プロジェクトに requirements.txt があればそれを使用してください。）

3. 環境変数 (.env)
   - ルートの .env/.env.local を自動読み込みします（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 主要な環境変数（例）:
     - KABUSYS_ENV: development | paper_trading | live  （default: development）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - OPENAI_API_KEY (AI 機能を使う場合必須)
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (アラート送信に必要)
     - SQLITE_PATH (監視 DB; default: data/monitoring.db)
     - DUCKDB_PATH (DuckDB ファイル; default: data/kabusys.duckdb)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB; default: data/paper_trading.db)
     - PID_FILE_PATH (デフォルト: data/execution.pid)
     - KILL_FLAG_PATH (デフォルト: data/kill.flag)
     - PAPER_FILL_MODE (paper_trading の約定モード: instant|partial|never|reject)
   - Settings クラスが読み込み・検証を行います。必須変数が未設定の場合は ValueError が出ます。

4. データベース初期化
   - 監視用 SQLite は起動スクリプト内で init_monitoring_db() が呼ばれ自動でテーブル生成（冪等）します。
   - DuckDB は prices_daily / raw_financials 等のテーブルが必要になります（データ投入は別途行ってください）。

使い方
------
- 実行エンジン（ExecutionEngine）を起動
  - 本番／ペーパーの切替は KABUSYS_ENV 環境変数で行います。
  - モジュール実行例:
    - python -m kabusys.run_execution
  - 起動時、プロセス優先度を high に設定し、必要な DB 接続を確立して Engine を開始します。
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、paper_trading DB（PAPER_TRADING_SQLITE_PATH）へ書き込みされます。

- 監視ループ（SystemMonitor 等）を起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可（デフォルト 60 秒）。
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（モニタは本番 DB を監視）。

- Streamlit ダッシュボード（監視データの可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションまたは PAPER_TRADING_SQLITE_PATH 環境変数で DB を指定

注意点 / 運用メモ
- プロセス優先度・CPU affinity:
  - 起動時に set_process_priority("high") を呼びます（プラットフォーム依存）。
  - 権限不足等で設定に失敗しても警告を出してスキップします。
- Kill Switch:
  - ディスク上の kill.flag を生成して ExecutionEngine に停止シグナルを送ります（KillSwitch）。
  - Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時にフラグをクリアする動作に関する設定があります（Settings.kill_flag_clear_on_start を参照）。
- Paper Trading:
  - PAPER_FILL_MODE により MockBroker の約定挙動を制御できます（instant/partial/never/reject）。
  - Paper 環境は本番 DB と完全分離される設計（PAPER_TRADING_SQLITE_PATH を使用）。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主要モジュールとその役割の概要です。

- run_execution.py
  - ExecutionEngine を初期化してセッションを実行する起動スクリプト
- run_monitoring.py
  - SystemMonitor のポーリングループを起動するスクリプト

- config.py
  - 環境変数のロード（.env 自動読み込み）と Settings クラス（各種設定取得・検証）

- __init__.py
  - パッケージメタ情報

- tools/
  - paper_verification_report.py: Paper Trading DB の検証レポート生成スクリプト

- portfolio/
  - portfolio_builder.py: 候補選び・重み計算（select_candidates, calc_equal_weights, calc_score_weights）
  - position_sizing.py: 株数決定・投資制限（calc_position_sizes）
  - risk_adjustment.py: セクター上限・レジーム乗数（apply_sector_cap, calc_regime_multiplier）

- research/
  - factor_research.py: Momentum / Volatility / Value ファクター
  - feature_exploration.py: 将来リターン・IC・統計サマリー

- ai/
  - news_nlp.py: raw_news を OpenAI で評価し ai_scores へ書込む
  - regime_detector.py: マクロ + ETF MA200 によるレジーム判定

- monitoring/
  - monitoring_db.py: monitoring SQLite のスキーマ初期化と永続化 API（MonitoringDB）
  - system_monitor.py: システム状態・データ鮮度の監視（SystemMonitor）
  - trade_monitor.py: 注文滞留・約定異常の監視（TradeMonitor）
  - risk_monitor.py: ドローダウン・ポジション上限監視（RiskMonitor）
  - kill_switch.py: kill.flag の管理
  - alert_manager.py: LINE への通知（AlertManager）
  - monitoring_engine.py: 上記モニタを束ねてポーリングする Engine
  - streamlit_dashboard.py: Streamlit ベースの監視ダッシュボード

- execution/
  - order_manager.py: 発注ワークフロー（OrderManager）
  - reconciler.py: 起動時のリコンシリエーション
  - （その他ブローカー抽象・リポジトリ・OrderRecord などはコードベース内に存在）

- utils/
  - process_priority.py: プロセス優先度／CPU affinity 設定ユーティリティ

デフォルトのファイルパス（主要）
- 監視 SQLite: data/monitoring.db
- DuckDB: data/kabusys.duckdb
- Paper Trading SQLite: data/paper_trading.db
- PID ファイル: data/execution.pid
- Kill flag: data/kill.flag

追加情報 / トラブルシューティング
-----------------------------------
- .env のパースは独自実装（export 付き、クォートやインラインコメントの取り扱いに対応）。詳細は config.py を参照してください。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml を基準）を検出して行います。検出できない場合は自動ロードをスキップします。
- DuckDB クエリの実行には prices_daily, raw_financials, raw_news などのテーブルが必要です。これらのデータ投入は運用側で行ってください。
- OpenAI 呼び出しは失敗に強い実装（リトライ・フォールバック）ですが、API キーが未設定だと例外を投げます。AI 機能を使う場合は OPENAI_API_KEY を設定してください。

ライセンス・貢献
----------------
- この README には記載がありません。実際のプロジェクトでは LICENSE ファイル等でライセンスを明記してください。
- バグ修正や機能追加の提案はコード内の設計コメントに沿って行ってください。

以上で基本的な導入ガイドは終わりです。詳細な内部設計や使用例は各モジュールの docstring / コメントに記載されています。必要であれば README に追加したい項目（例: 具体的な .env.example、requirements.txt、デプロイ手順など）を教えてください。