# KabuSys

日本株自動売買システムのミニマル実装。戦略のポートフォリオ構築、ポジションサイズ計算、実行エンジン、監視（Monitoring）、ニュースNLP / レジーム判定などのユーティリティ群を含みます。

この README はコードベース（src/kabusys）に基づいて作成しています。

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（起動・各ツール）
- 環境変数一覧（主要なもの）
- 停止・制御フラグ
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株自動売買を想定した小規模なシステムです。主な役割は次の通りです。

- 戦略で生成されたシグナルを受けて注文を管理・送信する ExecutionEngine（実行系）
- システム状態・注文・リスクを定期的に監視してログ・アラート・KillSwitch を提供する Monitoring
- ファクター計算・特徴量探索等の Research ツール（DuckDB を使用して価格・財務データを解析）
- ニュースを LLM（OpenAI）でスコアリングする AI モジュール（ニュースセンチメント -> ai_scores）
- Paper Trading 用の分離された DB を用意した検証パス
- Streamlit ベースの監視ダッシュボードや検証レポート作成ツール

設計方針として、DB（SQLite / DuckDB）をローカルファイルで管理し、外部ブローカー呼び出しは抽象化されています。LLM 呼び出しは OpenAI SDK を使う実装になっています。

---

## 主な機能一覧

- Execution
  - 注文状態管理（OrderManager / OrderRepository）
  - Reconciler による再起動後の自動同期
  - Paper Trading と Live の分離（PAPER_TRADING_SQLITE_PATH）
- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / プロセス生存 / データ鮮度監視
  - TradeMonitor: 滞留注文・約定価格異常の検出
  - RiskMonitor: ドローダウン・ポジション上限の監視、dashboard 更新
  - KillSwitch: 条件に応じて停止フラグ（data/kill.flag）を出力
  - AlertManager: LINE へ通知（push）
  - Streamlit ダッシュボードで監視データを可視化
- Research
  - ファクター計算（momentum / volatility / value）
  - 将来リターン、IC（情報係数）、統計サマリー
- AI
  - news_nlp: 記事を LLM でセンチメント化し ai_scores に保存
  - regime_detector: ma200 とマクロニュースを用いた市場レジーム判定
- Portfolio
  - 候補選定、重み計算、セクター制限、ポジションサイズ計算（単元丸め、集約キャップ）
- Tools
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report.py）

---

## セットアップ手順

1. Python（3.9+ 推奨）をインストールします。
2. 仮想環境を作成・有効化：
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストールします（requirements.txt が無い場合は手動で）：
   - pip install duckdb psutil requests openai streamlit
   - 追加の開発用ツールやテストフレームワークを必要に応じてインストールしてください。
4. データディレクトリを作成：
   - mkdir -p data
   - （必要に応じて）touch data/monitoring.db data/kabusys.duckdb data/paper_trading.db
     — 起動スクリプトは DB が存在しない場合でもテーブルを作成するユーティリティを呼びますが、事前にファイルを準備しておくとアクセス権の問題を回避できます。
5. 環境変数を準備：
   - プロジェクトルートに .env または .env.local を置くと自動読み込みされます（OS 環境変数が優先されます）。
   - テスト時に自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## 環境変数（主要なもの）

（デフォルト値があるものは併記）

- KABUSYS_ENV: 起動環境（development / paper_trading / live）。デフォルト: development
  - paper_trading の場合、専用の paper_trading DB（PAPER_TRADING_SQLITE_PATH）を使用します。
- JQUANTS_REFRESH_TOKEN: 必須（J-Quants API 用）
- KABU_API_PASSWORD: 必須（kabuステーション API パスワード）
- OPENAI_API_KEY: OpenAI API キー（AI モジュールで必要）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager（LINE push）で使用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: KillSwitch が書き込むフラグファイル（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag をクリアするか（"1" で有効）
- PAPER_FILL_MODE: Paper Trading の受渡シミュレーション（instant / partial / never / reject）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト: 60）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視の閾値（%）

注意: 必須 env が不足すると Settings が ValueError を投げます。

---

## 使い方（起動・各ツール）

基本的にはパッケージを Python モジュールとして実行します。プロジェクトルートで実行してください。

