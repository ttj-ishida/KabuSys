# KabuSys

日本株向け自動売買システムのサブコンポーネント群。  
このリポジトリには実行用エンジン、監視 (monitoring)、ポートフォリオ構築、リサーチ、AI（ニュース NLP / レジーム検出）などのモジュールが含まれます。

---

## プロジェクト概要

KabuSys は以下の役割を持つモジュールによって構成される自動売買基盤です。

- ExecutionEngine: 発注・オーダー管理・リスク管理を担う実行エンジン
- Monitoring: システム稼働状況・注文ログ・リスク監視および Kill Switch
- Portfolio モジュール: 候補選定、重み計算、ポジションサイズ計算
- Research/AI: DuckDB を用いたファクター計算、特徴量探索、ニュース NLP によるセンチメント評価、レジーム判定
- CLI ツール: .env ウィザード、設定検証、Paper Trading レポート生成 など

設計上のポイント:
- 設定は .env または環境変数で管理（`kabusys.config`）
- DuckDB / SQLite を分析・監視用 DB として利用
- Paper trading（仮想発注）と Live（実運用）を分離
- OpenAI を用いた NLP 機能（API キー必須）
- ロギングは統一的に設定し日次ローテート（`logs/<app>.log`）

---

## 主な機能一覧

- Execution
  - 発注・注文管理（OrderManager / OrderRepository）
  - リスクチェック（RiskManager）
  - Reconciler による注文整合
  - Paper trading 用に MockBroker を利用し本番 DB と分離可能

- Monitoring
  - システムリソース監視（CPU / メモリ / ディスク）
  - データ鮮度チェック（DuckDB の prices_daily 等）
  - 監視ログの永続化（SQLite, MonitoringDB）
  - RiskMonitor によるドローダウン・ポジション上限監視
  - Kill Switch（条件達成で data/kill.flag を書き込み ExecutionEngine を停止）
  - アラート通知へのフック（LINE 等の設定に対応）

- Portfolio / Position sizing
  - 候補選定（スコア降順）
  - 等金額／スコア加重／リスクベースの発注株数算出
  - セクター上限やレジーム乗数による調整

- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - 将来リターン計算、IC（Information Coefficient）算出、統計サマリー

- AI
  - ニュースのセンチメント評価（OpenAI を利用、gpt-4o-mini 想定）
  - マクロニュース + ETF MA による市場レジーム判定

- ユーティリティ
  - .env 対話ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

---

## セットアップ手順（開発 / ローカル利用向け）

前提:
- Python 3.10 以上（PEP 604 の型記法（|）を使用）
- OS: Linux / macOS / Windows（プロセス優先度等はプラットフォーム依存）

1. リポジトリをクローン
   - git clone <repo>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate   （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 必須（主要ライブラリの例）:
     - duckdb
     - psutil
     - openai
     - PyYAML（設定検証で YAML 内容チェックをする場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt がある場合はそれを使ってください:
    pip install -r requirements.txt）

4. .env の作成
   - 対話型ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に手動で .env を作成
   - 注意: .env は決して Git にコミットしないでください

5. 設定検証
   - python -m kabusys.validate_config
   - --strict をつけると警告も失敗扱いになります:
     - python -m kabusys.validate_config --strict

6. データディレクトリの準備（logs, data 等）
   - デフォルトでは `data/` と `logs/` を使用します。必要に応じて作成されますが、権限に注意してください。

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API トークン
- KABU_API_PASSWORD — kabuステーション API パスワード

主要オプション:
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（monitoring）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 専用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — paper_trading の約定挙動（instant / partial / never / reject）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR）
- LOG_DIR — ログファイル保存先（default: logs/）
- OPENAI_API_KEY — OpenAI API キー（ニュース NLP / レジーム検出で使用）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知設定（任意）
- PID_FILE_PATH — ExecutionEngine の PID ファイルパス（default: data/execution.pid）
- KILL_FLAG_PATH — Kill Switch フラグファイルパス（default: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか (0/1)
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

注意:
- run_monitoring は「環境に関係なく」本番 sqlite_path（Settings.sqlite_path）を使用します（監視 DB は一意）。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path を使用して本番 DB と分離します。

---

