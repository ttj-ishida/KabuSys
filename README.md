# KabuSys

日本株向け自動売買システムの Python コードベース。  
このリポジトリは取引エンジン、監視系、リサーチ/ファクター計算、ポートフォリオ構築、AI（ニュースセンチメント／レジーム判定）などのコンポーネントから構成されています。

---

## 概要

KabuSys は以下の主要機能を備えた自動売買フレームワークです。

- ExecutionEngine: ブローカーへの発注、注文状態管理、リコンシリエーション（再起動後の自動復旧）
- Monitoring: システム状態・注文状態・リスク監視、LINE による通知、kill flag による安全停止
- Research: DuckDB を用いた各種ファクター計算（モメンタム、ボラティリティ、バリュー等）と特徴量解析
- Portfolio construction: 候補選定、重み計算、ポジションサイズ算出、セクター制限・レジーム乗数
- AI (news_nlp / regime_detector): OpenAI を用いたニュースのセンチメント評価や市場レジーム判定
- Tools: Paper Trading の検証レポート生成等のユーティリティスクリプト
- Utilities: プロセス優先度や CPU affinity 設定などの実行環境ユーティリティ

設計上、リサーチや AI モジュールは本番ブローカー API へアクセスせず、DuckDB/SQLite のデータのみを参照するようになっています（ルックアヘッドバイアスに配慮）。

---

## 主な機能一覧

- Execution
  - Broker 抽象化（プロダクション / モックを切替）
  - OrderManager（状態遷移・重複チェック）
  - Reconciler（起動時の注文・ポジション突合）
  - RiskManager（各種リスク制御）
- Monitoring
  - SystemMonitor（CPU/メモリ/ディスク、データ鮮度、PID 生存チェック）
  - TradeMonitor（滞留注文・約定異常価格検出）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - KillSwitch（条件に応じた kill.flag の作成）
  - AlertManager（LINE push を用いたアラート送信、クールダウン管理）
  - Streamlit ダッシュボード（監視情報の可視化）
- Research / Portfolio
  - ファクター計算（momentum/value/volatility 等）
  - forward return / IC 計算、特徴量サマリ
  - 候補選定・等金額 / スコア加重配分
  - 単元丸め・リスクベースの株数算出・aggregate cap のスケールダウン
- AI
  - ニュース記事の銘柄別センチメント算出（OpenAI）
  - マクロニュース + ETF MA200 乖離を使った日次レジーム判定（OpenAI）
  - API エラー時のリトライやフォールバック処理を備える
- Tools
  - Paper Trading 検証レポート生成スクリプト（期間指定可）

---

## セットアップ手順（ローカル開発向け）

前提：Python 3.9+ を想定。環境に合わせて適宜調整してください。

1. リポジトリをクローンする
   - git clone ...

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   - （必要に応じて追加ライブラリをインストールしてください）

   > 注: requirements.txt がない場合、上記の主要パッケージをインストールしてください。

4. データディレクトリを作成
   - mkdir -p data

5. 環境変数（.env）を用意
   - プロジェクトルートに .env / .env.local を置くと自動読み込みされます（既存の OS 環境変数は保護されます）。
   - 主要な環境変数（例）:
     - KABUSYS_ENV=development | paper_trading | live
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - PAPER_FILL_MODE=instant|partial|never|reject
     - MONITOR_POLL_INTERVAL=60  （監視ループの秒間隔、既定は60）

6. DB 初期化
   - 監視用 SQLite テーブルは run_monitoring/run_execution スクリプトが init_monitoring_db を呼ぶため、これらを起動すると必要テーブルが自動作成されます。

---

## 実行方法（使い方）

- 実行エンジン（ExecutionEngine）起動
  - 通常起動（環境変数で KABUSYS_ENV を設定）
    - KABUSYS_ENV=development python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
      - paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録されます。
  - 起動時に data/stop_requested.flag が存在すると起動をスキップします。
  - 実行中は data/execution.pid に PID を書きます。停止は監視側からの kill.flag / stop_requested.flag によって行われます。

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可（デフォルト 60 秒）。
  - 監視は Settings にかかわらず本番 sqlite_path を使用して監視ログを記録します（monitoring DB は実運用 DB を参照）。

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - read-only URI で SQLite を開くため、MonitoringEngine を先に起動してデータを用意しておくと表示されます。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 範囲指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db パラメータで PAPER_TRADING_SQLITE_PATH を上書き可能

- AI 関連（OpenAI）
  - news_nlp.score_news / regime_detector.score_regime は OpenAI API キー（OPENAI_API_KEY）を参照します。未設定時は例外を投げます。
  - API 呼び出しはリトライやフォールバック（失敗時スコア 0.0 等）を実装しています。

- 停止フラグ
  - 強制停止（実行スレッドの監視・停止）: data/stop_requested.flag を作成すると run_monitoring/run_execution の監視ループが終了またはエンジン停止処理に入ります。
  - KillSwitch は条件を満たすと Settings.kill_flag_path（デフォルト data/kill.flag）へ理由を書き込み、ExecutionEngine 側でこれを検出して安全停止できます。

---

## 重要な設定・環境変数

- KABUSYS_ENV: development | paper_trading | live（設定ミスは例外）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 DB（分離）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- OPENAI_API_KEY: OpenAI 呼び出しに必要
- JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD: 外部 API 用トークン
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: アラート送信用
- MONITOR_POLL_INTERVAL: 監視ループ間隔（秒）

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・.env 読み込みと Settings
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory / broker_api 等（ブローカー抽象）
    - execution_engine.py    — 実行セッションのメインロジック
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - data/                     — 実行時に使用する DB / フラグファイル（プロジェクトルートに data フォルダを作成）
  - utils/
    - process_priority.py      — プロセス優先度・CPU affinity 設定
  - その他: duckdb/SQLite 関連の参照実装、ストリーミング・ダッシュボード補助など

---

## 開発上の注意点 / 補遺

- .env 自動読み込み
  - プロジェクトルート検出（.git または pyproject.toml）を行い、.env / .env.local を順に読み込みます。OS 環境変数は保護されます。
  - テスト等で自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- Paper Trading モードは本番 DB と分離して動作します（PAPER_TRADING_SQLITE_PATH を使用）。
- 監視ロジックは監視 DB（SQLite）へログを永続化し、streamlit ダッシュボード等で可視化できます。
- OpenAI を使うモジュールは API の一時エラーに対して指数バックオフのリトライを実装し、レスポンスのバリデーション（JSON mode を想定）やクリッピング等の保護処理があります。
- process_priority.set_process_priority はプラットフォーム差を吸収しており、権限不足時は警告ログを出してスキップします。

---

README に書かれているコマンドや環境変数の詳細は該当モジュール（src/kabusys/*）の docstring やコメントも併せて参照してください。必要であれば各コンポーネント単位の使い方ドキュメント（起動例、設定例、API 使用例）を追記します。