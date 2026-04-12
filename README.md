KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買・研究・監視を目的としたパッケージ的なコードベースです。  
主に以下の役割を持つコンポーネントで構成されています。

- ExecutionEngine: 発注・リスク管理・リコンシリエーション（broker 接続）
- MonitoringEngine: システム稼働状態・注文異常・リスク制御のポーリング監視
- Portfolio モジュール: 候補銘柄選定・重み算出・建玉サイズ計算
- Research モジュール: ファクター計算・特徴量解析
- AI モジュール: ニュースの LLM ベースセンチメント → スコア化、レジーム判定
- Tools: Paper Trading 検証レポート生成、Streamlit ダッシュボード等

主要機能
--------
- Execution
  - OrderManager / OrderRepository を通した発注・状態遷移管理
  - Reconciler による起動時の自動リコンシリエーション
  - paper_trading 環境では MockBroker を利用し、本番 DB と分離された data/paper_trading.db に記録
- Monitoring
  - SystemMonitor: CPU/Memory/Disk、プロセス生存、データ鮮度を監視し監視 DB に記録
  - TradeMonitor: 注文滞留・約定異常価格を検出して risk_logs に記録
  - RiskMonitor: ドローダウン、ポジション上限を監視し kill.flag の作成や risk_logs 記録
  - AlertManager: LINE Push による通知（設定がある場合）
  - Streamlit ベースの監視ダッシュボード（読み取り専用）
- Portfolio
  - 候補選定（スコア順 / rank）、等金額・スコア加重の重み計算
  - リスク調整（セクター上限、レジーム乗数）
  - 建玉サイズ計算（単元丸め、aggregate cap、利用可能現金考慮）
- Research
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB を利用）
  - 将来リターン・IC 計算・統計サマリ等
- AI
  - ニュース記事を OpenAI に投げて銘柄ごとのセンチメント（ai_scores）を算出・保存
  - ETF MA とマクロニュースを合成して市場レジーム判定（market_regime）

前提条件（主な依存）
------------------
- Python 3.9+
- sqlite3（標準ライブラリ）
- duckdb
- psutil
- requests
- openai
- streamlit（ダッシュボード利用時）

（実際の開発環境では requirements.txt を用意してください。例: pip install duckdb psutil requests openai streamlit）

設定と環境変数
---------------
このプロジェクトは .env / .env.local ファイルまたは OS 環境変数から設定を読み込みます（プロジェクトルートは .git または pyproject.toml を基準に自動検出します）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主な環境変数（Settings 参照）
- KABUSYS_ENV: 起動環境（"development" / "paper_trading" / "live"）。デフォルト: development
  - paper_trading の場合、発注は MockBroker を使い PAPER_TRADING_SQLITE_PATH（下）に記録します。
- JQUANTS_REFRESH_TOKEN: （必須）J-Quants API トークン
- KABU_API_PASSWORD: （必須）kabu API パスワード
- OPENAI_API_KEY: OpenAI を使う機能で必要
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE通知）用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading MockBroker の fill モード（"instant" | "partial" | "never" | "reject"、デフォルト "instant"）
- PID_FILE_PATH: ExecutionEngine 用 pid ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

