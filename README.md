# KabuSys

日本株自動売買システムのコアライブラリ（README）

このドキュメントはリポジトリ内の主要モジュールに基づく概要、機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

注意: 実行・運用には外部 API（kabuステーション、J-Quants、OpenAI など）やローカル DB（DuckDB / SQLite）を利用します。運用前に必要な API キー・環境変数の設定を必ず行ってください。

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な以下の機能を持つ Python ベースのモジュール群です。

- シグナルの受け取り→発注（ExecutionEngine）
- 発注管理（OrderManager / OrderRepository / Reconciler）
- リスク管理（RiskManager、Gate チェック、ドローダウン監視）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイジング、セクター制限）
- データ解析・リサーチ（ファクター計算、特徴量探索）
- ニュース NLP によるセンチメント（OpenAI を利用したスコアリング）
- 市場レジーム判定（MA とマクロセンチメントの合成）
- 監視（System / Trade / Risk の監視、kill flag、LINE 通知）
- 簡易ダッシュボード（Streamlit）

設計方針の一部：
- DB（DuckDB / SQLite）は読み書き用途で安全性を考慮した実装
- LLM（OpenAI）呼び出しは失敗耐性（リトライ、フォールバック）を備える
- ルックアヘッドバイアスを避ける設計（日付参照の扱いに注意）

---

## 主な機能一覧

- Execution
  - ExecutionEngine: シグナル取得→Gate（リスク）検査→発注→Push Drain（WebSocket 風のプッシュ処理）
  - OrderManager: 発注ワークフロー（作成→送信→同期→キャンセル）
  - Reconciler: 起動時の注文・ポジション同期（自動回復）
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク/プロセス/PID/データ鮮度監視
  - TradeMonitor: 注文滞留、約定異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード永続化
  - MonitoringEngine: 上記モニタを束ねたポーリングループ
  - AlertManager: LINE push による通知（クールダウン管理あり）
  - KillSwitch: kill.flag による ExecutionEngine 停止シグナル
  - Streamlit ダッシュボード（監視用）
- Portfolio
  - 候補選定（score 降順）、等金額・スコア加重の重み計算
  - ポジションサイジング（risk_based / equal / score）、単元株丸め・aggregate cap
  - セクターキャップ、レジーム乗数
- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB ベース）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
- AI
  - news_nlp.score_news: raw_news を集約して OpenAI で銘柄ごとにセンチメントスコアを作成、ai_scores テーブルへ書き込み
  - regime_detector.score_regime: ETF（1321）の MA とマクロセンチメントの合成による日次レジーム判定
- Utils
  - process_priority: プロセス優先度・CPU affinity 設定ユーティリティ
- 設定読み込み
  - kabusys.config.Settings: .env 自動読み込み（プロジェクトルート検出）と環境変数ラッパ

---

## セットアップ手順（ローカル開発 / テスト向け）

以下は最低限のローカルセットアップ手順です。環境に合わせて適宜調整してください。

1. リポジトリをクローン
   - git clone <repository_url>
   - cd <repository_root>

2. Python 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb psutil openai requests streamlit
   - （必要に応じて開発用ツールやテストフレームワークを追加）

   ※ SQLite は標準ライブラリの sqlite3 を使用します。duckdb は Python パッケージとして必要です。

4. data ディレクトリの作成（初期ファイル置き場）
   - mkdir -p data

5. 環境変数の準備（.env を作成するか環境へ設定）
   - .env 例（プロジェクトルートに配置）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - KABUSYS_ENV=development  # or paper_trading / live
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
     - PAPER_FILL_MODE=instant
     - LOG_LEVEL=INFO

   注意点:
   - Settings クラスは .git または pyproject.toml をプロジェクトルート検出基準に .env / .env.local を自動読み込みします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は Settings から必須取得されます。OpenAI キーは AI 機能使用時に必須。

6. DB の初期化
   - Monitoring 用 SQLite は起動スクリプトが必要に応じてスキーマ作成（init_monitoring_db）を実行します。特別な初期 SQL は不要です。
   - DuckDB は prices_daily / raw_financials 等のテーブルを準備する必要があります（データ投入は運用フローに依存）。

---

## 簡単な使い方

実行方法は幾つかのスクリプトから始められます。パッケージをインストールしていない場合は PYTHONPATH を通すかモジュール実行します。

- Execution（取引エンジン）を起動
  - 環境変数例: KABUSYS_ENV=paper_trading（ペーパートレード）、または live
  - 実行例:
    - python -m kabusys.run_execution
    - もしくは python src/kabusys/run_execution.py
  - paper_trading モードでは MockBrokerClient が使用され、デフォルトで data/paper_trading.db に記録されます。

- Monitoring（監視ループ）を起動
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 実行例:
    - python -m kabusys.run_monitoring
    - もしくは python src/kabusys/run_monitoring.py

