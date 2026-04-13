KabuSys — 日本株自動売買基盤
=======================

概要
----
KabuSys は日本株向けの自動売買/リサーチ/監視プラットフォームです。本コードベースは以下の主要機能を持つモジュール群で構成されています。

- 注文実行エンジン（ExecutionEngine, OrderManager / BrokerClient）
- リコンシリエーション（再起動後の注文・ポジション同期）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイジング・セクター制限）
- ファクター計算・リサーチ（モメンタム、ボラティリティ、バリュー等）
- ニュース NLP / レジーム判定（OpenAI を用いたセンチメントスコアリング）
- 監視（System / Trade / Risk モニタ、LINE 通知、kill flag）
- 運用支援ツール（ペーパートレード検証レポート、Streamlit ダッシュボード）

機能一覧
--------
- Execution
  - 注文の作成・送信・状態同期
  - Paper Trading（環境: KABUSYS_ENV=paper_trading）用に本番 DB と分離して動作
  - 起動時のリコンシリエーションで OrderSent 状態を復旧
- Monitoring
  - 定期ポーリングでプロセス生存、CPU/メモリ/ディスク、データ鮮度を記録
  - 注文滞留（stale orders）や約定価格異常の検知
  - リスク検知（ドローダウン、ポジション数上限）と kill.flag による強制停止シグナル
  - LINE へのアラート送信（AlertManager）
  - Streamlit での監視ダッシュボード表示
- Portfolio
  - 候補選定（スコア降順）、等金額・スコア加重配分
  - セクター上限の適用、レジームに応じた資金乗数
  - ポジションサイズ計算（単元丸め・aggregate cap・コストバッファ考慮）
- Research / AI
  - DuckDB 上の prices_daily / raw_financials を使ったファクター算出
  - 将来リターン計算、IC（情報係数）計算、統計サマリ
  - OpenAI（gpt-4o-mini 想定）を用いたニュースのセンチメント集約（ai_scores への書き込み）
  - ETF MA とマクロニュースを組み合わせた市場レジーム判定（market_regime 書き込み）
- Tools
  - paper_verification_report: ペーパートレード履歴から運用検証レポートを出力
  - Streamlit ダッシュボード（positions / trade_logs / system_status / risk_logs）

主な環境変数（重要）
-------------------
設定は環境変数またはプロジェクトルートの .env/.env.local 経由で読み込まれます（自動ロード）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

主要なキー（抜粋）:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- OPENAI_API_KEY — OpenAI API キー（AI 関連機能で必須）
- KABUSYS_ENV — 実行モード: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — Paper Trading の約定挙動（instant | partial | never | reject）
- PID_FILE_PATH, KILL_FLAG_PATH — プロセス制御用パス
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring で参照。デフォルト: 60）

セットアップ手順
--------------
以下は本リポジトリをローカルで動かすための一般的な手順です（目安）。

1. 必要な Python バージョン
   - Python 3.10 以上を推奨（型ヒントの union 演算子などを使用）

2. 仮想環境作成
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - 必要依存（代表例）:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit
   - 例:
     - pip install duckdb psutil requests openai streamlit

   （プロジェクトに requirements.txt があれば pip install -r requirements.txt を利用してください）

4. 環境変数設定
   - プロジェクトルートに .env または .env.local を作成して設定するか、OS 環境変数で上書きします。
   - 最低限必要なもの（例）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...   (AI 機能を使う場合)
     - KABUSYS_ENV=development

   - .env の自動読み込みは Settings モジュールにより行われます（プロジェクトルートは .git または pyproject.toml を基準に探索）。

5. データディレクトリ作成
   - data/ ディレクトリなど、SQLite / DuckDB のデフォルトパスが参照する場所を作成しておきます。

使い方
------
主要な起動スクリプトとツールの使い方:

- ExecutionEngine（取引実行）
  - 本番 / 開発 / Paper の切り替えは KABUSYS_ENV で制御
  - 起動:
    - python -m kabusys.run_execution
  - Paper Trading 例:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
  - 注意: Paper 時は settings.paper_sqlite_path（デフォルト data/paper_trading.db）に完全分離して記録されます。

