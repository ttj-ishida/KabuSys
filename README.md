KabuSys — 日本株自動売買システム
=============================

概要
----
KabuSys は日本株の自動売買とその周辺ユーティリティ群（発注エンジン、監視、ポートフォリオ構築、リサーチ、AI ベースのニュースセンチメント等）を含む Python コードベースです。本リポジトリは、発注ロジック・リスク管理・監視・検証レポート作成などのコンポーネントを分離して実装しています。

主な特徴
-------
- ExecutionEngine（発注エンジン）: ブローカークライアントを通じた発注フロー、リコンシリエーション、リスク管理
- MonitoringEngine（監視）: システム状態、注文滞留、リスクアラート、kill flag で Execution の停止指示
- ポートフォリオ構築: 候補選定・スコア配分・ポジションサイジング・セクター制限などの純粋関数群
- Research: DuckDB 上の時系列データに基づくファクター計算・IC 計算・統計サマリー
- AI モジュール: ニュース記事の LLM ベースセンチメント評価（OpenAI）と市場レジーム判定
- ツール: Paper Trading の検証レポート生成、Streamlit ベースの監視ダッシュボード

前提条件 / 依存
-------------
最低限のランタイム要件や外部ライブラリの例（プロジェクトで必要なパッケージを requirements.txt にまとめている想定です）:
- Python 3.9+
- duckdb
- psutil
- openai
- requests
- streamlit（ダッシュボードを使う場合）

例（必要パッケージのインストール）:
- pip install duckdb psutil openai requests streamlit

環境変数 / 設定
----------------
Settings クラスを通じて .env（.env.local）または環境変数から設定を読み込みます。自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われ、OS 環境変数は上書きされません。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

主な環境変数（一部抜粋）:
- KABUSYS_ENV: 実行環境 ("development" | "paper_trading" | "live")（デフォルト: development）
  - paper_trading の場合は MockBrokerClient を使用し、SQLite は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に分離されます
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI を使う機能（news/regime）で必要
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE）用（空でも動作する）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: Monitoring 用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: Paper Trading の約定挙動 ("instant" | "partial" | "never" | "reject")（デフォルト: instant）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60。0 以下の値は無効扱いしてデフォルトにフォールバック）
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT: SystemMonitor の閾値（%）

セットアップ手順
--------------
1. リポジトリをクローン、またはコードをチェックアウト
2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb psutil openai requests streamlit
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）
4. .env ファイルをプロジェクトルートに作成（.env.example を参照して必要なキーを設定）
5. データディレクトリ（data/）を作成する等、ファイルシステムの準備

使い方（起動方法・コマンド例）
----------------------------

注意: パッケージを import できるように、実行時にプロジェクトルート（src を PYTHONPATH に含める等）を設定してください。開発時はプロジェクトルート直下で PYTHONPATH=src を設定するか、pip install -e . しておくと便利です。

ExecutionEngine（発注エンジン）起動:
- 本番 / 開発 / ペーパートレード切替は KABUSYS_ENV で制御
  - 例（Paper Trading）:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
  - 本番運用:
    - export KABUSYS_ENV=live
    - python -m kabusys.run_execution

Monitoring（監視）起動:
- ポーリング監視プロセスを起動します。MONITOR_POLL_INTERVAL 環境変数で間隔を秒単位で指定可能（デフォルト 60）
  - 例:
    - export MONITOR_POLL_INTERVAL=30
    - python -m kabusys.run_monitoring

Streamlit ダッシュボード（監視 UI）:
- streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - --db オプションで読み取り専用で開きます（Monitoring を先に起動してデータを作成してください）

Paper Trading 検証レポート:
- data/paper_trading.db を対象に検証レポートを作成します
  - 例:
    - python -m kabusys.tools.paper_verification_report
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - --db オプションで DB パスを指定できます（PAPER_TRADING_SQLITE_PATH 環境変数でも可）

