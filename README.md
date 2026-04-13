KabuSys — README
=================

プロジェクト概要
---------------
KabuSys は日本株の自動売買プラットフォーム試作実装です。  
主な目的は以下のとおりです。

- シグナルからポジション構築・発注・リスク管理を行う ExecutionEngine
- システム稼働状況・注文・リスクを監視する Monitoring サービス
- ファクター計算・リサーチ（DuckDB ベース）
- ニュースの NLP によるセンチメント評価（OpenAI）
- Paper Trading（本番 DB と完全分離）と検証レポート生成
- Streamlit による監視ダッシュボード

機能一覧
--------
- Execution
  - 注文作成 / 送信 / 状態同期（Reconciler）
  - オーダー管理（OrderManager / OrderRepository）
  - RiskManager によるポジション・利用率制限
  - Paper Trading モード（MockBrokerClient、data/paper_trading.db）
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク・プロセス状態・市場データ鮮度監視
  - TradeMonitor: 滞留注文・約定価格異常検出
  - RiskMonitor: ドローダウン / 保有上限監視、kill.flag による停止シグナル
  - AlertManager: LINE へプッシュ通知（クールダウンあり）
  - Streamlit ダッシュボード（監視データ可視化）
- Portfolio Construction
  - 候補選定、等配分/スコア配分、ポジションサイズ計算、セクター制限、レジーム乗数
- Research
  - Momentum / Volatility / Value ファクター計算（DuckDB）
  - 将来リターン計算、IC、ファクター統計
- AI
  - news_nlp: OpenAI を用いたニュースセンチメントスコア算出（ai_scores へ書込）
  - regime_detector: MA200 とマクロセンチメント合成による市場レジーム判定
- ユーティリティ
  - process_priority: プロセス優先度・CPU affinity 設定ユーティリティ
  - .env 自動ロード（プロジェクトルート検出）と Settings 管理

セットアップ手順
----------------
前提
- Python 3.9+（ソースは typing | 明確なバージョンは環境に合わせてください）
- システムに duckdb, sqlite3 が利用可能であること

1. リポジトリをクローンし仮想環境を作成
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（例）
   - pip install duckdb psutil requests openai streamlit

   ※ 実際のプロジェクトでは requirements.txt / poetry 等を用意してください。

3. 環境変数設定
   - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 主要な環境変数（Settings 参照）:
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合必須）
     - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading モード用、デフォルト: instant）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - DUCKDB_PATH（DuckDB ファイル、デフォルト: data/kabusys.duckdb）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（AlertManager 用）
     - PID_FILE_PATH（デフォルト: data/execution.pid）
     - KILL_FLAG_PATH（デフォルト: data/kill.flag）
     - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT（監視閾値）

   例 (.env)
   - KABUSYS_ENV=paper_trading
   - OPENAI_API_KEY=sk-...
   - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

4. データディレクトリ作成
   - mkdir -p data

使い方
------
実行スクリプト
- Monitoring を起動
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可（デフォルト 60）
  - python -m kabusys.run_monitoring
  - MONITOR は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視データを記録します。

- ExecutionEngine を起動（注文処理）
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して paper_trading 用 DB に書き込みます（本番 DB と完全分離）。
  - python -m kabusys.run_execution

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 指定期間:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH で PAPER_TRADING_SQLITE_PATH を上書き可能

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で開き表示します。MonitoringEngine を先に起動してデータを生成してください。

設定/起動上の注意
- KABUSYS_ENV:
  - development: 開発設定
  - paper_trading: Paper Trading（ブローカーはモック、DB 分離）
  - live: 本番運用
- Paper Trading は default で data/paper_trading.db を使います。本番とは別ファイルで運用することを前提に実装されています。
- OpenAI 関連機能（news_nlp, regime_detector）は OPENAI_API_KEY が必要。未設定時は例外またはフォールバック挙動になります（モジュールにより異なる）。
- set_process_priority() を起動直後に呼び出します。psutil の権限や OS により設定できない場合があります（警告ログでスキップ）。

主要ファイル / エントリポイント
- src/kabusys/run_monitoring.py
- src/kabusys/run_execution.py
- src/kabusys/tools/paper_verification_report.py
- src/kabusys/monitoring/streamlit_dashboard.py

ディレクトリ構成
----------------
src/kabusys
- __init__.py
- config.py                       — 環境変数 / Settings 管理 (.env 自動ロード含む)
- run_monitoring.py               — SystemMonitor ポーリング起動スクリプト
- run_execution.py                — ExecutionEngine 起動スクリプト

src/kabusys/ai
- news_nlp.py                     — ニュースセンチメント（OpenAI）集約・書込
- regime_detector.py              — MA200 + マクロセンチメントでレジーム判定
- __init__.py

src/kabusys/execution
- order_manager.py
- order_repository.py
- order_record.py
- reconciler.py
- execution_engine.py (※実装ファイルが存在する想定)
- broker_factory.py / broker_api.py (ブローカー抽象)

src/kabusys/monitoring
- monitoring_db.py                 — SQLite スキーマ初期化 + DB アクセス層
- system_monitor.py
- trade_monitor.py
- risk_monitor.py
- kill_switch.py
- alert_manager.py
- monitoring_engine.py
- streamlit_dashboard.py
- __init__.py

src/kabusys/portfolio
- portfolio_builder.py
- position_sizing.py
- risk_adjustment.py
- __init__.py

src/kabusys/research
- factor_research.py
- feature_exploration.py
- __init__.py

src/kabusys/tools
- paper_verification_report.py
- __init__.py

src/kabusys/utils
- process_priority.py
- __init__.py

データファイル（デフォルト位置）
- data/monitoring.db              — 監視ログ SQLite（Settings.sqlite_path）
- data/paper_trading.db           — Paper Trading 用 SQLite（Settings.paper_sqlite_path）
- data/kabusys.duckdb             — DuckDB（Settings.duckdb_path）
- data/execution.pid              — ExecutionEngine PID（Settings.pid_file_path）
- data/kill.flag                  — ExecutionEngine 停止フラグ（Settings.kill_flag_path）

追加の注意事項
--------------
- .env 自動読み込み:
  - プロジェクトルートは .git または pyproject.toml を基準に探索します。見つからない場合は自動ロードをスキップします。
  - OS 環境変数が優先され、.env.local が .env をオーバーライドします。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化できます（テスト等で有用）。

- DB マイグレーション/互換性:
  - monitoring_db.init_monitoring_db は冪等でテーブル作成し、既存列のマイグレーション（列追加）も行います。

- 権限と実行環境:
  - プロセス優先度設定や CPU affinity の適用は OS と権限に依存します。設定に失敗した場合は警告ログが出力され実行は継続します。

貢献/拡張ポイント
------------------
- ストラテジー実装や ExecutionEngine の詳細なプラグイン化
- orders DB と monitoring DB の分離強化（現在既に別ファイル想定）
- Broker 実装の追加（実ブローカー連携）
- より細かな単元株（lot）対応、銘柄マスタ拡張
- テストカバレッジ、CI 設定、依存管理（poetry / pip-tools）

ライセンス / バージョン
-----------------------
パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（例: 0.1.0）。

お問い合わせ
------------
実装の意図や設計上の決定、使い方について質問があればお伝えください。README の内容をプロジェクト実態に合わせて調整できます。