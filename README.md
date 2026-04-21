# KabuSys

日本株自動売買システム（ライブラリ兼軽量実行フレームワーク）

このリポジトリは、シグナル生成・ポートフォリオ構築・注文実行・監視・調査用ユーティリティ群を含む自動売買基盤の一部実装です。各モジュールは可能な限り副作用を抑え、テストしやすい純粋関数と薄い I/O 層で構成されています。

---

## 主な機能（概要）

- Portfolio construction
  - 候補選定（スコア/ランクに基づく選定）
  - 等比配分 / スコア加重配分
  - ポジションサイジング（リスクベース、単元株丸め、資金配分調整）
  - セクター集中制限・レジーム乗数

- Research（DuckDB を用いたファクター計算）
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン・IC（情報係数）計算、特徴量サマリー

- Execution（注文実行基盤）
  - ExecutionEngine 起動スクリプト（本番 / ペーパートレード分離）
  - OrderManager / RiskManager / Reconciler 等（実装は別ファイルに存在）

- Monitoring（監視・アラート）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - 監視ログ永続化（SQLite）
  - Kill Switch（条件に応じて ExecutionEngine を停止するフラグ書き込み）
  - 起動スクリプト（ポーリングループ）

- AI 関連
  - ニュース NLP（OpenAI API を用いた銘柄別センチメント算出）
  - 市場レジーム判定（MA200 とマクロセンチメントの合成）

