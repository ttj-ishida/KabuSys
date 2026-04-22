# KabuSys

日本株向け自動売買／リサーチ基盤の簡易実装です。  
本リポジトリは取引エンジン、監視・アラート、ポートフォリオ構築、ファクター計算、LLM を用いたニュース評価などのコンポーネントを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群です。

- 日次（またはリアルタイム）でのシグナル検出 → 発注（ExecutionEngine）
- システム稼働状況・注文状況・リスク監視（Monitoring）
- ポートフォリオ構成・株数決定・セクター制約などの純粋関数群（portfolio）
- DuckDB を用いたファクター計算・リサーチ（research）
- OpenAI（LLM）を用いたニュースセンチメント評価（ai）
- ペーパートレード用の分離された DB と検証レポート生成ツール（tools）

設計上の留意点：
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB とは分離された SQLite を使用します（data/paper_trading.db）。
- 環境変数は .env ファイルで管理可能。`config_setup` ウィザード、`validate_config` で事前チェックが可能。
- ログはコンソール（stdout）と日次ローテーションファイル（logs/<app>.log）に出力します。

---

## 主な機能一覧

- Execution
  - 実口座（live）／ペーパートレード（paper_trading）対応の ExecutionEngine 起動スクリプト
  - BrokerClientFactory によるブローカークライアント生成（環境に応じて Mock を使用）
  - リスク管理（RiskManager）、注文管理（OrderManager）、照合（Reconciler）
- Monitoring
  - システム（CPU/Mem/Disk）、データ鮮度、プロセス生存の監視（SystemMonitor）
  - 注文ログの監視（TradeMonitor）、ドローダウン・ポジション数監視（RiskMonitor）
  - KillSwitch によるフラグファイルを書いて Execution を停止する仕組み
  - ポーリングループ起動用スクリプト、MONITOR_POLL_INTERVAL による間隔調整
- Portfolio（純粋関数）
  - 候補選定、等重／スコア重み、ポジションサイズ計算、セクター上限適用、レジーム乗数
- Research
  - DuckDB を用いたモメンタム／ボラティリティ／バリュー計算
  - 将来リターン・IC（Information Coefficient）計算、統計サマリー
- AI
  - ニュース記事を集約して OpenAI（gpt-4o-mini など）に投げ、銘柄ごとのスコアを ai_scores に保存
  - マクロ記事の LLM 判定と ma200 の組合せによる市場レジーム判定
- Tools
  - Paper Trading 検証レポート生成（期間指定可）
- その他ユーティリティ
  - 環境設定ウィザード（config_setup）、設定検証 CLI（validate_config）
  - ログ設定ユーティリティ、プロセス優先度設定ユーティリティ

---

## セットアップ手順

1. Python 環境を作成（例: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール  
   ※ requirements.txt が無い場合は主要依存を手動インストールしてください（例）。
   - pip install duckdb psutil openai

   任意（YAML 検証等）:
   - pip install PyYAML

3. リポジトリをクローン／配置

4. .env を作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - 手動で作成する場合は最低限以下の必須環境変数を設定してください:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要:
     - KABUSYS_ENV の値は "development", "paper_trading", "live" のいずれか
     - Paper Trading を使う場合: KABUSYS_ENV=paper_trading（専用 SQLite を使用）

5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 警告も FAIL 扱いにする: python -m kabusys.validate_config --strict

6. データディレクトリ準備
   - data/ フォルダや logs/ フォルダは自動作成されますが、権限等の問題がある場合は手動で作成してください。

---

## 環境変数（主なもの）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行環境
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- データベース
  - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
  - SQLITE_PATH — デフォルト: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH — ペーパー用 SQLite（デフォルト: data/paper_trading.db）
  - PAPER_FILL_MODE — ペーパートレードの約定モード (instant|partial|never|reject)
- ログ
  - LOG_LEVEL — DEBUG/INFO/...（デフォルト INFO）
  - LOG_DIR — ログ出力先（デフォルト logs/）
- モニタリング
  - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）
- OpenAI
  - OPENAI_API_KEY — ai.score_news / regime_detector 実行時に使用
- Kill Switch
  - KILL_FLAG_PATH — デフォルト data/kill.flag
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）

※ .env 自動ロード: プロジェクトルートに .env / .env.local があれば自動ロードされます。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

---

## 使い方

以下は主要なコマンド例です。パッケージモジュールとして実行します。

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード（警告も FAIL）: python -m kabusys.validate_config --strict

- ExecutionEngine を起動
  - 本番/開発/ペーパートレードは KABUSYS_ENV に依存します。例:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - python -m kabusys.run_execution
  - 実行時は data/execution.pid が指定され、data/stop_requested.flag によって停止できます。
  - ExecutionEngine は設定に応じて MockBrokerClient（paper_trading）や実ブローカーを選択します。

- Monitoring を起動
  - MONITOR_POLL_INTERVAL 環境変数で秒数を上書き可能（例: 30 秒）
  - python -m kabusys.run_monitoring
  - 監視は SQLite（settings.sqlite_path）にログを書きます。監視ループ停止は data/stop_requested.flag を作成。

- Paper Trading 検証レポートの生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI ニュース評価 / レジーム判定（コードから利用）
  - ai.score_news(conn, target_date, api_key=None)  — OPENAI_API_KEY を参照
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)

停止方法（Execution / Monitoring 共通）
- data/stop_requested.flag を作成すると起動中のループが検知して終了します。  
  また KillSwitch（条件を満たした場合）により data/kill.flag が書かれ、Execution 停止のトリガになります。

ログ
- デフォルトで logs/<app>.log に日次ローテーションで出力されます（30 日保持）。
- コンソールは stdout に出力されます。

---

## ディレクトリ構成

主要ファイル・ディレクトリ（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込み
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py            — ニュース NLP / OpenAI 統合
    - regime_detector.py     — 市場レジーム判定
  - monitoring/
    - monitoring_db.py       — SQLite 永続層
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py       — （存在する想定）注文監視
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py       — （存在する想定）通知管理
  - execution/
    - execution_engine.py    — 実エンジン（EngineConfig 等）
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - data/
    - pipeline.py            — DuckDB / prices データ取得ユーティリティ等
    - stats.py               — 正規化ユーティリティ等
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py

ルートに存在する想定のディレクトリ・ファイル：
- data/                       — SQLite ファイル、flag、pid など（自動生成されることが多い）
  - monitoring.db (SQLITE_PATH)
  - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
  - kill.flag
  - stop_requested.flag
  - execution.pid
- logs/                       — ログファイル（logs/execution.log, logs/monitoring.log 等）
- config/                     — YAML 設定ファイル（system_config.yaml 等。validate_config が参照）
- .env / .env.local            — 環境変数ファイル（.git にコミットしないこと）

---

## 注意事項 / 運用上のヒント

- 本番（KABUSYS_ENV=live）では kill.flag 自動クリア（KILL_FLAG_CLEAR_ON_START=1）は危険です。0 を推奨します。
- Paper Trading 用 DB は本番 DB と明確に分離されています。環境変数を正しく設定してください。
- OpenAI を使う機能を運用する場合、API のレート制限・料金に注意してください。API キーは安全に管理してください。
- ローカルで開発する場合は KABUSYS_ENV=development を使い、実際の発注処理が行われないことを確認してください。
- モジュールの多くは外部ライブラリ（duckdb, psutil, openai, PyYAML 等）に依存します。環境構築時にインストールを忘れないでください。

---

もし README に追加したい詳細（例: API ドキュメント、設定ファイルテンプレート、CI 手順、実行例のログ出力例など）があれば教えてください。必要に応じて追記します。