セットアップ手順
---------------
1. リポジトリをクローンして作業ディレクトリへ移動
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (または Windows で .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   （requirements.txt があれば pip install -r requirements.txt）
4. .env（および .env.local）を作成して必要な環境変数を設定
   - .env.example を参照して JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等を設定してください
   - KABUSYS_ENV=paper_trading にする場合は PAPER_TRADING_SQLITE_PATH を適切に設定可能
5. DB 初期化は各起動スクリプトが自動で行います（monitoring DB 用のテーブル作成などは init_monitoring_db による冪等処理）

使い方（主要な実行方法）
----------------------

- ExecutionEngine を起動（本番/開発/ペーパー共通の起点）
  - 環境変数で KABUSYS_ENV を切り替え
    - 本番: KABUSYS_ENV=live
    - ペーパー: KABUSYS_ENV=paper_trading
  - 実行:
    - python -m kabusys.run_execution
  - 特記事項:
    - 起動時にプロセス優先度を "high" に設定します（set_process_priority）。
    - paper_trading 環境では mock broker を使用し、記録はデフォルトで data/paper_trading.db に保存されます。

- MonitoringEngine（ポーリング監視）を起動
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。0 以下・不正値は無視されデフォルトが使われます。
  - 実行:
    - python -m kabusys.run_monitoring
  - 特記事項:
    - Monitoring は KABUSYS_ENV にかかわらず本番の sqlite_path（Settings.sqlite_path）を使用する設計になっています（監視データは本番 DB へ）。

- Streamlit ダッシュボード（監視）
  - 起動:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 読み取り専用で監視 DB を表示できます（read-only URI で接続）。

- Paper Trading 検証レポート生成
  - 期間を指定して paper_trading DB（default: data/paper_trading.db）を集計して標準出力へレポートを生成します。
  - 実行例:
    - python -m kabusys.tools.paper_verification_report
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - オプションで --db PATH を指定して別 DB を参照可能

- AI / レジーム判定（プログラム的に利用）
  - ニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")  → 書き込んだ銘柄数を返す
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")  → 1（成功）を返す
  - OPENAI_API_KEY を環境変数で設定するか、api_key 引数で渡してください。

- その他ユーティリティ
  - process_priority: kabusys.utils.process_priority.set_process_priority("high"|"normal"|"low")
  - kill.flag: KillSwitch により data/kill.flag が作成されると ExecutionEngine 停止シグナルとして扱われます。KillSwitch.clear() で削除できます。

ディレクトリ構成（抜粋）
---------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数/.env ロードと Settings 定義
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
- tools/
  - paper_verification_report.py — Paper Trading の検証レポート CLI
- ai/
  - news_nlp.py             — ニュース NLP（OpenAI）によるスコア化処理
  - regime_detector.py      — マクロ + MA から市場レジーム判定
- monitoring/
  - monitoring_db.py        — SQLite テーブル定義・永続化 API
  - system_monitor.py       — システム状態・データ鮮度監視
  - trade_monitor.py        — 注文滞留・約定異常監視
  - risk_monitor.py         — ドローダウン・ポジション上限監視
  - kill_switch.py          — kill.flag の書き込み/評価
  - alert_manager.py        — LINE 通知ユーティリティ
  - monitoring_engine.py    — モニタリングの統合エンジン
  - streamlit_dashboard.py  — Streamlit ダッシュボード
- execution/
  - order_manager.py        — 発注フロー管理
  - reconciler.py           — 起動時の状態リコンシリエーション
  - （その他 broker / order_repository 等、発注周りの実装）
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
  - __init__.py
- utils/
  - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ

開発者向けメモ / 運用注意
------------------------
- DB マイグレーション
  - monitoring_db.init_monitoring_db は必要なテーブルとカラム（冪等）を作成し、既存 DB に対する簡単な ALTER を行います（例: dashboard.peak_value, trade_logs.latency_ms の追加）。
- PID / kill.flag
  - ExecutionEngine は起動時に PID ファイルを作成します（Settings.pid_file_path）。SystemMonitor は PID ファイルを見てプロセス生存検査を行い、stale PID を検出したら削除してリスクログに記録します。
- paper_trading 分離
  - KABUSYS_ENV=paper_trading にすると paper_trading 用の SQLite に記録し、本番 DB と分離できます。PAPER_FILL_MODE によりモックの約定挙動を制御できます。
- モニタリングの Poll Interval
  - MONITOR_POLL_INTERVAL 環境変数で秒数を指定可能。無効値は無視されてデフォルト 60 秒が使われます。
- OpenAI 呼び出し
  - LLM API 呼び出しはリトライ・バックオフ・パースの堅牢化を行っていますが、API キーと利用クォータ・コストに注意してください。失敗した場合は安全にフェイルして 0.0 等の中立値で続行する設計になっています。

免責・今後の拡張
----------------
- 一部モジュールは外部の実装（broker API、データパイプライン等）に依存します。実運用前に十分なテストとモック確認を行ってください。
- 現時点で単元株（lot_size）は全銘柄共通の想定です。将来的に銘柄別ロットサイズ対応が想定されています（コード内に TODO あり）。

お問い合わせ
------------
- このコードベースに関する質問や改善提案はリポジトリの Issues / PR を利用してください。

以上がこのリポジトリの概要と基本的な使い方です。必要であれば、README に含めるサンプル .env.example や requirements.txt の雛形も用意します（ご希望があれば教えてください）。