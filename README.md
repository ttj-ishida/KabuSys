KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買・研究・監視を目的とした軽量な Python コードベースです。  
主な機能はシグナルに基づく発注・リスク管理・監視ログ記録・ファクター計算・ニュースベースの NLP 評価などを含みます。  
本リポジトリは実運用（live）・ペーパートレード（paper_trading）・開発（development）を想定した構成になっています。

主な特徴（機能一覧）
------------------
- Execution
  - 発注フロー（OrderManager / OrderRepository / ExecutionEngine）
  - ブローカー抽象化（BrokerClientFactory による本番 / モック切替）
  - 起動時のリコンシリエーション（Reconciler）
  - リスク管理（RiskManager）
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク/プロセス PID/データ鮮度監視
  - TradeMonitor: 滞留注文・約定異常の検出
  - RiskMonitor: ドローダウン監視・ポジション上限チェック
  - KillSwitch: 条件に応じた停止フラグ（data/kill.flag）作成
  - AlertManager: LINE Push による通知（任意）
  - Streamlit ダッシュボード（監視可視化）
- Portfolio Construction
  - 候補選定、等配分/スコア配分、ポジションサイジング、セクター制約、レジーム乗数
- Research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン・IC（Information Coefficient）計算、特徴量サマリー
- AI
  - ニュース NLP（OpenAI を使ったセンチメントスコアリング）
  - レジーム判定（ETF MA + マクロニュースセンチメント合成）
- ツール
  - Paper Trading 検証レポート生成スクリプト
  - 各種 DB 初期化・マイグレーション処理（監視 DB）

環境変数・設定
--------------
設定は環境変数またはプロジェクトルートの .env / .env.local から読み込まれます（自動ロード）。  
自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主な環境変数（代表例）
- KABUSYS_ENV: 起動環境（development / paper_trading / live）デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API 用（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合は必須）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH: ExecutionEngine の pid ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト: 60）
- PAPER_FILL_MODE: paper_trading のモック約定モード（instant / partial / never / reject）

セットアップ手順
--------------
1. Python のインストール（推奨: 3.10+）
2. 仮想環境の作成と有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージのインストール（プロジェクトに requirements.txt があればそれを使用）
   - pip install duckdb psutil openai requests streamlit
   - （必要に応じて他の依存を追加）
4. データディレクトリ作成
   - mkdir -p data
5. 環境変数設定
   - プロジェクトルートに .env（または .env.local）を作成して必要なキーを記載します。例:
     - KABUSYS_ENV=development
     - JQUANTS_REFRESH_TOKEN=your_token
     - KABU_API_PASSWORD=your_password
     - OPENAI_API_KEY=sk-...
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb

使い方（起動・ツール）
---------------------
- 監視ループを起動（SystemMonitor 単体の簡易起動）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書き可能（例: MONITOR_POLL_INTERVAL=30）
  - 監視は常に本番用の sqlite_path（Settings.sqlite_path）を使用します（環境にかかわらず）

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録され、本番 DB と分離されます。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは --db オプションか環境変数 PAPER_TRADING_SQLITE_PATH で指定可能

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視用 SQLite を読み取り専用で開いてダッシュボードを表示します

- AI 機能（ニュースセンチメント / レジーム判定）
  - OPENAI_API_KEY が必要
  - ニューススコアリング: kabusys.ai.news_nlp.score_news を呼ぶ（内部で OpenAI API を呼びます）
  - レジーム判定: kabusys.ai.regime_detector.score_regime を呼ぶ

注意点・運用上のメモ
------------------
- .env 自動読み込み
  - プロジェクトルート（.git または pyproject.toml を基準）にある .env と .env.local を自動で読み込みます。
  - 読み込み順: OS 環境 > .env.local (override) > .env
  - 自動読み込みを無効にする: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- DB マイグレーション
  - monitoring_db.init_monitoring_db は冪等でテーブル作成・一部カラム追加マイグレーションを行います。
- プロセス優先度
  - 起動時に set_process_priority("high") を呼び出してプロセス優先度を可能な限り上げます（プラットフォーム依存・権限不足時は警告を出してスキップ）。
- KillSwitch
  - KillSwitch は条件に応じて KILL_FLAG_PATH（デフォルト data/kill.flag）を作成します。ExecutionEngine はこのフラグを確認して安全に停止する想定です。
- Paper トレード分離
  - paper_trading モードでは発注イベントや監視ログは paper 専用の SQLite に書き込む設計（実口座データと完全分離）。

ディレクトリ構成（抜粋）
-----------------------
- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定管理
  - run_monitoring.py            — SystemMonitor ポーリング起動スクリプト
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py                — ニュース NLP（OpenAI 呼び出し）
    - regime_detector.py         — 市場レジーム判定
  - monitoring/
    - __init__.py
    - monitoring_db.py           — SQLite 監視ログ層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - reconciler.py
    - order_manager.py
    - (その他: broker_client, execution_engine 等の実装ファイル)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - process_priority.py
    - __init__.py
  - data/                         — デフォルトデータ・DB が置かれる想定（例: data/*.db）

サンプル .env（最小）
-------------------
例:
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-...
SQLITE_PATH=data/monitoring.db
DUCKDB_PATH=data/kabusys.duckdb
LINE_CHANNEL_ACCESS_TOKEN=             # LINE 通知を使う場合に設定
LINE_USER_ID=

FAQ / トラブルシューティング
----------------------------
- MONITOR_POLL_INTERVAL を 0 に設定すると無効値扱いでデフォルト（60 秒）に戻ります。
- OpenAI API 呼び出しで RateLimitError 等が発生した場合は内部で指数バックオフしリトライしますが、最終的に失敗するとその銘柄や機能はスキップされます（フェイルセーフ設計）。
- psutil による優先度設定や CPU affinity 設定は OS と権限に依存します。アクセス拒否時は警告が出て処理を継続します。

貢献・拡張
----------
- モックブローカーや本番ブローカーの実装（broker_client）を実装して ExecutionEngine に接続してください。
- 銘柄ごとの lot_size のサポート、手数料計算、より精緻な価格フォールバックなどは拡張ポイントです。
- テストは各モジュールの純粋関数（portfolio、research）から整備するのが容易です。AI 呼び出し部分はモック化してテストできます。

ライセンス
----------
（プロジェクトに応じてライセンスをここに記載してください）

---
以上が本リポジトリの概要と使い方になります。必要があれば各モジュールの詳細ドキュメント（API 仕様・設定可能なパラメータの一覧・運用手順）を別途作成します。