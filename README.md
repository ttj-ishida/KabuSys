# KabuSys

日本株向け自動売買システムのサンプル実装（ライブラリ + 起動スクリプト群）

> バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な以下の機能群を備えたモジュール群です：

- 戦略・ファクター計算（research）
- ポートフォリオ構築（portfolio）
- 発注・Execution エンジン（execution）
- 監視・アラート（monitoring）
- AI を使ったニュース NLP / レジーム判定（ai）
- 運用支援ツール（設定ウィザード・検証・レポート）

設計方針の一部：
- DuckDB を分析 DB、SQLite を監視/発注ログに利用
- 環境変数（.env）で設定を管理。`.env.local` によりローカル上書き可
- Paper Trading（ペーパートレード）用に本番 DB と分離可能
- OpenAI（LLM）連携はオプション。API キーは環境変数で指定

---

## 主な機能一覧

- 環境設定ウィザード（config_setup）: 対話式で `.env` を生成・更新
- 設定検証 CLI（validate_config）: 起動前に環境変数 / YAML を検証
- ExecutionEngine 起動（run_execution）: 実際の発注を行うエンジン（paper/live/dev モードあり）
- Monitoring（run_monitoring）: システム状態 / 注文状態 / リスク監視および Kill Switch 評価
- Paper Trading 検証レポート（tools.paper_verification_report）
- ニュース NLP（ai.news_nlp）: OpenAI を利用したニュースのセンチメントスコア算出
- レジーム判定（ai.regime_detector）: ma200 + マクロセンチメントを合成して市場レジームを判定
- 研究用ファクター計算（research.factor_research）
- ポートフォリオ構築・サイズ決定（portfolio）

---

## 要件

