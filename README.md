# KabuSys

日本株自動売買システムの一部コンポーネント群。バックエンド処理、モニタリング、ポートフォリオ構築、リサーチ／ファクター計算、AI ニュース解析などを含むモジュール群です。

※ 本 README は src/kabusys 以下のコードベースを元に作成しています。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買・研究基盤です。主な目的は次の通りです。

- データ（DuckDB / SQLite）を用いたファクター計算・リサーチ
- ポートフォリオ構築（銘柄選定・重み付け・ポジションサイズ計算）
- ExecutionEngine を介した発注処理（本番 / ペーパートレード切替）
- 監視（System / Trade / Risk）と Kill Switch による安全停止
- OpenAI を利用したニュース NLP によるセンチメントスコア生成
- 運用支援ツール（設定ウィザード、設定検証、Paper Trading レポート生成 等）

---

## 主な機能一覧

- 環境設定管理
  - .env ファイル自動読み込み（.env / .env.local、OS 環境優先）
  - 設定ウィザード: `kabusys.config_setup`（.env の対話的作成・更新）
  - 設定検証: `kabusys.validate_config`（起動前チェック）

- 実行エンジン
  - `run_execution.py`：ExecutionEngine 起動スクリプト
  - ペーパートレード時は MockBrokerClient を使用し DB を分離

- 監視
  - `run_monitoring.py`：SystemMonitor のポーリング起動
  - MonitoringDB（SQLite）へ system_status/trade_logs/risk_logs/dashboard を永続化
  - Kill Switch（data/kill.flag）による ExecutionEngine の停止

- ポートフォリオ構築
  - 候補選定、等重 / スコア重み、リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイズ計算（ロット丸め・合計投下額スケール調整）

- リサーチ
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン計算、IC（スピアマン）や統計サマリー

- AI（OpenAI）連携
  - ニュースを LLM でスコア化して ai_scores テーブルに書き込み
  - 市場レジーム判定（ETF MA + マクロニュースの組合せ）

- 運用ツール
  - Paper Trading 検証レポート生成（稼働率・注文成功率・レイテンシ等）

---

## セットアップ手順

1. Python (3.10+) 仮想環境を作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows (PowerShell)
   ```

2. 必要パッケージをインストール
   （プロジェクトに requirements.txt がない場合は次の主要依存を個別にインストール）
   ```bash
   pip install duckdb psutil openai
   # 追加で YAML 検証を行いたい場合:
   pip install pyyaml
   ```

3. .env を作成
   - 対話式ウィザードを使う:
     ```bash
     python -m kabusys.config_setup
     ```
   - もしくは手動でプロジェクトルートに `.env` を作成してください。
     必須環境変数（例）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     推奨（例）:
     - KABUSYS_ENV=development|paper_trading|live
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - OPENAI_API_KEY (AI 機能を利用する場合)
     - LOG_LEVEL=INFO

   サンプル（.env の一部）:
   ```
   KABUSYS_ENV=development
   JQUANTS_REFRESH_TOKEN=your_token_here
   KABU_API_PASSWORD=your_password_here
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   OPENAI_API_KEY=sk-...
   LOG_LEVEL=INFO
   ```

4. データディレクトリの用意（自動作成される場合もあります）
   ```
   mkdir -p data logs
   ```

注意:
- psutil によりプロセス優先度や CPU affinity を設定します。権限不足やプラットフォーム差により警告が出る場合がありますが、致命的ではありません。
- OpenAI を使う機能を利用する場合、`OPENAI_API_KEY` を必ず設定してください。

---

## 使い方（主要スクリプト）

- 環境設定ウィザード（.env 作成）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証（起動前チェック）
  ```bash
  python -m kabusys.validate_config
  # 警告もエラー扱いにする（CI 等で）
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン起動（ExecutionEngine）
  - デフォルト（KABUSYS_ENV に従う）
  ```bash
  python src/kabusys/run_execution.py
  ```
  - Paper trading（.env で KABUSYS_ENV=paper_trading を設定）では専用 DB（data/paper_trading.db）を使用します。

