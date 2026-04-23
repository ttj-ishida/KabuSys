# KabuSys

日本株自動売買システム（KabuSys）のコードベース用 README（日本語）

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムです。本リポジトリは以下の主要機能を提供します。

- 市場データ解析・ファクター計算（research）
- ポートフォリオ構築（selection / weighting / position sizing）
- 発注実行エンジン（ExecutionEngine）
- 監視（Monitoring）および Kill Switch（停止フラグ）
- ペーパートレード用の分離された DB / モックブローカー
- ニュースの LLM による NLP スコアリング（OpenAI）
- 検証用ツール（ペーパートレード検証レポート等）
- 設定ウィザード / 設定検証 CLI

設計方針として、ランタイム設定は環境変数（.env）で管理し、DuckDB / SQLite をデータ層に使用します。AI 呼び出し（OpenAI）は外部 API を利用しますが、呼び出し箇所は明確に分離されています。

---

## 主な機能一覧

- Execution
  - ExecutionEngine 起動スクリプト（`run_execution.py`）
  - 本番/ペーパーの切替（`KABUSYS_ENV`）
  - ペーパートレード時は MockBroker を利用し DB を分離

- Monitoring
  - System / Trade / Risk のモニタリング（`monitoring` パッケージ）
  - Kill Switch（閾値超過で `data/kill.flag` を書き込み Execution を停止）
  - モニタリングログの永続化（SQLite via `monitoring_db`）

- Research / Portfolio
  - ファクター計算（momentum, volatility, value）
  - 将来リターン計算・IC 計測・ファクター統計
  - 候補選定、等重・スコア加重、リスク調整、ポジションサイズ計算

- AI
  - ニュース記事のセンチメントスコアリング（OpenAI を利用）
  - 市場レジーム判定（ETF MA + LLM マクロセンチメント）

- Utilities / Tools
  - `.env` 対話式生成ウィザード（`config_setup.py`）
  - 設定検証 CLI（`validate_config.py`）
  - ペーパートレード検証レポート生成スクリプト

---

## 要件

- Python 3.10 以上（| 型注釈等を使用）
- 推奨パッケージ（主要なもの）
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で任意）
- OS: Linux / macOS / Windows（プロセス優先度設定や CPU affinity は OS に依存）

必要なパッケージはプロジェクト側で requirements.txt を用意していない場合は手動でインストールしてください。例:

pip install duckdb psutil openai PyYAML

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動。

2. 仮想環境を作成して有効化（任意だが推奨）:

   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール:

   pip install duckdb psutil openai PyYAML

4. データ / ログ ディレクトリを作成（自動作成されることもありますが事前作成推奨）:

   mkdir -p data logs

5. .env の初期作成（対話式ウィザード）:

   python -m kabusys.config_setup

   ウィザード実行後、`.env` が作成されます。必須の環境変数を設定してください（下記参照）。

6. 設定検証（任意）:

   python -m kabusys.validate_config
   # 警告も失敗扱いにする場合:
   python -m kabusys.validate_config --strict

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要オプション（デフォルト値を含む）:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading: モックブローカー・専用 DB（PAPER_TRADING_SQLITE_PATH）を使用
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: INFO（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: logs
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 本番アラート用（任意）
- OPENAI_API_KEY: OpenAI 呼び出しに必要（AI 機能使用時）
- PAPER_FILL_MODE: instant | partial | never | reject （ペーパートレードの約定動作）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env の自動ロードを無効化

注意:
- Monitoring は KABUSYS_ENV にかかわらず本番用の sqlite_path（SQLITE_PATH）を使用します。
- ExecutionEngine は KABUSYS_ENV=paper_trading のとき PAPER_TRADING_SQLITE_PATH を使用して本番 DB と分離します。

サンプル（.env の抜粋）:
```
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
```

---

## 使い方（起動・操作）

### 1) 設定のウィザードと検証

- ウィザードで .env を生成:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  --strict オプションで警告を FAIL 扱いにできます。

### 2) ExecutionEngine を起動

- 実行:
  python -m kabusys.run_execution

