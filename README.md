# KabuSys

日本株向けの自動売買 / 研究基盤ライブラリ群（簡易 README）

このリポジトリは、取引実行エンジン、監視（Monitoring）、ポートフォリオ構築・資金配分、リサーチ、AI（ニュース NLP / レジーム判定）などの機能を備えた自動売買フレームワークです。本 README ではセットアップと主要な使い方、ディレクトリ構成を日本語でまとめます。

---

## プロジェクト概要

KabuSys は以下の主要コンポーネントで構成されます。

- ExecutionEngine: 発注・リスク管理・オーダー管理を担当するエンジン（`run_execution.py` を起動）
- Monitoring: システム状態・注文状態・リスク監視と Kill Switch（`run_monitoring.py` を起動）
- Portfolio: 候補選定、重み計算、ポジションサイズ計算、セクター制限等の純粋関数群
- Research: DuckDB ベースのファクター計算・特徴量探索ツール
- AI: ニュースセンチメント（OpenAI）を利用したスコアリング、レジーム判定
- Tools: 設定ウィザード・設定検証・Paper Trading 検証レポート生成などの CLI

設計方針の一部:
- 環境変数 / .env による設定管理
- Paper trading（ペーパートレード）は本番 DB と分離
- 監視ログは SQLite、分析用は DuckDB を使用
- 外部 API 呼び出し部分はフェイルセーフやリトライを備える

---

## 主な機能一覧

- 発注フロー（OrderManager / ExecutionEngine）
- リスク管理（RiskManager / RiskMonitor）
- 監視（SystemMonitor / TradeMonitor / MonitoringEngine）
- Kill Switch（閾値超過で停止フラグを書き込み）
- .env 対話式ウィザード（`config_setup.py`）
- 設定検証 CLI（`validate_config.py`）
- Paper Trading 向け DB 分離と検証レポート（`tools/paper_verification_report.py`）
- ポートフォリオ構築ユーティリティ（候補選定 / 重み付け / 位置サイズ）
- DuckDB を使ったファクター計算（Momentum, Volatility, Value 等）
- OpenAI を使ったニュース NLP とレジーム判定（`ai` モジュール）

---

## 前提 / 必要環境

- Python 3.10+
- 推奨パッケージ（代表例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証を行う場合に推奨）
- その他ライブラリは用途により追加（requirements.txt がない場合は個別にインストールしてください）

インストール例（仮）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要な任意項目:
- KABUSYS_ENV: execution/monitoring の実行環境（`development` / `paper_trading` / `live`）
  - `paper_trading` の場合、発注はモック（MockBrokerClient）となり、Paper 用 SQLite（デフォルト `data/paper_trading.db`）を使用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
- SQLITE_PATH: 監視用 SQLite（デフォルト `data/monitoring.db`） — Monitoring は環境にかかわらず本番 sqlite_path を用いる設計です
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト `data/paper_trading.db`）
- LOG_LEVEL: ログレベル（`DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`）
- LOG_DIR: ログファイルの保存先（デフォルト `logs/`）
- OPENAI_API_KEY: OpenAI 呼び出しに必要（AI モジュール使用時）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、`run_monitoring` で上書き可能。デフォルト 60 秒）
- KILL_FLAG_CLEAR_ON_START: `1` にすると起動時に kill.flag を自動クリア（本番での自動クリアは危険なためデフォルトは `0`）

注意:
- `run_execution` は KABUSYS_ENV によって paper/live の挙動が変わります（paper_trading は DB を分離）。
- 監視側（monitoring）は常に `Settings.sqlite_path`（本番の sqlite）を参照します。

---

## セットアップ手順（推奨フロー）

1. リポジトリをクローン / コピー
2. Python 仮想環境を作成・有効化
3. 必要パッケージをインストール（上記参照）
4. .env を作成
   - 対話式で作る場合:
     ```bash
     python -m kabusys.config_setup
     ```
   - `.env` を直接作成する場合は `.env.example` を参考に必要な値を設定してください（このコードベースには .env.example の中身が README に示したキー群です）。
5. 設定検証:
   ```bash
   python -m kabusys.validate_config
   # 警告をエラー扱いにしたい場合:
   python -m kabusys.validate_config --strict
   ```
6. 初回起動時は DB の親ディレクトリ（`data/`）や `logs/` を作成しておくと安全です（`setup_logging`・DB 初期化は起動スクリプト側で作成を試みますが、権限等で失敗する場合があります）。

---

## 使い方（主要コマンド）

