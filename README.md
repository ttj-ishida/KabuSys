# KabuSys

KabuSys は日本株自動売買システム（試作/研究用途）のコードベースです。  
主に以下の責務を持つモジュール群で構成されています：市場データ処理、ファクター計算、ポートフォリオ構築、注文発行/管理、実行・リコンシリエーション、監視・アラート、AI を使ったニュース評価など。

---

## プロジェクト概要

- 名前: KabuSys
- 目的: 日本株の自動売買戦略を研究・実行するためのライブラリ兼実行基盤。
- 特徴:
  - DuckDB を使ったファクタ計算・研究用解析
  - SQLite を使った監視ログ／注文ログの永続化
  - 実行エンジン（ExecutionEngine）と監視エンジン（MonitoringEngine）
  - Paper Trading（環境分離）モードのサポート
  - OpenAI を用いたニュースセンチメント評価（ai モジュール）
  - Streamlit ベースの監視ダッシュボード

---

## 主な機能一覧

- research/
  - ファクター（モメンタム、ボラティリティ、バリュー）計算
  - 将来リターン計算・IC 計測・特徴量サマリ
- portfolio/
  - 候補選定、等重・スコア重み、リスク調整（セクター制限、レジーム乗数）
  - 発注株数（単元丸め、リスクベース・等分配）計算
- execution/
  - OrderManager、Reconciler、RiskManager 等による発注管理と起動時リコンシリエーション
  - ブローカークライアントの抽象化（Paper/Live 切替）
- monitoring/
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねた MonitoringEngine
  - SQLite ベースの監視 DB（init_monitoring_db）
  - KillSwitch（flag ファイルによる実行エンジン停止トリガー）
  - AlertManager（LINE へプッシュ通知）
  - Streamlit ダッシュボード（監視 UI）
- ai/
  - ニュースの LLM（OpenAI）によるセンチメントスコア化（batch/robust な実装）
  - 市場レジーム判定（MA200 とマクロニュースセンチメントの合成）
- tools/
  - paper_verification_report: Paper Trading の検証レポート生成スクリプト

---

## セットアップ手順（開発環境向け）

以下は開発環境での最低限の手順例です。環境に合わせて調整してください。

1. Python 仮想環境を作成・有効化（例: Python 3.10+ を想定）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - main に使用されている主な外部依存:
     - duckdb
     - psutil
     - requests
     - streamlit
     - openai
   - 例:
     - pip install duckdb psutil requests streamlit openai

   （プロジェクト配布に requirements.txt があればそれを使用してください。）

3. データディレクトリ作成
   - mkdir -p data

4. 環境変数設定（.env ファイルや環境変数）
   - KABUSYS_ENV: development（デフォルト） / paper_trading / live
   - JQUANTS_REFRESH_TOKEN: 必要に応じて
   - KABU_API_PASSWORD: kabuステーション利用時に必須
   - OPENAI_API_KEY: ai モジュールを使う場合に必須
   - その他の主要な環境変数（デフォルト値は Settings モジュール参照）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - PID_FILE_PATH: data/execution.pid
     - KILL_FLAG_PATH: data/kill.flag
     - PAPER_FILL_MODE: instant|partial|never|reject（paper_trading 時）
     - LOG_LEVEL, CPU/MEM/DISK 閾値など

   Settings モジュールはプロジェクトルートの .env / .env.local を自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

5. DB 初期化（監視 DB は run_* スクリプトでも自動作成されます）
   - run_monitoring や run_execution を起動すると init_monitoring_db が実行され、テーブル作成・マイグレーションを行います。

---

## 使い方（主なコマンド）

- 監視ループの起動（Monitoring）
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可。デフォルト 60 秒。
  - 実行:
    - python -m kabusys.run_monitoring
  - 監視は常に「本番」SQLite パス（Settings.sqlite_path）を使用します（KABUSYS_ENV に依らず）。

- 実行エンジンの起動（Execution）
  - KABUSYS_ENV=paper_trading を指定すると MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します（本番 DB と分離）。
  - 実行:
    - python -m kabusys.run_execution

- Streamlit ダッシュボード
  - 起動:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 読み取り専用で SQLite DB に接続し、ダッシュボードを表示します。

- Paper Trading 検証レポート
  - 実行例:
    - python -m kabusys.tools.paper_verification_report
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - --db で別 DB を指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）。

- AI / レジーム関連
  - OpenAI API を利用するためには OPENAI_API_KEY が必要です。
  - ai.news_nlp.score_news(conn, target_date, api_key=None)
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)

メインの run スクリプトはいずれもプロセス優先度を "high" に設定しようとします（psutil による設定。権限・OS に依存してスキップされる場合あり）。

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（デフォルト 60）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 DB（デフォルト data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- PID_FILE_PATH: ExecutionEngine 用 PID ファイル（デフォルト data/execution.pid）
- KILL_FLAG_PATH: KillSwitch 用 flag（デフォルト data/kill.flag）
- PAPER_FILL_MODE: paper_trading の約定モード（instant|partial|never|reject）
- OPENAI_API_KEY: OpenAI 呼び出しに必要
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE）で通知する場合

詳しくは src/kabusys/config.py の Settings クラスを参照してください。

---

## ディレクトリ構成（抜粋）

（root はパッケージソースの top: src/kabusys/ 以下）

- src/kabusys/
  - __init__.py
  - config.py
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - data/                    — （想定）データ関連（DuckDB テーブルや pipeline）
  - research/
    - factor_research.py     — Momentum/Volatility/Value のファクター計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 発注株数計算（単元丸め・スケールダウン）
    - risk_adjustment.py     — セクター制限・レジーム乗数
  - execution/
    - order_manager.py
    - reconciler.py
    - ...                    — ブローカー抽象・リポジトリ等（コードベースに応じて）
  - monitoring/
    - monitoring_db.py       — SQLite スキーマ/永続化ラッパー
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - alert_manager.py
    - kill_switch.py
    - streamlit_dashboard.py
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）で銘柄別センチメント取得
    - regime_detector.py     — 市場レジーム判定（MA200 + マクロニュース）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート出力ツール
  - utils/
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ

（上記は主なファイルの抜粋です。実ファイル群はリポジトリを参照してください。）

---

## 運用上の注意点 / 補足

- Paper Trading と Live は DB を分離して設計されています。KABUSYS_ENV=paper_trading を使うと paper 用 SQLite に記録され、本番 DB と混ざりません。
- Settings はプロジェクトルートの .env / .env.local を自動読み込みします。テスト時など自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI を用いるモジュールは、ネットワークや API レート制限に対して堅牢化（リトライ・バックオフ・フェイルセーフ）されていますが、API キーや料金に注意してください。
- Monitoring/Execution のプロセス優先度設定は OS による制約を受けます（psutil と権限）。
- kill.flag（Settings.kill_flag_path）を監視して ExecutionEngine を安全に停止する仕組みがあります。kill.flag は既存であれば再書き込みしません。Execution 起動時にクリアする設定もあります（Settings.kill_flag_clear_on_start）。

---

## よく使うコマンドまとめ

- 監視開始:
  - python -m kabusys.run_monitoring
- 実行（Paper Trading）:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要であれば README に「依存関係（requirements.txt の想定内容）」「より詳細な設定例（.env.example の要約）」「開発フロー（テスト・CI）」「各モジュールの詳細ドキュメント」を追加します。どの情報が欲しいか教えてください。