- 挙動:
  - 起動時に `data/execution.pid` を使用/書き込みします（PID ファイルパスは Settings で上書き可）。
  - KABUSYS_ENV=paper_trading の場合、MockBroker を用い paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録します。
  - 起動前に `data/stop_requested.flag` が存在すると起動せずに終了します。
  - 停止: `data/stop_requested.flag` を作成すると実行中のエンジンに停止を指示します（監視プロセス等から書き込む想定）。

### 3) Monitoring を起動

- 実行:
  python -m kabusys.run_monitoring

- 挙動:
  - MONITOR_POLL_INTERVAL 環境変数（秒）でポーリング間隔を変更できます（デフォルト 60）。
  - 監視ループは `data/stop_requested.flag` の存在を見て終了します。
  - 監視は SystemMonitor / TradeMonitor / RiskMonitor を呼び、必要に応じて Kill Switch を書き込みます（`data/kill.flag`）。

### 4) Kill Switch（手動トリガー）
- `KillSwitch` は条件を満たすと `data/kill.flag` を作成します。
- ExecutionEngine は起動時に kill flag のクリア設定（KILL_FLAG_CLEAR_ON_START）に応じた動作をします。

### 5) ツール：Paper Trading 検証レポート
- 実行:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- DB を指定する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

---

## ライブラリ的利用（API）

主要なモジュールは Python モジュールとして import して利用できます。例:

- ファクター計算:
  from kabusys.research import calc_momentum, calc_volatility, calc_value

- ポートフォリオ:
  from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes

- AI ニューススコア:
  from kabusys.ai.news_nlp import score_news
  # score_news(conn, target_date, api_key=None) を呼ぶ（api_key 指定または OPENAI_API_KEY 環境変数必要）

- レジーム判定:
  from kabusys.ai.regime_detector import score_regime

- 監視 DB 操作:
  from kabusys.monitoring.monitoring_db import MonitoringDB

それぞれの関数は docstring に使用方法が記載されています。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理・自動 .env ロード
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度・CPU affinity 設定
  - monitoring/
    - monitoring_db.py       — SQLite テーブル初期化・永続化層
    - system_monitor.py      — システム / データ鮮度チェック
    - trade_monitor.py       — 発注ログ監視（ファイルにあり）
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — kill.flag 書き込みロジック
    - monitoring_engine.py   — 複数モニタの束ね実行
    - alert_manager.py       — （アラート送信の実装想定）
  - execution/
    - execution_engine.py    — ExecutionEngine 本体（起動 / セッション管理）
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
  - ai/
    - news_nlp.py            — ニュース NLP & OpenAI 呼び出し
    - regime_detector.py
  - tools/
    - paper_verification_report.py

（上記以外にも補助モジュールがあります。各ファイルの docstring を参照してください。）

---

## ログとトラブルシューティング

- ログ:
  - デフォルトのログディレクトリは `logs/`。`LOG_DIR` で上書き可能。
  - `kabusys.utils.logging_setup.setup_logging` により stdout と日次ローテーションファイル出力が設定されます。
- 設定検証:
  - `python -m kabusys.validate_config` で必須環境変数やファイルの存在をチェックしてください。
- DB / ファイル:
  - `data/stop_requested.flag` — スクリプトの外部停止トリガー（存在すると監視/実行ループが終了）
  - `data/kill.flag` — Kill Switch による Execution 停止指示
  - PID ファイル（実行時に `data/execution.pid` 等を使用）
- AI 関連:
  - OpenAI API を使う処理は `OPENAI_API_KEY` が必要です。API の呼出し失敗はフェールセーフが組まれていますが、キー未設定は例外になります。

---

## 開発に関する注意点

- 自動で .env をロードします（プロジェクトルート検出）。テスト等で無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- モジュールの多くは DB 接続（DuckDB / SQLite）を引数で受け取る設計になっており、テスト容易性を考慮しています。
- OpenAI SDK のエラー種別（RateLimitError / APIError 等）に対するリトライ処理やフォールバックが組み込まれています。

---

この README はコード注釈と docstring に基づき作成しています。各モジュールの詳細な使い方は該当ファイルの docstring を参照してください。必要であれば、README に含める具体的な起動例や環境変数テンプレートの追加も作成します。