- Streamlit ダッシュボード（監視画面）を起動
  - 実行例:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- AI: ニューススコアリング（プログラムから呼ぶ）
  - 例（Python REPL / スクリプト内）:
    - from kabusys.ai.news_nlp import score_news
    - import duckdb, datetime
    - conn = duckdb.connect("data/kabusys.duckdb")
    - n = score_news(conn, datetime.date(2026, 3, 20), api_key="sk-...")
    - print("scored", n)
  - OpenAI API キーは引数で渡すか環境変数 OPENAI_API_KEY を利用します。

- レジーム判定（AI + MA による）
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(duckdb_conn, target_date, api_key=...)

- Research / Factor の利用（DuckDB 接続が必要）
  - from kabusys.research import calc_momentum, calc_value, calc_volatility
  - result = calc_momentum(duckdb_conn, target_date)

その他のユーティリティ、モジュール（OrderManager、Reconciler、MonitoringEngine 等）はアプリケーション起動フロー内で組み合わされます。各モジュールはドキュメント文字列と型注釈で使い方が明示されています。

---

## 重要な環境変数（主要なもの）

必須（実行時に参照される、未設定だとエラーになる可能性あり）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン（Settings.jquants_refresh_token）
- KABU_API_PASSWORD — kabuステーション API のパスワード（Settings.kabu_api_password）

主なオプション / 設定
- KABUSYS_ENV — 起動環境: development / paper_trading / live（デフォルト: development）
- OPENAI_API_KEY — OpenAI API キー（AI 機能で必須）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 時の専用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — paper_trading の模擬約定モード（instant|partial|never|reject、デフォルト: instant）
- PID_FILE_PATH — ExecutionEngine の pid ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — kill flag ファイル（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 1 にすると起動時に kill.flag をクリア
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — AlertManager（LINE 通知）設定
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

.env としてプロジェクトルートに配置すれば自動読み込みされます（ただし OS 環境変数が優先されます）。自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 運用上の注意点

- paper_trading モードは本番 DB と分離されるよう実装されています（PAPER_TRADING_SQLITE_PATH を使用）。
- ExecutionEngine と MonitoringEngine は PID ファイル・kill.flag を使ってプロセス監視・停止シグナルをやり取りします。適切なファイルパスと権限を設定してください。
- OpenAI API 呼び出しはレートリミットや一時エラーに対してリトライロジックがありますが、API キーや通信状況に依存するため運用環境での監視を推奨します。
- DuckDB のデータ（prices_daily, raw_financials, raw_news 等）は外部のデータ取得パイプラインで用意する必要があります。リサーチ関数はこれらのテーブルを前提としています。
- Streamlit ダッシュボードは監視 DB を read-only モードで開くため、MonitoringEngine が先に起動していないとエラーとなることがあります。

---

## ディレクトリ構成（主要ファイル説明）

- src/kabusys/
  - __init__.py — パッケージ定義
  - config.py — 環境変数 / 設定管理（.env 自動ロード含む）
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - execution/
    - execution_engine.py — ExecutionEngine（シグナル処理・push drain）
    - order_manager.py — 発注ワークフロー（作成・送信・同期・キャンセル）
    - order_repository.py — （DB 操作）※リポジトリファイル省略（存在前提）
    - reconciler.py — 起動時の注文・ポジション再同期
    - risk_manager.py — リスク管理（設定・チェック）※詳細はファイル参照
    - broker_api.py / broker_factory.py — ブローカー抽象化（本番・モック）
    - order_record.py — 注文状態モデル
  - monitoring/
    - monitoring_db.py — 監視用 SQLite スキーマ & DB ラッパ
    - system_monitor.py — システム状態・データ鮮度の監視
    - trade_monitor.py — 注文滞留・約定異常の監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 管理
    - alert_manager.py — LINE 通知実装
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py — 監視用ダッシュボード（Streamlit）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数算出・集約キャップ処理
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value 等のファクター計算
    - feature_exploration.py — 将来リターン・IC・統計要約
  - ai/
    - news_nlp.py — raw_news を OpenAI でスコアリングして ai_scores に保存
    - regime_detector.py — MA とマクロセンチメントでレジーム判定
  - monitoring/（上記）
  - data/ — 実行時 DB ファイル（デフォルト: data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db）
  - その他モジュール群（execution/order_repository など）

---

## 開発・拡張ポイント（参考）

- DuckDB 上のテーブル（prices_daily, raw_financials, raw_news）を整備すれば、研究・シグナル検証をローカルで実行可能です。
- Broker クライアントは抽象化されているため、新しいブローカー実装を BrokerClientFactory に追加して差し替えられます。
- AI モジュール（news_nlp / regime_detector）は OpenAI の応答形式に強く依存しているため、モデル変更時はレスポンス検証ロジックの確認を推奨します。
- テスト時は OpenAI 呼び出しや時間依存の関数をモックして deterministic に実行できるよう設計されています（モジュール内にモック差替え箇所あり）。

---

この README はコードベース内の docstring と関数説明に基づいて要約しています。各モジュールの詳細は該当ファイルの docstring を参照してください。運用前に .env 設定・DB 構造・ブローカーテスト（paper_trading）で十分に動作確認を行ってください。