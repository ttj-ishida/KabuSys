# KabuSys

日本株自動売買システムのリポジトリ向け README（日本語）。

概要、主要機能、セットアップ・使い方、ディレクトリ構成などをまとめています。

---

## プロジェクト概要

KabuSys は日本株の自動売買・研究・監視を行うためのモジュール群です。  
主要な機能は次のとおりです。

- 市場データ（DuckDB）を用いたファクター計算・リサーチ
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ算出）
- ExecutionEngine による発注処理（実運用 / ペーパートレード切替対応）
- 監視（System / Trade / Risk）とアラート管理（LINE Push）
- LLM を使ったニュース NLP（OpenAI）によるセンチメント評価・レジーム判定
- 各種 CLI / ツール（.env ウィザード、設定検証、Paper Trading 検証レポート等）

設計方針として、発注ロジックとデータ処理を分離し、テストしやすい純粋関数群を多用しています。ペーパートレード時は本番 DB と分離され、MockBroker を使用します。

---

## 機能一覧（主要）

- config:
  - .env 自動ロード（.env, .env.local）と Settings クラス
  - 対話式環境設定ウィザード: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config

- execution:
  - 実行エンジン起動スクリプト: python -m kabusys.run_execution
  - paper_trading モード対応（環境変数 KABUSYS_ENV=paper_trading）
  - ExecutionEngine は別スレッドで run_session を実行、停止フラグ（data/stop_requested.flag）で制御

- monitoring:
  - SystemMonitor / TradeMonitor / RiskMonitor によるポーリング監視
  - 監視 DB（SQLite）にログ永続化（テーブル: system_status, trade_logs, positions, risk_logs, dashboard）
  - KillSwitch による停止フラグ（data/kill.flag）生成と alert 通知
  - 監視ループ起動スクリプト: python -m kabusys.run_monitoring
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔上書き（デフォルト 60 秒）

- research / portfolio:
  - ファクター計算（momentum/volatility/value）
  - 将来リターン計算 / IC 計算 / ファクター統計
  - 候補選定、等重・スコア重み付け、ポジションサイズ算出、セクターキャップ、レジーム倍率

- ai:
  - news_nlp.score_news: OpenAI を使った銘柄ごとのニュースセンチメント算出（ai_scores テーブルへ書込）
  - regime_detector.score_regime: MA200 とマクロニュースの LLM センチメントを合成し market_regime に書込

- tools:
  - Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report
    - 注文成功率、稼働率、レイテンシ等の集計と PASS/FAIL 判定

---

## 前提 / 必要環境

- Python 3.9+
- 必要な Python パッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - PyYAML（config YAML 検証を行う場合）
- SQLite3（Python 標準ライブラリに同梱）
- ネットワーク接続（kabuステーション API / OpenAI を使う場合）

（プロジェクトに requirements.txt があればそちらを利用してください。無い場合は上記を pip install してください。）

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai pyyaml
```

---

## セットアップ手順

1. リポジトリをクローン・チェックアウト
2. Python 仮想環境を作成して依存をインストール（上記参照）
3. .env の作成
   - 対話式ウィザードを推奨:
     ```bash
     python -m kabusys.config_setup
     ```
   - もしくは手動でプロジェクトルートに `.env` を作成（下記「環境変数」参照）
4. 設定検証:
   ```bash
   python -m kabusys.validate_config
   # 警告を FAIL 扱いにしたい場合:
   python -m kabusys.validate_config --strict
   ```
5. データディレクトリ準備:
   - デフォルト DB / PID / フラグは `data/` 配下に置かれます。必要に応じてディレクトリを作成してください。
   - 例: `mkdir -p data`
6. DuckDB / SQLite の初期化は各モジュールが自動で行います（monitoring_db.init_monitoring_db は冪等）。

---

## 主要な環境変数（代表）

- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD: kabuステーション API パスワード

- 任意（デフォルト値）
  - KABUSYS_ENV: 実行環境 (development | paper_trading | live) — デフォルト: development
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - LOG_LEVEL: INFO（有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知設定（未設定なら通知はスキップ）
  - OPENAI_API_KEY: OpenAI を使う機能で参照されます
  - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、run_monitoring 用、デフォルト 60）
  - PID_FILE_PATH: data/execution.pid（ExecutionEngine の PID ファイル）
  - KILL_FLAG_PATH: data/kill.flag（Kill Switch フラグファイル）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか (0/1, デフォルト 0)

（`.env` は絶対にリポジトリにコミットしないでください。）

---

## 使い方（起動例）

- 環境変数を読み込んだ上で監視ループを起動:
  ```bash
  python -m kabusys.run_monitoring
  # MONITOR_POLL_INTERVAL を上書きする例（30秒間隔）
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

  注:
  - run_monitoring は監視用 SQLite（settings.sqlite_path）を使用します（環境にかかわらず本番 sqlite_path を参照する実装）。
  - 監視開始前にプロセス優先度を "high" に設定しようとします（psutil の権限不足時は警告でスキップ）。

