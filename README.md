# KabuSys

日本株向け自動売買システムのモジュール群。トレード実行・監視・リサーチ・ポートフォリオ構築・AI（ニュース・レジーム判定）などの機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は、日本株自動売買に必要なコンポーネントをライブラリ／起動スクリプトとしてまとめたコードベースです。主な役割は以下の通りです。

- ExecutionEngine（発注・注文管理・リスク管理）
- Monitoring（システム状態・注文・リスクの定期監視とアラート/Kill Switch）
- Research（ファクター計算、将来リターン、IC 計算など）
- Portfolio（候補選定・重み付け・ポジションサイジング・セクター制限）
- AI（ニュース NLP によるセンチメント評価、レジーム判定）
- ユーティリティ（設定管理、ログ設定、プロセス優先度設定、各種ツール）

設計上の特徴:
- 設定は .env ファイル / 環境変数で管理（自動ロード機能あり）
- Paper Trading と Live を分離（paper_trading は専用 SQLite）
- DuckDB をデータ解析用 DB として利用
- OpenAI API（gpt-4o-mini）を用いたニュースセンチメント / レジーム判定機能（オプション）

---

## 主な機能一覧

- 起動スクリプト
  - monitoring: システム・注文・リスクのポーリング（run_monitoring.py）
  - execution: 実行エンジン起動（run_execution.py）
  - 設定ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
- 監視
  - system_status / trade_logs / risk_logs / dashboard 等の永続化（SQLite）
  - Kill Switch（drawdown・ポジション上限で停止フラグを出力）
  - アラート送信インフラ（LINE 等を想定）
- Execution（エンジン）
  - Broker クライアント抽象化（実ブローカ or Mock）
  - Order Manager / Risk Manager / Reconciler
  - Paper Trading 用 DB 分離（data/paper_trading.db）
- Research / Portfolio
  - ファクター計算（Momentum, Volatility, Value）
  - Forward returns / IC / 統計サマリ
  - 候補選定、重み付け、ポジションサイジング、セクターキャップ、レジーム乗数
- AI モジュール（任意）
  - ニュース NLP（OpenAI で銘柄ごとにセンチメントを算出）
  - レジーム判定（ETF の MA とマクロニュースを合成）
- ツール
  - Paper Trading の検証レポート生成スクリプト

---

## 前提条件

- Python 3.8+（型注釈から 3.8 以降を想定）
- 必要な主要ライブラリ（例）:
  - duckdb
  - psutil
  - openai (AI機能を使う場合)
  - PyYAML（設定検証時に YAML を検証したい場合）
- SQLite（Python 標準ライブラリ sqlite3 を利用）

依存関係はプロジェクトに `requirements.txt` があればそちらを利用してください。なければ上記パッケージを pip でインストールしてください。

例:
```
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローン/展開
2. 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```
3. 依存ライブラリをインストール
   ```
   pip install -r requirements.txt   # requirements.txt がある場合
   ```
   または必要なパッケージを個別にインストール（上記参照）。
4. .env ファイルを作成
   - 対話式ウィザードを利用する:
     ```
     python -m kabusys.config_setup
     ```
     ウィザードは .env（デフォルト）を生成・更新します。
   - 既存の .env を手動で作成する場合は `.env.example` を参照してください（ない場合は README の「環境変数」欄を参照）。

5. 設定検証（任意）
   ```
   python -m kabusys.validate_config
   ```
   問題がある場合、`--strict` を付けると警告も失敗扱いになります。

---

## 環境変数（主要）

Settings クラスで参照される主な環境変数（必須は注記）:

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意／デフォルト有り:
- KABUSYS_ENV: 実行環境。`development`（デフォルト） / `paper_trading` / `live`
- LOG_LEVEL: ログレベル（例: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（monitoring）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の fill モード（instant|partial|never|reject）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を利用する場合）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知設定（任意）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（"0"/"1"、デフォルト 0）
- MONITOR_POLL_INTERVAL: monitoring のポーリング間隔（秒、デフォルト 60）

注意:
- 自動 .env ロードはデフォルトで有効。無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 実行方法

各スクリプトはモジュール実行可能です（プロジェクトルートから実行することを想定）。

- 監視ループ（SystemMonitor のポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  オプション:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書きできます（デフォルト 60 秒）。
  - 停止はプロジェクトルート配下 `data/stop_requested.flag` を作成すると検知して終了します。

