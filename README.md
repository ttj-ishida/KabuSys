KabuSys
=======

日本株向けの自動売買システムの軽量実装（ライブラリ + 実行用スクリプト群）です。  
このリポジトリは取引執行、監視、ポートフォリオ構築、ファクター計算、ニュースNLP 等の主要コンポーネントを含みます。  
README ではプロジェクト概要、主な機能、セットアップ・実行方法、ディレクトリ構成をまとめます。

プロジェクト概要
---------------
KabuSys は以下の責務を持つモジュール群で構成されています。

- execution: ブローカーとの発注・注文管理・再同期（Reconciler）を扱う実行エンジン
- monitoring: システム稼働監視、注文監視、リスク監視、アラート送信（LINE）やストリームリットダッシュボード
- portfolio: 候補選定・重み付け・株数決定・セクター上限などのポートフォリオ構築ロジック（純粋関数）
- research: ファクター計算・将来リターン・IC 計算など研究用ユーティリティ（DuckDB を利用）
- ai: ニュースのセンチメント評価やレジーム判定（OpenAI を利用）
- tools: Paper Trading 用の検証レポート生成スクリプト等

特徴（機能一覧）
----------------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - 本番 / Paper Trading の切替（KABUSYS_ENV）
  - MockBrokerClient を用いた paper_trading モード（DB を完全分離）
  - RiskManager / OrderManager / Reconciler 等を組み合わせた起動フロー
- Monitoring（run_monitoring.py / MonitoringEngine）
  - system / trade / risk のモニタリング、ポーリングループ
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60s）
  - SQLite（monitoring.db）へのログ保存（monitoring_db.init_monitoring_db がスキーマ作成）
  - LINE によるアラート送信（AlertManager）
  - kill.flag による ExecutionEngine 停止シグナル（KillSwitch）
  - Streamlit ダッシュボード（streamlit_dashboard.py）
- Portfolio モジュール（選定・配分・株数算出・リスク調整）
  - select_candidates, calc_equal_weights, calc_score_weights
  - calc_position_sizes（単元丸め、aggregate cap、risk_based 配分）
  - apply_sector_cap, calc_regime_multiplier
- Research（DuckDB ベース）
  - calc_momentum, calc_volatility, calc_value（prices_daily / raw_financials を参照）
  - calc_forward_returns, calc_ic, factor_summary 等の分析ユーティリティ
- AI（OpenAI）
  - news_nlp.score_news: raw_news を集約して LLM に投げ、ai_scores テーブルへ書き込む
  - regime_detector.score_regime: ma200 とマクロニュースの LLM 評価を合成して market_regime を作成
- Tools
  - tools.paper_verification_report: Paper Trading DB を解析して検証レポートを生成

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone ... && cd <repo>

2. Python 環境
   - Python 3.10 以上を推奨
   - 仮想環境を作成して有効化
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 最低限必要なパッケージ例:
     - duckdb, psutil, openai, requests, streamlit
   - 例:
     - pip install duckdb psutil openai requests streamlit

   （プロジェクトに requirements.txt があれば pip install -r requirements.txt を使用してください）

4. データディレクトリを作成
   - mkdir -p data

5. 環境変数設定
   - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（OS 環境変数が優先）。
   - 自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主要な環境変数（Settings で扱うもの）
---------------------------------------
以下は Settings クラスで参照される主要な環境変数（デフォルト値を併記）。

- KABUSYS_ENV: 起動モード。development / paper_trading / live（デフォルト: development）
  - paper_trading の場合、paper 用 SQLite DB（PAPER_TRADING_SQLITE_PATH）を使用し、Mock Broker を利用
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須と想定）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須と想定）
- KABU_API_BASE_URL: kabu API ベース（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（ai モジュールで使用）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用（AlertManager）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定モード（instant|partial|never|reject、デフォルト: instant）
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag をクリアする場合 "1"
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT: 監視閾値（デフォルト: 90/85/90 など）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

使い方（起動コマンド例）
-----------------------

- ExecutionEngine を起動（本番/ペーパー切り替えは KABUSYS_ENV）
  - 本番モード（例）:
    - KABUSYS_ENV=live python -m kabusys.run_execution
  - Paper Trading:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - paper_trading では PAPER_TRADING_SQLITE_PATH にトレード履歴を記録

- Monitoring を起動（ポーリングループ）
  - MONITOR_POLL_INTERVAL 環境変数で秒数を指定可能（デフォルト 60 秒）
  - python -m kabusys.run_monitoring
  - 監視は環境にかかわらず（Settings.env に関係なく）本番の sqlite_path を使用します