- ExecutionEngine を起動:
  ```bash
  python -m kabusys.run_execution
  ```

  ポイント:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に発注ログを記録して本番 DB と分離します。
  - 起動前に data/stop_requested.flag があると起動をスキップします。実行中も同フラグで停止します。

- Paper Trading 検証レポート生成:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示する場合
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- LLM を使ったニューススコア生成（ライブラリ呼び出し例）:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 4, 11), api_key="sk-...")
  print("書き込み銘柄数:", written)
  ```

- 市場レジーム算出:
  ```python
  from kabusys.ai.regime_detector import score_regime
  written = score_regime(conn, target_date=date(2026,4,11), api_key="sk-...")
  ```

---

## 監視・停止制御（Kill Switch / Stop フラグ）

- stop_requested.flag（data/stop_requested.flag）:
  - run_monitoring / run_execution のループで存在をチェックし、あれば監視ループ／エンジンを終了します（開発用の外部終了フラグ）。
- kill.flag（data/kill.flag）:
  - KillSwitch が条件に応じて書き込み、ExecutionEngine に対して停止シグナルを送る目的で使われます。
  - 本番では KILL_FLAG_CLEAR_ON_START=0 を推奨（自動クリアは危険）。

---

## 監視 DB（SQLite）スキーマ（自動作成）

init_monitoring_db() により以下テーブルを作成します（冪等）:

- system_status: cpu/memory/disk/process_ok 等
- trade_logs: 発注イベントログ（latency_ms カラムも追加でサポート）
- positions: 現在の保有
- risk_logs: リスク関連イベント（DRAWDOWN_ALERT など）
- dashboard: 集計（id=1 の1行保存、peak_value カラム有）

マイグレーション:
- 既存 DB に peak_value や latency_ms がない場合、自動的にカラム追加を試みます。

---

## 設定検証・ウィザード

- 簡易ウィザード（対話式）:
  ```bash
  python -m kabusys.config_setup
  ```
  で `.env` を作成・更新できます。

- 起動前チェック:
  ```bash
  python -m kabusys.validate_config
  ```
  --strict を付与すると警告もエラー扱いになります。

---

## 主要なディレクトリ構成

（リポジトリの src/kabusys を想定）

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_monitoring.py        — 監視ループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP / OpenAI 呼び出し
    - regime_detector.py     — レジーム判定
  - monitoring/
    - monitoring_db.py       — monitoring DB レイヤ
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - alert_manager.py
    - kill_switch.py
  - execution/                — Execution エンジン関連（発注・リポジトリ等）
    - (OrderManager, BrokerFactory 等)
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
    - process_priority.py

（上記は主要ファイルの抜粋です。実際のツリーはリポジトリ参照ください。）

---

## 注意事項 / ヒント

- 本番運用（KABUSYS_ENV=live）は危険を伴います。validate_config の警告をよく確認してください。
- OpenAI / 外部 API キーは `.env` に設定し、絶対にリポジトリにコミットしないでください。
- psutil を利用してプロセス優先度や CPU affinity を変更します。権限がない場合は警告でスキップされます。
- monitoring は settings.sqlite_path（本番 DB）を使用するため、paper_trading の実行とは別に DB を分けておくことを推奨します（PAPER_TRADING_SQLITE_PATH）。
- run_execution は起動時に data/stop_requested.flag が存在すると起動をスキップします。運用時はフラグファイルの有無に注意してください。

---

最後に、本リポジトリのコードを参照しつつ必要に応じて README を拡張してください。追加で「運用手順（systemd / supervisor 用のサービス定義例）」や「開発向けユニットテストの実行方法」などを含めたい場合は教えてください。