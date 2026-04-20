# KabuSys

日本株自動売買システムのライブラリ / 起動スクリプト群（抜粋ドキュメント）

この README は提供されたコードベースに基づく簡易ドキュメントです。実運用前に必ず `python -m kabusys.validate_config` で設定検証を行ってください。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買／研究ツール群です。主な機能は以下の通りです。

- 注文実行エンジン（ExecutionEngine） — 実際の発注（およびペーパートレード用のモック）を行うコンポーネント
- 監視システム（Monitoring） — システム状態、注文の滞留、リスク（ドローダウン・ポジション数）などを定期チェックし、kill flag の発動やアラート発行を行う
- ポートフォリオ構築モジュール（選定・重み付け・株数算出）
- リサーチモジュール（ファクター計算、特徴量探索）
- AI モジュール（ニュースの NLP によるセンチメント評価、レジーム判定）
- 運用・運転補助スクリプト（.env ウィザード、設定検証、ペーパートレード検証レポート生成 等）

設計上の特徴：
- 設定は .env ファイル（または環境変数）から読み込み。自動ロードの挙動は `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
- Paper trading（ペーパートレード）は本番データベースと完全分離（既定: `data/paper_trading.db`）。
- OpenAI を用いる機能（ニュース NLP / レジーム判定）は API キー（`OPENAI_API_KEY`）が必要。

---

## 機能一覧（抜粋）

- 起動スクリプト
  - `run_execution.py` — ExecutionEngine を起動。`KABUSYS_ENV=paper_trading` の場合は MockBroker を使用して paper DB に書き込む。
  - `run_monitoring.py` — SystemMonitor のポーリングループを起動。`MONITOR_POLL_INTERVAL` で間隔を変更可能（デフォルト 60 秒）。
- 設定関連
  - `config_setup.py` — 対話式ウィザードで .env を作成/更新。
  - `validate_config.py` — .env と config/*.yaml の検証 CLI。
- ツール
  - `tools/paper_verification_report.py` — ペーパートレードの検証レポート生成（稼働率や約定率、レイテンシ等）。
- コアライブラリ
  - `portfolio` — 候補選定、重み付け、株数算出、セクター上限、レジーム乗数など。
  - `research` — ファクター計算（モメンタム/ボラティリティ/バリュー）、将来リターン、IC、統計サマリー。
  - `ai` — ニュースNLP（OpenAI）による銘柄別スコアリング、レジーム判定。
  - `monitoring` — DB 永続化（SQLite）、System/Trade/Risk モニタ、KillSwitch、MonitoringEngine。
  - `utils` — ロギング設定、プロセス優先度設定 等。

---

## セットアップ手順（開発/テスト向け）

※ 実際のリポジトリに `requirements.txt` 等があればそちらを優先してください。ここでは最低限必要な依存を例示します。

1. Python 仮想環境を作成・有効化
   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

2. 必要なライブラリをインストール（例）
   ```
   pip install duckdb psutil openai PyYAML
   ```
   - `openai` は AI 機能を使用する場合に必要。
   - `PyYAML` は `validate_config` が config YAML のパースチェックを行うときにあると便利（無くても動作するが検証はスキップされる）。

3. ディレクトリ作成
   ```
   mkdir -p data logs
   ```
   デフォルトで使用される DB / PID / フラグファイルは `data/` 配下に置かれます。

4. .env を用意
   - 対話式ウィザードを使用:
     ```
     python -m kabusys.config_setup
     ```
   - 手動の最小例（プロジェクトルート `.env`）:
     ```
     KABUSYS_ENV=development
     JQUANTS_REFRESH_TOKEN=your_token_here
     KABU_API_PASSWORD=your_password_here
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     LOG_LEVEL=INFO
     ```
   - 自動ロードを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

5. 設定検証（推奨）
   ```
   python -m kabusys.validate_config
   # strict モード: 警告もエラー扱い
   python -m kabusys.validate_config --strict
   ```

---

## 使い方（主要なコマンド）

- ExecutionEngine を起動（実行）
  ```
  python -m kabusys.run_execution
  ```
  - `KABUSYS_ENV=paper_trading` の場合は paper DB を使用（既定: `data/paper_trading.db`）。
  - 実行中に `data/stop_requested.flag` が作成されるとスレッドループにより停止します。
  - Execution の PID は `data/execution.pid` に書き込まれます（設定により変更可）。

- Monitoring を起動（監視ループ）
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を変更するには `MONITOR_POLL_INTERVAL` を設定（秒）。例: `MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring`
  - Monitoring は常に本番用の `sqlite_path` を用いて監視 DB にログを残します（環境に依らず）。
  - 停止フラグファイル `data/stop_requested.flag` によりループ終了。

- .env の対話式セットアップ
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- ペーパートレード検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パスはオプション `--db`、または環境変数 `PAPER_TRADING_SQLITE_PATH` で指定可。

- AI 関連（プログラム的に呼ぶ）
  - OpenAI API を使う機能を実行する場合は `OPENAI_API_KEY` を設定してください。例:
    ```
    export OPENAI_API_KEY=sk-...
    ```
  - ニュース NLP（銘柄スコア）: `kabusys.ai.news_nlp.score_news(...)`
  - レジーム判定: `kabusys.ai.regime_detector.score_regime(...)`

---

## 主要な環境変数

（抜粋、デフォルトはコード上の説明に従う）

- セキュリティ／API
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
  - OPENAI_API_KEY (AI 機能使用時必須)

- 環境・動作
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL

- ファイルパス
  - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH: Execution の PID ファイルパス（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH: Kill Switch のフラグパス（デフォルト: data/kill.flag）
  - LOG_DIR: ログ保存ディレクトリ（デフォルト: logs/）

- その他
  - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
  - PAPER_FILL_MODE: ペーパートレードの約定モード（instant | partial | never | reject）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（1 = クリアする、0 = しない、デフォルト 0）

---

## Kill Switch / 停止制御

- KillSwitch（`data/kill.flag`）: RiskMonitor 等の判定で `KillSwitch.evaluate()` がトリガーされた場合に書き込まれ、ExecutionEngine はこれを検知して安全停止する仕組みです。ファイルは冪等に書かれ、既に存在する場合は再書き込みされません。
- 手動停止フラグ（全プロセス共通）
  - `data/stop_requested.flag` を作成すると、`run_execution.py` / `run_monitoring.py` がループ内で検知して終了します。
  - 起動時に `KILL_FLAG_CLEAR_ON_START=1` を設定すると kill.flag を自動的にクリアします（本番では推奨されません）。

---

## ログ

- ロギングは `kabusys.utils.logging_setup.setup_logging()` を通じて初期化されます。
  - stdout 出力（StreamHandler）と日次ローテートファイル出力（`<LOG_DIR>/<app_name>.log`）を設定。
  - デフォルトログディレクトリは `logs/`。

---

## ディレクトリ構成（抜粋）

以下は `src/kabusys` 配下の主要ファイル / ディレクトリとその簡単な説明です。

- kabusys/
  - __init__.py — パッケージ初期化（バージョン等）
  - config.py — 環境変数 / 設定取得ユーティリティ（Settings クラス）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングスクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成 CLI
  - portfolio/
    - portfolio_builder.py — 候補選定、重み計算
    - position_sizing.py — 株数算出・投資額スケール調整
    - risk_adjustment.py — セクターキャップ、レジーム乗数
  - research/
    - factor_research.py — モメンタム/ボラティリティ/バリュー計算（DuckDB 使用）
    - feature_exploration.py — 将来リターン、IC、統計サマリー
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI）による銘柄スコアリング
    - regime_detector.py — レジーム判定（MA + マクロ NLP 合成）
  - monitoring/
    - monitoring_db.py — SQLite テーブル定義・永続化 API
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — （存在）注文滞留や約定異常の検出（コードベースの一部）
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — kill.flag 管理
    - monitoring_engine.py — 各 Monitor を束ねる実行ループ
    - alert_manager.py — （存在）アラート発行（LINE 等、実装に依存）
  - execution/
    - execution_engine.py — 実行エンジン本体（外部 API と注文ロジック）
    - broker_factory.py — ブローカークライアント生成（本番 / Mock 切替）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py など
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

（注）一部ファイルはここに抜粋されていないか、依存関係により追加の実装ファイルが必要です。

---

## 注意事項 / 運用上の留意点

- 本番運用では `KABUSYS_ENV=live` を使用します。validate_config は `live` 設定で追加の警告を出します。LINE 通知や kill flag の設定は慎重に。
- .env を絶対に Git にコミットしないこと（`config_setup.py` のヘッダにも明記）。
- OpenAI を使用する箇所は API 呼び出し失敗に対してフォールバック・リトライ実装がありますが、API 利用量・コストに注意してください。
- `run_execution.py` と `run_monitoring.py` は `data/stop_requested.flag` を使って安全に停止できます。kill.flag は ExecutionEngine の停止判定のための重要なファイルであり、誤って削除したり自動クリアする設定は本番で慎重に扱ってください。
- DuckDB / SQLite ファイルのバックアップおよび適切な権限設定を行ってください。

---

README の内容は提供されたソースコードに基づいた要約です。追加の実行例や依存関係、CI/CD の設定、より詳細なドキュメントはリポジトリの残りのファイル（`config/*.yaml`、ドキュメントファイル）や管理方針に従って整備してください。