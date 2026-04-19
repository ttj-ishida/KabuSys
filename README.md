# KabuSys

日本株向け自動売買システムのコアライブラリ群。本リポジトリはトレード実行エンジン、監視機構、ポートフォリオ構築ロジック、リサーチ（ファクター計算）やニュースNLP連携などを含みます。

---

## プロジェクト概要

KabuSys は以下の主要機能を備えたモジュール構成の Python パッケージです。

- 発注エンジン（ExecutionEngine）：ブローカークライアントを利用して発注を行う（実運用 / ペーパートレード対応）
- 監視（Monitoring）：システム稼働状況、注文ログ、リスク（ドローダウン・ポジション上限）を定期監視し、必要に応じて Kill Switch を発動
- ポートフォリオ構築：候補選定、重み付け、ポジションサイズ算出、セクター制限、レジーム調整等の純粋関数群
- リサーチ：DuckDB 上の株価/財務データを用いたファクター計算・特徴量探索
- AI（OpenAI）連携：ニュース記事のセンチメントを LLM で評価しスコア化、マーケットレジーム判定など
- 運用ツール：設定ウィザード（.env 生成）、設定検証 CLI、Paper Trading 検証レポート出力

設計方針の一部：
- 設定は .env / 環境変数ベース。Settings クラス経由で参照。
- 本番とペーパートレードのデータは分離（paper_trading 用 DB を用意）。
- DuckDB を分析用 DB として利用。SQLite は監視・注文ログ用。
- LLM 呼び出しはフェイルセーフ（リトライ・失敗時はフォールバック）を採用。

---

## 主な機能一覧

- run_execution.py
  - ExecutionEngine 起動スクリプト
  - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、data/paper_trading.db に記録
  - PID ファイル管理、stop フラグ監視対応
- run_monitoring.py
  - SystemMonitor のポーリングループ起動（デフォルト 60s、環境変数で上書き可）
  - 監視ログは常に本番用 sqlite_path に記録（環境に依らず）
- config_setup.py
  - 対話式ウィザードで .env を生成・更新
