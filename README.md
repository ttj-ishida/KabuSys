# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ向け README（日本語）

この README はリポジトリ内のスクリプトと主要モジュールの使い方、セットアップ手順、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムのコードベースです。以下の機能群を含みます。

- シグナル生成 / ポートフォリオ構築（ファクター計算・配分・ポジションサイズ算出）
- ExecutionEngine（発注ロジック）およびペーパートレード切替
- 監視（System / Trade / Risk）と Kill Switch（停止フラグ）の管理
- ニュース NLP（OpenAI を使ったセンチメント評価）および市場レジーム判定
- DuckDB / SQLite を使ったデータ処理・ログ保存
- 各種ユーティリティ（ログ設定、プロセス優先度、設定ウィザード、設定検証）
- Paper Trading の検証レポート生成ツール

設計方針の一部：
- 本番・ペーパーの DB 分離（`KABUSYS_ENV=paper_trading` 時は専用 DB を使用）
- 重要処理はフェイルセーフ（API失敗時はスキップ、部分成功を保護）
- ルックアヘッドバイアス防止（日時を直接参照しない等）

---

## 機能一覧（主要ファイル・モジュール）

- 起動スクリプト
  - `python -m kabusys.run_execution`：ExecutionEngine（発注エンジン）起動
  - `python -m kabusys.run_monitoring`：SystemMonitor のポーリング監視起動
