# KabuSys — README

KabuSys は日本株向けの自動売買 / リサーチ / 監視フレームワークです。  
このリポジトリはトレード実行エンジン（Execution）、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI 支援（ニュース NLP / レジーム判定）などのコンポーネントを含みます。

バージョン: 0.1.0（`src/kabusys/__init__.py`）

---

## プロジェクト概要

KabuSys は次を目的としたモジュール群を提供します。

- 日次のファクター計算・リサーチ（DuckDB を用いた prices / financials ベースのファクター）
- シグナルに基づくポートフォリオ構築（候補選定、重み付け、株数計算）
- ExecutionEngine を通した発注管理（本番 / ペーパートレード分離）
- 監視サブシステム（システム状態・注文ログ・リスク監視、Kill Switch）
- AI モジュール（ニュースのセンチメントによる銘柄スコア / マクロセンチメントによるレジーム判定）
- 運用支援ツール（設定ウィザード、設定検証、ペーパートレード検証レポート等）

設計上のポイント:
- 実行スクリプトは環境変数で挙動を切り替え（`KABUSYS_ENV` 等）
- Paper trading は本番 DB と完全分離（`data/paper_trading.db`）
- DuckDB を解析用 DB として利用
- ロギングは統一的にセットアップし、日次ローテート（`logs/<app>.log`）

---

## 主な機能一覧

- 実行 / 監視起動スクリプト
  - `src/kabusys/run_execution.py` — ExecutionEngine 起動（`KABUSYS_ENV=paper_trading` 時は MockBroker）
  - `src/kabusys/run_monitoring.py` — SystemMonitor ポーリングループ起動（ポーリング間隔は環境変数で調整可）
