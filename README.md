# KabuSys

日本株自動売買システムの軽量実装。データ取得・リサーチ・ポートフォリオ構築・発注（実口座 / ペーパートレード）・監視・AI ベースのニュースセンチメントなどを含むモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は、日本株の自動売買ワークフローを構成するモジュールのコレクションです。主な責務は以下の通りです。

- データ格納と分析用 DuckDB（prices_daily / raw_financials など）
- ファクター計算・研究（momentum / value / volatility 等）
- ポートフォリオ構築（候補選定、重み付け、株数算出、セクター制約）
- 発注・実行エンジン（実口座 / ペーパートレードの分離）
- 監視（システム・注文・リスク監視）、Kill Switch によるエンジン停止
- AI（OpenAI）を用いたニュースセンチメント・レジーム判定
- 運用・検証用ツール（ペーパートレード検証レポート等）

設計方針として、外部 API 呼び出しや DB 書き込みは明示的に行い、テスト可能でフェイルセーフな挙動を重視しています。

---

## 主な機能一覧

- 環境設定ウィザード: `.env` を対話式に作成する `kabusys.config_setup`
- 設定検証 CLI: `.env` と `config/*.yaml` の起動前チェック `kabusys.validate_config`
- 実行エンジン起動スクリプト: `run_execution.py`
  - `KABUSYS_ENV=paper_trading` の場合は MockBroker を使い DB を分離
  - 停止用フラグファイル（data/stop_requested.flag）・PID ファイル管理
- 監視起動スクリプト: `run_monitoring.py`
  - ポーリングで SystemMonitor を実行。`MONITOR_POLL_INTERVAL` で間隔上書き可能
  - Monitoring は環境に関係なく本番用の sqlite_path を使用
- 監視エンジン・各モニタ: system / trade / risk / kill switch / alert manager
- ポートフォリオモジュール: 候補選定、等重・スコア重み、リスク調整、ポジションサイジング
- リサーチ: ファクター（momentum/value/volatility）、特徴量探索・IC 計算
- AI モジュール:
  - ニュース NLP（OpenAI）で銘柄別センチメントを ai_scores に書込み
  - レジーム判定（ma200 + マクロニュースセンチメント合成）
- ユーティリティ:
  - ログ設定（標準出力 + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定
- ツール: Paper Trading 検証レポート生成スクリプト

---

## セットアップ手順（開発 / ローカル）

※ 以下はリポジトリをクローンした前提です。

1. Python バージョン
   - Python 3.10+（コード内で `X | Y` の型ヒント等を使用）

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows (PowerShell)
   ```

3. 依存パッケージをインストール
   - 必須パッケージ（主なもの）: duckdb, psutil, openai
   - 開発時／一部機能: PyYAML（`validate_config` の YAML 検証用）
   - 例:
     ```
     pip install duckdb psutil openai PyYAML
     ```
   - 実環境では依存管理ファイル（requirements.txt）があればそれを使用してください。

4. `.env` を作成
   - ウィザードを使う（対話式）:
     ```
     python -m kabusys.config_setup
     ```
   - 必須環境変数（最低限）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要な環境変数（抜粋）
     - KABUSYS_ENV: development | paper_trading | live
     - DUCKDB_PATH: デフォルト `data/kabusys.duckdb`
     - SQLITE_PATH: 監視 DB デフォルト `data/monitoring.db`
     - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 DB（paper_trading モード）
     - OPENAI_API_KEY: AI 機能を使う場合に必須
     - LOG_LEVEL, LOG_DIR など

5. 設定検証
   ```
   python -m kabusys.validate_config
   # 必要なら --strict を付けて警告も失敗扱いにする
   python -m kabusys.validate_config --strict
   ```

6. データディレクトリ
   - ログ: デフォルト `logs/`（自動作成）
   - DB 等: `data/` 以下に配置（設定により変更可）
   - 停止フラグや PID ファイルも `data/` に作成されます（例: data/stop_requested.flag, data/execution.pid）

---

## 使い方（よく使うコマンド）

- 実行エンジン起動
  ```
  python -m kabusys.run_execution
  ```
  - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient が使用され、データは `PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）に保存されます。
  - 停止するには `data/stop_requested.flag` を作成するとエンジンが検知して終了します。手動で停止する場合は `CTRL+C`。

