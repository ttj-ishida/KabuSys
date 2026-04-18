# KabuSys

日本株向け自動売買システムのコアモジュール群（ライブラリ／起動スクリプト群）

このリポジトリは、戦略用ファクター計算、ポートフォリオ構築、発注／リスク管理、監視、そしてニュース NLP / レジーム判定などを含む自動売買システムの主要コンポーネントを提供します。

注意: 本 README は src/kabusys 配下の実装に基づいて作成しています。

---

## プロジェクト概要

- 戦略（research）モジュール: DuckDB 上の時系列データを用いたファクター計算（モメンタム・ボラティリティ・バリュー等）。
- ポートフォリオ（portfolio）モジュール: 候補選定、重み計算、ポジションサイズ計算、セクター制限、レジーム乗数などの純粋関数。
- 実行（execution）モジュール: ブローカークライアント経由での注文管理、リスク管理、実行エンジン（ExecutionEngine）起動用スクリプト。
- 監視（monitoring）モジュール: システム状態・注文状況・リスクを監視し、kill flag による停止やアラート送出を行う。
- AI（ai）モジュール: OpenAI を用いたニュースセンチメント算出（news_nlp）や市場レジーム判定（regime_detector）。
- ユーティリティ: ロギング設定、プロセス優先度設定、設定読み込みウィザード等。
- ツール: ペーパートレード検証レポート生成等のスクリプト群。

設計方針として、DuckDB/SQLite をデータ層として使用し、本番とペーパートレードを分離すること、外部 API 呼び出しは明示的に行うこと、そしてルックアヘッドバイアスを避ける実装方針が取られています。

---

## 主な機能一覧

