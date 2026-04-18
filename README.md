# KabuSys

日本株向け自動売買システムのコアライブラリ群と起動スクリプト群です。  
このリポジトリは、戦略・ポートフォリオ構築、監視、Execution エンジン、AI 補助（ニュース NLP / レジーム判定）などを含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の主要機能を持つ日本株向け自動売買プラットフォーム（ライブラリ）です。

- 戦略研究（ファクター計算・特徴量解析）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ算出）
- ExecutionEngine（ブローカー抽象化／注文管理／リスク制御）
- 監視（システム・注文・リスク監視、Kill Switch）
- AI 補助（ニュース NLP によるセンチメント、マクロニュースを用いたレジーム判定）
- ペーパートレードと本番の分離（DB・ブローカーの差分）
- 運用補助ツール（設定ウィザード、設定検証、ペーパートレード検証レポート）

設計方針として、
- DB は SQLite（監視）と DuckDB（分析）を利用
- 本番とペーパートレードは DB を分離
- 外部 API 呼び出し（OpenAI 等）は明示的にキーを渡す/環境変数から取得
- ルックアヘッドバイアスを避けるため日付参照に注意
などが採用されています。

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV によって MockBroker を利用）
  - run_monitoring.py: SystemMonitor のポーリングループを起動（監視ログを SQLite に永続化）
