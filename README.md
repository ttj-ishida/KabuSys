# KabuSys

日本株向け自動売買システムの一部（ライブラリ＆起動スクリプト群）。

本リポジトリは取引エンジン、監視、ポートフォリオ構築、ファクター計算、AIベースのニュース評価などを含むモジュール群を提供します。実運用・ペーパートレードの両方に対応する設計になっています。

---

## プロジェクト概要

- Python で実装された自動売買フレームワークのコアコンポーネント群。
- DuckDB / SQLite での時系列・監視データ保存を想定。
- OpenAI を用いたニュース NLP（センチメント評価）や市場レジーム判定をサポート。
- 設定は .env または環境変数で管理。`config_setup` で対話的に .env を生成可能。
- 監視（Monitoring）と実行（Execution）は別プロセスとして起動し、フラグファイルで安全に停止を通知可能。

---

## 主な機能一覧

- ExecutionEngine 起動スクリプト（実運用・ペーパートレード切替）
  - `run_execution.py`：本番／ペーパートレードの分離（ペーパートレードは専用 DB を使用）
  - プロセス優先度設定（High）
  - PID ファイル管理、停止フラグ監視

- Monitoring（監視）
  - `run_monitoring.py`：SystemMonitor のポーリングループ起動
  - システムリソース（CPU/MEM/DISK）監視、データ鮮度チェック、プロセス生存監視
  - RiskMonitor：ドローダウン・ポジション数監視、リスクイベント記録
  - KillSwitch：条件に応じて `data/kill.flag` を作成して ExecutionEngine に停止命令
  - Monitoring DB（SQLite）操作ユーティリティ（`monitoring_db.py`）

- ポートフォリオ構築（純粋関数）
  - 候補選定、等重・スコア重み計算、ポジションサイズ算出、セクター制限、レジーム乗数

- 研究用モジュール
  - ファクター計算（モメンタム、バリュー、ボラティリティ）
  - 特徴量探索（将来リターン計算、IC 計算、統計サマリー）

- AI モジュール
  - ニュースを LLM（OpenAI）で評価して `ai_scores` に書き込む（`ai.news_nlp`）
  - 市場レジーム判定（ETF + マクロニュースを組み合わせる `ai.regime_detector`）

- ユーティリティ
  - .env 対話式ウィザード（`config_setup.py`）
  - 設定検証 CLI（`validate_config.py`）
  - Paper Trading 検証レポート生成ツール（`tools/paper_verification_report.py`）
  - ログ設定、プロセス優先度設定ユーティリティなど

---

## 前提（依存関係）

- Python 3.9+
- 必要パッケージ（例）
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（設定 YAML のパース検証を行う場合）
- 実行環境に応じて .env に環境変数を設定

---

## 設定（環境変数）

必須（最低限）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要な環境変数（抜粋とデフォルト）:
- KABUSYS_ENV: 実行環境（development / paper_trading / live） — デフォルト `development`
- DUCKDB_PATH: DuckDB ファイルパス — デフォルト `data/kabusys.duckdb`
- SQLITE_PATH: 監視 DB（production 用） — デフォルト `data/monitoring.db`
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（paper_trading 環境時） — デフォルト `data/paper_trading.db`
- LOG_LEVEL: ログレベル（DEBUG/INFO/...） — デフォルト `INFO`
- OPENAI_API_KEY: OpenAI を使う場合に必要
- PAPER_FILL_MODE: ペーパートレードの約定動作（instant|partial|never|reject） — デフォルト `instant`
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒） — デフォルト `60`（run_monitoring で使用）
- KILL_FLAG_PATH: Kill Switch 用 flag のパス — デフォルト `data/kill.flag`
- PID_FILE_PATH: ExecutionEngine の PID ファイル — デフォルト `data/execution.pid`

自動 .env ロード:
- プロジェクトルートにある `.env`（優先度: OS 環境 > .env.local > .env）を自動で読み込みます。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

---

## セットアップ手順（ローカル開発想定）

1. リポジトリをクローンして Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install -r requirements.txt
   （requirements.txt がない場合は最低限 duckdb, psutil, openai, PyYAML などを入れる）

3. .env の作成
   - 対話式で作成:
     - python -m kabusys.config_setup
   - または `.env.example` を参考に手動で `.env` を作成

4. 設定検証
   - python -m kabusys.validate_config
   - 警告も FAIL にしたい場合: python -m kabusys.validate_config --strict