- 環境設定ウィザード（.env 生成 / 更新）: python -m kabusys.config_setup
- 設定検証 CLI（.env / config/*.yaml の検査）: python -m kabusys.validate_config
- ExecutionEngine 起動スクリプト: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録（本番 DB と分離）
- Monitoring 起動スクリプト（ポーリングループ）: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
  - 監視は環境にかかわらず本番 sqlite_path を利用して監視ログを永続化
- Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report
- AI 機能:
  - ニュースセンチメント算出（ai.score_news）: OpenAI API を利用
  - 市場レジーム判定（ai.regime_detector.score_regime）: ETF MA とマクロニュースを合成
- ポートフォリオ構築ユーティリティ:
  - 候補選定、等重／スコア加重、リスクベースのポジションサイズ計算、セクターキャップ適用、レジーム乗数

---

## 必要条件 / 事前準備

- Python 3.10 以上（| 型注釈、型の使用を想定）
- 必須パッケージ（例）
  - duckdb
  - psutil
  - openai
  - （オプション）PyYAML（config/*.yaml のパース検証用）
- 推奨: 仮想環境を作成して依存をインストールしてください。

例（venv + pip）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb psutil openai
# config 検証で YAML を使いたい場合:
pip install pyyaml
```

---

## 環境変数（主なもの）

- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- よく使う（デフォルト値）:
  - KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト: development
  - DUCKDB_PATH: 分析用 DuckDB のパス。デフォルト: data/kabusys.duckdb
  - SQLITE_PATH: 監視 DB（monitoring.db）パス。デフォルト: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード時の SQLite（data/paper_trading.db）
  - LOG_LEVEL: ログレベル（INFO）
  - LOG_DIR: ログ保存ディレクトリ（logs/）
  - OPENAI_API_KEY: OpenAI を使う機能で必要
  - PAPER_FILL_MODE: ペーパー取引の約定挙動（instant | partial | never | reject）（デフォルト: instant）
  - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START: 監視・停止関連

- 起動スクリプト固有:
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

自動 .env ロード:
- プロジェクトルートにある `.env` / `.env.local` が自動で読み込まれます（OS 環境変数が優先）。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化できます（テスト用）。

---

## セットアップ手順（初期）

1. リポジトリをクローンして仮想環境を作成:
   ```bash
   git clone <repo-url>
   cd <repo-root>
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb psutil openai
   ```

2. .env を生成（ウィザード）:
   ```bash
   python -m kabusys.config_setup
   ```
   - 必須値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を入力してください。
   - 注意: .env は必ず Git 管理から除外してください。

3. 設定検証:
   ```bash
   python -m kabusys.validate_config
   # 警告もエラー扱いで終了させたい場合:
   python -m kabusys.validate_config --strict
   ```

4. 必要に応じてデータディレクトリ作成:
   - デフォルトでは `data/` と `logs/` が作成されます。スクリプト実行時に自動で作成されますが、権限等に注意してください。

---

## 実行方法（使い方）

- ExecutionEngine を起動（デフォルト env に従う）
  ```bash
  # 本番/開発/ペーパーは KABUSYS_ENV に依存
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は専用ペーパーデータベース（PAPER_TRADING_SQLITE_PATH）を使用し、MockBrokerClient が使用されます。
  - 起動時に `data/stop_requested.flag` が存在すると起動せずに終了します。
  - 実行中は `data/execution.pid` に PID が書き込まれます。

- Monitoring を起動（ポーリング）
  ```bash
  # ポーリング間隔を環境変数で上書き（秒）
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```
  - 監視ループはデフォルト 60 秒毎に SystemMonitor.check_once を実行します。
  - `data/stop_requested.flag` を作成すると監視ループは終了します。
  - Monitoring は監視ログ（system_status / trade_logs / risk_logs / dashboard など）を SQLite (`SQLITE_PATH`) に記録します。

- Paper Trading 検証レポート生成:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を指定する場合:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI 機能（プログラム内 API 呼び出し例）
  - ニューススコア算出:
    ```py
    from kabusys.ai import score_news
    import duckdb, datetime
    conn = duckdb.connect("data/kabusys.duckdb")
    n_written = score_news(conn, datetime.date(2026, 4, 15), api_key="sk-...")
    ```
  - レジーム判定:
    ```py
    from kabusys.ai.regime_detector import score_regime
    n = score_regime(conn, datetime.date(2026, 4, 15), api_key="sk-...")
    ```

- kill.flag（Execution 停止）:
  - KillSwitch は `data/kill.flag` を書き込むことで ExecutionEngine に停止シグナルを送ります。
  - kill.flag は `Settings.kill_flag_clear_on_start` が 1 の場合に起動時自動クリアされる設定があります（本番では 0 が推奨）。

- 停止操作:
  - 常用: `data/stop_requested.flag` を作成すると run_execution / run_monitoring のループが検知して終了します。
  - Kill Switch は自動的にルールに従って `data/kill.flag` を書き込みます（手動で作成してプロセスを停止させることも可能）。

---

## ログ

- ログは `kabusys.utils.logging_setup.setup_logging` により統一的に設定されます。
  - コンソール（stdout）出力 + 日次ローテーションのファイル出力（logs/<app_name>.log）
  - ログディレクトリは `LOG_DIR` 環境変数または `logs/`
  - ログレベルは `LOG_LEVEL` 環境変数で制御

---

## ディレクトリ構成（抜粋）

プロジェクトルートの src/kabusys 配下の主要ファイル／モジュール:

- src/
  - kabusys/
    - __init__.py
    - config.py                  — 環境変数 / Settings
    - config_setup.py            — .env 対話式生成ウィザード
    - validate_config.py         — 設定検証 CLI
    - run_execution.py           — ExecutionEngine 起動スクリプト
    - run_monitoring.py          — Monitoring ポーリング起動スクリプト
    - tools/
      - paper_verification_report.py
    - ai/
      - __init__.py
      - news_nlp.py              — ニュース NLP（OpenAI）
      - regime_detector.py       — 市場レジーム判定（OpenAI + MA）
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - risk_adjustment.py
      - position_sizing.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - monitoring/
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - (trade_monitor.py 等：監視関連の他モジュール)
    - utils/
      - __init__.py
      - logging_setup.py
      - process_priority.py
    - (execution, data, strategy 等のパッケージが存在する想定)

ファイルは説明にある通り、監視用 DB や trade_logs / risk_logs / dashboard 等のスキーマ定義を持っています。

---

## 実運用上の注意点

- 本番環境（KABUSYS_ENV=live）は慎重に設定してください。validate_config は live の場合に追加の警告を出します（LINE 通知設定未設定など）。
- kill.flag を自動クリアする設定（KILL_FLAG_CLEAR_ON_START=1）は本番運用では危険です（推奨は 0）。
- OpenAI API を使う機能は API キー（OPENAI_API_KEY）が必要です。API 呼び出しは失敗時にフォールバックやリトライ実装がありますが、コストやレート制限に注意してください。
- run_monitoring は監視用 SQLite を書き換えます（Monitoring は本番 sqlite_path を使用する点に注意）。
- ペーパートレード時は DB を分離しています（PAPER_TRADING_SQLITE_PATH）。必ず本番 DB と分離してテストしてください。
- process priority / CPU affinity の設定は OS 権限により失敗する場合があります（警告ログのみ）。

---

## 開発者向けヒント

- 単体関数群（portfolio/*.py, research/*.py, monitoring/monitoring_db.py 等）は純粋関数または軽量な I/O に分離されており、ユニットテストしやすい設計です。
- `.env` の自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）を探して行います。テスト時に自動読み込みを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。
- OpenAI 呼び出し部分は _call_openai_api などのヘルパー関数に切り出されているため、テスト時は patch / mock による差し替えが容易です。

---

必要であれば、README に具体的な .env のテンプレート例、systemd / supervisord 用の起動ユニット例、Dockerfile / docker-compose 例などを追加できます。どの部分を詳しく追記しますか？