# KabuSys

日本株自動売買システムの一部である小規模モジュール群のリポジトリです。  
この README は、コードベース（src/kabusys 以下）を基に主要機能・セットアップ・利用方法を日本語でまとめたものです。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（起動コマンド例）
- 重要な環境変数
- ディレクトリ構成（主要ファイル説明）
- 補足・運用上の注意

---

## プロジェクト概要

KabuSys は日本株向けの自動売買／監視ツール群です。  
主な役割は次のとおりです。

- 注文の作成・送信・状態同期（ExecutionEngine 周辺）
- 実行系の監視（CPU・メモリ・ディスク・注文滞留・約定異常など）
- リスク監視（ドローダウン・ポジション上限）
- Paper Trading（模擬発注）とその検証レポート生成
- ファクター計算・リサーチ用ユーティリティ（DuckDB を用いる）
- ニュースに対する LLM を使ったセンチメントスコアリング（OpenAI）
- 簡易ダッシュボード（Streamlit）

コードは純粋関数（ポートフォリオ構築、ポジション決定など）と、DBアクセス・外部API呼び出しを行う実行部分に分かれています。設定は環境変数／`.env` ファイルで行います。

---

## 機能一覧（抜粋）

- execution
  - OrderManager：発注ワークフロー（作成→送信→同期）を管理
  - Reconciler：再起動時の注文・ポジション同期（ブローカー突合）
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - Paper Trading モード（KABUSYS_ENV=paper_trading）時は MockBrokerClient を利用し、data/paper_trading.db に記録して本番 DB と分離

- monitoring
  - SystemMonitor：CPU/メモリ/ディスク/プロセス・データ鮮度監視
  - TradeMonitor：滞留注文・約定異常価格検出
  - RiskMonitor：ドローダウン／ポジション上限監視（kill flag 生成）
  - KillSwitch：kill.flag による ExecutionEngine 停止シグナル出力
  - AlertManager：LINE Push を使った通知（クールダウン管理付き）
  - MonitoringEngine：上記を束ねてポーリング実行
  - SQLite ベースの永続化レイヤ（monitoring_db.py）
  - Streamlit ダッシュボード（read-only 接続）

- portfolio
  - 候補選定／重み計算（等配分・スコア配分）
  - セクター制限／レジーム乗数
  - 株数計算（単元丸め・risk-based 等）

- research
  - ファクター計算（モメンタム／バリュー／ボラティリティ）
  - 将来リターン計算、IC（Information Coefficient）などの統計ユーティリティ

- ai
  - news_nlp.score_news：OpenAI を使ったニュースセンチメントスコア計算と ai_scores への書き込み
  - regime_detector.score_regime：ETF の MA とマクロニュースの LLM センチメントを合成して市場レジーム判定

- tools
  - paper_verification_report：Paper Trading DB の検証レポート出力ツール（期間指定可）

- utils
  - process_priority：プロセス優先度 / CPU affinity 設定ユーティリティ

---

## セットアップ手順

前提
- Python 3.10 以上（型ヒントに `X | None` 形式を利用）
- SQLite（標準ライブラリ）、DuckDB、psutil 等の外部パッケージが必要

推奨手順（例）

1. 仮想環境の作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージのインストール（例）
   - pip install duckdb psutil requests openai streamlit
   - 追加でテストや運用に必要なパッケージをインストールしてください。

   （プロジェクトに requirements.txt があればそれを使ってください。）

3. 環境変数 / .env の準備
   - プロジェクトルートに .env または .env.local を置くと、自動的に読み込まれます（OS 環境変数を上書きしない動作がデフォルト）。
   - 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
   - 必要な環境変数の例は次節「重要な環境変数」を参照。

4. データディレクトリの作成
   - デフォルトで data/ 以下に DB ファイルを置きます。必要に応じてディレクトリを作成してください。
     - mkdir -p data

5. DuckDB / SQLite DB の準備
   - 初回起動時に監視 DB（SQLite）のテーブルは init_monitoring_db() により自動的に作られます。
   - DuckDB は prices_daily / raw_financials / raw_news 等のテーブルを期待します。データロードは別途行ってください。

---

## 使い方（起動コマンド例）

- Monitoring（常駐監視ループ）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 起動直後にプロセス優先度を "high" に変更しようとします（権限がない場合は警告）。

- Execution（発注エンジン）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 SQLite（デフォルト: data/paper_trading.db）へ書き込みます。
  - 通常環境（live / development）では settings.sqlite_path を使用します。

- Streamlit ダッシュボード（監視 UI）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは監視 DB を read-only で開き、概要・ポジション・直近注文・システム状態等を表示します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で SQLite ファイルを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH でも可）。