- Streamlit ダッシュボード（読み取り専用で monitoring.db を参照）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db data/paper_trading.db

- AI / Research をプログラムから利用
  - news スコア付け:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")

  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

  - ファクター計算・解析:
    - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary
    - 各関数は DuckDB 接続と target_date を受け取ります

主要コンポーネントの注意点 / 備考
---------------------------------
- PID / Kill flag
  - ExecutionEngine は起動時に PID ファイルを作成します。SystemMonitor はその PID を参照してプロセス稼働を判定します。
  - KillSwitch は data/kill.flag を生成して ExecutionEngine に停止シグナルを送ります。ExecutionEngine 側で flag を検知して停止する実装が前提です。
- プロセス優先度
  - run_execution.run_monitoring は起動直後に set_process_priority("high") を呼びます。psutil を使用し、プラットフォームごとに差分吸収します。権限がない場合は警告が出ますが継続します。
- Paper Trading
  - paper_trading モードでは paper_sqlite_path（デフォルト data/paper_trading.db）へ完全分離して記録されます。本番 DB を汚染しません。
- OpenAI 呼び出し
  - news_nlp と regime_detector は OpenAI API を使用します。API 呼び出しは例外や一時エラーに対してリトライ、あるいはフォールバック（safe default）する実装になっていますが、API キーの設定は必須です（関数内でチェックされます）。
- DuckDB / SQLite
  - リサーチ機能は DuckDB（高速分析向け）。監視やトレードログは SQLite を使用します。
  - monitoring_db.init_monitoring_db は冪等的にテーブル・インデックスを作成し、既存 DB にカラム追加が必要な場合はマイグレーションを行います。

監視用 SQLite スキーマ（概要）
-----------------------------
monitoring_db.init_monitoring_db により作成される主なテーブル:

- system_status: CPU/Memory/Disk/プロセス健康状態 の時系列ログ
- trade_logs: 発注イベントログ（event_type: Created/Sent/Filled 等）
- positions: 現在の保有ポジション（code を主キーに保持）
- risk_logs: リスクイベント（ドローダウン・滞留注文・価格異常など）
- dashboard: ダッシュボード集計（id=1 のみ保持）

ディレクトリ構成
-----------------
（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート CLI
  - execution/
    - execution_engine.py    — ExecutionEngine（起動 / セッション管理）
    - order_manager.py       — Order 管理（発注・送信・状態遷移）
    - order_repository.py    — Orders DB アクセス（SQLite）
    - reconciler.py          — 起動時の自動復旧・突合せ
    - broker_factory.py      — ブローカークライアント生成
    - broker_api.py          — ブローカー API インターフェース定義
  - monitoring/
    - monitoring_db.py       — monitoring DB スキーマ & 永続化層
    - system_monitor.py      — システム状態 / データ鮮度チェック
    - trade_monitor.py       — 注文滞留・約定異常チェック
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — kill.flag 管理
    - alert_manager.py       — LINE 通知ユーティリティ
    - monitoring_engine.py   — 各 Monitor を束ねるループ
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - portfolio/
    - portfolio_builder.py   — 候補選定 / スコアソート
    - position_sizing.py     — 株数決定・単元丸め・資金配分
    - risk_adjustment.py     — セクター制限 / レジーム乗数
  - research/
    - factor_research.py     — momentum/value/volatility 計算
    - feature_exploration.py — 将来リターン / IC / サマリ
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — 市場レジーム判定（ma200 + macro sentiment）
  - data/ (ランタイムで使用するディレクトリ)
    - kabusys.duckdb (デフォルト)
    - monitoring.db
    - paper_trading.db

その他 / 運用ノウハウ
---------------------
- 開発環境では KABUSYS_ENV=development を使用し、実運用時は live を使用してください。paper_trading は検証用で本番 DB と分離されます。
- 自動で .env を読み込む実装があり、プロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索して .env / .env.local を読み込みます。テスト時や特殊用途では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます。
- Streamlit ダッシュボードは monitoring.db を read-only モードで開けるように設計しています（URI に mode=ro を付与して接続）。
- OpenAI など外部 API を利用する機能を動かす際は API キーのレート制限や料金に注意してください。

問い合わせ・貢献
-----------------
- バグ報告、改善提案、プルリクエストは GitHub の Issue / Pull Request を利用してください。
- 大きな設計変更（API や DB スキーマの変更）は事前に Issue で議論してください。

以上。質問や README の補足（例: 具体的な .env.example、requirements.txt の追加）が必要であれば教えてください。