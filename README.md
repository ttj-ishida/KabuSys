# KabuSys

日本株向け自動売買システムの参考実装 (KabuSys)。  
この README はリポジトリ内の主要スクリプト・モジュールに基づき、セットアップと基本的な使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買／研究パイプラインを想定したモジュール群です。主な目的は以下のとおりです。

- 戦略用のファクター計算・特徴量解析（DuckDB を使用）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- 実行（ExecutionEngine）と監視（Monitoring）
- Paper Trading（本番と分離された DB を使用）および検証レポート生成
- ニュースを使った NLP（OpenAI APIを利用したセンチメント評価）および市場レジーム判定
- 環境設定 (.env) ウィザードと起動前の設定検証ツール

設計方針として「本番 DB と paper_trading の明確な分離」「ルックアヘッドバイアスの防止」「フェイルセーフ（API失敗時は安全側にフォールバック）」などに配慮しています。

---

## 主な機能一覧

- 環境設定ウィザード: `python -m kabusys.config_setup`
- 設定検証 CLI: `python -m kabusys.validate_config`
- 実行エンジン起動スクリプト: `python -m kabusys.run_execution`
  - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、paper DB（既定: `data/paper_trading.db`）へ記録
- 監視 (Monitoring) 起動スクリプト: `python -m kabusys.run_monitoring`
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）
  - 監視は環境にかかわらず監視用 sqlite（既定: `data/monitoring.db`）を使用
- Paper Trading 検証レポート生成: `python -m kabusys.tools.paper_verification_report`
- ファクター計算・リサーチモジュール（DuckDB 利用）
- AI モジュール:
  - ニュースセンチメント評価 (`kabusys.ai.score_news`) — OpenAI API 必須
  - 市場レジーム判定 (`kabusys.ai.regime_detector.score_regime`) — OpenAI API 必須
- ログ設定ユーティリティ（コンソール + 日次ローテートファイル）
- プロセス優先度 / CPU アフィニティユーティリティ
- Kill Switch（`data/kill.flag`）による ExecutionEngine 停止制御

---

## セットアップ手順（開発・ローカル向け）

1. Python 環境の作成（推奨: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

2. 必要なパッケージをインストール  
   リポジトリに requirements.txt がある場合:
   ```
   pip install -r requirements.txt
   ```
   ※ このコードベースで使用される主な外部ライブラリ:
   - duckdb
   - psutil
   - openai
   - PyYAML（config 検証で任意）
   - その他（用途に応じて）

3. .env の作成（対話式ウィザード推奨）
   ```
   python -m kabusys.config_setup
   ```
   ウィザードは `.env`（デフォルト）を生成/更新します。`.env` は絶対にバージョン管理にコミットしないでください。

4. 設定検証
   ```
   python -m kabusys.validate_config
   ```
   `--strict` を付けると警告もエラー扱いになります。

5. データディレクトリの確認（必要なら作成）
   - 既定では `data/` に SQLite / DB / フラグファイル等を格納します。
   - ログは既定で `logs/` に出力されます（`LOG_DIR` で変更可能）。

---

## 環境変数（主要な設定項目とデフォルト）

以下は主に `kabusys.config.Settings` による設定項目です。ウィザードで設定できます。

必須（少なくとも設定が必要）:
- JQUANTS_REFRESH_TOKEN — J-Quants API（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

任意・デフォルト:
- KABUSYS_ENV — 実行環境（development / paper_trading / live）。デフォルト: development
- DUCKDB_PATH — 分析用 DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）。デフォルト: INFO
- LOG_DIR — ログ保存ディレクトリ（デフォルト: logs）
- PID_FILE_PATH — ExecutionEngine の pid ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — Kill Switch ファイル（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag をクリアするか（開発用、デフォルト: 0）
- OPENAI_API_KEY — OpenAI API キー（AI モジュール使用時に必要）
- PAPER_FILL_MODE — paper_trading 時のモック約定モード（instant/partial/never/reject。デフォルト: instant）

監視関連:
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

---

## 使い方（主要コマンド）

- .env の作成（対話式）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン起動
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は paper_trading DB に記録し、MockBrokerClient が使われます。
  - 起動中は `data/execution.pid` を作成します。
  - 停止には `data/stop_requested.flag` を作成するか、プロセスを終了させます。

- 監視（Monitoring）起動
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を変更する例:
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - 監視は `data/monitoring.db`（既定）にログを残します。
  - `data/stop_requested.flag` を配置すると監視ループは終了します。

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パス指定:
    ```
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
    ```