- 設定関連
  - `kabusys.config_setup`：.env を対話的に作成・更新するウィザード
  - `kabusys.validate_config`：環境変数 / config/*.yaml の検証 CLI
- 監視関連
  - `kabusys.monitoring`：SystemMonitor / TradeMonitor / RiskMonitor、KillSwitch、MonitoringEngine
  - `kabusys.monitoring.monitoring_db`：SQLite 用永続化層
- Execution / 発注関連（ディレクトリ `execution/` に多数）
  - BrokerFactory / ExecutionEngine / OrderManager / RiskManager 等
- ポートフォリオ構築（`kabusys.portfolio`）
  - 候補選定・重み計算・リスク調整・ポジションサイズ算出
- 研究 / ファクター計算（`kabusys.research`）
  - momentum / volatility / value 等のファクター計算、IC や将来リターン計算
- AI（`kabusys.ai`）
  - `news_nlp`：OpenAI を用いたニュースセンチメント → ai_scores へ書込
  - `regime_detector`：マクロ + ETF 指標から日次レジーム判定
- ツール
  - `kabusys.tools.paper_verification_report`：ペーパートレード検証レポート生成

---

## セットアップ手順（開発 / 実行環境準備）

以下は一般的なセットアップ手順の例です。環境や OS に応じて適宜調整してください。

1. リポジトリをクローン
   ```
   git clone <repository-url>
   cd <repo-root>
   ```

2. Python 仮想環境を作成・有効化（例: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   - リポジトリに `requirements.txt` があればそれを使ってください（無ければ主要依存を例示）。
   ```
   pip install -r requirements.txt
   ```
   - 主要パッケージ（例）:
     - duckdb
     - psutil
     - openai
     - PyYAML（`kabusys.validate_config` の YAML 検証に必要）
   ```
   pip install duckdb psutil openai PyYAML
   ```

4. .env の作成
   - 対話式ウィザードで作成：
   ```
   python -m kabusys.config_setup
   ```
   - 作成後、`python -m kabusys.validate_config` で検証してください。

5. データディレクトリの準備（logs / data）
   - ログや DB はデフォルトで `data/` や `logs/` に作成されます。必要に応じて権限や所有者を確認してください。

注意:
- SQLite / DuckDB ファイルはデフォルトで `data/monitoring.db` / `data/kabusys.duckdb` に作成されます。
- 一部の機能は OpenAI API キー（`OPENAI_API_KEY`）や外部 API トークンが必須です。

---

## 環境変数（主要）

- 必須（最低限セット）
  - JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード

- 実行環境切替
  - KABUSYS_ENV — one of `development` | `paper_trading` | `live`（デフォルト: development）

- DB / ファイルパス
  - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH — ExecutionEngine の pid ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH — Kill Switch の flag（デフォルト: data/kill.flag）

- ログ
  - LOG_LEVEL — `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`（デフォルト: INFO）
  - LOG_DIR — ログファイルの出力先（デフォルト: logs/）

- OpenAI
  - OPENAI_API_KEY — OpenAI 呼び出しに必要（news_nlp / regime_detector など）

- Paper / その他
  - PAPER_FILL_MODE — ペーパートレードの約定モード（`instant` / `partial` / `never` / `reject`。デフォルト: `instant`）
  - MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔秒（デフォルト: 60）。1未満や不正値は無視され 60 にフォールバック。
  - KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリアするか（"1" でクリア、デフォルト "0"）

---

## 使い方（起動・運用）

以下は主要なコマンド例です。

- .env を生成（対話式）
  ```
  python -m kabusys.config_setup
  ```

- 設定を検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict   # 警告も失敗扱い
  ```

- ExecutionEngine（発注エンジン）起動
  - 本番 / ペーパーは KABUSYS_ENV に従う。`paper_trading` の場合は専用 DB（`data/paper_trading.db`）を使用し、MockBrokerClient を利用する設計。
  ```
  python -m kabusys.run_execution
  ```
  起動時に `data/stop_requested.flag` が存在すると起動せず終了します。起動中は同ファイルを作成することで外部から停止要求ができます（デーモン停止用）。

- Monitoring 起動（SystemMonitor のポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書きできます（例: 30）。
  - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path（`SQLITE_PATH`）を使用します（監視ログは一元化）。
  - `data/stop_requested.flag` の検出でループを終了します。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  または DB 指定：
  ```
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI モジュール実行（プログラム的に呼び出す）
  - 例: `kabusys.ai.news_nlp.score_news(conn, target_date, api_key=...)`
  - `OPENAI_API_KEY` が必要（または api_key を明示的に渡す）

停止・フラグ関連：
- stop（監視 / エンジンを穏やかに停止）:
  - ルートプロジェクト直下の `data/stop_requested.flag` を作成すると、`run_execution` / `run_monitoring` のループが検出して終了します。
- kill switch（緊急停止: Execution を止める）
  - `KillSwitch` は `data/kill.flag` を書き込み、ExecutionEngine に対して停止シグナルを与えます（`KillSwitch.clear()` で削除可能）。本番（`KABUSYS_ENV=live`）では `KILL_FLAG_CLEAR_ON_START` を `1` にするのは危険です。

ログ:
- `kabusys.utils.logging_setup.setup_logging` を各起動スクリプトが呼び出します
- デフォルト: コンソール（stdout） + 日次ローテーションファイル（`logs/<app_name>.log`）
- ログディレクトリが作れない場合はコンソールのみで継続します

プロセス優先度:
- 起動スクリプトは最初に `set_process_priority("high")` を呼びます（可能な場合のみ）

---

## ディレクトリ構成（主要部分）

以下は `src/kabusys` 以下の主要モジュール・ファイル構成（抜粋）です。

- kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト
  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI 連携）
    - regime_detector.py      — 市場レジーム判定
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py         # （実装ファイルあり）
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py         # （実装ファイルあり）
  - execution/
    - execution_engine.py     # ExecutionEngine 本体
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py

注: 上記は主要ファイルの一覧です。実際のリポジトリにはさらに細かいモジュール・テスト・スクリプトが含まれる可能性があります。

---

## 運用上の注意点 / ベストプラクティス

- 本番での起動前に必ず `python -m kabusys.validate_config` を実行し設定を確認してください。
- `KABUSYS_ENV=live` 時は kill flag の自動クリア（`KILL_FLAG_CLEAR_ON_START=1`）を避けてください（誤発動で復旧できなくなる恐れがあります）。
- OpenAI API 呼び出しはレート制限やネットワーク不安定性を考慮したリトライ実装が入っていますが、APIキーの管理と利用コストに注意してください。
- ログや DB の保存先はバックアップとアクセス権設定を適切に行ってください（特に監視ログや注文ログ）。
- ペーパートレードは実取引のテスト用途に限定し、実運用切替時は設定（DB パスや `KABUSYS_ENV`）を必ず確認してください。

---

README は以上です。実際に動かす際、リポジトリ内の README / docs / config/*.yaml / scripts ディレクトリも参照してください。追加で詳細な起動手順や運用手順（systemd / cron / supervisor 用の unit ファイル、CI/CD の設定など）を追記したい場合は、その内容に合わせてサンプルを作成します。必要であれば教えてください。