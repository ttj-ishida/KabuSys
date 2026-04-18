# KabuSys

日本株向け自動売買システムの一部を実装したリポジトリ（ライブラリ・ユーティリティ群）。
本 README はコードベースの概要、主要機能、セットアップ方法、使い方例、ディレクトリ構成をまとめたものです。

重要: 本プロジェクトは実取引に関わる設定（kabuステーションのパスワードや API トークンなど）を扱います。KABUSYS_ENV を `live` に設定する際は十分にテスト・確認してください。

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したシステムで、次の機能群を含みます（ライブラリ的に分割）:

- Execution（発注エンジン）: ブローカークライアントを介した発注ロジック（paper/live 切替対応）。
- Monitoring（監視）: システム状態、注文フロー、リスク（ドローダウン・ポジション数）を定期監視し、kill flag 等でエンジン停止を誘導。
- Portfolio（ポートフォリオ構築）: 候補選定、重み付け、ポジションサイズ計算、セクター制約などの純粋関数実装。
- Research（リサーチ）: DuckDB を用いたファクター計算・特徴量解析・IC 計算。
- AI（ニュース NLP / レジーム判定）: OpenAI API を用いたニュースセンチメント集約、マクロセンチメントとの組合せでレジーム判定。
- ツール群: .env 設定ウィザード、設定検証 CLI、Paper Trading 検証レポートなど。

---

## 主な機能一覧

- 設定管理
  - .env 自動ロード（プロジェクトルートの .env / .env.local を優先的に読み込み）
  - 対話式設定ウィザード: `python -m kabusys.config_setup`
  - 設定検証 CLI: `python -m kabusys.validate_config`

- 実行/監視プロセス
  - ExecutionEngine 起動スクリプト: `run_execution.py`
    - `KABUSYS_ENV=paper_trading` のときは MockBrokerClient を使用し、本番 DB と分離して `data/paper_trading.db` を使用
    - 起動時に PID ファイル / stop フラグを参照して安全に停止
  - Monitoring 起動スクリプト: `run_monitoring.py`
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
    - SystemMonitor / TradeMonitor / RiskMonitor を組み合わせて定期チェックし、kill.flag 書込みやアラートを通知

- 監視 DB 層（SQLite）
  - system_status, trade_logs, positions, risk_logs, dashboard テーブルの作成・マイグレーション機能を提供（冪等）

- ポートフォリオ構築
  - 候補選定（スコア順）、等金額/スコア加重、リスクベースの発注株数計算、セクター上限適用、レジーム乗数

- 研究/分析
  - DuckDB を用いたファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン・IC（スピアマン）・統計サマリー計算

- AI（OpenAI 統合）
  - ニュースを銘柄ごとに集約し LLM（gpt-4o-mini 想定）でセンチメントスコアを算出して ai_scores に書き込む処理
  - マクロニュース + ETF MA200 を組み合わせた市場レジーム判定（`score_regime`）

- ツール
  - Paper Trading 検証レポート生成スクリプト: `python -m kabusys.tools.paper_verification_report`

---

## 前提・依存パッケージ

主に以下の外部ライブラリを使用しています（最小限）:

- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（config YAML の検証時にあれば便利だが必須ではない）

インストール例（仮想環境推奨）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb psutil openai PyYAML
# またはパッケージ化している場合は: pip install -e .
```

（requirements.txt がある場合はそちらを利用してください）

---

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリへ移動:

   ```bash
   git clone <repo_url>
   cd <repo>
   ```

2. Python 仮想環境を作成・有効化し、依存パッケージをインストール（上記参照）。

3. .env ファイルを作成:
   - 対話式ウィザードを使用するのが簡単です:

     ```bash
     python -m kabusys.config_setup
     ```

   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
     - OPENAI_API_KEY（AI を使う場合）
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト data/paper_trading.db）
     - LOG_LEVEL（DEBUG/INFO/…）
     - その他: LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID など（通知用）

4. 設定検証（推奨）:

   ```bash
   python -m kabusys.validate_config
   # 問題があると exit code != 0
   # 警告をエラー扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリ作成（必要に応じて）:

   ```bash
   mkdir -p data logs
   ```

