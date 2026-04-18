# KabuSys

日本株向け自動売買システムのライブラリ / 実行スクリプト群の README。

このリポジトリは戦略計算、発注エンジン、監視、AI ベースのニュース評価、検証ツール等を含む小規模なトレーディング基盤を提供します。

---

## 概要

KabuSys は以下のコンポーネントを提供します。

- ExecutionEngine: 発注・注文管理・リスク管理を行う実行エンジン（paper_trading モードで仮想発注が可能）
- Monitoring: システム状態・注文状態・リスク指標を定期的に監視し、kill flag を発行して実行エンジンを停止できる
- Portfolio: 銘柄選定・重みづけ・株数算出などのポートフォリオ構築ロジック
- Research: DuckDB 上の株価・財務データに基づくファクター計算・特徴量探索
- AI: OpenAI を用いたニュース NLP（銘柄毎のセンチメント付与）と市場レジーム判定
- 管理ツール: .env ウィザード、設定検証、Paper Trading 検証レポート生成等

設計方針として「本番 DB と Paper Trading は分離」「ルックアヘッドバイアスを避ける」「外部 API 呼び出しは明示的に制御する」「冪等性を意識した DB 操作」を重視しています。

---

## 主な機能一覧

- Execution
  - 本番 / ペーパートレード切替（`KABUSYS_ENV`）
  - リスク管理（ポジション上限、ドローダウン等）
  - OrderManager / Reconciler による注文管理
- Monitoring
  - CPU / メモリ / ディスク使用率の記録
  - データ鮮度チェック（DuckDB の prices_daily）
  - 滞留注文・約定異常の検出
  - KillSwitch: 条件に基づいて `data/kill.flag` を書き込み ExecutionEngine を停止
- Portfolio
  - 候補選定、等金額・スコア加重配分、リスクベースポジションサイズ算出
  - セクターキャップ、レジーム乗数の適用
- Research
  - Momentum / Volatility / Value ファクター計算
  - 将来リターン・IC（情報係数）計算、統計サマリ
- AI
  - ニュースを LLM（gpt-4o-mini 相当）で評価して ai_scores に書き込み
  - マクロニュース + ETF MA200 を用いた市場レジーム判定
- 管理・運用
  - `.env` 対話式ウィザード（`kabusys.config_setup`）
  - 起動前チェック（`kabusys.validate_config`）
  - Paper Trading 検証レポート生成（`kabusys.tools.paper_verification_report`）

---

## 必要要件

少なくとも次のパッケージが必要です（実行環境によって可変）:

- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（設定 YAML の検証を行う場合）

インストール例:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

（実プロジェクトでは requirements.txt を用意して管理してください）

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化する。
2. 依存パッケージをインストールする（上記参照）。
3. `.env` を作成する（対話式ウィザード推奨）:

   ```bash
   python -m kabusys.config_setup
   ```

   生成される `.env` は絶対にコミットしないでください。

4. 設定検証を実行（起動前チェック）:

   ```bash
   python -m kabusys.validate_config
   # 警告も失敗にする場合（本番チェック）:
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリ（`data/`）やログディレクトリ（`logs/`）は自動的に作成されますが、権限等で失敗する場合は手動作成してください。

---

## 主要な環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: `development` | `paper_trading` | `live`（デフォルト: development）
  - `paper_trading` のとき ExecutionEngine は MockBroker を使用し、paper 用 SQLite に書き込む
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading の DB、デフォルト: data/paper_trading.db）
- OPENAI_API_KEY（AI 機能を使う場合に必要）
- LOG_LEVEL（デフォルト: INFO）
- LOG_DIR（デフォルト: logs/）
- MONITOR_POLL_INTERVAL（監視ループのポーリング間隔秒、デフォルト: 60）
- PAPER_FILL_MODE（paper_trading の約定挙動: `instant` | `partial` | `never` | `reject`）
- KILL_FLAG_CLEAR_ON_START（本番での自動クリアを避ける: 0 推奨）

例（`.env` 断片）:

```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...
KILL_FLAG_CLEAR_ON_START=0
```

---

## 起動 / 使い方

各スクリプトはパッケージとしてモジュール実行できます（推奨）。

- ExecutionEngine を起動

  - 通常起動:

    ```bash
    python -m kabusys.run_execution
    ```

  - 注意:
    - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を使い `data/paper_trading.db` に記録します（本番 DB とは分離）。
    - 起動前に `data/stop_requested.flag` が存在すると起動せず終了します。
    - エンジンは `data/execution.pid` を作成します。停止は `data/stop_requested.flag` を作成するか KillSwitch により `data/kill.flag` が作られた場合に行われます。

- Monitoring を起動

  ```bash
  # ポーリング間隔を環境変数で上書き（秒）
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

  - Monitoring は監視ログ用の SQLite（`SQLITE_PATH`）に接続し、データ鮮度やプロセス状態を定期記録します。
  - 既定のポーリング間隔は 60 秒です。
  - 停止は `data/stop_requested.flag` を作成するか Ctrl+C。