- AI / レジーム判定等（Python API）
  - ai スコアリング関数はプログラムから直接呼べます（例）:
    - from kabusys.ai.news_nlp import score_news
    - from kabusys.ai.regime_detector import score_regime
  - これらは DuckDB 接続と target_date を受け取り、OpenAI API KEY（api_key 引数または環境変数 OPENAI_API_KEY）を用いて処理します。

---

## 重要な環境変数（主要なもの）

- 基本
  - KABUSYS_ENV: 実行環境。development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL: ログレベル（DEBUG, INFO, ...）

- API / 認証
  - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須な箇所あり）
  - KABU_API_PASSWORD: kabuステーション API のパスワード（必須な箇所あり）
  - OPENAI_API_KEY: OpenAI API Key（ai モジュール使用時）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用

- DB / ファイルパス
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: Monitoring SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH: ExecutionEngine 用 PID ファイルパス（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH: Kill flag ファイルパス（デフォルト: data/kill.flag）

- Paper Trading 固有
  - PAPER_FILL_MODE: 模擬約定の振る舞い（instant / partial / never / reject、デフォルト: instant）

- Monitoring 関連
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）
  - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: しきい値（%）

- その他
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動読み込みを無効化します。  
    デフォルトではプロジェクトルート（.git または pyproject.toml を基準）にある .env/.env.local を読み込みます。

---

## ディレクトリ構成（主要ファイルと役割）

（パスは src/kabusys 以下）

- __init__.py
  - パッケージメタデータ（__version__ 等）

- config.py
  - 環境変数 / .env の読み込みと Settings クラス。自動 .env ロード機能を含む。

- run_monitoring.py
  - SystemMonitor をポーリングで実行する起動スクリプト。MONITOR_POLL_INTERVAL を参照。

- run_execution.py
  - ExecutionEngine を起動するスクリプト。paper_trading 時は専用 DB を使用。

- monitoring/
  - monitoring_db.py: SQLite を使った永続化レイヤ（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py: CPU/メモリ/ディスク/プロセス/データ鮮度のチェック
  - trade_monitor.py: 注文滞留／約定異常の検出
  - risk_monitor.py: ドローダウン・ポジション上限の監視
  - kill_switch.py: kill.flag を書き込むロジック
  - alert_manager.py: LINE 通知（クールダウン付き）
  - monitoring_engine.py: 各 Monitor を束ねるエンジン（run / run_once）
  - streamlit_dashboard.py: Streamlit ベースの監視ダッシュボード

- execution/
  - order_manager.py: 発注ワークフロー（作成→送信→同期）
  - reconciler.py: 再起動時の注文/ポジション突合自動化
  - order_repository.py 等（DB とのやり取りを担うモジュールが想定される）

- portfolio/
  - portfolio_builder.py: 候補選定・スコア順ソート
  - position_sizing.py: 株数計算（リスクベース・等分等）
  - risk_adjustment.py: セクター上限・レジーム乗数

- research/
  - factor_research.py: Momentum / Value / Volatility 等のファクター計算（DuckDB）
  - feature_exploration.py: 将来リターン、IC、統計サマリ等

- ai/
  - news_nlp.py: raw_news を OpenAI でパースして ai_scores を書き込む
  - regime_detector.py: MA とマクロニュースを組み合わせたレジーム判定

- tools/
  - paper_verification_report.py: Paper Trading DB の検証レポート生成スクリプト

- utils/
  - process_priority.py: プラットフォーム差分を吸収したプロセス優先度・CPU affinity ユーティリティ

---

## 補足・運用上の注意

- Paper Trading は本番 DB と分離するよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）。
- 監視（Monitoring）モジュールは監視ログ（SQLite）へ永続化します。初回起動でテーブルが自動作成され、既存スキーマに対するマイグレーション（カラム追加）も行います。
- OpenAI を呼ぶモジュールは API の rate limit / 一時エラーに対してエクスポネンシャルバックオフを実装していますが、API キーやコストの管理には注意してください。
- process priority / cpu affinity の設定は OS によって動作が異なります。権限不足で設定に失敗した場合はログに警告が出ますが、処理自体は継続します。
- .env パーサはシェル風の記述（export を含む行、クォートやエスケープ）に対応します。`.env.example` を用意しておくと環境準備が簡単になります（リポジトリにある場合）。

---

README はここまでです。必要があれば次の情報を追記します：
- requirements.txt の推奨内容（依存バージョン）
- 実行例のログ抜粋
- DB スキーマの詳細（列説明）
- テストの実行方法

どれを追加しますか？