- ユーティリティ
  - 環境設定ウィザード（.env の対話式作成）
  - 設定検証 CLI（.env と config/*.yaml の簡易チェック）
  - Paper Trading 検証レポート生成スクリプト

---

## 必要条件 / インストール

動作に必要な主要パッケージ例（プロジェクトに requirements.txt が無い場合の例）:

- Python 3.10+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config 検証で YAML をパースする場合）

インストール例:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

（必要に応じて他の依存を追加してください）

---

## 環境変数（主なもの）

必須:

- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要なオプション / デフォルト:

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- LOG_DIR: logs/
- OPENAI_API_KEY: OpenAI API を使う場合に必要
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアする（"1" で有効）
- KILL_FLAG_PATH: data/kill.flag（Settings.kill_flag_path のデフォルト）

注意:
- .env 自動読み込み: プロジェクトルート（.git か pyproject.toml がある場所）にある `.env` と `.env.local` を自動で読み込みます。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順（推奨）

1. リポジトリを取得
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成・依存インストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb psutil openai pyyaml
   ```

3. .env 作成（対話式ウィザード）
   ```bash
   python -m kabusys.config_setup
   ```
   - ウィザードで質問に答えると `.env` が作成されます。
   - 生成後に `python -m kabusys.validate_config` で検証してください。

4. DB の初期化
   - 監視用 SQLite や DuckDB は起動スクリプトが自動で必要テーブルを作成します。特別な手順は不要です。

---

## 使い方（主要スクリプト / コマンド）

実行はプロジェクトルートから行ってください（.env の自動読み込みが働くため）。

- 環境設定ウィザード（.env の作成 / 更新）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  - 警告を FAIL とする strict モード:
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine 起動（注文実行部分）
  ```bash
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、Paper Trading 専用 DB に記録します（デフォルト: data/paper_trading.db）。
  - 起動中に `data/stop_requested.flag` を作成すると安全に停止します。
  - 実行時にプロセス PID は `data/execution.pid` に記録されます。

- Monitoring 起動（ポーリングループ）
  ```bash
  python -m kabusys.run_monitoring
  ```
  - `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60）。
  - Monitoring は KABUSYS_ENV にかかわらず production 用の sqlite_path を使用して監視テーブルを初期化します。
  - 停止方法: `data/stop_requested.flag` を作成するとループが次回チェック時に終了します。

- Paper Trading 検証レポート（集計・判定）
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パスは `--db` または環境変数 `PAPER_TRADING_SQLITE_PATH` で指定可能（デフォルト: data/paper_trading.db）。

- AI スコアリング / レジーム判定（Python から呼び出す）
  - ニュース NLP:
    ```python
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026, 4, 10), api_key="sk-...")
    ```
  - レジーム判定:
    ```python
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026, 4, 10), api_key="sk-...")
    ```
  - OpenAI API キーは引数で渡すか環境変数 `OPENAI_API_KEY` を設定してください。API 呼び出しは冗長性を確保するためにリトライやフォールバック（失敗時は安全な既定値）を行います。

---

## ログ/監視/フラグについて

- ログ:
  - setup_logging により stdout へ出力され、file handler は日次ローテートで `logs/<app_name>.log` に出力（デフォルト 30 日保持）。
  - ログレベルは `LOG_LEVEL` または引数で設定。

- 停止フラグ:
  - run_monitoring / run_execution 等はプロジェクトルートの `data/stop_requested.flag` を監視して安全停止します。
  - Kill Switch: `data/kill.flag`（デフォルト）は KillSwitch により書き込まれ、ExecutionEngine に停止シグナルを与えます。`KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に kill.flag を自動クリアします（本番では推奨されません）。

---

## 開発者向けノート

- Settings（kabusys.config）は `.env` と OS 環境変数を組み合わせて設定を提供します。自動ロードはプロジェクトルートが見つかった場合にのみ行われ、テスト環境のために無効化可能です。
- MonitoringDB（monitoring_db.py）は SQLite に対するスキーマ初期化・マイグレーションロジックを提供します（idempotent）。
- Research / Portfolio / Position sizing モジュールは副作用を持たない純粋関数群として実装されており、単体テストが容易です。
- AI モジュールは OpenAI SDK（chat completions）を呼び出します。API の失敗や JSON パースの問題に対し堅牢なハンドリングが入っています。

---

## 主要ディレクトリ構成

（src/kabusys 以下を想定）

- kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定取得ロジック
  - config_setup.py                — .env 対話式ウィザード
  - validate_config.py             — 設定検証 CLI
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポートスクリプト
  - ai/
    - news_nlp.py                  — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py           — 市場レジーム判定（MA + マクロセンチメント）
  - monitoring/
    - monitoring_db.py             — 監視用 DB 層（SQLite）
    - monitoring_engine.py         — 各 Monitor を束ねるエンジン
    - system_monitor.py            — システム状態 / データ鮮度監視
    - risk_monitor.py              — ドローダウン・ポジション上限監視
    - trade_monitor.py             — （約定・滞留注文監視等 — 実装あり）
    - kill_switch.py               — kill.flag 書き込みロジック
    - alert_manager.py             — アラート配信ロジック（実装あり）
  - portfolio/
    - portfolio_builder.py         — 候補選定 / 重み計算
    - position_sizing.py           — 株数計算 / スケーリング
    - risk_adjustment.py           — セクター上限 / レジーム乗数
  - research/
    - factor_research.py           — ファクター計算（DuckDB）
    - feature_exploration.py       — IC / 統計サマリ等
  - utils/
    - logging_setup.py             — ログ設定ユーティリティ
    - process_priority.py          — プロセス優先度 / CPU affinity 設定
  - execution/                      — 注文実行関連: engine, order_manager, broker_factory 等
  - data/                           — 実行時生成ファイル（data/monitoring.db, data/kabusys.duckdb, data/kill.flag 等）

（実際のファイル一覧はリポジトリのツリーをご参照ください）

---

## よくある質問 / 注意点

- 監視（Monitoring）は環境に関係なく `Settings.sqlite_path`（production 設定）を利用して監視テーブルを初期化します。paper_trading 中でも監視ログは production DB に書き込まれる点に注意してください（意図的な設計）。
- Paper Trading 実行時はブローカークライアントが Mock 実装に切り替わり、発注の副作用は paper_trading DB に限定されます。
- OpenAI API を使用するワークフローでは、API キーの管理（環境変数／秘密管理）は十分に注意してください。大量のリクエストを行う場合はレート制限やコストに注意。

---

この README はコードベースの主要な使い方・設計方針を簡潔にまとめたものです。詳細な内部仕様や各モジュールの挙動はソースコードの docstring / コメントを参照してください。必要であれば本 README を補足する具体的な運用手順（systemd / supervisor 用のユニットファイル例、Dockerfile など）も別途作成できます。