- Python 3.10+
- 推奨（必須ではないが多機能に必要なパッケージ）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config/*.yaml の検証を行う場合）

インストール例（仮）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
# 実プロジェクトでは requirements.txt があればそれを使用
```

標準ライブラリの sqlite3 は不要インストール。

---

## セットアップ手順

1. リポジトリをチェックアウトし、仮想環境・依存をインストールします（上記参照）。

2. `.env` を作成する
   - 対話式ウィザード（推奨）:
     ```bash
     python -m kabusys.config_setup
     ```
   - または手動で作成: プロジェクトルートの `.env`（`.env.example` を参照）

3. 必須環境変数
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   - その他オプション: KABUSYS_ENV, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, OPENAI_API_KEY など

4. 自動ロードについて
   - 起動時に `.env` と `.env.local` は自動的に読み込まれます（OS 環境変数が優先）。
   - 自動ロードを無効にする場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

5. DB とログの準備
   - デフォルト:
     - DuckDB: `data/kabusys.duckdb`
     - SQLite (monitoring): `data/monitoring.db`
     - Paper trading SQLite: `data/paper_trading.db`（KABUSYS_ENV=paper_trading 時に使用）
   - ログ: `logs/` ディレクトリに `execution.log` / `monitoring.log` 等が出力されます。`LOG_DIR` 環境変数で変更可能。

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV: 実行環境。`development` / `paper_trading` / `live`（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（ai 機能利用時）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/…）
- LOG_DIR: ログ出力先ディレクトリ（デフォルト: logs/）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト: 60）
- PAPER_FILL_MODE: paper_trading 用 MockBroker の約定挙動（instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、本番は 0 推奨）

---

## 使い方（代表的なコマンド）

- 設定ウィザード（.env 作成）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  # 警告も FAIL 扱いにする:
  python -m kabusys.validate_config --strict
  ```

- Execution エンジン起動
  ```bash
  # 本番/開発は KABUSYS_ENV で切り替え
  python -m kabusys.run_execution
  # ペーパートレードで起動（MockBroker 使用、DB 分離）
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```

  - 実行時の挙動:
    - 起動直後にプロセス優先度を `high` に設定
    - `Settings` に基づいて SQLite/DuckDB に接続
    - `data/stop_requested.flag` が存在する場合は起動しない
    - `data/execution.pid` に PID を書く（設定で変更可）
    - 停止は `data/stop_requested.flag` を作る、または ExecutionEngine に stop() を呼ぶ

- Monitoring 起動
  ```bash
  python -m kabusys.run_monitoring
  # ポーリング間隔を変更したい場合
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  - Monitoring は本番の sqlite_path を常に使用して監視テーブルを保持します
  - `data/stop_requested.flag` が存在するとループを終了します

- Paper Trading 検証レポート
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを直接指定:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI（ニューススコア / レジーム判定）利用例（Python から）
  ```python
  import duckdb
  from kabusys.ai.news_nlp import score_news
  conn = duckdb.connect("data/kabusys.duckdb")
  from datetime import date
  score_news(conn, target_date=date(2026, 4, 20), api_key="sk-XXX")
  ```

---

## 停止・Kill Switch

- Graceful stop:
  - 両起動スクリプト（run_execution / run_monitoring）はプロジェクトの `data/stop_requested.flag` を監視しており、存在する場合ループを中断して終了します。
  - 手動で停止するにはプロセスに SIGINT（Ctrl+C）でも対応。

- Kill Switch（運用停止トリガー）:
  - 監視コンポーネントが検知した重大リスク（ドローダウン閾値超過など）により `data/kill.flag` が生成されます。
  - ExecutionEngine は起動時に kill.flag をクリアするオプション（KILL_FLAG_CLEAR_ON_START）を持ちますが、本番ではクリアしない設定を推奨します。
  - クリアは CLI やファイル削除で手動実行可能（KillSwitch.clear() を呼ぶか `rm data/kill.flag`）。

---

## 開発者向けユーティリティ

- config_setup: `.env` の作成・更新を対話式で補助
- validate_config: 必須環境変数・設定ファイル・パス等の事前チェック
- tools.paper_verification_report: Paper Trading の健全性（稼働率、約定率、レイテンシ等）を出力

---

## モジュール概要（簡潔）

- kabusys.config: 環境変数の読み込み・Settings クラス（.env 自動ロード・優先度処理含む）
- kabusys.utils:
  - logging_setup: 一貫したログ出力（コンソール + 日次ローテート）
  - process_priority: プラットフォーム依存を吸収したプロセス優先度設定
- kabusys.execution: 発注ロジック・ExecutionEngine（BrokerFactory によるモック/実ブローカ切替）
- kabusys.monitoring:
  - monitoring_db: SQLite による永続化（system_status / trade_logs / positions / risk_logs / dashboard）
  - system_monitor / trade_monitor / risk_monitor / monitoring_engine / kill_switch / alert_manager（監視と通知）
- kabusys.portfolio: 銘柄選定、重み計算、セクター制限、ポジションサイズ算出
- kabusys.research: ファクター計算、特徴量探索（IC 等）
- kabusys.ai: news_nlp（OpenAI 経由で銘柄毎センチメント）、regime_detector

---

## ディレクトリ構成

以下は主要ファイルのツリー（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_execution.py
  - run_monitoring.py
  - execution/
    - (ExecutionEngine, order_manager, broker_factory, etc.)
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/ (実行時に生成される)
    - monitoring.db (デフォルト)
    - paper_trading.db (paper_trading 時)
    - kill.flag, stop_requested.flag, execution.pid
  - logs/
    - execution.log
    - monitoring.log
    - ...

---

## 運用上の注意（抜粋）

- 本番（KABUSYS_ENV=live）では `KILL_FLAG_CLEAR_ON_START=0` を推奨。kill.flag の自動クリアは危険です。
- Paper Trading は DB を分離し、MockBroker を使って挙動確認ができます（実資金は使われません）。
- OpenAI を使う処理は API の遅延・エラーに強い（リトライ、フォールバック）設計ですが、API キー漏洩に注意してください。
- ログと DB ファイルは Git には含めない（.gitignore を使用）。

---

この README はコードベースの主要機能・使い方をまとめたものです。詳細な API ドキュメントや設計仕様（PortfolioConstruction.md / StrategyModel.md 等）がプロジェクト内にある場合はそちらを参照してください。必要であれば、個別モジュールの使用例や API サンプルを追記します。