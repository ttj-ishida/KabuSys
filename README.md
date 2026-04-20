# KabuSys

日本株向け自動売買システムのコアライブラリ群（スクリプト群）。
このリポジトリは、発注エンジン（ExecutionEngine）、監視（Monitoring）、
ポートフォリオ構築、ファクター研究、AI ベースのニュース解析などの
主要コンポーネントを含みます。

---

## 概要

KabuSys は以下の目的を持つモジュール群を提供します。

- 自動発注エンジン（ExecutionEngine）と注文管理
- 監視サブシステム（System / Trade / Risk の監視、Kill Switch）
- ポートフォリオ構築（候補選定・重み算出・ポジションサイズ計算）
- リサーチ（ファクター計算・特徴量探索）
- AI モジュール（ニュースのセンチメント解析、レジーム判定）
- 運用ユーティリティ（.env ウィザード、設定検証、ペーパートレード検証レポート）

この README はリポジトリ内の主要スクリプトの使い方、設定、ディレクトリ構成をまとめたものです。

---

## 主な機能一覧

- Execution
  - ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - paper_trading モードでは MockBroker を使用し、本番 DB から分離された `data/paper_trading.db` を使用
- Monitoring
  - System / Trade / Risk の監視とログ永続化（SQLite）
  - Kill Switch（条件により `data/kill.flag` を書き込み ExecutionEngine を停止）
  - 監視ループ起動スクリプト（python -m kabusys.run_monitoring）
  - 監視 DB 初期化ユーティリティ
- Portfolio
  - 候補選定（score-based / equal）
  - 重み計算、セクター制限、レジーム乗数、ポジションサイズ計算
- Research
  - ファクター計算（モメンタム・ボラティリティ・バリュー）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- AI
  - ニュース NLP（OpenAI を用いた銘柄センチメントの算出・ai_scores への格納）
  - レジーム判定（ETF MA200 とマクロニュースを合成）
- Tools
  - .env 対話式ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
  - Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）

---

## セットアップ手順

前提:
- Python 3.10 以上（typing の `X | Y` 構文を使用）
- SQLite（標準ライブラリ）
- いくつかのサードパーティライブラリが必要

1. 仮想環境を作成・有効化（任意）:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

2. 必要パッケージをインストール:
   （requirements.txt がないため主要依存を手動で列挙）
   ```bash
   pip install duckdb psutil openai
   # オプション: YAML 設定ファイル検証に PyYAML を使う
   pip install PyYAML
   ```

3. プロジェクトルートに `data/` および `logs/` ディレクトリを作成（多くの処理が自動作成するが手動で用意すると確実）:
   ```bash
   mkdir -p data logs
   ```

4. 初期環境変数設定（.env）の作成:
   - 対話式ウィザードを使う:
     ```bash
     python -m kabusys.config_setup
     ```
   - あるいは `.env` を手動で作成してください（例は下記）。

5. 設定検証:
   ```bash
   python -m kabusys.validate_config
   # 警告も FAIL にしたい場合:
   python -m kabusys.validate_config --strict
   ```

必須環境変数（最低限設定が必要なもの）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

重要な環境変数（よく使うもの）
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（paper_trading モードで使用）
- LOG_LEVEL: ログレベル（INFO 等）
- LOG_DIR: ログの出力先ディレクトリ（デフォルト: logs/）
- KILL_FLAG_CLEAR_ON_START: 起動時 kill.flag を自動クリア（1: 有効、0: 無効、デフォルト 0 推奨）

.env の簡易例:
```env
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
```

注意: `.env` は決して git にコミットしないでください（ウィザードにも表記あり）。

---

## 使い方

主要なスクリプト／CLI の起動方法:

- 環境設定ウィザード（.env の対話式生成）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- 監視ループ起動（SystemMonitor のポーリング）
  - 標準 polling 間隔は 60 秒。環境変数で上書き可:
    ```bash
    export MONITOR_POLL_INTERVAL=30
    python -m kabusys.run_monitoring
    ```
  - run_monitoring は常に Settings.sqlite_path（本番監視 DB）を使用します（KABUSYS_ENV に依存しない点に注意）。