- AI モジュール（プログラム内呼び出し）
  - ニューススコアリング:
    ```py
    from kabusys.ai import score_news
    # duckdb_conn は duckdb.connect(...)
    count = score_news(duckdb_conn, target_date, api_key="sk-...")
    ```
  - レジーム判定:
    ```py
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="sk-...")
    ```
  - 注意: OpenAI API キーは `OPENAI_API_KEY` 環境変数または関数引数で渡す必要があります。

- Kill Switch
  - 監視モジュールが一定のリスク条件（ドローダウンやポジション上限）を検出した場合、`data/kill.flag` を書き込みます。ExecutionEngine は起動時や実行中にこのフラグを参照して安全に停止します。

---

## 停止 / フラグ操作

- 即時停止（手動で）:
  - `data/stop_requested.flag` を作成すると、run_execution と run_monitoring のループが検知して終了します（run_execution は起動時に既に存在する場合は起動を回避します）。
- Kill Switch（自動）:
  - 監視が条件を満たすと `data/kill.flag` を書き込み、ExecutionEngine に停止シグナルを送ります。
- kill.flag を起動時に自動でクリアしたい場合は `.env` の `KILL_FLAG_CLEAR_ON_START=1` を設定できます（ただし本番では通常 0 を推奨）。

---

## ログ

- ログは標準出力（コンソール）とファイル（`<LOG_DIR>/<app_name>.log`）に出力されます。
- デフォルトのログディレクトリ: `logs/`
- ローテーション: 日次、30 日分保持

ログ設定は `kabusys.utils.logging_setup.setup_logging()` を通して統一的に行われます。

---

## ディレクトリ構成（主要）

概略（src/kabusys 以下）:

```
src/kabusys/
├── __init__.py
├── run_execution.py           # ExecutionEngine 起動スクリプト
├── run_monitoring.py         # SystemMonitor ポーリング起動スクリプト
├── config.py                 # 環境変数設定読み込み / Settings
├── config_setup.py           # .env 対話式ウィザード
├── validate_config.py        # 設定検証 CLI
├── utils/
│   ├── __init__.py
│   ├── logging_setup.py      # ログユーティリティ
│   └── process_priority.py   # プロセス優先度 / CPU affinity
├── execution/                # Execution エンジン周り（broker, order_manager 等）
├── monitoring/
│   ├── monitoring_db.py
│   ├── system_monitor.py
│   ├── trade_monitor.py
│   ├── risk_monitor.py
│   ├── kill_switch.py
│   └── monitoring_engine.py
├── portfolio/
│   ├── portfolio_builder.py
│   ├── position_sizing.py
│   └── risk_adjustment.py
├── research/
│   ├── factor_research.py
│   └── feature_exploration.py
├── ai/
│   ├── news_nlp.py
│   └── regime_detector.py
├── monitoring/                # 監視関連（DB / エンジン / モニタ）
└── tools/
    └── paper_verification_report.py
```

（上は抜粋です。実際のファイル一覧はリポジトリを参照してください。）

---

## 開発者向けの補足

- DuckDB は分析用の高速列指向 DB として利用しています。prices_daily / raw_financials / raw_news などのテーブルを想定しています。
- MonitoringDB（SQLite）は監視ログ・トレードログ・ポジション・リスクログ等を記録します。
- Paper Trading と Live は DB を分離して扱うように設計されています（Settings.is_paper フラグで切替）。
- OpenAI API を使う機能は外部 API に依存するため、API の失敗に対するリトライやフォールバックを組み込んでいます（429 / タイムアウト / 5xx など）。
- 一部の機能は PyYAML（config の YAML 検証）に依存しますが必須ではありません（validate_config は未インストール時に YAML 検証をスキップします）。

---

## よくあるトラブルと対処

- .env が正しく読み込まれない場合
  - プロジェクトルートの自動探索が働かないケースがあります。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を用いて自動ロードを抑制しているか確認してください。
  - `python -m kabusys.config_setup` で .env を再生成してください。
- OpenAI 関連で API キーが見つからない/認証エラー
  - `OPENAI_API_KEY` を .env に設定するか、関数呼び出し時に api_key 引数で渡してください。
- モニタリングが動かない/ポーリングされない
  - `MONITOR_POLL_INTERVAL` の値を確認（正の整数であること）。不正値の場合はデフォルト 60 秒にフォールバックします。
- ログファイルが作成されない
  - `LOG_DIR` の書き込み権限を確認してください。ディレクトリ作成に失敗した場合はコンソール出力のみになります。

---

この README はリポジトリ内のコードを参照してまとめています。実装の詳細や追加の利用例は各モジュールの docstring（ソース内のコメント）を参照してください。必要であれば、特定モジュールの詳しい使い方（例: ExecutionEngine の拡張方法や Research の duckdb テーブル構造）も別途記載します。