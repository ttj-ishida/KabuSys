# KabuSys — README (日本語)

KabuSys は日本株の自動売買・リサーチ・監視を目的としたモジュール群です。本リポジトリは実運用向けの Execution / Monitoring / Research / AI 支援機能を含みます。設計方針は「副作用を最小化した純粋関数」「フェイルセーフ」「ルックアヘッドバイアス回避」です。

以下はコードベース（src/kabusys）に基づく README です。

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（起動コマンド・サンプル）
- 環境変数（主要）
- ディレクトリ構成（主要ファイルと説明）
- 開発メモ / 注意点

---

## プロジェクト概要

KabuSys は以下の主要機能を備えた日本株向けの自動売買システムライブラリです。

- ExecutionEngine：ブローカー API とやり取りして注文を送信／管理する
- Monitoring：システム／注文／リスクの監視、アラート送信、kill flag による安全停止
- Portfolio construction：銘柄選定・重み計算・ポジションサイズ算出（純粋関数）
- Research：DuckDB 上の価格・財務データからファクター計算・IC 解析など
- AI 支援：ニュースから LLM を用いた銘柄センチメント / マクロセンチメント判定
- Tools：Paper Trading の検証レポート生成、Streamlit ダッシュボードなど

設計上、Research / AI の一部処理は DuckDB（ローカルファイル）を使って完結します。Paper trading は本番 DB と分離する仕組みを持ちます。

---

## 主な機能一覧

- System monitoring（CPU/メモリ/ディスク、データ鮮度、実行プロセス監視）
- Trade monitoring（滞留注文チェック、約定価格異常検出）
- Risk monitoring（ドローダウン・ポジション上限検知、risk_logs 登録）
- Kill switch（条件発生時にファイルを書き kill flag で Execution を停止）
- LINE 通知（AlertManager）による通知（トークン未設定時はログに落とす）
- ExecutionEngine の再起動時リコンシリエーション（注文状態・ポジション整合）
- Portfolio construction：候補選定（score / equal）、セクター制限、リスクベースサイズ算出
- Research：モメンタム／ボラティリティ／バリューなどのファクター計算、IC・統計要約
- AI：ニュースを LLM（OpenAI）でスコアリングして ai_scores に保存、レジーム判定
- ツール：Paper Trading 検証レポート生成（DB から指標を算出）、Streamlit ダッシュボード

---

## セットアップ手順（ローカル開発向け）

前提：
- Python 3.10+（typing | None などの型注釈に依存）
- SQLite（標準ライブラリ）
- DuckDB（ローカルファイル DB）
- ネットワークアクセス（OpenAI API を使う場合）

1. リポジトリをクローンし、仮想環境を作成して有効化：
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージをインストール（requirements.txt がある想定、無ければ下記を手動インストール）：
   - pip install duckdb psutil requests streamlit openai

   必要に応じて development 用に追加パッケージをインストールしてください。

3. 環境変数の用意：
   - プロジェクトルートに `.env` / `.env.local` を作成して設定できます。
   - 自動ロードはデフォルトで有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）。
   - 主要な環境変数例（詳細は次節参照）：
     - KABUSYS_ENV, OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など。

4. データディレクトリ（デフォルト）：
   - data/kabusys.duckdb（DuckDB）
   - data/monitoring.db（監視用 SQLite）
   - data/paper_trading.db（paper_trading 用 SQLite）
   - これらは Settings のデフォルト値で変更可能です。

5. DB 初期化：
   - Monitoring 系は起動時に init_monitoring_db() が呼ばれます。特別なマイグレーションは自動で行われます。

---

## 使い方（起動コマンド・サンプル）

コードはパッケージモジュールとして実行できます。プロジェクトルートで仮想環境を有効にした状態で実行してください。

- 監視（Monitoring）を起動：
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
  - Monitoring は本番の sqlite_path を環境にかかわらず使用します（監視ログは production DB に記録）

- ExecutionEngine を起動：
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を利用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に注文ログを記録します。
  - 起動時にプロセス優先度が High に設定されます（psutil を利用）

- Streamlit ダッシュボード：
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を read-only で開いてダッシュボード表示。MonitoringEngine が稼働している必要があります。

- Paper Trading 検証レポート生成：
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを指定可能。デフォルトは data/paper_trading.db。

- AI スコアリング（プログラムから呼ぶ例）：
  - kabusys.ai.score_news(conn, target_date, api_key=...)
  - kabusys.ai.regime_detector.score_regime(duckdb_conn, target_date, api_key=...)
  - OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY を使用。

- Research API（プログラム利用）：
  - duckdb_conn = duckdb.connect("data/kabusys.duckdb")
  - from kabusys.research import calc_momentum, calc_volatility, calc_value
  - calc_momentum(duckdb_conn, date(2026, 4, 1)) など

