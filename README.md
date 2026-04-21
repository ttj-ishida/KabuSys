# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ。  
この README はソースツリー内の主要スクリプト・モジュールに基づいて作成しています。

## プロジェクト概要
KabuSys は、日本株向けの自動売買フレームワークです。  
主な機能は次の通りです。

- 戦略のためのファクター計算・特徴量解析（DuckDB を利用）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ算出）
- ExecutionEngine による発注管理（paper/live 切替対応）
- 監視（System / Trade / Risk）と Kill Switch による自動停止
- ニュース NLP（OpenAI）を用いた銘柄・マクロセンチメント評価
- Paper Trading 検証レポート出力ツール
- 環境設定ウィザード・設定検証 CLI

設計上の留意点：
- DuckDB を分析用 DB、SQLite を監視・発注ログ用に使用
- 本番/ペーパートレードは環境変数 `KABUSYS_ENV` で切替
- AI 関連は OpenAI API を利用（API キー必須、失敗時は安全にフォールバック）

---

## 機能一覧（抜粋）
- kabusys.run_execution: ExecutionEngine 起動スクリプト（paper/live 切替）
- kabusys.run_monitoring: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL）
- kabusys.config_setup: 対話式 .env 生成ウィザード
- kabusys.validate_config: .env / config/*.yaml の起動前検証
- kabusys.tools.paper_verification_report: Paper Trading の検証レポート出力
- kabusys.research: ファクター計算・特徴量解析ユーティリティ
- kabusys.portfolio: ポートフォリオ構築ユーティリティ（選定・配分・リスク調整）
- kabusys.ai: ニュース NLP（score_news）および市場レジーム判定（regime_detector）
- kabusys.monitoring: 監視 DB、各種モニタ、KillSwitch、アラート連係用ロジック
- kabusys.utils: ロギング設定、プロセス優先度 / CPU affinity 設定 など

---

## 前提 / 依存ライブラリ（主なもの）
- Python 3.9+
- duckdb
- psutil
- openai （AI 機能利用時）
- PyYAML（`validate_config` の YAML 検証に任意で使用）
- 標準ライブラリ: sqlite3, logging, threading, datetime など

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```
（プロジェクトに requirements.txt がある場合はそちらを利用してください）

---

## セットアップ手順（初回）
1. リポジトリをクローンし、仮想環境を作成・有効化する。
2. 依存ライブラリをインストールする（上記参照）。
3. 対話式ウィザードで `.env` を作成する（推奨）:
   ```bash
   python -m kabusys.config_setup
   ```
   ウィザードは J-Quants / kabuAPI / DB パス /ログレベル等を順に尋ねます。`.env` は Git にコミットしないでください。
4. 設定を検証する:
   ```bash
   python -m kabusys.validate_config
   # 警告も失敗扱いにする場合:
   python -m kabusys.validate_config --strict
   ```
   - PyYAML がインストールされていれば `config/*.yaml` の構文チェックも行います。
5. 必要に応じてデータディレクトリを作成（デフォルトは `data/`、ログは `logs/`）。

---

## 主要環境変数（代表）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: `development` | `paper_trading` | `live`（デフォルト: `development`）
- OPENAI_API_KEY: OpenAI API キー（ai モジュール使用時必須）
- PAPER_FILL_MODE: paper_trading 用の約定挙動 (`instant` | `partial` | `never` | `reject`)（デフォルト: `instant`）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: `data/paper_trading.db`）
- SQLITE_PATH: 監視 DB（デフォルト: `data/monitoring.db`） — monitoring は環境に関係なく「本番 sqlite_path」を使用する設計箇所あり
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: `data/kabusys.duckdb`）
- LOG_LEVEL: ログレベル（`INFO` 等）
- LOG_DIR: ログ出力先（デフォルト: `logs/`）
- MONITOR_POLL_INTERVAL: SystemMonitor のポーリング間隔（秒、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に `data/kill.flag` を自動クリアするか（`0`/`1`、本番は `0` 推奨）

---

## 使い方（実行例）
- ExecutionEngine を起動（paper_trading モードでは MockBroker を使い、`data/paper_trading.db` に記録）
  ```bash
  python -m kabusys.run_execution
  ```
  起動時にプロセス優先度を "high" に設定します。`data/execution.pid` を PID ファイルとして扱います。`data/stop_requested.flag` が既に存在する場合は起動せず終了します。

- Monitoring を起動（ポーリングループ）
  ```bash
  # デフォルト 60 秒ポーリング。環境変数で上書き可能:
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```
  監視は常に（KABUSYS_ENV にかかわらず）設定された sqlite_path を使用して監視テーブルを初期化します。停止は `data/stop_requested.flag` の作成で行えます。

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- 環境設定ウィザード（.env 作成）
  ```bash
  python -m kabusys.config_setup
  ```

- Paper Trading 検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # --db で別 DB 指定可:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI / リサーチ関数はモジュール API として利用:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - kabusys.research.calc_momentum(conn, target_date) 等

---

## ログ・ファイル / フラグ
- ログ: デフォルト `logs/<app_name>.log`（TimedRotatingFileHandler、日次ローテーション、30日保持）
- PID ファイル: `data/execution.pid`（ExecutionEngine）
- 停止フラグ: `data/stop_requested.flag`（stop 指示、run_execution / run_monitoring はこれで停止）
- Kill Switch フラグ: `data/kill.flag`（KillSwitch が書き込むことで Execution 停止をトリガー）

---

## 注意点 / 運用上のヒント
- 本番（KABUSYS_ENV=live）では環境変数や LINE 通知設定等を十分に確認してください。`validate_config` は live の場合に追加警告を出します。
- Monitoring は監視 DB のパスを参照して起動します。監視 DB を共有・バックアップする運用を検討してください。
- OpenAI API を利用する機能（ニュース NLP / レジーム判定）は API キーが必須です。API 呼び出し失敗時はフェイルセーフとして無視または中立値を使う設計です。
- `KILL_FLAG_CLEAR_ON_START=1` は本番では危険です（起動時に自動的に kill.flag を削除します）。本番は `0` 推奨。
- ログディレクトリの作成に失敗した場合、ファイルログは無効化されコンソール出力のみになります（setup_logging の挙動）。

---

## ディレクトリ構成（主要ファイル）
以下はソースツリー内の主要モジュール群（`src/kabusys` 相当）です。

- kabusys/
  - __init__.py                — パッケージ定義
  - config.py                  — 環境変数 / 設定読み込みロジック（自動 .env ロード）
  - config_setup.py            — 対話式 .env ウィザード
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor ポーリング起動スクリプト

  - utils/
    - logging_setup.py         — ログ設定ユーティリティ
    - process_priority.py      — プロセス優先度 / CPU affinity 設定ユーティリティ

  - monitoring/
    - monitoring_db.py         — 監視 DB（SQLite）ラッパー
    - system_monitor.py        — システム状態 / データ鮮度監視
    - trade_monitor.py         — (発注ログ監視等の実装が想定される)
    - risk_monitor.py          — ドローダウン・ポジション上限監視
    - kill_switch.py           — kill.flag を生成するロジック
    - monitoring_engine.py     — 監視エンジン（複数 Monitor を束ねる）
    - alert_manager.py         — アラート送信（LINE 等）/※実装に依存

  - execution/
    - execution_engine.py      — 発注エンジン（EngineConfig, run_session など）
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py

  - portfolio/
    - portfolio_builder.py      — 候補選定・重み計算
    - position_sizing.py        — 発注株数計算・スケーリング
    - risk_adjustment.py        — セクターキャップ・レジーム乗数

  - research/
    - factor_research.py       — モメンタム / ボラティリティ / バリュー等のファクター計算
    - feature_exploration.py   — 将来リターン / IC / 統計サマリ

  - ai/
    - news_nlp.py              — ニュースセンチメントを OpenAI で評価し ai_scores に保存
    - regime_detector.py       — マクロ + MA200 で市場レジーム判定

  - data/                      — デフォルトの DB / フラグ / PID 保存先（実行時作成）
  - logs/                      — ログ出力先（デフォルト）

---

## 開発者向けメモ
- DuckDB 接続を受け取る関数群は副作用を持たず、ユニットテストが比較的容易です（純粋関数が多い）。
- AI 呼び出しは `_call_openai_api` を抽象化しており、テスト時はモックで差し替えられる想定です。
- MonitoringDB はスキーママイグレーションコードを含み、既存 DB にカラムを追加する処理があります。
- 重い計算や外部 API 呼び出しを含む処理はリトライ / フェイルセーフ実装があるため、本番運用を想定した頑健性があります。

---

必要に応じて README を拡張します。特に「起動手順の詳細（systemd / docker / supervisor でのサービス化）」や「リカバリ手順 / 運用 Runbook」などを追加したい場合は、用途に合わせて追記します。