- 監視モニタ起動
  ```bash
  python src/kabusys/run_monitoring.py
  ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト: 60）
    例: `export MONITOR_POLL_INTERVAL=30`

- Paper Trading 検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パスは `--db` オプションまたは環境変数 `PAPER_TRADING_SQLITE_PATH` で指定可能。

- AI ニューススコアリング（プログラム的呼び出し）
  - DuckDB 接続を渡して `kabusys.ai.score_news(conn, target_date, api_key=None)` を呼び出します。
  - `OPENAI_API_KEY` が環境変数で設定されていれば api_key は省略可能。

停止制御:
- ExecutionEngine を停止させたい場合はプロジェクトルートの `data/kill.flag` を作成してください（KillSwitch により検出されると Execution 停止シグナルになります）。
- 監視プロセスの停止や強制停止用のフラグ `data/stop_requested.flag` / `data/execution.pid` などが利用されます。

---

## 主要モジュールと役割

- kabusys.config
  - 環境変数・.env 読み込み、Settings クラス（アプリ設定）を提供

- kabusys.config_setup
  - .env の対話型ウィザード

- kabusys.validate_config
  - 起動前の設定検証ツール

- run_execution.py
  - ExecutionEngine 起動スクリプト（本番 / ペーパートレードを分離）

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL）

- kabusys.monitoring
  - monitoring_db: SQLite テーブル作成 / 永続化 API
  - system_monitor, trade_monitor, risk_monitor, kill_switch, monitoring_engine, alert_manager などを含む（監視・アラート・Kill Switch）

- kabusys.portfolio
  - portfolio_builder, position_sizing, risk_adjustment：銘柄選定・配分・サイズ決定・セクター制約・レジーム乗数

- kabusys.research
  - factor_research, feature_exploration：ファクター計算・将来リターン・IC・統計サマリー

- kabusys.ai
  - news_nlp, regime_detector：OpenAI を使ったニュースセンチメント / レジーム判定

- kabusys.utils
  - logging_setup: 統一ログ設定（stdout + 日次ローテーションファイル）
  - process_priority: psutil を使った優先度 / CPU affinity 設定

- kabusys.tools
  - paper_verification_report：Paper Trading の検証レポート生成スクリプト

---

## ディレクトリ構成

（主要ファイルを抜粋したツリー）
```
.
├─ data/                          # デフォルト DB / フラグ等（生成される）
│  ├─ monitoring.db               # SQLite（監視用） デフォルト
│  ├─ paper_trading.db             # Paper Trading 用 SQLite（paper_trading 環境）
│  ├─ kabusys.duckdb              # DuckDB（分析用）
│  ├─ execution.pid
│  ├─ kill.flag
│  └─ stop_requested.flag
├─ logs/                          # ログ（logs/<app_name>.log）
├─ src/
│  └─ kabusys/
│     ├─ __init__.py
│     ├─ config.py
│     ├─ config_setup.py
│     ├─ validate_config.py
│     ├─ run_execution.py
│     ├─ run_monitoring.py
│     ├─ utils/
│     │  ├─ logging_setup.py
│     │  └─ process_priority.py
│     ├─ monitoring/
│     │  ├─ monitoring_db.py
│     │  ├─ system_monitor.py
│     │  ├─ trade_monitor.py       # （参照あり）
│     │  ├─ risk_monitor.py
│     │  ├─ monitoring_engine.py
│     │  ├─ kill_switch.py
│     │  └─ alert_manager.py       # （参照あり）
│     ├─ execution/                # Execution 関連（order_manager 等）
│     ├─ portfolio/
│     │  ├─ portfolio_builder.py
│     │  ├─ position_sizing.py
│     │  └─ risk_adjustment.py
│     ├─ research/
│     │  ├─ factor_research.py
│     │  └─ feature_exploration.py
│     ├─ ai/
│     │  ├─ news_nlp.py
│     │  └─ regime_detector.py
│     └─ tools/
│        └─ paper_verification_report.py
└─ .env, .env.local, pyproject.toml, ...
```

---

## 環境変数（主なもの）

- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視）ファイルパス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時）
- LOG_LEVEL: ログレベル（DEBUG/INFO/…）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知設定（任意）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE: Paper Trading の約定モード（instant/partial/never/reject）

---

## 注意事項 / 運用上のヒント

- .env は機密情報を含むため Git にコミットしないでください（config_setup でも警告あり）。
- 実運用（KABUSYS_ENV=live）の場合は Kill Switch 設定（KILL_FLAG_CLEAR_ON_START 等）を慎重に扱ってください。
- OpenAI による NLP 処理は API 費用がかかります。キー管理と利用制限に注意してください。
- DuckDB / SQLite のファイルパスは環境変数で指定できます。運用時は永続ストレージ上のパスを設定してください。
- ログは logs/<app_name>.log に日次ローテーションで保存されます（既定で 30 日分保持）。

---

README にない細かい実装や追加のコマンドはコード内 docstring や各モジュールのコメントを参照してください。必要であれば、特定モジュールの使い方や API ドキュメントをさらに生成します。