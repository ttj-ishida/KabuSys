KabuSys — 日本株自動売買システム
=============================

このリポジトリは、日本株向けの自動売買基盤の一部実装です。戦略のリサーチ、ポートフォリオ構築、発注エンジン（ExecutionEngine）、監視（Monitoring）や AI（ニュース NLP / レジーム判定）などのコンポーネントを含みます。本 README ではプロジェクト概要、機能一覧、セットアップ手順、使い方（主要スクリプト／ツールの起動例）、およびディレクトリ構成を日本語でまとめます。

プロジェクト概要
--------------
KabuSys は以下の役割を持つコンポーネント群から構成されています。

- 発注周り（execution）: OrderManager, ExecutionEngine, Reconciler 等。ブローカーへの発注、注文状態管理、自動リコンシリエーションを行う。
- 監視（monitoring）: SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine。稼働監視、注文異常検知、ドローダウン監視、LINE 通知、kill flag による自動停止シグナルなど。
- ポートフォリオ構築（portfolio）: 候補選定、重み計算、位置サイズ決定、セクター制約・レジーム乗数適用。
- リサーチ（research）: ファクター計算（モメンタム、バリュー、ボラティリティ等）、特徴量解析（IC, forward returns, summary）。
- AI（ai）: ニュースの NLP によるセンチメントスコアリング（OpenAI 使用）、マクロニュース＋ETF MA200 による市場レジーム判定。
- ユーティリティ（utils）: プロセス優先度や CPU affinity の設定など。
- ツール（tools）: Paper Trading 検証レポート生成など。
- ダッシュボード: Streamlit ベースの監視ダッシュボード。

主な設計方針:
- DuckDB（時系列・リサーチデータ用）と SQLite（監視ログ・注文 DB 用）を併用。
- 本番／ペーパー（paper_trading）環境の分離（paper_trading 時は専用 SQLite を使用）。
- 外部 API 呼び出し（OpenAI など）はフェイルセーフ（失敗時はデフォルト値で継続）を想定。
- ルックアヘッドバイアスに配慮（datetime.today() 等を直接参照しない関数設計など）。

主な機能一覧
--------------
- Execution
  - 発注作成、送信、状態同期（OrderManager / OrderRepository）
  - リコンシリエーション（Reconciler）: 起動時に不確定な注文をブローカーと突合
  - RiskManager による注文可否判定（rate limit / position / drawdown 等）

- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / プロセス生存確認 / データ鮮度チェック
  - TradeMonitor: 滞留注文（stale orders）・約定価格の異常検知
  - RiskMonitor: ドローダウン監視、ポジション上限監視。ダッシュボード更新・risk_logs への記録
  - AlertManager: LINE Push による通知（クールダウン管理）
  - KillSwitch: 条件達成で data/kill.flag を書き込み、ExecutionEngine を安全停止

- Research / Portfolio
  - ファクタ計算（momentum/value/volatility）および forward returns / IC 計算
  - 候補選定・重み計算（等金額・スコア加重）・単元丸め・リスクベースの position sizing
  - セクターキャップ適用・レジーム乗数計算

- AI
  - ニュースセンチメント（news_nlp.score_news）: OpenAI による銘柄別スコア算出と ai_scores への書き込み
  - レジーム判定（regime_detector.score_regime）: ETF 1321 の MA200 乖離 + マクロニュースセンチメントから daily レジームを決定

- ツール
  - paper_verification_report: Paper Trading の SQLite から検証レポート（稼働率・成功率・レイテンシ等）を生成
  - Streamlit ダッシュボード（監視データの可視化）

セットアップ手順
----------------
前提
- Python 3.10+ を推奨（型アノテーションやモダンな記法を使用）
- system パッケージ（psutil, duckdb, openai, requests, streamlit など）

1. リポジトリをクローン
   - git clone ... （リポジトリ URL）

2. 仮想環境作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストール
   - requirements.txt が存在する前提:
     - pip install -r requirements.txt
   - 主要パッケージ例（個別にインストールする場合）:
     - pip install duckdb psutil openai requests streamlit

   SQLite は標準ライブラリ、DuckDB は duckdb パッケージで提供されます。

4. data ディレクトリの作成（必要に応じて）
   - mkdir -p data

5. 環境変数設定
   - プロジェクトルートに .env / .env.local を作成して必要な値を設定できます。
   - 自動ロード（config.py）が有効な場合は .env → .env.local の順で読み込まれます。
   - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

主に使用する環境変数（一部）
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- OPENAI_API_KEY: OpenAI API キー（ai モジュールで使用）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（research 用）
- KABU_API_PASSWORD: kabuステーション API パスワード（ブローカー連携）
- PAPER_FILL_MODE: paper_trading 時の fulfil モード（instant|partial|never|reject。デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用
- LOG_LEVEL: DEBUG/INFO/...
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）※ run_monitoring で使用

使い方（主要スクリプト・ツール）
------------------------------

1) ExecutionEngine を起動（本番 / ペーパー共通）
- 実行:
  - python -m kabusys.run_execution
  - このスクリプトは Settings を読み、KABUSYS_ENV が paper_trading の場合は paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）と MockBrokerClient を使います。
- 停止方法:
  - data/stop_requested.flag を作成すると、run_execution が検知して安全に停止します。
  - または監視側が kill.flag を出力することで ExecutionEngine に停止指示を出せます（KillSwitch 経由）。

2) Monitoring を起動（ポーリング）
- 実行:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可（デフォルト 60 秒）。
- 特記事項:
  - Monitoring は KABUSYS_ENV に関係なく本番 sqlite_path（Settings.sqlite_path）を使用して監視ログを書きます。
  - stop_requested.flag を検知するとループを終了します。

