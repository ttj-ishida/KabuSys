# KabuSys

日本株自動売買システムのサブコンポーネント群（リサーチ、ポートフォリオ構築、注文実行、監視、簡易AI連携など）の実装例です。本リポジトリはモジュール単位で実行可能なランタイム／ツール群を提供します。  
以下はコードベース（src/kabusys/*）に基づく README です。

注意: 実行には外部ライブラリ（duckdb、psutil、requests、openai、streamlit 等）および API キーや環境変数の設定が必要です。実運用前に必ずコードと設定をレビューしてください。

---

## プロジェクト概要

KabuSys は以下の主要機能を分離したモジュールで提供します。

- リサーチ（ファクター計算、特徴量探索、前方リターン・IC 計算）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ算出、セクター制限）
- 注文実行（ExecutionEngine / OrderManager / Reconciler 等 — ブローカー抽象化）
- 監視（システム状態、注文滞留・約定異常、リスク監視、Kill Switch、アラート）
- AI連携（ニュース NLP によるセンチメント、マクロセンチメントとレジーム判定）
- 運用ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）

設計方針の一部:
- データ解析は DuckDB を使用し、prices_daily / raw_financials / raw_news 等のテーブルを参照
- 監視ログは SQLite（デフォルト: data/monitoring.db）に永続化
- 環境ごとの挙動（development / paper_trading / live）を Settings で制御
- Paper Trading は本番 DB と分離して data/paper_trading.db に記録（モックブローカー利用）

---

## 主な機能一覧

- Portfolio
  - 銘柄候補選定（スコア降順）
  - 等金額／スコア重み付け
  - ポジションサイズ計算（リスクベース、単元丸め、aggregate cap）
  - セクター集中制限、レジーム乗数

- Research
  - Momentum / Volatility / Value ファクター計算
  - 将来リターン（forward returns）計算
  - IC（Spearman）やファクター統計量の出力

- Execution（実行系）
  - OrderManager / Reconciler / RiskManager（部分実装が含まれる）
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - Paper Trading モード時は MockBrokerClient を使用（DB分離）

- Monitoring
  - SystemMonitor（CPU/メモリ/ディスク/プロセス/データ鮮度）
  - TradeMonitor（滞留注文・約定異常）
  - RiskMonitor（ドローダウン・ポジション上限）
  - KillSwitch（data/kill.flag により ExecutionEngine 停止指示）
  - AlertManager（LINE Pushによる通知）
  - MonitoringEngine（各 Monitor を束ねるポーリング）
  - Streamlit ベースの監視ダッシュボード

- AI
  - ニュース NLP（OpenAI を用いた銘柄ごとのセンチメントを ai_scores テーブルに書込み）
  - レジーム判定（ETF の MA200 歪みとマクロセンチメントを合成）

- Tools
  - Paper Trading 検証レポート（期間指定で検証指標を出力）

---

## セットアップ手順

1. Python 環境（推奨: 3.9+）
2. 必要パッケージのインストール（最低限）:
   - duckdb
   - psutil
   - requests
   - openai
   - streamlit
   例:
   pip install duckdb psutil requests openai streamlit

   実運用では requirements.txt / poetry 等で依存管理してください。

3. 環境変数 / .env の準備
   - .env / .env.local をプロジェクトルートに置くと自動読み込みされます（ただし OS 環境変数が優先されます）。
   - 自動読み込みを無効にする場合:
     KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   主要な環境変数:
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須な箇所あり）
   - KABU_API_PASSWORD: kabuステーション API 用（実行系で必須）
   - OPENAI_API_KEY: OpenAI API キー（AI機能使用時）
   - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite パス（デフォルト: data/paper_trading.db）
   - SQLITE_PATH: 監視ログ用 SQLite パス（デフォルト: data/monitoring.db）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知設定（任意）
   - PID_FILE_PATH / KILL_FLAG_PATH: PID / kill.flag のパス（デフォルトは data/ 内）
   - PAPER_FILL_MODE: paper_trading 時の fill モード（instant/partial/never/reject、デフォルト: instant）
   - MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト: 60）

4. データディレクトリの作成
   - data/ 以下に DB を配置する場合はディレクトリを作成しておく:
     mkdir -p data

5. DB 初期化
   - run_monitoring.py / run_execution.py は監視用テーブルを起動時に自動作成（init_monitoring_db）します。
   - DuckDB や prices_daily/raw_financials/raw_news 等のテーブルは別途 ETL/スクリプトで投入する想定です。

---

## 使い方（代表的なコマンド）

- 監視ループ起動（Monitoring）
  - デフォルトのポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で秒数を上書きできます（1 以上の正整数）。
  - 例:
    KABUSYS_ENV=production MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - run_monitoring は Settings から sqlite_path を読み、monitoring DB を初期化して SystemMonitor のループを実行します。

- ExecutionEngine 起動
  - 実行系（当日セッション）を起動します。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録します（本番 DB と分離）。
  - 例:
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Streamlit ダッシュボード
  - 監視 DB を読み取るダッシュボードです（読み取り専用で起動）。
  - 例:
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート（ツール）
  - data/paper_trading.db の内容から検証指標を出力します。
  - 例:
    python -m kabusys.tools.paper_verification_report
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI スコア / レジーム判定（ライブラリ API）
  - AI 機能は Python API を通して呼び出します。OpenAI API キーが必要です。
  - 例（スクリプト内から）:
    from kabusys.ai import score_news
    n = score_news(duckdb_conn, target_date, api_key="sk-...")

    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="sk-...")

- 注意: 実行スクリプトはモジュールとして実行することを想定しています（python -m kabusys.run_monitoring 等）。

---

## 設定（Settings モジュールの要点）

- 自動で .env / .env.local をプロジェクトルートから探索して読み込み（ただし OS 環境変数が優先）。
- KABUSYS_ENV: development / paper_trading / live をサポート（値検証あり）。
- Paper Trading の DB パスは PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）。
- PAPER_FILL_MODE: instant | partial | never | reject（値検証あり）。
- 各種閾値（CPU/MEM/DISK）や PID / kill.flag の path などを環境変数で上書き可能。

環境読み込みを無効化する場合:
- export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 主要ファイル／ディレクトリ構成

下は src/kabusys 以下のおおまかな構成と各モジュールの説明（本 README は提供されたコード群に基づく抜粋）:

- src/kabusys/
  - __init__.py
    - パッケージメタ情報（バージョンなど）
  - config.py
    - 環境変数 / .env 読み込み、Settings クラス
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL）
  - run_execution.py
    - ExecutionEngine 起動スクリプト（KABUSYS_ENV=paper_trading の挙動を切替）
  - ai/
    - news_nlp.py
      - raw_news を集約して OpenAI で銘柄ごとのセンチメントを算出し ai_scores に書込む
    - regime_detector.py
      - ETF MA200 とマクロセンチメントを合成して market_regime に書込む
  - monitoring/
    - monitoring_db.py
      - SQLite スキーマ初期化と永続化 API（MonitoringDB）
    - system_monitor.py
      - CPU/MEM/DISK/プロセス/データ鮮度監視
    - trade_monitor.py
      - 滞留注文 / 約定異常検出
    - risk_monitor.py
      - ドローダウン / ポジション上限の監視
    - kill_switch.py
      - data/kill.flag を書き込むことで ExecutionEngine に停止を促す
    - alert_manager.py
      - LINE Push による通知（クールダウン管理）
    - monitoring_engine.py
      - 各 Monitor を束ねる実行ループ（本番向け）
    - streamlit_dashboard.py
      - Streamlit ベースの監視ダッシュボード（起動方法をファイル冒頭に記載）
  - portfolio/
    - portfolio_builder.py
      - 候補選定、重み計算（等金額/スコア重み）
    - position_sizing.py
      - 発注株数計算（risk_based / equal / score）、単元丸め、aggregate cap
    - risk_adjustment.py
      - セクターキャップの適用、レジーム乗数計算
  - research/
    - factor_research.py
      - Momentum / Volatility / Value 等のファクター計算（DuckDB 利用）
    - feature_exploration.py
      - 将来リターン、IC、統計サマリー等
  - tools/
    - paper_verification_report.py
      - Paper Trading の検証レポート生成 CLI
  - utils/
    - process_priority.py
      - プロセス優先度設定（Windows/Linux 差分を吸収）
  - execution/
    - order_manager.py, reconciler.py, ...（注文実行に関するコンポーネント）
      - Execution 系の中心的なロジック（OrderManager/OrderRepository/Reconciler 等）
    - （ブローカー抽象やリポジトリは別ファイルに分かれています）

（実際のフルツリーはリポジトリに応じて異なります。上記は提供されたコード群の抜粋です。）

---

## 運用上の注意・実装ノート（重要）

- 実取引を行う前に十分なテストとコードレビューを実施してください。特に Execution 系は実際の資金損失に直結します。
- Paper Trading モードは本番 DB と分離するよう設計されていますが、設定ミスで本番 DB にアクセスしないか確認してください。
- OpenAI API 呼び出しは料金が発生します。API キー管理・呼び出し頻度に注意してください。また異常応答や一時エラーに対してはエクスポネンシャルバックオフの実装がありますが、失敗時はフェイルセーフ（スコア0.0 等）で継続する実装になっています。
- monitoring の poll 間隔は MONITOR_POLL_INTERVAL で調整可能（値が不正だと 60 秒にフォールバック）。
- プロセス優先度設定（set_process_priority）は実行開始直後に呼び出され、psutil の制約や OS の権限によって失敗することがあります（警告ログのみ）。

---

## 参考コマンドまとめ（例）

- 監視サービス起動:
  MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring

- 実行エンジン（Paper Trading）起動:
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Streamlit ダッシュボード起動:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

この README は提供されたコードの説明に基づいて作成しています。導入・運用にあたっては各モジュールの実装詳細や未実装箇所、外部データ投入手順などを必ず確認してください。必要であれば、README を環境構築用の手順書（requirements, docker-compose, DB 初期ロード手順 等）として拡張できます。必要な追加情報があれば教えてください。