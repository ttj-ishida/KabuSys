# KabuSys — README (日本語)

このリポジトリは日本株自動売買システム KabuSys の主要モジュールを含みます。  
本 README はリポジトリ内のスクリプトとモジュール（実行エンジン、監視、ポートフォリオ構築、リサーチ、AI補助処理、ユーティリティ等）の概要、セットアップ、使い方、ディレクトリ構成を日本語でまとめたものです。

注意: 実際に発注を伴う運用を行う場合は、設定（.env 等）を慎重に確認し、本番（KABUSYS_ENV=live）での運用手順・ガードを必ず整えてください。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを構成するライブラリ群と起動スクリプトを提供します。設計方針は安全性・可観測性・テスト容易性を重視しており、以下の主要コンポーネントを含みます：

- ExecutionEngine（発注エンジン） — ブローカークライアント経由で発注を管理。paper_trading 環境ではモックブローカーを使用。
- Monitoring（監視） — システム状態、注文ログ、リスク（ドローダウン・ポジション）を定期チェックしアラート／Kill Switch を評価。
- Portfolio（ポートフォリオ構築） — 候補選定、重み付け、ポジションサイズ算出、リスク調整。
- Research（リサーチ） — DuckDB に格納された時系列データからファクター計算、特徴量探索。
- AI 補助（news_nlp / regime_detector） — OpenAI を用いたニュースセンチメント評価や市場レジーム判定（OpenAI API キーが必要）。
- ユーティリティ（ログセットアップ、プロセス優先度設定、設定ロード等）。

---

## 機能一覧

- 実行エンジン起動スクリプト: `run_execution.py`
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使い、paper_trading 用 DB (`data/paper_trading.db` デフォルト) に記録する。
  - PID ファイル管理、停止フラグの検出、スレッドでのセッション実行。
- 監視ループ起動スクリプト: `run_monitoring.py`
  - SystemMonitor を定期的に実行。MONITOR_POLL_INTERVAL でポーリング間隔変更可（デフォルト 60 秒）。
  - 監視は実環境の sqlite_path（監視 DB）を使用。
- 設定ウィザード: `config_setup.py`
  - インタラクティブに `.env` を作成／更新する補助 CLI。
- 設定検証: `validate_config.py`
  - .env と `config/*.yaml` の存在・基本妥当性をチェック（--strict オプションあり）。
- Paper Trading 検証レポート: `tools/paper_verification_report.py`
  - Paper Trading の監視／注文ログを解析し、稼働率・成功率・レイテンシ等のレポートを出力。
- ポートフォリオ構築関数群:
  - 候補選定、スコア重み・等重み、ポジションサイズ算出、セクター制限、レジーム倍率等。
- AI 関連:
  - `ai.news_nlp.score_news`：raw_news を LLM に投げて銘柄ごとのスコアを ai_scores に書き込み。
  - `ai.regime_detector.score_regime`：ETF 200日MA とマクロニュースを合成して market_regime に書き込む。
- モニタリング DB 層:
  - `monitoring_db.py` が SQLite テーブルの初期化と CRUD を提供。
- ユーティリティ:
  - ロギングセットアップ（コンソール + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定ユーティリティ

---

## セットアップ手順（ローカル / 開発向け）

1. Python 環境を用意
   - 推奨: Python 3.9+（コードは型アノテーションを使用）
   - 仮想環境を作成・有効化（venv / pyenv など）

2. 依存パッケージをインストール
   - 必要な主なパッケージ（例）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config の検証を行う場合。任意）
   - 例:
     ```
     pip install duckdb psutil openai PyYAML
     ```
   - プロジェクトに requirements.txt があればそれを使用してください（本コード断片には含まれていません）。

3. 環境変数（.env）を作成
   - リポジトリルートで以下を実行して対話ウィザードを起動：
     ```
     python -m kabusys.config_setup
     ```
   - あるいは `.env` を直接作成。主に必要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development / paper_trading / live） — デフォルト: development
     - DUCKDB_PATH（例: data/kabusys.duckdb）
     - SQLITE_PATH（監視DB、例: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、例: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LOG_LEVEL（DEBUG/INFO/...）
     - 他（LINE 通知用など任意）

4. 設定検証
   ```
   python -m kabusys.validate_config
   ```
   - `--strict` を付けると警告も失敗扱いになります。

5. データディレクトリの準備（必要に応じて）
   - デフォルトでは `data/`、`logs/` に DB・ログ・フラグファイル等が置かれます。適宜作成・パーミッション確認してください（`logging_setup` は `logs/` を自動作成しますが権限に注意）。

---

## 主要な環境変数（抜粋・デフォルト）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト: development
- DUCKDB_PATH: DuckDB ファイルパス。デフォルト: data/kabusys.duckdb
- SQLITE_PATH: 監視用 SQLite パス。デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（分離）。デフォルト: data/paper_trading.db
- LOG_LEVEL: ログレベル（INFO）
- LOG_DIR: ログ出力先ディレクトリ（default: logs/）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）。`run_monitoring.py` の場合、デフォルト 60
- PAPER_FILL_MODE: ペーパートレードの約定振る舞い（instant / partial / never / reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）
- PID_FILE_PATH / KILL_FLAG_PATH: 実行スクリプトが参照・書き込みするパス（デフォルト: data/execution.pid, data/kill.flag）