---

## 主要な環境変数（抜粋）

設定は Settings クラス（kabusys.config）で管理され、自動的に `.env` / `.env.local` をプロジェクトルートから読み込みます（OS 環境変数を上書きしない挙動がデフォルト）。

- KABUSYS_ENV
  - 値: development | paper_trading | live
  - デフォルト: development

- OPENAI_API_KEY
  - OpenAI API のキー（news_nlp / regime_detector で使用）

- JQUANTS_REFRESH_TOKEN
  - J-Quants API 用トークン（必須プロパティを参照する箇所あり）

- KABU_API_PASSWORD
  - kabuステーション等の API パスワード

- KABU_API_BASE_URL
  - デフォルト: http://localhost:18080/kabusapi

- DUCKDB_PATH
  - デフォルト: data/kabusys.duckdb

- SQLITE_PATH
  - 監視 DB（monitoring）デフォルト: data/monitoring.db

- PAPER_TRADING_SQLITE_PATH
  - paper_trading 用 SQLite（デフォルト: data/paper_trading.db）

- PAPER_FILL_MODE
  - paper_trading の MockBroker の約定挙動
  - 有効値: instant | partial | never | reject
  - デフォルト: instant

- PID_FILE_PATH
  - デフォルト: data/execution.pid

- KILL_FLAG_PATH
  - デフォルト: data/kill.flag

- MONITOR_POLL_INTERVAL
  - run_monitoring のポーリング間隔（秒）、デフォルト 60（整数）

- LOG_LEVEL
  - DEBUG|INFO|WARNING|ERROR|CRITICAL

- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
  - AlertManager（LINE Push）用。未設定なら送信をスキップしてログのみ。

- KABUSYS_DISABLE_AUTO_ENV_LOAD
  - 1 を設定すると .env の自動読み込みを無効化します（テスト用）

---

## ディレクトリ構成（主要ファイルと説明）

以下は src/kabusys 内の主要モジュールと簡単な説明です。

- kabusys/
  - __init__.py — パッケージメタ情報（__version__ 等）
  - config.py — 環境変数 / Settings 管理、.env 自動ロードロジック
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト（Paper Trading モードあり）
- kabusys/monitoring/
  - monitoring_db.py — SQLite スキーマ初期化・永続化ユーティリティ（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py — CPU/メモリ/ディスク/データ鮮度・PID ファイル監視
  - trade_monitor.py — 注文滞留・約定価格異常チェック
  - risk_monitor.py — ドローダウン / ポジション上限の監視
  - kill_switch.py — kill.flag ファイル書き込みロジック
  - alert_manager.py — LINE Push API 経由の通知
  - monitoring_engine.py — 複数モニタを束ねるエンジン（run / run_once）
  - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード
- kabusys/execution/
  - order_manager.py, order_repository.py, reconciler.py, execution_engine.py, broker_factory 等 — 注文管理・永続化・再同期ロジック
- kabusys/portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 発注株数計算（単元丸め・リスク制限）
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- kabusys/research/
  - factor_research.py — Momentum / Volatility / Value のファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン計算、IC、統計サマリ機能
- kabusys/ai/
  - news_nlp.py — raw_news を LLM で評価して ai_scores に保存する処理（OpenAI）
  - regime_detector.py — ETF の MA200 とマクロニュースの LLM 出力を合成して市場レジーム判定
- kabusys/tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成ツール（コマンドライン）
- kabusys/utils/
  - process_priority.py — psutil を使った優先度 / CPU affinity 設定ユーティリティ

---

## 開発メモ / 注意点

- .env パーサーは複雑なクォートやエスケープ、コメント処理をサポートします。自動読み込みはプロジェクトルート（.git / pyproject.toml）を検出して行います。
- Monitoring の init は冪等であり、既存スキーマに対する軽微なマイグレーション（列追加）を行います。
- Execution の Paper Trading モードは本番 DB と完全に分離する設計（PAPER_TRADING_SQLITE_PATH を使用）。
- AI の OpenAI 呼び出しはネットワークエラーや 429 や 5xx をリトライする実装になっていますが、API キーは必須（未設定だと例外）。
- process priority / cpu affinity はプラットフォーム差分を吸収しますが、権限不足で失敗することがあります（警告ログ）。
- DuckDB の executemany に空リストを渡すとバージョンによってエラーになるため、空リスト時の分岐が実装されています。
- LLM 出力は JSON mode を利用し、失敗した場合でもフェイルセーフに 0.0 を使うなどの保護があります。テストでは API 呼び出しをモックしてください。

---

もし README に追加して欲しい項目（インストール用 requirements.txt、CI / テスト手順、.env.example のテンプレート、実行例のログ出力例など）があれば教えてください。必要に応じて追記・整形します。