1. Monitoring を起動する（常時ポーリング）
   - モジュール: src/kabusys/run_monitoring.py
   - 実行例:
     - python -m kabusys.run_monitoring
   - 動作:
     - MONITOR_POLL_INTERVAL（秒）を環境変数で上書き可能（デフォルト 60 秒）
     - 監視データは Settings.sqlite_path（監視 DB）へ書き込む
     - 停止フラグ（data/stop_requested.flag）を検知するとループを終了します
     - 起動直後にプロセス優先度を "high" に設定しようとします（権限により失敗する場合は警告）

2. ExecutionEngine を起動する（注文実行）
   - モジュール: src/kabusys/run_execution.py
   - 実行例:
     - python -m kabusys.run_execution
     - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
   - 動作:
     - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（data/paper_trading.db）に記録して本番 DB と分離
     - 実行中は PID を data/execution.pid に書きます（設定により変更可能）
     - data/stop_requested.flag を作成すると安全に停止します

3. Streamlit ダッシュボード（監視データの可視化）
   - ファイル: src/kabusys/monitoring/streamlit_dashboard.py
   - 実行例:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

4. Paper Trading 検証レポートを生成
   - スクリプト: src/kabusys/tools/paper_verification_report.py
   - 実行例:
     - python -m kabusys.tools.paper_verification_report
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     - デフォルト DB: data/paper_trading.db。--db で指定可能。

5. AI / レジーム判定・ニューススコアリング
   - ニューススコアリング:
     - from kabusys.ai.news_nlp import score_news
     - duckdb 接続を渡し、score_news(conn, target_date, api_key=None)
     - OPENAI_API_KEY が必要（引数で渡すことも可）
   - レジーム判定:
     - from kabusys.ai.regime_detector import score_regime
     - score_regime(conn, target_date, api_key=None)

6. 停止・制御
   - 即時停止（ExecutionEngine を停止させる）：data/kill.flag を作成（KillSwitch が評価していれば ExecutionEngine を停止する仕組み）
   - 優雅な停止（run_execution/run_monitoring へ）：data/stop_requested.flag を作成すると各ループが検知して終了
   - 起動時に kill.flag を自動で消したい場合は Settings.kill_flag_clear_on_start を有効にする設定を使ってください。

---

## 注意事項・運用メモ

- Paper Trading と Live は DB を分離しており、paper_trading 環境は本番 DB に影響を与えません（PAPER_TRADING_SQLITE_PATH を使用）。
- OpenAI を使用する機能は API 呼び出しの失敗に対してバックオフとフェイルセーフ（スコア 0.0 等）を実装していますが、本番運用時には API レートや料金に注意してください。
- プロセス優先度設定や CPU affinity は OS 権限に依存します。権限不足の場合はログに警告が出ます。
- 一部の DB 操作は既存列の有無でマイグレーション（ALTER）を行います。既存 DB に対する後方互換性をある程度考慮していますが、運用時はバックアップを推奨します。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュールの一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                        — 環境変数読み込み・Settings
  - run_monitoring.py                — SystemMonitor ポーリング起動スクリプト
  - run_execution.py                 — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py   — Paper Trading レポート生成
  - monitoring/
    - __init__.py
    - monitoring_db.py               — SQLite 監視 DB の初期化・操作
    - monitoring_engine.py           — 各 Monitor を束ねるエンジン
    - system_monitor.py              — CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - trade_monitor.py               — 滞留注文・約定異常監視
    - risk_monitor.py                — ドローダウン/ポジション上限監視
    - kill_switch.py                 — kill.flag 書込みロジック
    - alert_manager.py               — LINE 通知
    - streamlit_dashboard.py         — Streamlit ダッシュボード
  - execution/
    - order_manager.py
    - reconciler.py
    - order_repository.py
    - ... (ブローカー抽象など)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py                     — ニュースセンチメント取得（OpenAI）
    - regime_detector.py              — レジーム判定（ma200 + macro sentiment）
    - __init__.py
  - utils/
    - process_priority.py             — process priority / CPU affinity ユーティリティ
    - __init__.py
  - data/                             — 実行時に使用するファイル群（DB・フラグ・PID など）
    - monitoring.db (デフォルト)
    - kabusys.duckdb (デフォルト)
    - paper_trading.db (paper_trading 用)

（実際のツリーはリポジトリ内のファイルに従ってください。上は要点の抜粋です）

---

必要であれば README に追加してほしい内容（例: 詳細な API 使用例、テストの実行方法、CI 設定、requirements.txt の具体的記載など）を教えてください。