- validate_config.py
  - .env や config/*.yaml 等の設定検証 CLI（--strict オプションあり）
- tools/paper_verification_report.py
  - ペーパートレード DB を集計して PASS/FAIL レポートを標準出力へ生成
- ai/news_nlp.py, ai/regime_detector.py
  - OpenAI API を用いたニュースセンチメント評価、マーケットレジーム判定
- portfolio/*
  - 候補選定 / 重み計算 / ポジションサイズ決定 / セクター制約 / レジーム乗数など
- research/*
  - ファクター計算（Momentum/Volatility/Value 等）・将来リターン・IC 計算

---

## 前提条件（推奨）

- Python 3.10+
- パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML 検証を行う場合）
- 仮想環境（venv / virtualenv / poetry 等）の利用を推奨

requirements.txt はリポジトリに含めていない場合があるため、適宜上記パッケージをインストールしてください。

例：
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順

1. リポジトリをクローン / チェックアウト
2. 仮想環境を作成して依存をインストール（上記参照）
3. データ・ログディレクトリを作成（自動作成される箇所もありますが事前に用意すると安全）
   - data/
   - logs/
4. .env を作成
   - 対話式ウィザードを使用する例：
     ```
     python -m kabusys.config_setup
     ```
   - または手動で `.env` を作成（.env.example を参考に）

5. 設定検証
   ```
   python -m kabusys.validate_config
   # 警告を FAIL とする厳密モード:
   python -m kabusys.validate_config --strict
   ```

---

## 重要な環境変数 / デフォルト値

（主なもの。必要に応じて .env に設定してください）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト: development）
- DUCKDB_PATH: 分析 DB（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: "INFO"（デフォルト）
- LOG_DIR: ログ保存ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY: OpenAI 呼び出しに必要（AI モジュール使用時）
- PAPER_FILL_MODE: ペーパートレードの約定挙動 ("instant" | "partial" | "never" | "reject")
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（"0" or "1"、本番では 0 推奨）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

---

## 使い方（起動・運用）

基本的にモジュールを直接実行します。以下は代表的なコマンド例です。

- 設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- ExecutionEngine 起動（発注エンジン）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録します。
  - 起動時に data/stop_requested.flag が存在すると起動をスキップします。
  - 実行中は PID ファイル（data/execution.pid デフォルト）を作成します。

- Monitoring 起動（ポーリング監視）
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒、デフォルト 60）。
  - 監視は常に本番 sqlite_path（SQLITE_PATH）を使用して記録します。
  - 停止は data/stop_requested.flag を作る／削除による制御や Ctrl-C で可能。

- Paper Trading 検証レポート（レポート出力）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 機能の呼び出し（コードから）
  - 例：ニューススコアリングを呼ぶ
    ```python
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    # target_date は datetime.date オブジェクト（ルックアヘッドを避けるため外部から渡す）
    written = score_news(conn, target_date, api_key="sk-XXXXX")
    ```

---

## 停止・Kill Switch

- kill.flag（デフォルト: data/kill.flag）
  - KillSwitch がトリガー条件に合致した際に書き込まれます（ExecutionEngine の停止要求）。
  - ExecutionEngine は起動時に kill.flag を検出してクリアするかどうかのオプション（KILL_FLAG_CLEAR_ON_START）があります。※本番では自動クリアは推奨されません。

- stop_requested.flag（data/stop_requested.flag）
  - run_monitoring / run_execution のループ停止に使われるフラグファイル（存在を検知すると終了処理を行う）。

管理上は systemd / Supervisor / Docker 等でプロセスを管理し、flag ファイルはメンテ用のソフト停止トリガーとして使用する想定です。

---

## ログ

- ログは kabusys.utils.logging_setup.setup_logging により一元設定されます。
- コンソール(stdout) とファイル（logs/<app_name>.log）へ日次ローテーションで出力（30 日分保持）。
- LOG_DIR 環境変数や setup_logging の引数で保存先を変更可能。

---

## ディレクトリ構成（抜粋）

プロジェクト主要ファイルの例（src/kabusys 以下）：

- src/
  - kabusys/
    - __init__.py
    - config.py                   # 環境変数/Settings 管理、自動 .env ロード
    - config_setup.py             # .env 対話式ウィザード
    - validate_config.py          # 設定検証 CLI
    - run_execution.py            # ExecutionEngine 起動スクリプト
    - run_monitoring.py           # SystemMonitor ポーリング起動スクリプト
    - tools/
      - paper_verification_report.py
      - __init__.py
    - ai/
      - news_nlp.py
      - regime_detector.py
      - __init__.py
    - monitoring/
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - risk_monitor.py
      - trade_monitor.py          # 注文件数や約定監視（参照あり）
      - kill_switch.py
      - alert_manager.py          # アラート送信ロジック（LINE 等）
    - execution/
      - execution_engine.py
      - broker_factory.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
      - その他実行関連モジュール...
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
    - data/                        # 実行時に使用する DB / フラグ / PID 等（リポジトリ外で作成）
    - logs/                        # ログ出力先（デフォルト）

※上記はソース内参照に基づく抜粋です。実際のファイル数やパスはリポジトリのツリーを確認してください。

---

## 開発時の注意点 / 運用上の安全ガイド

- 本番運用時（KABUSYS_ENV=live）は設定（LINE トークンや KILL フラグのクリア挙動など）を慎重に確認してください。
- OpenAI API キー等のシークレットは .env に保存し、決して Git 等へコミットしないでください。
- run_execution の実行は実資金を動かす可能性があるため、まずは KABUSYS_ENV=paper_trading で十分に検証してください。
- monitoring は必ず本番用 monitoring DB（SQLITE_PATH）にログを残す仕様です。監視データは運用上重要です。

---

README はこのプロジェクトの概略と運用に必要な手順をまとめたものです。その他モジュールの API（例: portfolio.calc_position_sizes、research.calc_momentum、ai.score_news など）はソースの docstring に詳細が記載されています。必要に応じて該当モジュールのドキュメントを参照してください。