- ExecutionEngine 起動（発注エンジン）
  ```bash
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し `data/paper_trading.db` に記録して本番 DB と分離します。
  - 実行中のプロセス優先度を「high」に設定します（set_process_priority を利用）。

- Paper Trading 検証レポート
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB は `data/paper_trading.db`。`--db` オプションや環境変数 `PAPER_TRADING_SQLITE_PATH` で指定可能。

- AI モジュール（ニューススコア付与）
  - プログラム的に呼ぶ:
    ```py
    from kabusys.ai import score_news
    # conn: duckdb connection, target_date: datetime.date, api_key: str | None
    count = score_news(conn, target_date, api_key="sk-...")
    ```
  - OpenAI API キー（OPENAI_API_KEY）を必ず設定してください。API 呼び出しで課金されます。

停止・再起動に関する運用フラグ:
- 停止フラグ: `data/stop_requested.flag`（run_monitoring/run_execution が参照）
- Kill Switch: `data/kill.flag`（監視が条件に応じて書き込み、ExecutionEngine に停止シグナルを送る）
- ExecutionEngine の PID ファイル: `data/execution.pid`（デフォルト）

ログ:
- ログは `logs/<app_name>.log`（日次ローテーション、30 日保持）に出ます。
- コンソール出力は stdout に送られます（cron / systemd からの実行に配慮）。

---

## 重要な挙動の補足

- run_monitoring のポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能。デフォルト 60 秒。整数かつ >=1 を期待する。無効値の場合はデフォルトにフォールバックします。
- run_monitoring は KABUSYS_ENV にかかわらず Settings.sqlite_path（本番の monitoring DB）を使用します。監視ログは本番 DB に記録されます。
- run_execution は KABUSYS_ENV=paper_trading の場合 `paper_sqlite_path`（デフォルト `data/paper_trading.db`）を使用して本番 DB と分離します。
- AI 関連機能は OpenAI API を利用します。大量 API 呼び出しはコストが発生するため注意してください。API のリトライやフェイルセーフは実装されていますが、キーは必須です。
- validate_config は `.env` ファイルと `config/*.yaml`（任意）をチェックします。PyYAML が無い場合、YAML 内容チェックはスキップされます。
- ロギングセットアップ（kabusys.utils.logging_setup）により、全スクリプトで統一ログ管理が行われます。ログディレクトリ作成に失敗するとファイル出力は無効化され、コンソールのみでログを出力します。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数/.env 自動読み込み、Settings クラス
  - config_setup.py
    - .env 対話式ウィザード
  - validate_config.py
    - 起動前設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
      - Paper Trading 検証レポート生成
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュースの OpenAI によるスコアリング
    - regime_detector.py
      - 市場レジーム判定（MA200 + マクロニュース）
  - monitoring/
    - monitoring_db.py
      - 監視ログ用 SQLite スキーマ初期化・永続化 API
    - system_monitor.py
      - システム状態・データ鮮度監視
    - trade_monitor.py (存在想定: トレード監視)
    - risk_monitor.py
      - ドローダウン・ポジション上限監視
    - kill_switch.py
      - kill.flag の管理
    - monitoring_engine.py
      - 全 Monitor を束ねる実行ループ
    - alert_manager.py (存在想定: 通知管理)
  - execution/
    - broker_factory.py (ブローカークライアント生成)
    - execution_engine.py (ExecutionEngine 本体)
    - order_manager.py / order_repository.py / reconciler.py / risk_manager.py
  - portfolio/
    - portfolio_builder.py
      - 候補選定・重み算出
    - position_sizing.py
      - 株数計算・資金割当
    - risk_adjustment.py
      - セクターキャップ・レジーム乗数
  - research/
    - factor_research.py
      - momentum/value/volatility ファクター計算
    - feature_exploration.py
      - 将来リターン/IC/統計サマリー
  - utils/
    - logging_setup.py
      - 統一ログ設定
    - process_priority.py
      - プロセス優先度 / CPU affinity 設定
  - data/ (実行時に生成されることが多い)
    - monitoring.db (デフォルト)
    - paper_trading.db (paper_trading 時)
    - stop_requested.flag / kill.flag / execution.pid

---

## 運用上の注意点

- 本番環境（KABUSYS_ENV=live）での起動は慎重に行ってください。
  - validate_config の警告を確認し、LINE 通知等の設定を整えてください。
  - KILL_FLAG_CLEAR_ON_START が 1 のままだと Kill Switch が自動クリアされるため本番では 0 を推奨します。
- AI モジュールは外部 API（OpenAI）を使用します。キーの管理やコスト管理に注意してください。
- DB ファイルのバックアップやログローテーションの運用ルールを決めてください（DuckDB / SQLite はファイルベースなのでファイルサイズに注意）。
- set_process_priority は OS 権限が必要な場合があります（特に negative nice 値は root 権限が必要なことがある）。

---

## 開発・テスト

- 各モジュールは可能な限り純粋関数化されており、ユニットテストを書きやすい設計になっています（例: portfolio/、research/ の多くは外部 DB を直接書き換えない）。
- AI 呼び出し部分はテスト時にモック可能なように設計されています（_call_openai_api の差し替えなど）。
- validate_config や config_setup は CI 前に設定検証を自動化する際に便利です。

---

必要があれば README にサンプル .env の完全テンプレート、systemd / cron 用の起動サンプル、Dockerfile/compose の記載、さらに細かな運用手順（バックアップ・リストア・マイグレーション方針等）を追加できます。どの情報を追加したいか教えてください。