- 設定サポート
  - config_setup.py: .env ファイルを対話的に作成・更新するウィザード
  - validate_config.py: .env と config/*.yaml の事前検証 CLI
- 監視（monitoring パッケージ）
  - SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch, MonitoringEngine, MonitoringDB
- ポートフォリオ（portfolio パッケージ）
  - 候補選定、等重／スコア加重、ポジションサイズ決定、セクターキャップ、レジーム乗数
- 研究（research パッケージ）
  - ファクター計算（momentum/value/volatility）、前方リターン、IC 計算、統計サマリ
- AI（ai パッケージ）
  - news_nlp: ニュースを OpenAI API で評価して ai_scores に保存
  - regime_detector: マクロニュース + ETF MA で市場レジーム判定
- ツール
  - tools/paper_verification_report.py: ペーパートレード結果の検証レポート生成

---

## セットアップ手順

前提
- Python 3.10+ を推奨（型注釈、typing の構文を利用）
- SQLite は標準ライブラリで利用可能
- 実行環境に応じて以下のライブラリをインストールしてください

推奨パッケージ（例）
```
pip install duckdb psutil openai PyYAML
```
- duckdb: 分析用 DB
- psutil: プロセス優先度/メトリクス取得
- openai: ニュース NLP / レジーム判定（API を使う場合）
- PyYAML: validate_config の YAML 検証（任意だがあると詳細検証が可能）

プロジェクト初期化
1. リポジトリをクローンして作業ディレクトリに移動
2. 仮想環境を作成して有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate（UNIX）
3. 依存をインストール（上記参照）
4. .env を作成
   - 対話式: python -m kabusys.config_setup
     - このウィザードで J-Quants トークン、kabu API パスワード、DB パスなどを設定します
   - 自動ロードについて: デフォルトでプロジェクトルートの `.env` と `.env.local` を自動読み込みします。
     - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください
5. 設定検証:
   - python -m kabusys.validate_config
   - 警告も厳格に扱う場合: python -m kabusys.validate_config --strict

ディレクトリ作成
- data/ と logs/ は自動的に作成されますが、権限等で失敗する場合は手動で作成してください。

注意点
- .env は絶対に git にコミットしないでください（README には記載されています）
- 本番環境（KABUSYS_ENV=live）の設定は慎重に行ってください（validate_config は警告を出します）

---

## 環境変数（主要なもの）

以下はアプリケーションで使用される主な環境変数とデフォルト/説明です（Settings クラス・config_setup の内容に基づく）。

- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants API リフレッシュトークン
  - KABU_API_PASSWORD: kabuステーション API パスワード

- オプション / デフォルト
  - KABUSYS_ENV: 実行環境（development / paper_trading / live）デフォルト: development
  - KABU_API_BASE_URL: kabuステーション API ベース URL（デフォルト: http://localhost:18080/kabusapi）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite ファイルパス（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
  - PAPER_FILL_MODE: ペーパートレードのフィルモード（instant/partial/never/reject）デフォルト: instant
  - LOG_LEVEL: ログレベル（DEBUG/INFO/...）デフォルト: INFO
  - LOG_DIR: ログディレクトリ（デフォルト: logs/）
  - PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH: Kill Switch の flag パス（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
  - OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時）

その他の閾値
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など（monitoring 用）

---

## 使い方（実行例）

基本的にモジュールはパッケージ実行で起動します。

1. ExecutionEngine（実際のエンジン）を起動
```
python -m kabusys.run_execution
```
- KABUSYS_ENV=paper_trading の場合は MockBroker を使い、data/paper_trading.db を使用して本番 DB と分離します。
- 起動時に data/stop_requested.flag が存在すると起動しません。
- 実行中に stop を指示する場合は data/stop_requested.flag を作成すると安全に停止できます。

2. 監視ループを起動
```
python -m kabusys.run_monitoring
```
- MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（秒、デフォルト 60）。
- 監視は常に本番用 sqlite_path を使って監視ログを残します（環境にかかわらず）。
- 停止は data/stop_requested.flag を作ることでループが終了します。

3. 設定ウィザード（.env 作成）
```
python -m kabusys.config_setup
```

4. 設定検証
```
python -m kabusys.validate_config
python -m kabusys.validate_config --strict   # 警告も FAIL 扱い
```

5. ペーパートレード検証レポート（ツール）
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# または環境変数で DB 指定:
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db python -m kabusys.tools.paper_verification_report
```

6. AI モジュール
- news_nlp.score_news, regime_detector.score_regime などはライブラリ関数として呼び出します。OpenAI API を使用する場合は OPENAI_API_KEY を設定するか、関数へ `api_key` を渡してください。

ログ
- setup_logging により stdout と logs/<app_name>.log（日次ローテート）へ出力します。logs/ ディレクトリは自動的に作成されます（作成に失敗した場合はファイル出力をスキップして標準出力のみ）。

停止 / Kill Switch
- リスク警告等で ExecutionEngine を停止したい場合、KillSwitch が data/kill.flag を書き込みます（実際に ExecutionEngine は stop フラグの検出で停止）。KillSwitch は drawdown やポジション上限等を評価します。
- 管理者は data/kill.flag を手動で作成することでも停止を誘発できます。起動オプションで KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリアします（本番では推奨されません）。

---

## ディレクトリ構成（主要ファイル）

リポジトリの主要なソース配置は以下の通りです（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理（.env 自動読み込み）
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py             — ニュース NLP（OpenAI 経由）
    - regime_detector.py      — レジーム判定
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py        (ファイルは本 README に抜粋されていませんが監視ロジックが存在)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py        (アラート送信ロジックが存在)
  - execution/                 (ExecutionEngine、OrderManager、BrokerFactory 等を含む)
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/                      (runtime: data/*.db, pid/flag ファイルなどを保存)
  - logs/                      (runtime logs/*)

注意: 上記はソースツリーの主要ファイルを抜粋して示したものです。実際のツリーはさらにファイルが含まれます。

---

## 開発・運用上の注意

- 本番環境（KABUSYS_ENV=live）では DB / API キー / Kill Switch の設定を慎重に管理してください。validate_config で本番向けの注意喚起を行います。
- .env は絶対にコミットしないこと（config_setup.py のトップに注意喚起あり）。
- OpenAI API の呼び出しやブローカー呼び出しは外部料金・実取引リスクを伴います。テストは必ず paper_trading 環境で行ってください。
- run_execution / run_monitoring は PID ファイル、stop フラグ、kill.flag を使ってプロセス間制御を行っています。運用時は data/ ディレクトリの取り扱いに注意してください。
- ロギングは stdout とログファイル両方に出力します。ログディレクトリに書き込み権限が必要です。

---

必要であれば、インストール用の requirements.txt や systemd / supervisor 用のユニット定義のテンプレート、開発向けの Dockerfile 等のサンプル README を追記します。どの情報を追加したいか教えてください。