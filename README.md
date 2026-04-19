# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ向け README。

本書はこのコードベースの概要、機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買プラットフォーム用ライブラリ兼実行スクリプト群です。以下の主要コンポーネントを含みます。

- ExecutionEngine：注文発行・リスク管理・約定ハンドリングを行うエンジン
- Monitoring：システム・注文・リスク監視、アラート発行、Kill Switch（停止フラグ）管理
- Portfolio Construction：銘柄選定、重み付け、ポジションサイズ計算
- Research：ファクター計算・統計解析ユーティリティ（DuckDB を利用）
- AI モジュール：ニュースの NLP スコアリング（OpenAI）や市場レジーム判定
- Tools：ペーパートレード検証レポート等の補助スクリプト
- Utils：ロギング設定、プロセス優先度設定 等

設計上のポイント：
- 本番／ペーパー環境を区別（KABUSYS_ENV）
- 設定は .env（自動ロード・対話式ウィザードあり）
- DuckDB/SQLite をデータストアに使用
- OpenAI を使った NLP 機能は API キー必須（任意）

---

## 主な機能一覧

- Execution
  - ブローカークライアント抽象化（本番 / Mock）
  - 注文管理・リスク管理・約定照合
  - paper_trading 環境では MockBrokerClient を用い、別 SQLite に記録
- Monitoring
  - CPU / メモリ / ディスク / プロセス生存のポーリング
  - 注文滞留・約定異常の検出
  - ドローダウン・ポジション上限監視と Kill Switch（data/kill.flag）
  - 通知（LINE など）連携（設定があれば）
- Portfolio construction
  - 候補選定（スコア順）、等金額／スコア加重配分
  - セクター上限適用、レジーム乗数
  - ポジションサイズ計算（リスクベース等）、単元株丸め・スケールダウン処理
- Research
  - Momentum, Volatility, Value 等ファクターの DuckDB ベース計算
  - 将来リターン計算、IC（Information Coefficient）算出、統計サマリー
- AI
  - ニュース記事を LLM（gpt-4o-mini 等）でスコアリングして ai_scores に書き込み
  - マクロニュースを用いた市場レジーム判定（market_regime テーブル）
- Tools
  - ペーパートレード検証レポート生成（成功率、レイテンシ、稼働率判定）

---

## セットアップ手順（ローカル開発用）

前提：
- Python 3.9+ 推奨
- Git 等の基本ツール

1. リポジトリをクローンして作業ディレクトリに移動
   - git clone ... && cd <repo>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必須ライブラリ例（環境に応じて調整してください）:
     - duckdb, psutil, openai, pyyaml
   - 例：
     - pip install duckdb psutil openai pyyaml

   注：requirements.txt はリポジトリに無い場合があります。CI/配布側の指示に従ってください。

4. .env を作成
   - 対話式ウィザードで作成：
     - python -m kabusys.config_setup
   - あるいは手動で .env を作成（プロジェクトルート）。主要な環境変数は下記参照。

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告も含めて厳密に失敗させたい場合は `--strict` オプションを付ける

6. データディレクトリや SQLite/DuckDB ファイルは自動生成されますが、必要に応じて `data/` 配下の権限・場所を確認してください。

---

## 環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

重要（デフォルト値あり）:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: 分析用 DB（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 DB（デフォルト: data/paper_trading.db）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
- LOG_DIR: ログ保存ディレクトリ（既定: logs）
- OPENAI_API_KEY: OpenAI を使う機能を利用する際に必要
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

注意:
- KABUSYS_ENV=paper_trading の場合、Execution は MockBrokerClient を使い、ペーパー用 DB（PAPER_TRADING_SQLITE_PATH）に書き込みます。本番 DB と完全分離されています。
- OpenAI を利用する機能は API コストが発生します。APIキーとコスト管理に注意してください。

---

## 使い方（主要コマンド）

- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine 起動（自動発注）
  - python -m kabusys.run_execution
  - KABUSYS_ENV 環境変数で paper_trading / live 等を指定
  - 停止シグナル: プロジェクトルートの data/stop_requested.flag を作成すると待ちループが停止します
  - Execution は PID を data/execution.pid に書きます（設定によりパス変更可）

- Monitoring 起動（ポーリング）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で変更: MONITOR_POLL_INTERVAL（秒）
  - Monitoring は常に本番用 sqlite_path（SQLITE_PATH）を使用して状態を記録します

- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI 機能（プログラム呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - いずれも OPENAI_API_KEY（または api_key 引数）必須

ログ:
- デフォルトは stdout とログファイル（logs/<app_name>.log）に出力。ログ設定は kabusys.utils.logging_setup.setup_logging で統一。

停止フラグ / Kill Switch:
- Kill Switch: data/kill.flag を作成すると ExecutionEngine に停止シグナルを送ります（モニタリングが検出して書き込む）
- stop_requested.flag: run_* スクリプトの外部停止用フラグ（実行ループがこれを見て終了します）

---

## ディレクトリ構成

（主要ファイルを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数・.env の自動読み込みと Settings クラス
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 起動前設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py             — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py      — 市場レジーム判定（OpenAI を利用）
  - monitoring/
    - monitoring_db.py        — SQLite 永続層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py
    - trade_monitor.py        — （ファイル抜粋にて定義あり）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py        — （アラート送信ロジック等）
  - execution/
    - execution_engine.py     — エンジン本体
    - broker_factory.py       — ブローカークライアント生成（Mock/実ブローカー切替）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py
    - process_priority.py

プロジェクトルートには通常以下が存在:
- .env, .env.local（設定）
- data/（SQLite/DuckDB ファイル、PID/flag ファイル等）
- logs/（ログファイル）
- config/*.yaml（各種テンプレート・設定ファイル、validate_config が参照）

---

## 追加メモ / 運用上の注意

- KABUSYS_ENV の値によって実行挙動が大きく変わります。production 相当の `live` を使う場合は `validate_config` の警告を必ず確認してください。
- OpenAI を用いる機能は外部 API 呼び出しとコスト、応答不安定性を伴います。API失敗時はフォールバック動作（スコア 0 や処理のスキップ）をするよう設計されていますが、運用では API キー管理とレート制限に注意してください。
- ログディレクトリ作成に失敗するとファイル出力は無効化され、コンソールのみの出力になります（setup_logging の仕様）。
- SQLite / DuckDB のパスは Settings 経由で柔軟に上書き可能です（環境変数で指定）。
- ペーパートレードは本番資産・発注系から完全に分離されるよう設計されています。テスト時は paper_trading を有効活用してください。

---

必要に応じて README を拡張します（例: API ドキュメント、起動時の推奨 SystemD ユニット例、CI/CD 用手順、詳細なログ解析方法等）。どの項目を詳述したいか教えてください。