- ExecutionEngine の起動
  - 本番（または env に応じた挙動）:
    ```bash
    python -m kabusys.run_execution
    ```
  - Paper Trading に切り替える（環境変数）:
    ```bash
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```
  - 停止
    - 実行プロセスはプロジェクトルートの `data/stop_requested.flag` を検知して終了します（`run_execution` と `run_monitoring` はこのフラグファイルを参照）。
    - Kill Switch がトリガーされた場合は `data/kill.flag` が作成され、ExecutionEngine による取引を防止します（KillSwitch により書き込まれます）。

- Monitoring の起動
  - デフォルト 60 秒周期:
    ```bash
    python -m kabusys.run_monitoring
    ```
  - ポーリング間隔を変更:
    ```bash
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```

- 設定ウィザード
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート（SQLite のパスは環境変数か --db で指定）
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または別 DB を指定
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI / レジーム判定 等（プログラム的に利用）
  - OpenAI を利用する機能は `OPENAI_API_KEY` 環境変数（または API キー引数）を必要とします。API 呼び出しはリトライ/フェイルセーフが組み込まれています。
  - 例（Python から呼ぶ）:
    ```python
    from kabusys.ai.news_nlp import score_news
    # duckdb_conn は duckdb.connect('data/kabusys.duckdb') 等で取得
    score_news(duckdb_conn, target_date=date(2026,4,10), api_key="sk-...")
    ```

---

## 注意点 / 運用上のポイント

- Paper Trading
  - KABUSYS_ENV=paper_trading の場合、発注は MockBrokerClient を使い、Paper 用 SQLite に記録されます。本番 DB と完全分離される設計です。
- 監視 DB（monitoring）は、Monitoring のために起動スクリプトで必ず `init_monitoring_db()` を呼んでいるため、明示的なマイグレーションは不要（起動時にテーブル作成・ALTER を行います）。
- Kill Switch / Stop フラグ
  - `data/kill.flag`: KillSwitch が書き込む停止フラグ（存在すると Execution を止める意図）。`KILL_FLAG_CLEAR_ON_START=1` により起動時に自動クリア可能だが、本番では `0` を推奨。
  - `data/stop_requested.flag`: 起動中のループを止めたいときに作成（`run_execution` / `run_monitoring` が検知して終了）。
- ログ
  - `kabusys.utils.logging_setup.setup_logging()` により stdout と日次ローテートファイル（`logs/<app_name>.log`）へ出力します。ログディレクトリは `LOG_DIR` 環境変数または `logs/` がデフォルトです。
- CPU 優先度
  - 起動スクリプトは最初に `set_process_priority("high")` を呼んで試みますが、権限不足や OS によって設定できない場合は警告が出ます（フェイルセーフ）。

---

## ディレクトリ構成（抜粋）

（プロジェクトルートの `src/kabusys/` を基準に重要ファイルを列挙）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity 管理
  - execution/                 — 発注エンジン関連（OrderManager 等）
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層（system_status, trade_logs…）
    - system_monitor.py       — システム監視（CPU/メモリ/データ鮮度）
    - risk_monitor.py         — ドローダウン / 保有数監視
    - kill_switch.py          — Kill Switch 実装
    - monitoring_engine.py    — 各 Monitor を束ねるエンジン
    - alert_manager.py        — （アラートの送信管理：LINE 等、実装場所）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI 呼び出し）
    - regime_detector.py      — レジーム判定（ma200 + macro sentiment）
  - tools/
    - paper_verification_report.py

（上記は主要ファイルの抜粋。実際のディレクトリにはさらに補助モジュールがあります）

---

## よくある運用フロー（例）

1. .env を作成（`python -m kabusys.config_setup`）
2. 設定検証（`python -m kabusys.validate_config`）
3. DuckDB / SQLite の配置（`data/` フォルダを作成）
4. 監視プロセスを起動（本番では常駐）
   - `MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring`
5. Execution を起動（paper/live を環境変数で切替え）
   - `KABUSYS_ENV=live python -m kabusys.run_execution`
6. 監視が閾値を検出した場合、Kill Switch により `data/kill.flag` が作成され、Execution 側で発注停止等の挙動を取ります。

---

## 最後に / 付記

- この README はコード内コメント・設計意図を元に要点をまとめたものです。実環境での運用前には必ず `validate_config` やテストを実行して設定や DB の整合性を確認してください。
- OpenAI など外部 API を用いる機能はコスト・レート制限・API 仕様に注意して運用してください（リトライ・フェイルセーフは組み込まれていますが、運用設計は運用者の責任です）。

必要であれば、インストール手順の詳細なコマンド例、.env のサンプル、起動 / 停止スクリプト例（systemd / supervisor 用ユニット）なども作成します。どの情報がさらに要りますか？