## 使い方（主要コマンド例）

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン開始（ExecutionEngine）
  - python -m kabusys.run_execution
  - 実運用: KABUSYS_ENV=live を設定して起動（十分な注意を要する）

  動作メモ:
  - paper_trading 環境では MockBrokerClient を使用し data/paper_trading.db に記録されます
  - 起動後は data/execution.pid（または PID_FILE_PATH）の作成・管理を行います
  - 停止は data/stop_requested.flag や data/kill.flag の作成で制御される場合があります（kill.flag は Kill Switch）

- 監視プロセス開始（SystemMonitor）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング周期を秒単位で上書き可能（デフォルト 60 秒）
  - run_monitoring は同一プロジェクトの data/stop_requested.flag を監視し、存在するとループを抜けます

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数より優先）

- AI / レジーム判定・ニュース NLP
  - これらはライブラリ関数として利用できます（OpenAI API キー必要）
  - 例（Python コード内）:
    - from kabusys.ai import score_news
    - score_news(duckdb_conn, target_date, api_key="...")

停止フロー:
- 実行中のエンジン・監視プロセスは data/stop_requested.flag の存在を検知して終了します。
- KillSwitch は条件を満たすと data/kill.flag を書き込み、ExecutionEngine 側で検出して安全に停止する設計です。

ログ:
- デフォルトで logs/<app_name>.log に日次ローテートで保存されます。コンソール出力は stdout。

---

## ディレクトリ構成（要約）

主要ファイル／ディレクトリの説明:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト

  - execution/                — 発注関連コンポーネント群（Engine, Broker, OrderManager, RiskManager 等）
  - monitoring/
    - monitoring_db.py        — SQLite 永続層（テーブル作成・読み書き）
    - system_monitor.py       — システム状態・データ鮮度監視
    - trade_monitor.py        — 注文ログ監視（stale orders / anomaly）
    - risk_monitor.py         — ドローダウン / ポジション上限監視
    - kill_switch.py          — kill.flag の管理
    - monitoring_engine.py    — 各モニタを束ねるエンジン
    - alert_manager.py        — 通知（LINE など）をラップする想定

  - portfolio/
    - portfolio_builder.py    — 候補選定・重み計算
    - position_sizing.py      — 株数計算・キャップ・スケーリング
    - risk_adjustment.py      — セクターキャップ・レジーム乗数

  - research/
    - factor_research.py      — Momentum/Volatility/Value 等の計算（DuckDB）
    - feature_exploration.py  — 将来リターン・IC・統計解析

  - ai/
    - news_nlp.py             — raw_news → OpenAI で銘柄ごとセンチメント算出、ai_scores へ保存
    - regime_detector.py      — ETF MA + マクロ NLP で市場レジームを判定

  - monitoring/               — 上で説明した監視関連（同名ディレクトリ）
  - tools/
    - paper_verification_report.py — Paper Trading レポート生成ツール

  - utils/
    - logging_setup.py        — ログ初期化ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity 設定ユーティリティ

- data/                       — 実行時に使用される SQLite 等の DB、フラグファイルなど（生成される）
- logs/                       — ログファイル出力先（デフォルト）

（注: 上記はリポジトリのソース構成を要約したものです。詳細は各モジュールの docstring を参照してください）

---

## 運用上の注意 / ベストプラクティス

- .env は決してリポジトリにコミットしない。秘密情報（APIキー等）は安全に管理すること。
- 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 に設定することを推奨します。
- OpenAI を使う機能は API 呼び出しにコストが発生するため、テスト時はモックするか API キーなしでスキップしてください。
- run_monitoring は監視 DB（sqlite_path）に書き込みます。監視が常時稼働する想定のため、DB のバックアップやディスク容量に注意してください。
- プロセス優先度の設定（set_process_priority）はプラットフォームにより権限が必要な場合があります（AccessDenied が発生する可能性あり）。
- DuckDB / SQLite のバージョンによって SQL のバインド挙動に差が出るため、テスト環境と本番環境での互換性を確認してください。

---

本 README はコードベースの主要点をまとめたものです。より詳細な実装・拡張方法は各モジュールの docstring やソースを参照してください。必要であればサンプル .env テンプレートや運用手順書（Runbook）を追加で作成します。