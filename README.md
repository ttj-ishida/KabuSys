# KabuSys

日本株向けの自動売買システムのコアライブラリ群と起動スクリプト群です。  
本リポジトリは発注ロジック、監視、ポートフォリオ構築、研究用ファクター計算、AI を使ったニュースセンチメント評価などを含むモジュール群で構成されています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の主要機能を持つモジュール群です。

- ExecutionEngine: ブローカーと連携して発注／注文管理を行う実行エンジン
- Monitoring: システム稼働状況・注文状況・リスク（ドローダウン等）を監視し必要に応じて Kill Switch を起動
- Portfolio construction: 候補選定、重み算出、ポジションサイズ計算、セクター上限適用など
- Research: DuckDB を用いたファクター計算・特徴量解析モジュール（モメンタム、ボラティリティ、バリュー等）
- AI モジュール: ニュースを LLM（OpenAI）で評価しスコアリング、マクロセンチメントを用いたレジーム判定
- ユーティリティ: ロギング設定、プロセス優先度設定、設定ウィザード、設定検証、ツール類（ペーパートレード検証レポート等）

設計上のポイント:
- データ永続化は主に SQLite（監視・トレードログ）と DuckDB（分析用）を使用
- Paper Trading 環境では本番 DB と分離（別 SQLite ファイル）されるようになっています
- .env による環境変数管理をサポート、対話式ウィザードで .env を作成可能

---

## 機能一覧（主要）

- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動（paper_trading 時は MockBroker 使用）
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL による間隔変更可）
- 設定管理
  - config_setup.py: .env を対話式で作成／更新するウィザード
  - validate_config.py: 起動前に環境変数や config/*.yaml の基本検証を行う CLI
- 監視
  - monitoring_engine.py: 監視コンポーネントを束ねるポーリングエンジン
  - system_monitor.py / trade_monitor.py / risk_monitor.py: 各種監視ロジック
  - monitoring_db.py: SQLite テーブル定義・永続層
  - kill_switch.py: kill.flag による ExecutionEngine 停止トリガー
- ポートフォリオ構築
  - portfolio_builder.py / position_sizing.py / risk_adjustment.py
- 研究・分析
  - research.factor_research: モメンタム・ボラティリティ・バリュー等の計算（DuckDB）
  - research.feature_exploration: 将来リターンの計算、IC 等の統計
- AI（OpenAI）
  - ai.news_nlp: ニュースを LLM でセンチメント評価し ai_scores に書き込み
  - ai.regime_detector: ETF を用いた MA 乖離＋マクロニュースでレジーム判定
- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成

---

## 前提 / 必要な環境

- Python 3.10+（3.11 を推奨）
- SQLite（組み込み）
- 主要ライブラリ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証時に YAML 内容検証を行いたい場合に必要）
- ネットワーク（OpenAI API を使用する機能を利用する場合）

インストール例（仮の最低限）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```
（必要に応じて追加パッケージをインストールしてください）

---

## セットアップ手順

1. リポジトリをクローン／展開する
2. 仮想環境を作成して依存をインストール
3. .env を生成・編集
   - 対話式で作る場合:
     ```bash
     python -m kabusys.config_setup
     ```
   - または手動でリポジトリルートに `.env` を作成する

4. 設定検証（起動前チェック）:
   ```bash
   python -m kabusys.validate_config
   # 警告も失敗にしたい場合:
   python -m kabusys.validate_config --strict
   ```

---

## 主な環境変数（.env で設定）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

主な任意／デフォルト値:
- KABUSYS_ENV — 実行環境（development / paper_trading / live）デフォルト: development
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/…。デフォルト: INFO）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知用（任意）
- OPENAI_API_KEY — OpenAI を利用するモジュールを有効にする場合に必須

監視・その他:
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリアするか (0/1)
- PID_FILE_PATH / KILL_FLAG_PATH — 各種ファイルパス（デフォルト data/ 下）

注記:
- run_monitoring は KABUSYS_ENV にかかわらず settings.sqlite_path（監視用 DB）を使用します。
- run_execution は KABUSYS_ENV=paper_trading の場合は paper_sqlite_path を使用して本番 DB と分離します。

---

## 実行方法（主要コマンド）

- 実行エンジン（ExecutionEngine）を起動:
  ```bash
  python -m kabusys.run_execution
  ```
  - paper_trading 環境で起動する場合:
    ```bash
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```

- 監視プロセスを起動:
  ```bash
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を 30 秒に変更する例:
    ```bash
    export MONITOR_POLL_INTERVAL=30
    python -m kabusys.run_monitoring
    ```

- 設定ウィザード:
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - データベースを明示指定する場合:
    ```bash
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
    ```

- AI / 研究用関数は Python からインポートして利用できます（例）:
  ```python
  import sqlite3
  import duckdb
  from datetime import date
  from kabusys.research import calc_momentum
  from kabusys.ai import score_news

  duck_conn = duckdb.connect("data/kabusys.duckdb")
  # calc_momentum の例
  mom = calc_momentum(duck_conn, date(2026, 4, 1))

  # ai.score_news の例（OpenAI API キーを環境変数に設定しておく）
  duck_conn = duckdb.connect("data/kabusys.duckdb")
  n = score_news(duck_conn, date(2026, 4, 1), api_key=None)  # None → 環境変数 OPENAI_API_KEY を使用
  ```

---

## 停止／Kill Switch の仕組み

- ExecutionEngine の停止は主に flag ファイル（data/kill.flag または data/stop_requested.flag）によって行います。
- Monitoring は指定の停止フラグファイル（run_monitoring 内では data/stop_requested.flag）を検知するとループを終了します。
- KillSwitch は RiskMonitor 等の監視結果に基づき `data/kill.flag` を書き込み、ExecutionEngine に停止を促します。
- ExecutionEngine は起動時に kill.flag を自動クリアする設定（KILL_FLAG_CLEAR_ON_START=1）を選択可能ですが、本番では 0 を推奨します。

---

## ロギング

- 共通ロギングユーティリティ `kabusys.utils.logging_setup.setup_logging()` を各起動スクリプトで使用しています。
- デフォルトはコンソール出力（stdout）と logs/<app_name>.log への日次ローテーション出力（30日分保持）。
- ログ出力先は環境変数 `LOG_DIR` で変更できます。

---

## ディレクトリ構成（主要）

- src/kabusys/
  - __init__.py
  - config.py, config_setup.py, validate_config.py
  - run_execution.py
  - run_monitoring.py
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - trade_monitor.py (存在)
    - alert_manager.py (存在)
  - execution/ (発注・注文管理関連)
    - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - data/ (runtime に生成される想定ディレクトリ: DB ファイル・PID・フラグ等)

（上記はソース内で参照される主なファイル群を抜粋しています）

---

## 開発上の注意点 / 運用メモ

- Paper Trading:
  - KABUSYS_ENV=paper_trading の場合、ExecutionEngine は settings.paper_sqlite_path を使用して本番 DB と分離します。
  - paper_trading 用の振る舞い（MockBrokerClient の挙動等）は実装によるため、テスト前に設定を確認してください。

- データ鮮度とルックアヘッド:
  - 研究・AI モジュールは「ルックアヘッドバイアス」を避ける設計（target_date 未満のみ利用など）になっていますが、呼び出し方次第でバイアスが入ります。利用時はドキュメントを確認してください。

- DB マイグレーション的処理:
  - monitoring_db.init_monitoring_db() は既存 DB に対して必要なカラム追加（ALTER TABLE）を行います。バックアップを推奨します。

- OpenAI:
  - OPENAI_API_KEY が未設定だと ai モジュールは例外を投げます（呼び出し側でキャッチするか .env に設定してください）。
  - API 呼び出しはリトライやフォールバックを備えていますが、料金やレート制限に注意してください。

---

必要に応じて README を拡張します。特に以下の情報があれば追記できます:
- requirements.txt（厳密な依存リスト）
- 起動／監視運用手順（systemd / Supervisor / cron 用の例）
- テスト方法（ユニットテスト・統合テストの手順）
- 詳細なアーキテクチャ図や API シーケンス図

追加で含めたい内容や出力形式（英語版 README、リリース手順等）があれば教えてください。