---

## 実行方法（代表例）

- ExecutionEngine（発注エンジン）を起動
  - 通常起動:
    ```
    python -m kabusys.run_execution
    ```
  - paper_trading で起動（env を指定する例）:
    ```
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```
  - 起動前に `data/stop_requested.flag` が存在すると起動をスキップします（停止フラグによる制御）。

- Monitoring（監視ループ）を起動
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を変える:
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - 監視ループは `data/stop_requested.flag` の存在を検出すると終了します。

- 設定ウィザード（.env の作成／更新）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB を指定:
    ```
    python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
    ```

- AI 機能（コードから呼び出す）
  - ニューススコアリング:
    - 関数: `kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)`
    - 引数: DuckDB 接続、対象日、API キー（省略時は OPENAI_API_KEY 環境変数を使用）
  - レジーム判定:
    - 関数: `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)`

---

## Kill / Stop フラグについて（運用メモ）

- stop_requested.flag
  - `run_monitoring.py` / `run_execution.py` はプロジェクトルート直下の `data/stop_requested.flag`（パスはスクリプト実装に依存）を監視し、存在を検出するとループを終了します。外部から安全にプロセスを停止させたい場合に使用します。

- kill.flag
  - `KillSwitch`（監視側）により条件（ドローダウン超過やポジション上限超過）を満たすと `data/kill.flag` を書き込み、ExecutionEngine 側で検出して停止させる運用を想定しています。
  - `KILL_FLAG_CLEAR_ON_START=1` により起動時に自動でクリアする設定もありますが、本番では危険なので推奨されません。

- PID ファイル
  - Execution 側は `data/execution.pid` に PID を書く実装になっています（Settings.pid_file_path を参照）。外部からの停止監視や管理に使用できます。

---

## ロギング

- ログは StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）をルートロガーにセットします（`kabusys.utils.logging_setup.setup_logging`）。
- デフォルトログディレクトリ: `logs/`。`LOG_DIR` 環境変数または `setup_logging` の引数で変更可能。
- ログファイル名は起動時に渡す app_name（例: `execution` → `logs/execution.log`）に基づきます。

---

## 注意点 / 運用上の留意事項

- paper_trading モードは本番 DB と完全分離されるよう `PAPER_TRADING_SQLITE_PATH` を利用します。テスト・検証時は必ず paper_trading 用 DB を用いてください。
- AI 機能（OpenAI）を使うには有効な API キーが必要です。API レート制限やエラーはリトライロジックが組み込まれているものの、運用時はコストとフェイルセーフを考慮してください。
- 設定ファイル（.env）は絶対にバージョン管理にコミットしないでください（`config_setup` のヘッダにも注意書きあり）。
- 本番（KABUSYS_ENV=live）では LINE 通知等の設定を確認し、`validate_config.py` を用いてガードチェックを行ってください。

---

## ディレクトリ構成（抜粋）

以下は主要ファイル・モジュールのツリー（src/kabusys 配下を中心に抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / Settings
    - config_setup.py          — .env ウィザード
    - validate_config.py       — 設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — Monitoring 起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py  — Paper Trading レポート
    - execution/               — 発注関連（Engine, BrokerFactory, OrderManager 等）
      - (複数のモジュールが想定)
    - monitoring/
      - monitoring_db.py       — SQLite 監視 DB 層
      - monitoring_engine.py   — 監視ループ束ね
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - ai/
      - news_nlp.py            — ニュース NLP スコアリング
      - regime_detector.py     — 市場レジーム判定
      - __init__.py
    - utils/
      - logging_setup.py
      - process_priority.py
      - __init__.py

プロジェクトルートには想定される補助ディレクトリ：
- config/ (system_config.yaml 等)
- data/   (DBファイル・フラグファイル・pid等)
- logs/   (ログファイル)

---

## 開発・デバッグ向けメモ

- `validate_config.py` は PyYAML 未インストール時に YAML 内容の検証をスキップします（警告）。YAML チェックを行う場合は PyYAML を入れておくと安全です。
- プロセス優先度設定（`utils.process_priority.set_process_priority`）はプラットフォーム依存であり、権限や OS によって設定できない場合があります。失敗時は警告でスキップされます。
- DuckDB を使ったリサーチコードは外部 API を呼ばず、ローカル DB（prices_daily / raw_financials 等）を前提にしています。テスト用に小規模の DuckDB を用意して関数を単体テストできます。
- LLM レスポンスのバリデーションは慎重に行われていますが、LLM の出力は不安定になり得るためログやバリデーションルールを確認してください。

---

必要に応じて README に追記します。特定のスクリプトやモジュールの詳細なドキュメント（例えば ExecutionEngine の設定パラメータや OrderManager の振る舞い等）が必要であれば、対象モジュール名を指定してリクエストしてください。