---

## 使い方（サンプル）

- ExecutionEngine（発注エンジン）を起動:

  ```bash
  # 実行（通常はシステムでデーモン化して運用）
  python -m kabusys.run_execution
  ```

  注意:
  - `KABUSYS_ENV=paper_trading` の場合は paper_trading 用の SQLite DB（デフォルト `data/paper_trading.db`）に記録され、本番 DB と分離されます。
  - 起動時に `data/stop_requested.flag` や `data/kill.flag` をチェックします。これらのフラグにより起動抑制や停止制御が行われます。
  - Execution は PID ファイル（デフォルト `data/execution.pid`）を使用します。

- Monitoring（定期監視）を起動:

  ```bash
  # デフォルトは 60 秒間隔。環境変数で上書き可:
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```

  Monitoring は SystemMonitor / TradeMonitor / RiskMonitor を呼び、必要に応じて kill.flag を書き込んだり、アラート通知を行います。
  監視は本番 sqlite_path（Settings.sqlite_path）を使用します（環境にかかわらず監視 DB は production path を参照する設計）。

- .env の初期化 / 更新:

  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証:

  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポートを生成:

  ```bash
  # デフォルト DB は data/paper_trading.db。--db で指定可能。
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

- AI / 研究用関数（ライブラリ呼び出し）:
  - news_nlp.score_news(conn, target_date, api_key=...) — DuckDB 接続を渡して実行
  - regime_detector.score_regime(conn, target_date, api_key=...) — 同上
  - research.calc_momentum / calc_volatility / calc_value などは DuckDB 接続と日付を渡して利用します

（AI 関連を実行する際は OPENAI_API_KEY を設定してください）

---

## 停止 / Kill Switch / フラグの扱い

- 停止フラグ:
  - run_execution / run_monitoring はいくつかのフラグファイルを参照します:
    - data/stop_requested.flag — 即時停止リクエスト（run_* 側が検知してループを抜ける）
    - data/kill.flag — Kill Switch（監視側が条件成立時に書き込み、Execution に停止を促す）
  - KillSwitch はリスク条件（ドローダウン超過、ポジション上限超過など）で `kill.flag` を作成します。
  - Execution 起動時の `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に kill.flag を自動クリアします（本番では 0 を推奨）。

---

## ログ

- ログ設定ユーティリティ: `kabusys.utils.logging_setup.setup_logging`
  - stdout ストリームハンドラ + 日次ローテーションファイルハンドラ（logs/<app_name>.log）をルートロガーに設定
  - デフォルトログディレクトリ: `logs/`
  - 環境変数 LOG_DIR / LOG_LEVEL で上書き可能

---

## ディレクトリ構成（主要ファイル）

（抜粋・主要モジュールのみ）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定取得
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - (trade_monitor.py 等が存在する想定)
  - execution/
    - execution_engine.py     (呼び出される想定)
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py
    - process_priority.py

※ 実際のファイルツリーはリポジトリの内容に依存します。上は主要モジュールの概観です。

---

## 安全上の注意

- KABUSYS_ENV を `live` にすると実際の発注が行われます。必ず設定・コード・ブローカー設定を事前に検証してください。
- .env は機密情報を含むため絶対にリポジトリにコミットしないでください。
- Production では `KILL_FLAG_CLEAR_ON_START` を `0` にしておくことを推奨します（誤って自動クリアされると Kill Switch が無効化される恐れがあります）。

---

## 追加情報 / 開発者向け

- 設定検証は `validate_config.py` によって .env および config/*.yaml の存在や形式をチェックします（PyYAML があれば YAML のパースも行います）。
- DuckDB を利用した研究モジュールは prices_daily / raw_financials / raw_news 等のテーブルを参照します。これらのテーブルを準備してから関数を実行してください。
- OpenAI 関連はネットワーク・料金に注意して利用してください。API の呼び出しはリトライ・バックオフ実装がなされていますが、呼び出し回数・文字数によってコストが発生します。

---

必要であれば、この README に CI/デプロイ手順、systemd ユニットの例、より詳細な API 使用例（コードスニペット）を追記できます。どの情報を追加しましょうか？