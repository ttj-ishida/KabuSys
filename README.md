# KabuSys — 日本株自動売買システム（README）

このリポジトリは日本株の自動売買に関するコンポーネント群（Execution / Monitoring / Research / Portfolio / AI 等）を含むライブラリ／実行モジュール群です。本 README はコードベースの概要、機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

注意: .env に API キーやパスワードなどの機密情報を格納します。絶対に Git にコミットしないでください。

---

## プロジェクト概要

KabuSys は以下の主要機能を持つモジュール群で構成される自動売買基盤です。

- 注文エンジン（ExecutionEngine）: ブローカークライアントを通じた発注ロジック、リスク管理、レコンシリエーション
- 監視（Monitoring）: システム稼働状態・データ鮮度・注文異常・ドローダウン監視と Kill Switch 制御
- ポートフォリオ構築（Portfolio）: 候補選定、重み計算、ポジションサイズ計算、セクター制限
- リサーチ（Research）: ファクター計算、将来リターン・IC（情報係数）計算など（DuckDB ベース）
- AI（news_nlp / regime_detector）: OpenAI を用いたニュースセンチメント評価・市場レジーム判定
- ユーティリティ: .env ウィザード、設定検証、プロセス優先度設定、レポート生成ツール等

設計方針の一例:
- 本番 DB とペーパートレード DB を明確に分離
- ルックアヘッドバイアス回避（date.today() など直接参照しない実装方針）
- フェイルセーフ（API 失敗時は安全側フォールバック）と冪等性を重視

---

## 主な機能一覧

- Execution
  - ExecutionEngine 起動スクリプト: run_execution.py
  - Paper Trading モード: KABUSYS_ENV=paper_trading のとき MockBroker を使用し data/paper_trading.db に記録
  - Kill Switch（data/kill.flag）で外部からエンジン停止可能
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を組み合わせた MonitoringEngine（run_monitoring.py）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定（デフォルト 60 秒）
  - 監視ログは SQLite（デフォルト: data/monitoring.db）に永続化
- Portfolio
  - 候補選定、等重・スコア加重、リスクベース割当、セクターキャップ、レジーム乗数
- Research
  - DuckDB を使ったファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン・IC・統計サマリー
- AI
  - news_nlp.score_news: raw_news を集約し OpenAI に送って ai_scores を更新
  - regime_detector.score_regime: ma200 の乖離とマクロニュース（LLM）の組合せで regime 判定
  - OpenAI API 利用には OPENAI_API_KEY が必要
- ツール
  - 環境設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config
  - Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report

---

## セットアップ手順（開発環境）

1. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (macOS / Linux)
   - .venv\Scripts\activate     (Windows)

2. 必要パッケージをインストール（minimal）
   - duckdb
   - psutil
   - openai
   - requests
   - PyYAML (config YAML 検証を使う場合)
   例:
     pip install duckdb psutil openai requests PyYAML

   （プロジェクトに requirements.txt があればそちらを使用してください）

3. .env の準備
   - 対話式ウィザードで生成:
       python -m kabusys.config_setup
   - もしくはルートに .env を作成して環境変数を設定する
   - 自動読み込み: config.Settings はプロジェクトルート（.git か pyproject.toml がある場所）を探索して .env/.env.local を自動ロードします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

4. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告をエラー扱いにする: python -m kabusys.validate_config --strict

5. データディレクトリ作成
   - デフォルトで使用されるファイルは data/ 配下に配置されます。
   - 例: mkdir -p data

---

## 主要な環境変数（代表例）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時に必須）
- DUCKDB_PATH: デフォルト data/kabusys.duckdb
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 DB（デフォルト data/paper_trading.db）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、run_monitoring 用。デフォルト 60）
- PAPER_FILL_MODE: ペーパートレード時の約定モード（instant / partial / never / reject）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START など（Settings を参照）