3) Streamlit ダッシュボード（監視表示）
- 起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 説明:
  - 読み取り専用モードで SQLite を開き、ダッシュボード（Overview / Positions / Orders / System）を表示。

4) Paper Trading 検証レポート
- 実行:
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD 期間開始
    - --to YYYY-MM-DD 期間終了
    - --db PATH 直接 DB パス指定（環境変数 PAPER_TRADING_SQLITE_PATH より優先）
- 出力:
  - 稼働率、注文成功率、送信率、P95 レイテンシ等のサマリと PASS/FAIL 判定を標準出力へ出力します。

5) AI / レジーム判定（プログラム的に呼び出す）
- news_nlp.score_news(conn, target_date, api_key=None)
  - DuckDB 接続（raw_news / news_symbols / ai_scores 等）を渡して呼び出す。
- regime_detector.score_regime(conn, target_date, api_key=None)
  - DuckDB 接続（prices_daily / raw_news / market_regime）を渡して呼び出す。
- これらは CLI ではなく Python API として設計されています。必要に応じてラッパースクリプトを作成してください。

6) その他ユーティリティ
- process_priority.set_process_priority("high"|"normal"|"low")
  - run_execution / run_monitoring の起動時に呼ばれ、プロセス優先度を設定します（psutil を使用）。

データベース（簡易）
-------------------
- SQLite（monitoring.db / paper_trading.db）
  - monitoring_db.init_monitoring_db() が必要なテーブルを作成する（冪等）。
  - 主要テーブル:
    - system_status (cpu/memory/disk/process_ok)
    - trade_logs (trade イベントログ + latency_ms カラム)
    - positions (現在ポジション)
    - risk_logs (リスクイベント)
    - dashboard (集計、常に id=1)
- DuckDB（kabusys.duckdb）
  - prices_daily, raw_financials, raw_news, ai_scores, market_regime などの時系列・リサーチデータを想定。

主要ファイル / ディレクトリ構成
-------------------------------
（src/kabusys 以下の主要ファイルを抜粋）

- src/kabusys/
  - __init__.py (パッケージ定義)
  - config.py (環境変数・Settings 読込ロジック、.env 自動読み込み)
  - run_execution.py (ExecutionEngine 起動スクリプト)
  - run_monitoring.py (SystemMonitor ポーリング起動スクリプト)

- src/kabusys/execution/
  - execution_engine.py (エンジン本体: run_session 等) — ※詳細実装は省略
  - order_manager.py (OrderManager)
  - order_repository.py (SQLite ベースの Order 永続化)
  - reconciler.py (リコンシリエーション)
  - broker_factory.py, broker_api.py, order_record.py 等

- src/kabusys/monitoring/
  - monitoring_db.py (SQLite スキーマ初期化 + MonitoringDB クラス)
  - system_monitor.py (SystemMonitor)
  - trade_monitor.py (TradeMonitor)
  - risk_monitor.py (RiskMonitor)
  - monitoring_engine.py (各 Monitor を束ねる Engine)
  - alert_manager.py (LINE 通知)
  - kill_switch.py (kill.flag 書込)
  - streamlit_dashboard.py (監視ダッシュボード)

- src/kabusys/research/
  - factor_research.py (momentum/value/volatility)
  - feature_exploration.py (forward returns / IC / summary)
  - __init__.py (エクスポート)

- src/kabusys/portfolio/
  - portfolio_builder.py (候補選定・重み計算)
  - position_sizing.py (株数計算・aggregate cap)
  - risk_adjustment.py (セクターキャップ・レジーム乗数)
  - __init__.py

- src/kabusys/ai/
  - news_nlp.py (ニュース NLP スコアリング。OpenAI 呼出しとレスポンス検証・DB 書込)
  - regime_detector.py (レジーム判定、MA200 + マクロセンチメント合成)
  - __init__.py

- src/kabusys/tools/
  - paper_verification_report.py (Paper Trading 検証レポート生成)
  - __init__.py

- src/kabusys/utils/
  - process_priority.py (psutil を用いた優先度/affinity 設定)
  - __init__.py

運用上の注意点 / ヒント
-----------------------
- Paper trading と本番 DB は分離:
  - KABUSYS_ENV=paper_trading に切替えると、paper_sqlite_path（デフォルト data/paper_trading.db）を使用します。
- 監視は常に本番 sqlite_path を使用:
  - run_monitoring は Settings.sqlite_path（monitoring DB）を参照します。監視ログは環境にかかわらず本番監視 DB に保存されます。
- kill/stop フラグ:
  - data/stop_requested.flag: run_execution / run_monitoring が存在を検知して安全終了します。
  - data/kill.flag: KillSwitch が書き込み、ExecutionEngine に停止指示を送る用途に使います（flag の存在チェック／削除関数あり）。
- OpenAI API:
  - AI 機能を使う場合は OPENAI_API_KEY の設定が必要。API 呼出しはリトライ・バックオフ・レスポンスバリデーションを行いますが、API 失敗時はフォールバック処理が行われる設計です。
- ローカル開発:
  - .env / .env.local を使い環境変数をセットすると簡便です。config.py はプロジェクトルート（.git や pyproject.toml）を基に自動で .env を読み込みます。
  - テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを無効化できます。

ライセンス / 貢献
-----------------
本リポジトリのライセンスや貢献方法はプロジェクトルートの LICENSE / CONTRIBUTING.md を参照してください（ここには記載されていないため、適宜追加してください）。

最後に
------
この README はコードベースから抽出した機能説明と起動手順のサマリです。実運用にあたっては安全に関する追加検討（権限、例外処理、監査ログ、バックアップ、CI テスト等）を行ってください。必要ならば README に含めるサンプル .env や requirements.txt のテンプレート、運用手順書（Runbooks）やアーキテクチャ図も作成できます。希望があれば追加で作成します。