- 設定支援
  - `src/kabusys/config_setup.py` — .env の対話式ウィザード
  - `src/kabusys/validate_config.py` — .env / config/*.yaml の事前検証（`--strict` オプションあり）
- 運用ツール
  - `src/kabusys/tools/paper_verification_report.py` — ペーパートレード検証レポート生成
- 監視（Monitoring）
  - `monitoring_db.py` — SQLite による監視ログ永続化
  - `system_monitor.py`, `trade_monitor.py`, `risk_monitor.py`, `monitoring_engine.py`, `kill_switch.py`（Kill Switch 実装）
- ポートフォリオ構築（純粋関数）
  - `portfolio/*` — 候補選定、重み計算、ポジションサイズ計算、セクター制限、レジーム補正
- リサーチ（DuckDB ベース）
  - `research/factor_research.py`, `research/feature_exploration.py` — ファクター計算、IC 等
- AI
  - `ai/news_nlp.py` — OpenAI を使ったニュースセンチメント集計（結果を ai_scores に格納）
  - `ai/regime_detector.py` — ETF MA とマクロニュースで市場レジーム判定
- ユーティリティ
  - `utils/logging_setup.py` — ログ設定
  - `utils/process_priority.py` — プロセス優先度 / CPU affinity 設定

---

## 必須・推奨環境

- Python 3.9+（ソースの型注釈に基づく）
- 推奨パッケージ（例）
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - pyyaml（`validate_config` の YAML 検証を行う場合）

（requirements.txt は本リポジトリに含まれていない場合があるため、プロジェクトに合わせて作成してください）

---

## セットアップ手順

1. リポジトリをクローン、プロジェクトルートへ移動
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   例:
   ```
   pip install duckdb psutil openai pyyaml
   ```
   （AI 機能を使わない場合は `openai` は不要）

4. データ / ログ用ディレクトリを用意（多くのスクリプトは存在しない場合自動作成しますが、手動作成しておくと安全です）
   ```
   mkdir -p data logs
   ```

5. 初期設定（.env）を作成
   - 対話式ウィザード:
     ```
     python -m kabusys.config_setup
     ```
   - または `.env` を手動で作成（`.env.example` を参照して必要な値を設定してください）。

6. 設定検証
   ```
   python -m kabusys.validate_config
   # 警告も fail としたい場合
   python -m kabusys.validate_config --strict
   ```

注意: `.env` は絶対に Git にコミットしないでください。

---

## 主な環境変数（抜粋）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行 / 動作切替
  - KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト: development）
    - paper_trading: MockBroker を使い `PAPER_TRADING_SQLITE_PATH`（デフォルト data/paper_trading.db）に記録
    - live: 本番運用モード（注意喚起あり）
  - LOG_LEVEL: "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"（ログレベル）
  - LOG_DIR: ログディレクトリ（デフォルト `logs/`）

- DB パス
  - DUCKDB_PATH: DuckDB ファイル（デフォルト: `data/kabusys.duckdb`）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: `data/monitoring.db`）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: `data/paper_trading.db`）

- 監視 / 制御
  - PID_FILE_PATH: PID ファイルパス（デフォルト: `data/execution.pid`）
  - KILL_FLAG_PATH: kill.flag のパス（デフォルト: `data/kill.flag`）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（"1" で有効、デフォルト "0"）
  - MONITOR_POLL_INTERVAL: `run_monitoring` のポーリング間隔（秒、デフォルト 60 秒）
  - PAPER_FILL_MODE: ペーパー取引時の約定モード（"instant" | "partial" | "never" | "reject"、デフォルト "instant"）

---

## 使い方（実行例）

- ExecutionEngine 起動（デフォルトは `.env` の KABUSYS_ENV を参照）
  ```
  python -m kabusys.run_execution
  ```
  - `KABUSYS_ENV=paper_trading` のときは MockBroker を使用し、ペーパートレード DB に記録します。
  - 起動前に `data/kill.flag` が存在する場合は起動を中止します（Kill Switch）。

- Monitoring 起動
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  - `MONITOR_POLL_INTERVAL` でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）。
  - 停止は `data/stop_requested.flag` を作成するか、Ctrl+C（KeyboardInterrupt）で行います。スクリプトは `data/stop_requested.flag` を検出するとループを終了します。

- 設定作成（対話式）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ペーパートレード検証レポート（ツール）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または別 DB を指定
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI モジュールの利用例（プログラムから呼び出す）
  - ニュース NLP（ai_scores 登録）
    ```python
    from kabusys.ai.news_nlp import score_news
    score_news(duckdb_conn, target_date=date(2026,4,1), api_key="sk-...")
    ```
  - レジーム判定
    ```python
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date=date(2026,4,1), api_key="sk-...")
    ```

注意:
- OpenAI API を利用する場合は `OPENAI_API_KEY` を環境変数または関数引数で指定してください。
- AI 呼び出しはネットワークのエラーやレート制限に対してリトライ実装が入っていますが、API キーが無い場合は例外になります。

---

## 停止 / Kill Switch の仕組み

- Kill Switch は `data/kill.flag` に理由文字列を書き込むことで ExecutionEngine に停止シグナルを送ります（`KillSwitch`）。
- `run_execution.py` と `run_monitoring.py` は別に `data/stop_requested.flag`（stop loop）を監視:
  - `data/stop_requested.flag` が存在すると `run_*` スクリプトはループを抜けて正常終了します。
- 本番運用時は `KILL_FLAG_CLEAR_ON_START=0` を推奨。`1` にすると起動時に `kill.flag` を自動クリアします（危険）。

---

## ディレクトリ構成（抜粋）

リポジトリ内の主要ファイル・ディレクトリ:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込みロジック
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py (存在する場合)
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py

- data/         — デフォルト DB / フラグファイル保存先（例: monitoring.db, paper_trading.db, kill.flag, stop_requested.flag）
- logs/         — ログファイル（日次ローテート）

（実際のリポジトリでは他のサブモジュールやファイルが存在する可能性があります）

---

## 運用上の注意事項

- .env 内の機密情報（API トークン、パスワード）は厳重に管理してください。`.env` をリポジトリに含めないでください。
- `KABUSYS_ENV=live` の設定は本番運用です。`validate_config` は本番時に警告を表示します。設定を慎重に確認してください。
- ペーパートレードは本番 DB と分離されますが、運用時は DB パスを再確認してください。
- ログディレクトリ作成に失敗した場合はコンソール出力のみになります（`logging_setup` はその場合に警告を出します）。
- `psutil` によるプロセス優先度設定や CPU affinity は権限に依存します。失敗した場合は警告が出てスキップされます。

---

## 追加情報 / 開発者向け

- 単体関数群（portfolio, research）は副作用なしにテスト可能に設計されています。
- DuckDB を使ったクエリは SQL を直接実行するため、テーブルスキーマ（`prices_daily`, `raw_financials`, `raw_news`, `ai_scores` 等）に依存します。テストデータを用意して検証してください。
- `validate_config` は `config/*.yaml` の存在・YAML パースチェックを行います（`pyyaml` がある場合のみ）。テンプレートは `scripts/generate_config.py` 等で生成可能な想定です。

---

必要であれば、README の英語版・インストール用 requirements.txt、簡易運用手順（systemd ユニット / Dockerfile）の雛形を作成します。必要な情報（OS や利用形態、本番/開発の想定等）を教えてください。