- 実行エンジン（ExecutionEngine）
  ```
  python -m kabusys.run_execution
  ```
  特記事項:
  - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient が利用され、paper trading 用 DB（PAPER_TRADING_SQLITE_PATH、デフォルト: data/paper_trading.db）に記録されます。本番 DB と完全に分離されます。
  - 実行中に停止させたい場合は `data/stop_requested.flag` を作成します。run_execution は `data/execution.pid`（デフォルト）を使用します。

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  デフォルト DB は `data/paper_trading.db`。`--db` でパス指定可。

ログ:
- デフォルトのログディレクトリは `logs/`、ログファイルは `<app_name>.log`（例: logs/monitoring.log, logs/execution.log）です。ログ設定は `kabusys.utils.logging_setup.setup_logging` で統一的に行われます。

---

## ツールとユーティリティ

- `kabusys.config_setup` : .env の対話式作成/更新
- `kabusys.validate_config` : 起動前の設定検証（必須環境変数や YAML ファイルの存在チェック）
- `kabusys.tools.paper_verification_report` : ペーパートレード実行の検証用レポート生成
- `kabusys.utils.process_priority` : プロセス優先度 / CPU affinity 設定ユーティリティ
- `kabusys.utils.logging_setup` : 全体のログ設定を統一

---

## ディレクトリ構成（主要ファイル）

以下は `src/kabusys` 以下の主要モジュール構成（抜粋）です。

- kabusys/
  - __init__.py
  - config.py                   # 環境設定読み込み・Settings
  - config_setup.py             # .env 対話式ウィザード
  - validate_config.py          # 設定検証 CLI
  - run_monitoring.py           # SystemMonitor ポーリング起動スクリプト
  - run_execution.py            # ExecutionEngine 起動スクリプト
  - monitoring/
    - monitoring_db.py          # SQLite 永続化層
    - system_monitor.py         # システム状態・データ鮮度監視
    - trade_monitor.py          # （注文滞留・約定異常などの監視）※実装参照
    - risk_monitor.py           # ドローダウン・ポジション制限監視
    - kill_switch.py            # kill.flag 管理
    - monitoring_engine.py      # 各 Monitor を束ねる
    - alert_manager.py          # （アラート送信管理）※実装参照
  - execution/
    - execution_engine.py       # ExecutionEngine 本体（発注ループ）
    - broker_factory.py         # Broker クライアント生成（Mock or 実ブローカ）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py      # 候補選定・重み計算
    - position_sizing.py        # 発注株数計算・スケーリング
    - risk_adjustment.py        # セクターキャップ・レジーム乗数
  - research/
    - factor_research.py        # ファクター計算（momentum, value, volatility）
    - feature_exploration.py    # forward returns, IC, stats
  - ai/
    - news_nlp.py               # ニュース NLP（OpenAI 経由）
    - regime_detector.py        # レジーム判定（MA + マクロニュース）
  - data/                       # データ / DB の既定パス（実行時に作成）
  - logs/                       # ログ出力先（デフォルト）

※一部ファイルは本ドキュメント作成時点の抜粋であり、実際のリポジトリ内にさらに実装ファイルが存在します。

---

## 重要な設計・運用上の注意

- KABUSYS_ENV を `live` にすると本番モードになります。設定ミスによる誤発注を避けるため、`validate_config` で設定を十分に検証してください。
- Paper Trading は本番 DB と分離されています。paper_trading で実行していることを必ず確認してください（PAPER_TRADING_SQLITE_PATH を確認）。
- Kill Switch（data/kill.flag）は本番での緊急停止用の仕組みです。`KILL_FLAG_CLEAR_ON_START=1` を本番で設定するのは危険です（デフォルト 0 推奨）。
- AI 機能を利用する場合は OpenAI API キー（OPENAI_API_KEY）が必要です。料金・レイテンシ・API エラーへの耐性を考慮してください。AI 呼び出しはリトライ・フォールバック設計が組み込まれていますが、失敗時は安全側の挙動（0.0 フォールバック等）になります。
- ログディレクトリの作成に失敗した場合はコンソール出力のみになります。`LOG_DIR` 環境変数で変更可能です。
- プロセス優先度設定は OS に依存します。psutil による設定が失敗した場合は警告になりますが、実行は継続します。

---

## よく使うコマンドまとめ

- .env の作成:
  ```
  python -m kabusys.config_setup
  ```
- 設定検証:
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```
- 監視開始:
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
- 実行エンジン起動:
  ```
  python -m kabusys.run_execution
  ```
- Paper Trading 検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

もし README に追記したい部分（例: 実際の依存パッケージ一覧、設定例の .env テンプレート、より詳細なディレクトリツリーなど）があれば教えてください。必要に応じてサンプル .env や運用手順（systemd ユニット例、Docker 化の説明）も作成します。