.env の例（機密値は実際の値に置き換える）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
```

---

## 使い方（実行例）

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告をエラー扱いにできます

- 監視ループ起動（モニタープロセス）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可（秒）
  - 監視処理は Settings.sqlite_path（デフォルト data/monitoring.db）を使用します（run_monitoring は KABUSYS_ENV にかかわらず production sqlite_path を使用する実装になっています）
  - 停止: プロセスを Ctrl+C するか、プロジェクトルート/data/stop_requested.flag を作成するとループが終了します

- ExecutionEngine 起動（注文エンジン）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）を使用し MockBrokerClient で動作します
  - 起動時に data/stop_requested.flag が存在すると起動をスキップします
  - Execution は data/execution.pid に PID を書きます（Run スクリプトが管理）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で別 DB を指定可能。環境変数 PAPER_TRADING_SQLITE_PATH を優先利用

- AI 機能（ライブラリ API）
  - news_nlp.score_news(conn, target_date, api_key=None)
    - DuckDB 接続と target_date（datetime.date）を渡すと ai_scores テーブルに書き込みます
    - api_key = None の場合は環境変数 OPENAI_API_KEY を参照
  - regime_detector.score_regime(conn, target_date, api_key=None)
    - market_regime テーブルへ冪等的に書き込みます
  - いずれも OpenAI 呼び出しを行うため OPENAI_API_KEY の設定が必要（無い場合は例外またはフォールバック）

---

## 運用に関する注意点

- Kill Switch
  - KillSwitch は Settings.kill_flag_path（デフォルト data/kill.flag）へ理由テキストを書き込むことで ExecutionEngine に停止を促します。KillSwitch はリスク条件（ドローダウン・ポジション上限等）に基づいて書き込みます。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると Execution 起動時に kill.flag を自動削除しますが、本番環境では危険です（デフォルト 0 推奨）。

- 停止フラグ / PID
  - data/stop_requested.flag が作られると run_monitoring と run_execution はそれを検出して安全に停止または起動を阻止します
  - run_execution は data/execution.pid に PID を書きます。system monitor はこの PID を見てプロセス生存を検査します。古い（stale）PID は自動削除されリスクログが残されます。

- DB マイグレーション
  - monitoring_db.init_monitoring_db は起動時に必要なテーブルとインデックスを作成し、必要に応じて軽微なカラム追加マイグレーションを行います（例: trade_logs.latency_ms, dashboard.peak_value）。

- ロギング
  - デフォルトのログレベルは LOG_LEVEL（環境変数, Settings.log_level）。run_* スクリプトは logging.basicConfig(level=logging.INFO) を使用します。

- プロセス優先度
  - run_monitoring / run_execution は起動時に set_process_priority("high") を呼び出します（platform に依存し動作しない場合は警告出力）。

---

## ディレクトリ構成（主なファイルと説明）

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / 設定管理（.env 自動読み込み、Settings クラス）
  - config_setup.py — .env 対話式ウィザード CLI
  - validate_config.py — 設定検証 CLI
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - utils/
    - process_priority.py — プロセス優先度・CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py — システム・データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常検出
    - risk_monitor.py — ドローダウン・ポジション数監視
    - monitoring_engine.py — 複数モニタ束ね（Polling loop / run_once 用メソッド）
    - alert_manager.py — LINE Push 通知（クールダウン管理）
    - kill_switch.py — Kill Switch ロジック（flag 書き込み）
  - execution/ (実装の一部はここでは省略)
    - order_repository.py, order_manager.py, reconciler.py, risk_manager.py, execution_engine.py, broker_factory.py, order_record.py など（発注・リスク管理）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数決定
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン計算・IC・統計サマリ
  - ai/
    - news_nlp.py — ニュースセンチメント LLM スコアリング（ai_scores へ書き込み）
    - regime_detector.py — マーケットレジーム判定（ma200 + LLM）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト

ルート（プロジェクト）
- .env, .env.local（環境変数ファイル）
- data/ — DB・PID・flag 等の配置先（デフォルト）
  - data/kabusys.duckdb
  - data/monitoring.db
  - data/paper_trading.db
  - data/execution.pid
  - data/kill.flag
  - data/stop_requested.flag

---

## 開発・拡張のヒント

- DuckDB と prices_daily / raw_financials / raw_news 等のテーブル設計に依存するため、Research / AI 機能を使うには事前に適切なデータをロードしてください。
- AI 機能（news_nlp, regime_detector）は OpenAI 呼び出しを伴うため、テストでは _call_openai_api をモックするとよいです（unittest.mock.patch を推奨）。
- Monitoring / Execution 間の安全な停止は kill.flag / stop_requested.flag / PID 管理に依存しているため、運用スクリプトでこれらを適切に管理してください。
- config/*.yaml（system_config.yaml 等）を用いる設計要素があるため、必要に応じて scripts/generate_config.py 等でテンプレート生成を行ってください（validate_config がファイル存在と YAML パースをチェックします）。

---

必要であればこの README をベースに「運用手順書」「デプロイ手順」「API リファレンス（関数別）」などのドキュメントを追加作成できます。どの情報をさらに詳述したいか教えてください。