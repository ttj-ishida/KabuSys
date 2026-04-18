# KabuSys

日本株自動売買システムの一部を実装した Python パッケージ（README 抜粋）。
このリポジトリには運用用の監視・実行スクリプト、ポートフォリオ構築・ポジションサイジング、
リサーチ（ファクター計算）、AI（ニュース NLP / レジーム判定）などのモジュールが含まれます。

以下はローカルでのセットアップ・起動に必要な概要・手順・使い方の説明です。

---

## プロジェクト概要

- 自動売買のコアロジックを含むライブラリ群（ポートフォリオ構築、ポジション計算、リスク調整 等）。
- 実行エンジン（ExecutionEngine）を起動するためのスクリプト（run_execution）。
- 運用監視用のポーリングプロセス（SystemMonitor / TradeMonitor / RiskMonitor 等）を起動するスクリプト（run_monitoring）。
- Paper Trading 用 DB と本番 DB を分離して運用可能（KABUSYS_ENV に依存）。
- ニュースの NLP スコアリングや市場レジーム判定に OpenAI API を利用する機能。
- 監視ログは SQLite、分析用には DuckDB を利用。

---

## 主な機能一覧

- Execution
  - 実際の発注ロジック（ExecutionEngine、OrderManager、RiskManager、Reconciler 等）
  - ブローカークライアントの切り替え（本番 / モック）
- Monitoring
  - システム状態監視（CPU/メモリ/ディスク、プロセス生存チェック、データ鮮度）
  - トレードログ監視（滞留注文、異常約定など）
  - リスク監視（ドローダウン、ポジション上限）
  - Kill Switch（条件に応じて data/kill.flag を書き込み ExecutionEngine を停止）
- Portfolio
  - 候補選定、等配分 / スコア配分の重み計算
  - ポジションサイズ計算（risk_based / equal / score）
  - セクターキャップ、レジーム乗数の適用
- Research
  - ファクター計算（Momentum / Value / Volatility / Liquidity）
  - 特徴量探索（将来リターン計算、IC 計算、統計サマリ）
- AI
  - ニュース NPL（OpenAI による銘柄別センチメントの取得）
  - 市場レジーム判定（ETF の MA とマクロニュースの合成）
- Tools
  - Paper Trading 検証レポート生成スクリプト（tools.paper_verification_report）
- 設定支援
  - 対話式 .env 作成ウィザード（config_setup）
  - 起動前設定検証 CLI（validate_config）

---

## 前提条件 / 依存ライブラリ

（実行環境に合わせて requirements.txt を用意していることを想定しますが、ここは主要要件のみ）