- Monitoring（監視ポーリング）
  - 起動:
    - python -m kabusys.run_monitoring
  - ポーリング間隔の上書き:
    - export MONITOR_POLL_INTERVAL=30
  - 監視は Settings.sqlite_path（本番監視 DB）を使います（KABUSYS_ENV に依存しない点に注意）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db path/to/paper_trading.db （なければ環境変数 PAPER_TRADING_SQLITE_PATH を参照）

- Streamlit ダッシュボード（監視）
  - 起動:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB は read-only で開かれます（起動中の MonitoringEngine がデータ書き込み）。

- AI 関連（プログラム的呼び出し）
  - ニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key=None)
  - レジームスコア:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key=None)

設計上の注意点 / 運用メモ
-------------------------
- .env の読み込み順: OS 環境 > .env.local > .env（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）
- Monitoring は常に production sqlite_path を使用（run_monitoring の設計）
- Paper Trading は本番 DB と完全分離（paper_sqlite_path）
- KillSwitch はデータ/kill.flag を作成すると ExecutionEngine に停止要求を伝えるため、運用時は取り扱いに注意
- Process 優先度設定: 起動時に set_process_priority("high") を試みます（psutil を利用、権限や OS により失敗する可能性あり）
- DuckDB 操作は SQL + Python で完結（研究用。外部 API に依存しない設計）
- OpenAI 呼び出しはリトライやレスポンス検証を実装済み。API キー未設定時は例外が出るため運用前に必ず設定してください

ディレクトリ構成
----------------
（src/kabusys 配下の主要ファイル／モジュールを抜粋）

- src/kabusys/
  - __init__.py (バージョン等)
  - config.py (Settings: 環境変数読み取り・ .env 自動ロード)
  - run_execution.py (ExecutionEngine 起動スクリプト)
  - run_monitoring.py (SystemMonitor ポーリング起動スクリプト)
  - tools/
    - __init__.py
    - paper_verification_report.py (ペーパートレード検証レポート)
  - monitoring/
    - __init__.py
    - monitoring_db.py (SQLite 永続化レイヤ)
    - system_monitor.py (CPU/メモリ/ディスク・データ鮮度監視)
    - trade_monitor.py (滞留注文・約定異常検出)
    - risk_monitor.py (ドローダウン・ポジション数監視)
    - kill_switch.py (kill.flag 書込み)
    - monitoring_engine.py (各 monitor の統合実行)
    - alert_manager.py (LINE Push 通知)
    - streamlit_dashboard.py (Streamlit ダッシュボード)
  - execution/
    - order_manager.py, order_repository.py, reconciler.py, execution_engine.py, broker_factory.py, ...（注文と実行関連）
  - portfolio/
    - portfolio_builder.py (候補選定、重み)
    - position_sizing.py (発注株数算出)
    - risk_adjustment.py (セクター制限、レジーム乗数)
  - research/
    - factor_research.py (ファクター計算: momentum / volatility / value)
    - feature_exploration.py (将来リターン、IC、統計)
  - ai/
    - news_nlp.py (ニュースセンチメント -> ai_scores)
    - regime_detector.py (ETF MA + マクロ NLP -> market_regime)
  - utils/
    - process_priority.py (プロセス優先度・CPU affinity ユーティリティ)
  - data/（想定: DB ファイルや pid/flag を置くディレクトリ。実行時に作成されることが多い）

ライセンス / 貢献
-----------------
（このリポジトリにライセンスファイルがあればそこを参照してください。貢献する際の手順やコードスタイルはプロジェクトの CONTRIBUTING.md 等に従ってください。）

補足（トラブルシュート）
---------------------
- SQLite / DuckDB ファイルが見つからない / 開けない場合はパスの確認とファイル権限をチェックしてください。
- OpenAI API エラー（レート制限・ネットワーク）時は各モジュールでリトライ実装がありますが、キーの有効性とネットワーク状況を確認してください。
- psutil による優先度変更や cpu_affinity 設定は権限が必要な場合があります（AccessDenied 警告が出ることがあります）。

以上。初期導入や運用で不明点があれば、使用したい機能（例: Execution 起動、Monitoring 設定、AI スコア取得）を指定していただければ詳細な手順や例を補足します。