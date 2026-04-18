# KabuSys

日本株自動売買システムの一部コードベース。ポートフォリオ構築、発注エンジン（ExecutionEngine）、監視（Monitoring）、リサーチ（DuckDB を使ったファクター計算）、AI ベースのニュース・レジーム判定などのユーティリティ群を含みます。

バージョン: 0.1.0

## 概要

KabuSys は日本株の自動売買に関連する以下の機能を提供するモジュール群です。

- 発注実行エンジン（ExecutionEngine）とブローカー抽象化（本番/ペーパートレード対応）
- システム監視（CPU/メモリ/ディスク、プロセス監視、データ鮮度検証）とリスク監視（ドローダウン、ポジション上限）
- Kill Switch（条件成立時に flag ファイルを書き ExecutionEngine を停止）
- ポートフォリオ構築ロジック（候補選定、重み付け、ポジションサイズ計算、セクター制限）
- リサーチ（DuckDB を使ったファクター計算・特徴量解析）
- AI モジュール（OpenAI を使ったニュースセンチメント / レジーム判定）
- ツール（ペーパートレード検証レポート生成など）
- 設定ウィザードと設定検証 CLI、ログ設定ユーティリティ、プロセス優先度ユーティリティ等

このリポジトリはライブラリ／バッチ処理群として設計されており、実行スクリプトを通じて運用します。

## 主な機能一覧

- Execution:
  - ExecutionEngine（ライブ/ペーパー両対応）
  - BrokerClientFactory によるブローカークライアントの選択（KABUSYS_ENV に依存）
  - OrderManager / OrderRepository / Reconciler / RiskManager（ロジックは Execution 内）
- Monitoring:
  - SystemMonitor（リソース・データ鮮度・プロセス監視）
  - TradeMonitor（発注ログ検査）
  - RiskMonitor（ドローダウン・ポジション上限検出）
  - KillSwitch（条件に応じて data/kill.flag を書き Execution を止める）
  - MonitoringEngine（各 Monitor を統合してポーリング）
- Portfolio:
  - 候補選定、等比重／スコア重み、リスクベースのポジション決定、セクター上限適用などの純粋関数
- Research:
  - DuckDB を用いたファクター計算（モメンタム／ボラティリティ／バリュー等）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリツール
- AI:
  - news_nlp: OpenAI を用いたニュースセンチメント → ai_scores テーブルへの格納
  - regime_detector: ETF の MA200 とマクロニュースの LLM スコアを合成して market_regime に格納
- Utilities:
  - 設定ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
  - ロギング設定（kabusys.utils.logging_setup）
  - プロセス優先度 / CPU affinity 設定（kabusys.utils.process_priority）
- Tools:
  - paper_verification_report: ペーパートレード DB から検証レポートを生成

## 前提 / 推奨環境

- Python 3.10 以上（型ヒントや構文から推奨）
- SQLite（標準ライブラリで利用）
- DuckDB（pip install duckdb）
- psutil（プロセス/リソース監視）
- openai（AI モジュール利用時）
- PyYAML（設定検証で YAML 検証を行う場合）

推奨パッケージ（例）:
pip install duckdb psutil openai PyYAML

（プロジェクトに requirements.txt があればそれを利用してください）

## セットアップ手順

1. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール（例）
   - pip install duckdb psutil openai PyYAML

3. プロジェクトの初期設定
   - 対話式で .env を作る:
     - python -m kabusys.config_setup
     - このウィザードは .env を生成・更新します。生成後、必須環境変数（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD など）を設定してください。
   - 自動読み込みを無効化したい場合:
     - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動読み込みがスキップされます。

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります:
     - python -m kabusys.validate_config --strict

5. データディレクトリ
   - デフォルトでは data/ に DB やフラグファイルを置きます。必要に応じて .env の DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH を変更してください。
   - ログはデフォルト logs/ に出力されます（kabusys.utils.logging_setup が自動作成）。

## 環境変数（主なもの）

重要な環境変数とデフォルト値（.env で設定）:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト: development）
  - paper_trading: Execution は MockBrokerClient を使用し、ペーパートレード専用 DB（PAPER_TRADING_SQLITE_PATH）を使用します
  - monitoring は KABUSYS_ENV に関係なく本番 sqlite_path（SQLITE_PATH）を使用する設計の箇所があります（run_monitoring）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: INFO（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: logs/
- OPENAI_API_KEY: OpenAI を使う機能（news_nlp / regime_detector）で必要
- PAPER_FILL_MODE: ペーパートレードでの約定モード（instant|partial|never|reject、デフォルト: instant）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（本番では 0 推奨）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動ロードを無効化

Settings クラス（kabusys.config.Settings）で細かいデフォルトやバリデーションを行っています。足りない値は _require() により起動時に例外が出ます。

## 使い方（主なエントリポイント）

