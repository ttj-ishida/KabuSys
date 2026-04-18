# KabuSys

日本株向け自動売買システムのサンプル実装 (モジュール群のみ)。  
この README はリポジトリ内の主要スクリプト・設定方法・使い方・ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は以下の主要機能を持つモジュール群から構成されています。

- 実取引/ペーパートレード用の ExecutionEngine 起動スクリプト
- 監視（System / Trade / Risk）を行う Monitoring コンポーネントとポーリングエンジン
- ポートフォリオ構築（候補選定・重み算出・ポジションサイズ計算）ロジック
- リサーチ用のファクター計算・特徴量探索モジュール（DuckDB を利用）
- ニュース NLP を使ったセンチメント評価・レジーム判定（OpenAI API 経由）
- 設定ウィザード・設定検証ツール・検証レポート生成スクリプト
- ロギング/プロセス優先度設定などのユーティリティ

設計上のポイント:
- DuckDB / SQLite をデータストアとして使用
- 設定は .env（環境変数）で管理。`.env.local` による上書きもサポート
- ペーパートレードは本番 DB とは分離（デフォルトで `data/paper_trading.db`）
- ロギングは共通ユーティリティで統一（コンソール + 日次ローテートファイル）

---

## 主な機能一覧

- run_execution.py: ExecutionEngine の起動。KABUSYS_ENV=`paper_trading` の場合は MockBroker（paper DB）を使用
- run_monitoring.py: SystemMonitor のポーリングループ起動。ポーリング間隔は環境変数で調整可能
- monitoring/*: SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / MonitoringEngine 等
- portfolio/*: 候補選定、重み計算、リスク調整、ポジションサイズ計算（純粋関数）
- research/*: ファクター計算（モメンタム/ボラティリティ/バリュー）、将来リターン、IC 計算
- ai/*: ニュース NLP（OpenAI を使った銘柄センチメント）とレジーム判定
- tools/paper_verification_report.py: Paper Trading の検証レポート生成 CLI
- config_setup.py: .env の対話式ウィザード（初期設定）
- validate_config.py: 起動前の設定検証 CLI
- utils/*: ロギング設定、プロセス優先度設定、など

---

## 必要条件 / 依存ライブラリ

推奨: Python 3.10+（型注釈に union 型等を使用）  
主要依存（例）:
- duckdb
- psutil
- openai
- PyYAML（config ファイルの検証に使用。インストールされていない場合は検証をスキップ）
（requirements.txt がある場合はそれを使ってください）

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順（簡易ガイド）

1. リポジトリをチェックアウトし、仮想環境を作成・有効化します。

2. 必要パッケージをインストールします（上記参照）。

3. .env を作成（対話式ウィザード推奨）:
```bash
python -m kabusys.config_setup
```
ウィザードは J-Quants トークン、kabuAPI パスワード、DB パス、KABUSYS_ENV など主要な設定を対話的に作成します。

4. 設定を検証:
```bash
python -m kabusys.validate_config        # 警告は表示されるが exit 0
python -m kabusys.validate_config --strict  # 警告も FAIL として exit 1
```

5. データディレクトリなど初期ファイルが必要なら作成します（`data/` や `logs/` は logging_setup が自動で作成しますが、権限等に注意）。

---

## 主要環境変数（抜粋）

- KABUSYS_ENV: 実行環境 (development | paper_trading | live)、既定: development
- JQUANTS_REFRESH_TOKEN: J-Quants API リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB ファイルパス（既定: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（既定: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（既定: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定モード（instant | partial | never | reject）既定: instant
- LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）
- OPENAI_API_KEY: OpenAI API キー（ai/news_nlp, ai/regime_detector で使用）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）。既定: 60
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（0/1）

注意:
- run_monitoring は KABUSYS_ENV にかかわらず監視用に設定された sqlite_path（デフォルト `data/monitoring.db`）を使用します。
- run_execution は `KABUSYS_ENV=paper_trading` の場合、paper 用 DB（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離します。

---

## 使い方（コマンド／起動例）

基本的に各スクリプトはパッケージモードで実行します。

- 設定ウィザード（.env 作成）:
```bash
python -m kabusys.config_setup
```

- 設定検証:
```bash
python -m kabusys.validate_config
python -m kabusys.validate_config --strict
```

- 実行エンジン起動（ExecutionEngine）:
```bash
python -m kabusys.run_execution
```
- 実行時の挙動:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して paper DB (`data/paper_trading.db` など) に記録します。
  - 起動中に `data/stop_requested.flag` が存在すると起動を抑止 or 停止します（実装に依存）。
  - 実行中は `data/execution.pid` が使われます。

- 監視（Monitoring）起動:
```bash
python -m kabusys.run_monitoring
```
- オプション:
  - ポーリング間隔を変更するには環境変数 `MONITOR_POLL_INTERVAL` を設定します（秒、1以上）。
  - 監視ループは `data/stop_requested.flag` を検知すると終了します。

- Paper Trading 検証レポート:
```bash
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# デフォルト DB パスは環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db
```

- AI 関連（プログラム呼び出し）:
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
  これらは DuckDB の接続オブジェクト（kabusys のコネクション）を渡して呼び出します。API キーは OPENAI_API_KEY または引数経由で指定してください。

---

## 停止・Kill Switch の仕組み

- KillSwitch は `data/kill.flag` を書き込むことで ExecutionEngine に「停止せよ」というシグナルを送ります。
- run_execution / run_monitoring は `data/stop_requested.flag` の存在を確認して安全に終了する仕組みがあります。
- 本番で `KABUSYS_ENV=live` を使用する場合は `KILL_FLAG_CLEAR_ON_START` の設定に注意してください（自動クリアを有効にすると危険です）。

---

## ログ

- 共通ユーティリティ `kabusys.utils.logging_setup.setup_logging` により、
  - コンソール出力（stdout）
  - 日次ローテーションファイル（logs/<app_name>.log）
  がルートロガーに設定されます。
- LOG_DIR 環境変数でログディレクトリを指定可能（デフォルト: logs/）。

---

## ディレクトリ構成

以下はリポジトリの主要な（src 以下）構成例です:

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数読み込み / Settings クラス
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py (存在する場合)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (存在する場合)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py

補足:
- data/ ディレクトリ（DB・フラグファイル）や logs/ は実行時に自動生成されます（権限が必要）。
- DuckDB / SQLite のスキーマはモジュール内部で初期化やマイグレーションが行われます（例: monitoring_db.init_monitoring_db）。

---

## 開発・拡張のヒント

- DuckDB 接続を渡す設計のため、ローカルでの分析・ユニットテストが容易です。
- AI 周り（news_nlp / regime_detector）は OpenAI API のエラーハンドリングやリトライ処理を備えています。単体テストでは API 呼び出し部分をモックしてください（モジュール内に _call_openai_api を分離しています）。
- 設定ファイル（config/*.yaml）や環境変数のチェックは `validate_config.py` で行えます。CI に組み込むと安全です。

---

## よく使うコマンドまとめ

- 環境作成・依存インストール
  - python -m venv .venv; source .venv/bin/activate; pip install duckdb psutil openai pyyaml
- .env 作成
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン起動
  - python -m kabusys.run_execution
- 監視起動
  - python -m kabusys.run_monitoring
- Paper 検証レポート
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD

---

必要であれば、この README に実行例、環境変数テンプレート（.env.example）、あるいは Docker / systemd ユニットファイルの例を追加できます。どの追加が欲しいか教えてください。