- 監視プロセス起動
  ```
  # ポーリング間隔を 30 秒にしたい場合
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  - 監視は `MONITOR_POLL_INTERVAL`（秒）で間隔指定。デフォルトは 60 秒。
  - 監視は「監視用 DB（sqlite_path）」を使用し、KABUSYS_ENV に関係なく本番の sqlite_path を参照します（注意）。

- Kill Switch / 停止フラグ
  - KillSwitch は `data/kill.flag` に理由を書き込むことで ExecutionEngine 停止をトリガできます。
  - `KillSwitch.clear()` を呼ぶかファイルを手動で削除してクリアしてください。
  - Execution 側は起動時に `KILL_FLAG_CLEAR_ON_START` を 1 にすると自動的にクリアする設定があります（本番では 0 推奨）。

- ペーパートレード検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを指定する場合
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI 機能（ニューススコア・レジーム判定）
  - OpenAI API キーを `OPENAI_API_KEY` に設定して使用します（もしくは関数呼び出し時に渡す）。
  - 例（プログラム内で呼ぶ）:
    - kabusys.ai.score_news(conn, target_date, api_key)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key)

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- OPENAI_API_KEY: OpenAI を使う場合に必須
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 DB（デフォルト data/paper_trading.db）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant | partial | never | reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログ出力ディレクトリ（デフォルト logs/）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START など監視制御系

validate_config と config_setup を使って `.env` を正しく整備してください。

---

## 実装上の注意点 / 備考

- run_monitoring はドキュメントにもある通り KABUSYS_ENV に関係なく本番 sqlite_path を使用します。監視の DB は運用用 DB と意図的に切り離さない設計になっています（設定でパスを変えることは可能）。
- run_execution は paper_trading モード時に専用の DB を用いることで本番 DB と分離します（安全設計）。
- ロギングは共通のユーティリティ `kabusys.utils.logging_setup.setup_logging` を通じて行われます。既存ハンドラはクリアされてから再設定されるため、複数起動時の二重出力を防ぎます。
- プロセス優先度設定・CPU affinity は psutil を使って OS ごとの差分を吸収します。権限不足時は警告を出して続行します。
- AI 機能は OpenAI API への依存があり、ネットワークエラーやレート制限時にリトライやフォールバック（ゼロスコアなど）する実装になっています。API キーの取り扱いは厳重に行ってください。
- 各モジュールは可能な限り副作用を抑え、テストしやすい純粋関数群（research / portfolio）と I/O 層（monitoring_db / ai I/O）を分離しています。

---

## ディレクトリ構成（主要ファイル）

プロジェクトの主要なディレクトリ・ファイル構成（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py               — 環境変数 / 設定管理
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor 起動スクリプト
  - utils/
    - logging_setup.py      — ログ設定ユーティリティ
    - process_priority.py   — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py      — SQLite 永続化層（テーブル作成・読み書き）
    - system_monitor.py     — システム・データ鮮度監視
    - trade_monitor.py      — 注文ログ監視（存在）
    - risk_monitor.py       — ドローダウン / ポジション上限監視
    - kill_switch.py        — kill.flag 書込による停止シグナル
    - monitoring_engine.py  — 各 Monitor を束ねるエンジン
    - alert_manager.py      — （アラート送信管理; 実装あり）
  - execution/
    - execution_engine.py   — Execution エンジン（主要ロジック）
    - broker_factory.py     — ブローカークライアント生成
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
  - ai/
    - news_nlp.py           — ニュース NLP / スコアリング
    - regime_detector.py    — 市場レジーム判定
  - tools/
    - paper_verification_report.py

（実際のリポジトリはさらに多くの補助モジュール・ファイルが含まれます。上は主要点の抜粋です）

---

## よくある運用フロー（例）

1. 仮想環境を作り依存をインストール
2. `python -m kabusys.config_setup` で `.env` を作成
3. `python -m kabusys.validate_config` で設定をチェック
4. 本番実行:
   - 監視: `MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring &`
   - 実行: `python -m kabusys.run_execution &`
5. 問題発生時は `data/kill.flag` を作り Execution を停止、または `data/stop_requested.flag` を作って両プロセスを終了させます
6. ペーパートレード検証: `python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD`

---

必要であれば、README にサンプル .env.example のテンプレート、各 CLI の出力例、テスト手順、あるいは Docker-compose の起動例などを追記できます。どの情報を優先して追加しますか？