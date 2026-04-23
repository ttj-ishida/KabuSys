# KabuSys

日本株向けの自動売買システム（ライブラリ＋起動スクリプト群）。  
主に以下の役割を持つモジュールで構成されています。

- 発注・実行エンジン（ExecutionEngine）
- 監視（Monitoring）／Kill Switch（停止フラグ）
- ポートフォリオ構築（銘柄選定・配分・株数決定）
- リサーチ（ファクター計算・特徴量解析）
- AI モジュール（ニュース NLP、レジーム判定）
- 各種ユーティリティ（ログ設定・プロセス優先度等）
- ツール群（Paper Trading 検証レポート生成 等）
- .env ウィザード / 設定検証 CLI

以下は本リポジトリの概要、セットアップ手順、使い方、主要機能とディレクトリ構成です。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムのコアライブラリです。  
設計方針の要点：

- 本番 DB と Paper Trading DB を分離（paper_trading モード）。
- DuckDB を用いたリサーチ・ファクター計算（prices_daily / raw_financials 等）。
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（AI モジュール）。
- 監視エンジンによりシステム状態・注文状態・リスクを定期チェックし、必要に応じて kill.flag を書き込むことで実行エンジンを停止可能。
- ロギングは統一インターフェース（console + 日次ローテートファイル）で管理。

バージョン: 0.1.0（パッケージ情報は src/kabusys/__init__.py）

---

## 主な機能一覧

- Execution
  - ExecutionEngine による注文発行・リスク管理・再整合処理
  - paper_trading モードでは MockBrokerClient を使用し data/paper_trading.db に記録
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク/プロセス状態・データ鮮度監視
  - TradeMonitor: 注文滞留・約定異常等の監視（trade_logs テーブル参照）
  - RiskMonitor: ドローダウン / ポジション上限の監視と risk_logs への記録
  - KillSwitch: 条件に応じて data/kill.flag を作成し ExecutionEngine を停止
  - MonitoringEngine: 各監視を束ねてポーリングし、AlertManager へ通知
- Portfolio
  - 銘柄候補選定、重み計算（等配分 / スコア加重）
  - セクター上限適用、レジーム乗数
  - 株数決定（単元株丸め、リスクベース配分、aggregate cap スケーリング）
- Research
  - Momentum / Volatility / Value ファクター計算（DuckDB を使用）
  - 将来リターン、IC（Spearman）等の解析ツール
- AI
  - news_nlp.score_news: raw_news を LLM で評価して ai_scores に書き込む
  - regime_detector.score_regime: ETF (1321) MA200 とマクロニュースで市場レジーム判定
- ツール
  - paper_verification_report: Paper Trading DB（data/paper_trading.db）から検証レポートを生成
- 設定管理
  - config.py：.env の自動ロード ／ Settings クラス
  - config_setup.py：対話式 .env ウィザード（python -m kabusys.config_setup）
  - validate_config.py：起動前に環境・config/*.yaml の検証（python -m kabusys.validate_config）

---

## 必要な依存パッケージ

主に次を想定しています（最低限）:

- Python 3.10+
- duckdb
- psutil
- openai
- (オプション) PyYAML — validate_config による YAML 検証を行う場合

インストール例:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

（requirements.txt がある場合は `pip install -r requirements.txt` を利用してください）

---

## 環境変数（主要）

必須（動作に必須）:

- JQUANTS_REFRESH_TOKEN — J-Quants API トークン
- KABU_API_PASSWORD — kabuステーション API パスワード

運用上よく使う / 推奨指定:

- KABUSYS_ENV — 実行環境 (development | paper_trading | live)。デフォルト: development
  - paper_trading: 発注は MockBrokerClient、DB は data/paper_trading.db
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- OPENAI_API_KEY — OpenAI API キー（AI モジュールで使用）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知設定（任意）
- PAPER_FILL_MODE — Paper Trading の約定モード（instant|partial|never|reject）
- PID_FILE_PATH — ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — Kill Switch 用フラグファイルパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）

設定は .env ファイルに保存できます。.env の作成/更新はウィザードを推奨（下記参照）。

---

## セットアップ手順

1. リポジトリをクローンし作業ディレクトリへ移動

2. 仮想環境を作成して依存をインストール

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb psutil openai pyyaml
   ```

3. .env を用意（推奨: ウィザードで作成）

   ```bash
   python -m kabusys.config_setup
   ```

   ウィザードで入力後、`.env` がプロジェクトルートに作成されます。

4. 設定検証（本番投入前に必ず実行）

   ```bash
   python -m kabusys.validate_config
   # 警告を FAIL 扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

5. 必要なディレクトリを作成（logs や data 等）

   ```bash
   mkdir -p data logs
   ```

---

## 使い方（起動例）

- ExecutionEngine を起動（通常はプロセスマネージャから）:

  ```bash
  # 本番/開発いずれも settings.KABUSYS_ENV により動作切替
  python -m kabusys.run_execution
  ```

  補足:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に記録します（本番 DB と分離）。
  - 起動時に data/stop_requested.flag が存在する場合は起動を中止します。
  - ExecutionEngine は data/execution.pid に PID を書きます。

- Monitoring を起動（監視プロセス）:

  ```bash
  # MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書き（デフォルト 60 秒）
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```

  補足:
  - Monitoring は Settings に依存せず、本番 sqlite_path を使用して監視テーブルを初期化します。
  - 停止は data/stop_requested.flag を作成するか KeyboardInterrupt。

- Paper Trading 検証レポート生成:

  ```bash
  # デフォルト DB: data/paper_trading.db
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # 別 DB を直接指定する場合
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI モジュール（スクリプトではなくライブラリ関数として使用）:

  - ニュース NLP（ai_scores に書き込み）
    - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - レジーム判定
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

  いずれも OpenAI API キーは引数で渡すか OPENAI_API_KEY 環境変数を設定します。

---

## 運用上のポイント

- Kill Switch:
  - `KillSwitch` は条件（ドローダウン超過等）を満たすと `data/kill.flag` を作成します。ExecutionEngine 起動時または監視側で検出し、エンジン停止やフラグクリアの運用を行ってください。
  - 本番で KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動で kill.flag を消去しますが、危険なので本番では 0 を推奨します。

- ログ:
  - ルートロガーはコンソール出力（stdout）と日次ローテートファイル（logs/<app_name>.log）を使用します。`kabusys.utils.logging_setup.setup_logging` により統一されます。

- Paper Trading と本番 DB の分離:
  - paper_trading モードでは `PAPER_TRADING_SQLITE_PATH`（デフォルト data/paper_trading.db）を使用します。実データと完全に分離してください。

- 環境変数の自動ロード:
  - プロジェクトルートに `.env` (および .env.local) があれば、config.py が自動的に読み込みます（OS 環境変数より優先度は低い）。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主要ファイル・モジュール一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings
  - config_setup.py           — .env ウィザード CLI
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py (参照されるが抜粋外)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - execution/                 — ExecutionEngine・OrderManager 等（詳細モジュール群）
  - data/                      — （期待されるデータファイル）data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db
  - logs/                      — ログ出力先（実行時作成）

（実際のファイル全体はリポジトリを参照してください。上は主要ファイルの要約です。）

---

## 参考コマンドまとめ

- .env ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- Execution 起動:
  - python -m kabusys.run_execution
- Monitoring 起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

README に記載のない内部 API（ライブラリ関数）や詳細な実装の使い方は、各モジュールの docstring を参照してください。必要であれば、各機能の使い方（例: ExecutionEngine の設定・拡張方法、AI モジュールのテスト用モックの差し替え方等）について別途ドキュメントを作成します。