AI / Regime / News スコア:
- OpenAI API キー（OPENAI_API_KEY）が必要です
- プログラム的に使う場合:
  - from kabusys.ai.news_nlp import score_news
  - from kabusys.ai.regime_detector import score_regime
- それぞれ DuckDB 接続と target_date を渡して実行します

ツール / ライブラリの呼び出し例:
- 研究系:
  - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic
- ポートフォリオ:
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier

運用上の留意点
-------------
- Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計になっています（run_monitoring は settings.sqlite_path を参照）。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path を使用して本番 DB と分離します。
- プロセス優先度: run_execution / run_monitoring は起動時に set_process_priority("high") を試みます（プラットフォームに依存）。
- kill.flag: KillSwitch が条件に応じて kill.flag を書き込みます（ExecutionEngine 側で検知して停止する想定）。ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START 環境変数で自動クリアを制御できます。
- MONITOR_POLL_INTERVAL の値は正の整数を与えてください。不正な値（非整数や 0 以下）はデフォルト（60 秒）にフォールバックします。

ディレクトリ構成（抜粋）
----------------------
以下は src/kabusys 以下の主なファイル・モジュールと役割の概略です。

- kabusys/
  - __init__.py — パッケージメタ情報（__version__ 等）
  - config.py — 環境変数 / .env の読み込みと Settings 定義
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor 単体ポーリング起動スクリプト

- kabusys/execution/
  - order_manager.py — 発注フロー（OrderState マシンの外側 API）
  - reconciler.py — 起動時リコンシリエーション（Order / Position 照合）
  - その他: broker_factory 等（ブローカー抽象化）

- kabusys/monitoring/
  - monitoring_db.py — SQLite による永続化（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py — CPU / メモリ / ディスク / データ鮮度 / PID チェック
  - trade_monitor.py — 滞留注文 / 約定異常の検出
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - monitoring_engine.py — 各 Monitor を束ねるループ
  - alert_manager.py — LINE push 通知ラッパー
  - kill_switch.py — kill.flag を書き込むロジック
  - streamlit_dashboard.py — Streamlit ダッシュボード

- kabusys/portfolio/
  - portfolio_builder.py — 候補選定・重み計算（等金額・スコア）
  - position_sizing.py — 株数計算・lot 単位丸め・集約キャップ
  - risk_adjustment.py — セクターキャップ・レジーム乗数

- kabusys/research/
  - factor_research.py — Momentum / Volatility / Value 等のファクター計算（DuckDB ベース）
  - feature_exploration.py — 将来リターン計算、IC、統計サマリー

- kabusys/ai/
  - news_nlp.py — raw_news を LLM（OpenAI）で評価して ai_scores に書き込む
  - regime_detector.py — マクロニュース + ETF ma200 を合成して market_regime に書き込む

- kabusys/tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成（CLI）

- kabusys/utils/
  - process_priority.py — クロスプラットフォームな優先度 / CPU affinity 設定ユーティリティ

追加メモ
--------
- DB スキーマの初期化: monitoring_db.init_monitoring_db() は冪等にテーブルを作成し、必要に応じて簡易マイグレーション（カラム追加）も行います。
- DuckDB 接続は research / ai モジュールで SQL を直接実行してファクターやニュース集計を行います。DuckDB ファイルパスは DUCKDB_PATH で指定します。
- テスト時の .env 読み込みは Settings モジュールの自動ロードを無効化して制御できます（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

貢献 / 開発
-----------
- 開発時は src を PYTHONPATH に含めるか、ローカル開発インストールを行ってください（pip install -e .）。
- 各モジュールは単体でテスト可能な純粋関数（portfolio 等）と、DB/外部 API に依存するコンポーネントに分離されています。モックやユニットテストで差し替えしやすい設計を心がけています。

お問い合わせ
----------
リポジトリ内のコード（docstring / コメント）を参照してください。README に無い利用方法や追加の運用ルールが必要であれば、具体的なユースケースを教えてください — 例: デプロイ手順、systemd ユニットファイル例、CI 設定例 など。

以上