- .env ウィザード（対話形式）

  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証

  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Paper Trading 検証レポート生成

  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB 指定
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 機能（プログラムから呼ぶ）
  - ニュース評価: `kabusys.ai.news_nlp.score_news(duckdb_conn, target_date, api_key=None)`
  - レジーム判定: `kabusys.ai.regime_detector.score_regime(duckdb_conn, target_date, api_key=None)`
  - どちらも `OPENAI_API_KEY` を環境変数で設定しておくか、関数引数で渡します。

---

## 停止・Kill フラグの取り扱い

- 停止フラグ（強制停止要求）
  - ファイル: data/stop_requested.flag
  - run_execution.py / run_monitoring.py はこのファイルの存在をチェックして処理を終了します。
  - 外部から起動スクリプトを穏やかに停止させたい場合に作成します。

- KillSwitch（自動停止トリガ）
  - ファイル: data/kill.flag
  - Monitoring の KillSwitch が条件を満たした場合に書き込み、ExecutionEngine を停止させるために使用します。
  - `KILL_FLAG_CLEAR_ON_START` を 1 にすると起動時に kill.flag を自動クリアしますが、本番では 0 を推奨します。

---

## ロギング・データベース

- ログ
  - デフォルト出力先: logs/<app_name>.log（TimedRotatingFileHandler、日次ローテーション、30 日保持）
  - stdout にも出力されます（StreamHandler）。

- データベース
  - DuckDB（分析用）: `DUCKDB_PATH`（デフォルト: data/kabusys.duckdb）
  - SQLite（監視用）: `SQLITE_PATH`（デフォルト: data/monitoring.db）
  - Paper Trading SQLite（分離）: `PAPER_TRADING_SQLITE_PATH`（paper_trading 時に使用）
  - 監視 DB のスキーマは MonitoringDB.init_monitoring_db() で自動作成・マイグレーションされます。

---

## ディレクトリ構成（主なファイル）

src/kabusys/
- __init__.py
- config.py — 環境変数 / 設定読み込みロジック（.env 自動ロード）
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 起動前設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor 起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py — ニュース NLP（OpenAI）
  - regime_detector.py — 市場レジーム判定（LLM + ETF MA）
- monitoring/
  - monitoring_db.py — SQLite 永続化層
  - system_monitor.py — システム監視
  - trade_monitor.py — 注文監視（省略）
  - risk_monitor.py — ドローダウン／ポジション上限監視
  - kill_switch.py — kill.flag 操作
  - monitoring_engine.py — 各 Monitor を束ねる
  - alert_manager.py — 通知（LINE 等、実装に依存）
- execution/ (発注関連コンポーネント)
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
  - broker_factory.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py
  - process_priority.py

（注: `trade_monitor.py`, `alert_manager.py`, `execution/*` の詳細実装はリポジトリ内の該当ファイルを参照してください）

---

## 運用上の注意 / トラブルシューティング

- 本番運用時は `KABUSYS_ENV=live` を設定し、`.env` の内容を慎重に管理してください（`validate_config` が警告を出します）。
- `KILL_FLAG_CLEAR_ON_START=1` は本番で危険です（kill.flag が自動クリアされる）。本番は `0` を推奨。
- DuckDB / SQLite のファイルパスは適切なディスク容量と権限のある場所を指定してください。
- ログディレクトリや data ディレクトリの作成に失敗した場合、ログはコンソール出力のみになります。権限設定を確認してください。
- OpenAI API を使用する際はレート制限や課金に注意してください。ネットワークエラーや 5xx は内部でリトライされますが、上限に達すると処理はスキップされます。
- `psutil` によるプロセス優先度設定や CPU affinity の操作は管理者権限を要する場合があります。失敗しても警告に留まり処理は続行されます。

---

## 参考コマンド一覧（まとめ）

- 仮想環境作成・依存インストール

  ```bash
  python -m venv .venv
  source .venv/bin/activate
  pip install duckdb psutil openai pyyaml
  ```

- .env ウィザード（対話式）

  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証

  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Execution Engine 起動

  ```bash
  python -m kabusys.run_execution
  ```

- Monitoring 起動（ポーリング間隔を 30 秒に設定する例）

  ```bash
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- Paper Trading 検証レポート

  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

README はここまでです。実装の詳細や各モジュールの使い方はソースコードの docstring / 関数コメントを参照してください。質問やドキュメント補足の希望があれば教えてください。