- Python 3.10+
- duckdb
- psutil
- openai
- PyYAML（config/*.yaml の検証を行う場合、任意）
- sqlite3（標準ライブラリ）

インストール例（仮）:
- 仮想環境作成・有効化
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
- 必須パッケージをインストール
  - pip install duckdb psutil openai PyYAML

---

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリへ移動。

2. Python 仮想環境の作成（推奨）と依存ライブラリのインストール。

3. .env ファイル作成
   - 対話式ウィザード（.env を生成／更新）:
     - python -m kabusys.config_setup
   - もしくは手動でプロジェクトルートに `.env` を作成し、以下必須値を設定:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - そのほか、KABUSYS_ENV（development / paper_trading / live）や各種パスを設定可能

4. 設定検証（起動前チェック）:
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合:
     - python -m kabusys.validate_config --strict

5. DB ファイルの準備
   - デフォルト:
     - DuckDB: data/kabusys.duckdb
     - Monitoring SQLite: data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading 時に使用）
   - 必要に応じて .env で DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH を上書き

6. OpenAI を使う機能を利用する場合:
   - 環境変数 OPENAI_API_KEY を設定（または関数呼び出し時に api_key を渡す）

補足:
- KILL_FLAG_CLEAR_ON_START=1 を設定すると ExecutionEngine 起動時に kill.flag を自動的に消す（本番では 0 推奨）
- run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH / data/monitoring.db）を使用します
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離します

---

## 環境変数（主なもの）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 運用・一般
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
  - LOG_DIR: ログ保存ディレクトリ（デフォルト: logs）
- DB パス
  - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB、デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト data/paper_trading.db）
- Execution / Monitoring
  - PID_FILE_PATH（デフォルト data/execution.pid）
  - KILL_FLAG_PATH（デフォルト data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START（"1" なら起動時に kill.flag を削除。デフォルト "0"）
  - MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔（秒）。デフォルト 60）
- OpenAI
  - OPENAI_API_KEY（news_nlp / regime_detector 用）
- Paper trading 振る舞い
  - PAPER_FILL_MODE（instant | partial | never | reject、デフォルト "instant"）

注:
- MONITOR_POLL_INTERVAL に 0 以下を与えるとデフォルト（60秒）にフォールバックします。

---

## 使い方（起動例）

プロジェクトルートで実行してください（.env の自動読み込みが有効）。

- 設定ウィザード（.env の作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード（警告も失敗）: python -m kabusys.validate_config --strict

- 監視プロセス起動（SystemMonitor のポーリングループ）
  - python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔を変更:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

  特記事項:
  - run_monitoring は data/stop_requested.flag が存在するとループを終了します。
  - run_monitoring は Settings.env にかかわらず本番 sqlite_path を使用して監視ログを記録します。

- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient が使用され、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録されます。
  - 実行中に data/stop_requested.flag を作成すると起動済みエンジンに停止シグナルを送ります（run_execution は flag を監視して停止処理を行います）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI / リサーチ機能の利用
  - kabusys.ai.score_news(conn, target_date, api_key=...)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)
  - これらは DuckDB 接続を受け取り、内部で DuckDB のテーブル（raw_news / prices_daily 等）を参照します。
  - OpenAI API を利用するため OPENAI_API_KEY が必要です。

---

## ログとデータ

- ログ: デフォルトは logs/<app_name>.log（TimedRotatingFileHandler、日次ローテーション、30世代保持）
  - app_name 例: execution / monitoring
  - 標準出力にもログを出力（stdout）

- SQLite（監視ログ）
  - デフォルト: data/monitoring.db
  - run_monitoring/run_execution は init_monitoring_db を呼び監視テーブルを自動作成（冪等）

- DuckDB（分析用）
  - デフォルト: data/kabusys.duckdb

- フラグファイル
  - data/stop_requested.flag : スクリプト（run_execution / run_monitoring）の外部停止要求に使われる（存在するとループを抜ける）
  - data/kill.flag : KillSwitch が検出時に作成（ExecutionEngine に対する停止シグナル）。KILL_FLAG_CLEAR_ON_START で起動時自動クリアを制御

- PID ファイル
  - data/execution.pid（ExecutionEngine 起動時に書き込まれる）

---

## 注意点 / 運用上のヒント

- 本番環境（KABUSYS_ENV=live）では .env の内容・LINE 通知設定などを十分に確認してください。validate_config は live 時にいくつかの注意を出します。
- KABUSYS_ENV=paper_trading を使えば本番 DB と完全分離してペーパートレードの検証ができます。
- run_monitoring は監視用途のため、常に本番の monitoring DB（SQLITE_PATH）を使用します。意図的に監視 DB を別にしたい場合は SQLITE_PATH を環境変数で差し替えてください。
- OpenAI 呼び出しは外部 API なのでレート制限や障害に注意。ニュース NLP / レジーム判定ではリトライ・フォールバックを実装済み（完全には失敗を防げないのでログ監視を推奨）。

---

## 主要なディレクトリ構成

以下はソースツリーの主要ファイル一覧（抜粋）。実際は src/kabusys 以下にモジュールが配置されています。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 自動ロード・Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py       — SQLite に対する永続層
    - system_monitor.py      — システム状態 / データ鮮度監視
    - trade_monitor.py       — （トレード監視ロジック）
    - risk_monitor.py        — ドローダウン・ポジション監視
    - kill_switch.py         — Kill Switch（kill.flag 制御）
    - monitoring_engine.py   — 各 Monitor を束ねる実行ループ
    - alert_manager.py       — （アラート通知機構）
  - execution/
    - execution_engine.py    — ExecutionEngine（発注セッション管理）
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）
    - regime_detector.py     — 市場レジーム判定（OpenAI + MA）
  - tools/
    - paper_verification_report.py

（上記は抜粋です。詳細はソースツリーを参照してください。）

---

## 開発・拡張のヒント

- DuckDB のテーブル（prices_daily, raw_financials, raw_news, news_symbols 等）はリサーチ・AI 機能で参照されます。分析データの準備/更新はパイプライン側の実装に依存します。
- テスト時は OpenAI 呼び出し関数をパッチしてモックレスポンスを返すようにしてください（モジュール内の _call_openai_api を unittest.mock.patch する設計になっています）。
- モジュールは可能な限り副作用を避け、DuckDB / sqlite の接続を引数で受け取る純粋関数設計を志向しています。ユニットテストが書きやすい構造です。

---

必要があれば README の英語版、systemd / supervisor 用のサービスファイル例、デプロイ手順（Dockerfile など）や requirements.txt のサンプルを追加で作成します。どの情報を優先して追加しますか？