- 設定の対話式作成
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視ループの起動（常駐監視）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60）
  - run_monitoring は監視用の sqlite_path（Settings.sqlite_path）を常に使用します（KABUSYS_ENV に依存しない）

- 実行エンジン（ExecutionEngine）の起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合はペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH）を使用し MockBrokerClient を使います
  - 停止フラグは data/stop_requested.flag（プロジェクトルート/data/stop_requested.flag）で検出されます
  - Execution は実行中、PID ファイル（data/execution.pid など）を出力します

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI モジュール（プログラムから呼び出し）
  - news_nlp.score_news(conn, target_date, api_key=None)
    - conn: duckdb connection (duckdb.connect(...))
    - target_date: datetime.date
    - api_key: OpenAI API キー（未指定で環境変数 OPENAI_API_KEY を利用）
  - regime_detector.score_regime(conn, target_date, api_key=None)
    - 同上

例（DuckDB コネクションを使ってニューススコアを生成）:
```py
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n = score_news(conn, date(2026, 4, 10), api_key="sk-...")
print("scored:", n)
```

注意:
- OpenAI 呼び出しはネットワーク、API レート制限、JSON パース等で失敗することがあります。モジュールは多くの失敗ケースをフェイルセーフ（スコア 0 やスキップ）で扱う設計になっています。
- Monitoring / Execution の各スクリプトは setup_logging() を最初に呼び、ログは stdout とファイルに出力されます。

## 停止 / フラグファイル

- ExecutionEngine の停止はフラグファイル（data/stop_requested.flag）で検出します（run_execution と run_monitoring の両方で利用）
- Kill Switch（KillSwitch）は data/kill.flag を書き込んで強制停止を指示します（Monitoring が検出・書き込み）
- Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動的に kill.flag をクリアします（本番では 0 を推奨）

## ロギング

- ログはデフォルトで stdout と logs/<app_name>.log（日次ローテーション、30日保存）に出力されます
- setup_logging(app_name="execution" | "monitoring" | ...) を各スクリプトで呼び出して統一的に管理します
- LOG_DIR 環境変数や引数でログディレクトリを変更可能

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                 — Settings / .env 自動ロードロジック
  - config_setup.py           — .env 初期作成ウィザード（対話式）
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート生成
  - ai/
    - news_nlp.py              — ニュース NLP / OpenAI 呼び出し
    - regime_detector.py       — 市場レジーム判定（MA200 + マクロニュース）
  - monitoring/
    - monitoring_db.py         — SQLite テーブル初期化 / 永続化ヘルパ
    - system_monitor.py        — CPU/MEM/DISK/プロセス/データ鮮度監視
    - trade_monitor.py         — trade_logs を監視（ファイルにある）
    - risk_monitor.py          — ドローダウン・ポジション上限監視
    - kill_switch.py           — kill.flag 書き込みロジック
    - monitoring_engine.py     — 各 Monitor を束ねる
    - alert_manager.py         — （アラート送信管理、LINE等）※実装ファイルがある場合
  - execution/
    - (ExecutionEngine, OrderManager, BrokerFactory などの実装ファイル群)
  - portfolio/
    - portfolio_builder.py     — 候補選定 / weight 計算
    - position_sizing.py       — 発注株数計算
    - risk_adjustment.py       — セクター上限 / レジーム乗数
  - research/
    - factor_research.py       — ファクター計算（momentum/value/volatility）
    - feature_exploration.py   — 将来リターン / IC / summary
  - utils/
    - logging_setup.py         — ログ初期化ユーティリティ
    - process_priority.py      — プロセス優先度 / CPU affinity
  - data/                      —（実行時に使用される DB / pid / flag ファイル）（既定）
  - logs/                      —（ログ出力先：setup_logging による）

（上記は本リポジトリに含まれる主要ファイル群の要約です。実装の詳細は各モジュール内の docstring を参照してください。）

## 開発メモ / 注意事項

- .env は機密情報を含むため Git にコミットしないでください（config_setup.py にも注意書きあり）。
- validate_config は起動前チェックに有用です。production では --strict モードでのチェックを推奨します。
- run_monitoring は「監視専用」DB（SQLITE_PATH）を使用するため、監視ログは本番 DB に記録されます（意図的な仕様）。
- AI 機能を利用するには OpenAI API キーの設定が必要です（OPENAI_API_KEY）。
- psutil の一部 API（プロセス優先度、CPU affinity）は実行権限や OS により失敗する可能性があります。失敗時は警告ログを出してスキップします。

---

README に書かれているコマンドや環境変数を参考にして最初のセットアップ（.env 作成 → validate → DB パス確認 → 実行）を行ってください。追加で知りたい情報（各モジュールの詳細な API 使用例、ExecutionEngine の起動オプション、Broker の実装概要など）があれば教えてください。必要に応じて README を拡張します。