5. 必要なディレクトリを作成（自動で作られることが多いが、権限等で失敗する可能性あり）
   - mkdir -p data logs

6. （AI 機能を使う場合）OPENAI_API_KEY を設定

---

## 使い方（主要コマンド）

- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を用い `data/paper_trading.db` に記録（本番 DB と完全分離）
    - 起動時に `data/stop_requested.flag` の存在を確認し、存在する場合は起動せず終了
    - スレッドでエンジンを起動し、同フラグで停止を検知する

- 監視ループ（Monitoring）起動
  - python -m kabusys.run_monitoring
  - オプション:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト 60 秒）
  - 注意:
    - Monitoring は KABUSYS_ENV にかかわらず常に本番 sqlite_path（Settings.sqlite_path）を使用します（監視の対象 DB は本番 DB 想定）
    - 監視停止はプロジェクトルート `data/stop_requested.flag` を作成することで実施（ファイル存在でループ終了）

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（`PAPER_TRADING_SQLITE_PATH` 環境変数を優先）

- AI / 研究用 API（ライブラリ呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 研究関数: kabusys.research.calc_momentum / calc_volatility / calc_value / calc_forward_returns など

---

## 停止 / Kill フロー

- 優雅な停止（監視・実行共通）
  - 監視ループ / 実行エンジンはプロジェクト内ファイル `data/stop_requested.flag` の有無を監視しています。停止したい場合はこのファイルを作成してください。
  - Execution 停止のための Kill Switch（重大リスク時に自動生成される）:
    - `data/kill.flag` が作成されると ExecutionEngine 側で停止判定を受け取る仕組みがあります。`KILL_FLAG_CLEAR_ON_START` が `1` の場合、起動時に自動でクリアされます（本番では 0 推奨）。

---

## ログ

- ルートロガーは `kabusys.utils.logging_setup.setup_logging()` で統一的に設定されます。
- デフォルト出力:
  - コンソール stdout
  - 日次ローテーションでファイル保存（デフォルトディレクトリ `logs/`、ファイル名 `<app_name>.log`）
  - ログの保持: 30 日分
- ログディレクトリは `LOG_DIR` 環境変数か引数 `log_dir` で変更可能。作成に失敗した場合はコンソール出力のみとなります。

---

## 注意点 / 運用メモ

- Monitoring は常に Settings.sqlite_path（本番の monitoring DB）を使用するため、監視対象と実行エンジンの DB の取り扱いに注意してください。
- ExecutionEngine は paper_trading 環境であれば paper_sqlite_path を使い、本番 DB とデータを分離します。
- process priority の設定（High）を行いますが、必ずしも権限があるとは限らないため失敗時は警告でスキップされます（psutil に依存）。
- OpenAI 関連の呼び出しは失敗時にフォールバック（スコア 0.0 等）するよう設計されていますが、API キーは必須です。
- .env は絶対にリポジトリにコミットしないでください（`config_setup` のヘッダにも明記）。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_execution.py
  - run_monitoring.py
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py (存在想定)
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py (存在想定)
  - execution/
    - execution_engine.py (存在想定)
    - broker_factory.py (存在想定)
    - order_manager.py (存在想定)
    - order_repository.py (存在想定)
    - reconciler.py (存在想定)
    - risk_manager.py (存在想定)
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/  (上記)
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py
  - data/  (実行時に使用されるデフォルトディレクトリ)
  - logs/  (デフォルトログ出力先)

注: 上記は主要なファイルを抜粋した構成です。実際のリポジトリではさらに細分化されたモジュールや補助スクリプトが存在します。

---

## よく使うコマンドまとめ

- .env 作成（対話式）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 監視起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 実行エンジン起動
  - python -m kabusys.run_execution
- Paper 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- AI スコア実行（ライブラリ呼び出し例）
  - Python スクリプト内で kabusys.ai.score_news(conn, target_date, api_key=os.environ["OPENAI_API_KEY"])

---

## 貢献・拡張メモ

- strategy / execution ロジックや broker client は抽象化されているため、実装を差し替えて利用できます。
- DuckDB のテーブルスキーマに合わせて研究モジュールを拡張してください（prices_daily / raw_financials / raw_news 等）。
- テスト化を行う際は Settings の自動 .env ロードを `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます。

---

質問や追記してほしい項目があれば教えてください。README を特定の運用手順（Systemd サービス化や Docker 化）に合わせて追記することも可能です。