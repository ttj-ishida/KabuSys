# KabuSys

日本株自動売買システムの一部コードベース向け README（日本語）

このリポジトリは自動売買のコアコンポーネント（実行エンジン、監視、ポートフォリオ構築、ファクター計算、AI 補助モジュール等）を含みます。ここではローカルでのセットアップ・主要スクリプトの使い方・ディレクトリ構成をまとめます。

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な以下の機能群を提供するモジュール群です：

- ExecutionEngine（発注・約定管理・リスク管理）
- Monitoring（システム状態・注文・リスクの定期監視とアラート）
- Portfolio construction（銘柄選定、配分、ポジションサイズ計算、セクター制約）
- Research（ファクター計算、特徴量探索）
- AI 補助（ニュースのセンチメント解析によるスコアリング・市場レジーム判定）
- 各種ユーティリティ（ログ設定、プロセス優先度設定、環境設定ウィザード等）
- 運用用ツール（Paper Trading 検証レポート生成 等）

設計上の特徴：
- 設定は環境変数 / .env ファイルベース
- Paper Trading と Live 環境を分離（専用 DB を利用）
- DuckDB（時系列データ分析）と SQLite（監視・ログ）を併用
- OpenAI を用いた NLP 処理を実装（環境変数 OPENAI_API_KEY 必須）

---

## 機能一覧（抜粋）

- 環境設定ウィザード: python -m kabusys.config_setup
- 設定検証 CLI: python -m kabusys.validate_config
- ExecutionEngine 起動スクリプト: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading DB に記録
- Monitoring 起動スクリプト: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
- Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report
- AI:
  - ニュースセンチメントスコアリング: kabusys.ai.score_news
  - 市場レジーム判定: kabusys.ai.regime_detector.score_regime
- Portfolio モジュール:
  - 候補選定 / 等配分・スコア配分 / ポジションサイズ計算 / セクターキャップ適用 etc.
- Monitoring DB（SQLite）管理ユーティリティ（テーブル作成・マイグレーション）
- ログ設定ユーティリティ（stdout と日次ローテートファイル）

---

## 必要要件（推奨）

- Python 3.10+
- 推奨パッケージ（最低限）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML の検証を行いたい場合）
- SQLite（標準ライブラリに同梱）
- ネットワークアクセス（kabuステーション API / OpenAI を利用する場合）

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
# または要件ファイルがある場合:
# pip install -r requirements.txt
```

---

## セットアップ手順（基本）

1. リポジトリをクローン：
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成・パッケージインストール（上記参照）

3. .env の準備（ウィザード推奨）：
   ```bash
   python -m kabusys.config_setup
   ```
   ウィザードは .env を生成・更新します。生成された .env は決して Git にコミットしないでください。

4. 設定検証（任意）：
   ```bash
   python -m kabusys.validate_config
   # --strict を付けると警告も失敗扱いになります
   python -m kabusys.validate_config --strict
   ```

5. DB 初期化
   - Monitoring スクリプト / Execution スクリプトを起動すると必要な SQLite テーブルは自動作成されます。
   - DuckDB 用のファイルパス（デフォルト: data/kabusys.duckdb）は .env の DUCKDB_PATH で指定可能です。

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- OPENAI_API_KEY（AI 機能を使う場合、必須）
- KABUSYS_ENV（development | paper_trading | live、デフォルト: development）
  - paper_trading: ExecutionEngine は MockBroker を使用し paper_trading DB に記録
- PAPER_FILL_MODE（paper_trading の約定動作: instant | partial | never | reject、デフォルト: instant）
- DUCKDB_PATH（DuckDB ファイルパス、デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 SQLite、デフォルト: data/paper_trading.db）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- LOG_DIR（ログ出力ディレクトリ、デフォルト: logs/）
- PID_FILE_PATH（ExecutionEngine が作成する PID ファイル、デフォルト: data/execution.pid）
- KILL_FLAG_PATH（Kill Switch 用フラグパス、デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか 0/1、デフォルト: 0）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔（秒）、デフォルト: 60）

例（bash）:
```bash
export KABUSYS_ENV=paper_trading
export JQUANTS_REFRESH_TOKEN="xxxxx"
export KABU_API_PASSWORD="xxxxx"
export OPENAI_API_KEY="sk-xxxxx"
export DUCKDB_PATH="data/kabusys.duckdb"
export SQLITE_PATH="data/monitoring.db"
```

---

## 実行方法（代表的なコマンド）

- 環境設定ウィザード（対話式 .env 作成）:
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine 起動:
  ```bash
  python -m kabusys.run_execution
  ```
  注意:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い PAPER_TRADING_SQLITE_PATH に記録します。
  - 起動前に data/stop_requested.flag が存在する場合は起動しません。
  - 実行中に data/stop_requested.flag が書き込まれると安全に停止します。
  - 実行時に data/execution.pid が作成されます。

- Monitoring 起動:
  ```bash
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数で秒数を上書き可能（例: export MONITOR_POLL_INTERVAL=30）
  - 監視は常に（KABUSYS_ENV に関わらず）本番の sqlite_path を使用して監視ログを記録します。
  - 停止は data/stop_requested.flag を作成するか、Ctrl+C（KeyboardInterrupt）で可能です。

