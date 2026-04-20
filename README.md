# KabuSys

日本株自動売買システム（ライブラリ / 起動スクリプト群）

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買・研究・監視を目的とした Python ベースのコードベースです。  
主なコンポーネント:

- ExecutionEngine: ブローカークライアント経由で発注・注文管理・リスク管理を行う実行エンジン
- Monitoring: システム稼働状況・注文ログ・リスクを監視し、必要に応じて Kill Switch を発動
- Research: DuckDB を用いたファクター計算・特徴量解析ユーティリティ
- Portfolio: 候補選定・重み付け・ポジションサイズ計算などのポートフォリオ構築ロジック
- AI モジュール: ニュース NLP によるセンチメント評価やレジーム判定（OpenAI API）
- ユーティリティ: 設定ウィザード、設定検証、ログ設定、プロセス優先度設定 等
- ツール: ペーパートレード検証レポート生成など

設計方針として、本番 DB とペーパートレード DB の分離、ルックアヘッドバイアス回避、外部 API 呼び出しの失敗に対するフェイルセーフ等を重視しています。

---

## 機能一覧（抜粋）

- 環境設定ウィザード（.env の対話式生成）: `kabusys.config_setup`
- 設定検証 CLI（.env / config/*.yaml の検査）: `kabusys.validate_config`
- ExecutionEngine 起動スクリプト: `kabusys.run_execution`（KABUSYS_ENV により paper_trading モードをサポート）
- Monitoring 起動スクリプト: `kabusys.run_monitoring`（システム・注文・リスク監視）
- Monitoring DB 永続化層（SQLite）: `kabusys.monitoring.monitoring_db`
- Kill Switch（フラグファイルで ExecutionEngine を停止）
- Paper Trading 検証レポート生成ツール: `kabusys.tools.paper_verification_report`
- ファクター計算・特徴量解析（DuckDB ベース）: `kabusys.research.*`
- ニュース NLP（OpenAI を使った銘柄センチメント）: `kabusys.ai.news_nlp`
- 市場レジーム判定（AI + ETF MA を合成）: `kabusys.ai.regime_detector`
- ポートフォリオ構築の純関数群（候補選定・重み付け・位置決め）: `kabusys.portfolio.*`
- ログ設定ユーティリティ、プロセス優先度/CPU affinity ユーティリティ

---

## 前提 / 依存関係

- Python 3.10+
- 必須ライブラリ（実行する機能により異なる）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config/*.yaml の内容検証を行う場合、必須ではない）
- 標準ライブラリ: sqlite3, threading, logging 等

インストール例（仮の requirements）:
```bash
python -m pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順

1. リポジトリを取得して作業ディレクトリに移動します。

2. Python 仮想環境を作成・有効化（推奨）:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux / macOS
   .venv\Scripts\activate     # Windows
   ```

3. 必要なパッケージをインストール:
   ```bash
   python -m pip install --upgrade pip
   python -m pip install duckdb psutil openai pyyaml
   ```

4. 環境変数（.env）を作成:
   - 対話式ウィザードを使う:
     ```bash
     python -m kabusys.config_setup
     ```
   - あるいは `.env` を手動作成。重要な環境変数:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH（必要に応じて）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LOG_LEVEL（例: INFO）

   自動ロードについて:
   - デフォルトでプロジェクトルート（.git または pyproject.toml がある場所）から `.env` と `.env.local` を自動読み込みします。
   - 自動読み込みを無効化する場合: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

5. 設定検証（起動前に推奨）:
   ```bash
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict  # 警告も失敗扱いにする
   ```

6. データディレクトリ等の作成:
   - デフォルトでは `data/`、`logs/` が使われます。必要なら事前に作成してください。ログディレクトリは `LOG_DIR` で変更可能。

---

## 使い方

基本的に Python モジュールを直接実行します。

- Monitoring の起動:
  - ポーリングループを開始します。環境変数 `MONITOR_POLL_INTERVAL`（秒）で間隔を上書き可能（デフォルト 60 秒）。
  ```bash
  python -m kabusys.run_monitoring
  ```
  停止方法:
  - プロジェクトルートの `data/stop_requested.flag` ファイルを作成するとループが検出して終了します。

- ExecutionEngine の起動:
  - 本番/ペーパーは `KABUSYS_ENV` に従います。`paper_trading` の場合は MockBroker を使用し `data/paper_trading.db` に記録します。
  ```bash
  python -m kabusys.run_execution
  ```
  停止方法:
  - `data/stop_requested.flag` を作成するとエンジンに検知され停止処理が走ります。
  - 実行中は `data/execution.pid` に PID が書かれます。

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
  python -m kabusys.tools.paper_verification_report
  # 期間指定や DB パス指定:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
  ```

- AI 関連（プログラム的に利用）:
  - ニューススコア付与:
    - 関数: `kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)`
  - レジーム判定:
    - 関数: `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)`

注意点:
- Monitoring は環境にかかわらず本番の `SQLITE_PATH` を使用して監視ログを記録します（設計上の仕様）。
- Execution は `KABUSYS_ENV=paper_trading` のとき専用の `PAPER_TRADING_SQLITE_PATH` を使用して本番 DB と分離します。
- Kill Switch: `data/kill.flag` を書き込むことで ExecutionEngine に対して停止シグナルを送れます（Monitoring のリスク判定等から自動で書き込まれます）。

環境変数の主要例:
- KABUSYS_ENV=development | paper_trading | live
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- OPENAI_API_KEY=...
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- LOG_LEVEL=INFO
- MONITOR_POLL_INTERVAL=30

---

## ログ・プロセス管理

- ロギング: `kabusys.utils.logging_setup.setup_logging(app_name="...")` を各起動スクリプトが使用します。
  - コンソール（stdout）と日次ローテートファイル（logs/<app_name>.log）に出力されます。
  - ログディレクトリは環境変数 `LOG_DIR` または引数で変更可能。
- プロセス優先度: 起動時に `kabusys.utils.process_priority.set_process_priority("high")` を呼び出し優先度を上げます（権限により失敗する場合は警告）。

---

## フラグファイル・PID の扱い

- 停止要求（外部）:
  - data/stop_requested.flag — このファイルが存在すると monitoring / execution のループが停止します（起動前に存在する場合は起動を抑止することがあります）。
- Kill Switch:
  - data/kill.flag — KillSwitch が条件を満たした際に書き込まれ、Execution 停止の強制トリガーとなります。
  - KillSwitch は冪等（既に存在する場合は再書き込みしない）です。
- PID ファイル:
  - `data/execution.pid` 等に PID を書きます（ExecutionEngine が使用）。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理（自動 .env ロード等）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_monitoring.py        — Monitoring の起動スクリプト
  - run_execution.py         — ExecutionEngine の起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）による銘柄スコアリング
    - regime_detector.py     — 市場レジーム判定（AI + MA）
  - monitoring/
    - monitoring_db.py       — SQLite ベースの監視ログ永続化
    - system_monitor.py      — システム稼働 / データ鮮度チェック
    - trade_monitor.py       — （注文ログ監視）※詳細実装ファイルがある想定
    - risk_monitor.py        — ドローダウン / ポジション数監視
    - kill_switch.py         — Kill Switch 実装（フラグファイル書込）
    - monitoring_engine.py   — 監視用エンジン（複数モニタ束ねる）
    - alert_manager.py       — （アラート送信管理）※実装想定
  - execution/
    - execution_engine.py    — ExecutionEngine 本体（run_session 等）
    - broker_factory.py      — ブローカークライアント生成
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - ...                    — 実行周りの補助モジュール
  - portfolio/
    - portfolio_builder.py   — 候補選定、重み付け
    - position_sizing.py     — 発注株数算出、スケールダウンロジック
    - risk_adjustment.py     — セクター上限、レジーム乗数
  - research/
    - factor_research.py     — 各ファクター計算（momentum / value / volatility）
    - feature_exploration.py — IC などの解析ユーティリティ
  - utils/
    - logging_setup.py       — 共通ロギング設定
    - process_priority.py    — 優先度 / CPU affinity 設定
    - ...                    — その他ユーティルティ

その他:
- data/                    — デフォルトの DB / フラグ / PID 等（実行時に作成）
- logs/                    — 日次ローテートログ出力先（デフォルト）

---

## 開発 / 貢献メモ

- 単体テストやモック化を容易にするため、AI 呼び出し部分（_call_openai_api など）は差し替え可能に設計されています（unittest.mock を使用）。
- DuckDB 接続を受け取る関数が多く、ローカルでの高速集計・研究に適しています。
- 本番環境（KABUSYS_ENV=live）では LINE 通知や Kill Switch の扱いに注意してください。`validate_config` の live 専用ガードを参照してください。

---

以上がこのコードベースの README です。必要であれば各コンポーネント（ExecutionEngine の API、TradeMonitor の詳細、AlertManager の送信先など）について別途詳しいドキュメントを作成します。どの部分を優先しましょうか？