- Paper Trading 検証レポート:
  ```bash
  # デフォルト DB path: data/paper_trading.db
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # --db オプションで DB ファイルパスを指定可
  ```

- AI 関連（プログラム的に呼び出す）:
  - ニュースセンチメントスコアを生成して DB に書き込む:
    ```python
    import duckdb
    from kabusys.ai import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=<date_obj>, api_key="sk-...")
    ```
  - 市場レジーム判定:
    ```python
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=<date_obj>, api_key="sk-...")
    ```

---

## 停止 / Kill Switch 等

- 実行を止めたい場合:
  - 実行中プロセスへは data/stop_requested.flag を作成すると、run_execution/run_monitoring は検出して終了（または安全停止）します。
  - Execution 側の強制停止トリガー（取引停止）として Kill Switch があり、監視側が条件を満たすと data/kill.flag を書き込みます（ExecutionEngine は起動時に kill.flag を確認および挙動に従います）。
- KILL_FLAG_CLEAR_ON_START=1 に設定すると起動時に自動的に kill.flag を削除します（本番では危険なためデフォルト 0 推奨）。

---

## ログ

- ログは stdout にも出力され、日次でローテートされたファイルも logs/<app_name>.log に保存されます（LOG_DIR で変更可能）。
- ログレベルは LOG_LEVEL 環境変数で指定します（デフォルト INFO）。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 配下の主なモジュール・ファイル構成（リポジトリ中のファイルから抜粋）:

- kabusys/
  - __init__.py
  - config.py               — 環境変数 / .env 自動読み込み / Settings クラス
  - config_setup.py         — 対話式 .env ウィザード
  - validate_config.py      — 設定ファイル・環境変数検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — Monitoring ポーリング起動スクリプト
  - utils/
    - logging_setup.py      — ログ設定ユーティリティ
    - process_priority.py   — プロセス優先度 / CPU affinity 設定
  - execution/               — ExecutionEngine 関連コンポーネント（broker, order_manager 等）
    (※詳細ファイル群は省略)
  - monitoring/
    - monitoring_db.py      — SQLite モデル（テーブル作成 / DB 操作）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py      (アラート送信ロジック)
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
    - __init__.py
  - tools/
    - paper_verification_report.py
    - __init__.py
  - data/                   — 実行時に使用するファイル群（デフォルト）
    - monitoring.db (default SQLITE_PATH)
    - paper_trading.db
    - kill.flag
    - stop_requested.flag
    - execution.pid
  - config/                 — YAML 設定ファイル（system_config.yaml 等、テンプレートあり）

（実際のリポジトリではさらに細かいサブモジュール・ファイルが存在します）

---

## 開発・運用上の注意点

- 環境変数の管理:
  - .env ファイルは機密情報（APIキー等）を含むため Git 管理しないでください。
  - config_setup で生成した .env を利用してください。
- 本番環境（KABUSYS_ENV=live）では特に LINE 通知設定や Kill Switch の設定を慎重に行ってください。validate_config は live 時に追加警告を出します。
- OpenAI API 呼び出しにはコストが発生します。AI 関連処理は必ず OPENAI_API_KEY を適切に設定し、利用料管理してください。
- psutil を用いたプロセス優先度設定は OS と権限に依存します。権限不足で設定に失敗する場合がありますが、ソフトフォールバックで継続します。
- DuckDB / SQLite のファイルパスは .env で調整可能。運用時は適切なディレクトリ・バックアップ運用を行ってください。

---

## 参考コマンドまとめ

- ウィザードで .env 作成:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 実行エンジン起動:
  python -m kabusys.run_execution

- 監視起動:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

この README はリポジトリ内の Python モジュール群から抽出した情報をもとに作成しています。運用前に python -m kabusys.validate_config で環境設定を確認してください。質問や追加で記載してほしい具体的な使用例（systemd / supervisor の Unit ファイル例、Dockerfile 例、CI/CD 設定 など）があれば教えてください。