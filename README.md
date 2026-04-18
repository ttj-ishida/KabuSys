# KabuSys

日本株自動売買システムの軽量コンポーネント群。バックテストや研究、ペーパートレード、本番実行・監視、AIベースのニュースセンチメント評価などを含むモジュール化された実装です。

Version: 0.1.0

---

## 概要

このリポジトリは、以下の主要機能を持つコンポーネント群で構成されています。

- ExecutionEngine：発注・注文管理・リスク管理を行う実行エンジン（本番 / ペーパートレード対応）
- Monitoring：システム稼働状況、データ鮮度、注文状態、リスクを監視しアラート／Kill Switch を管理
- Research：DuckDB を用いたファクター計算・特徴量探索
- Portfolio：銘柄選定・重み付け・ポジションサイズ決定（純粋関数群）
- AI：ニュースの NLP スコアリング / 市場レジーム判定（OpenAI を利用）
- Tools：Paper Trading 用の検証レポート生成スクリプト 等
- utils / config：ログ設定・プロセス優先度設定、環境設定読み込みなど共通ユーティリティ

設計方針の例：
- DuckDB / SQLite を用いたローカル DB 運用
- 環境変数 / .env による設定管理（対話式ウィザードあり）
- 本番（live）とペーパートレード（paper_trading）を明確に分離
- LLM 呼び出しは失敗に対してフォールバック（フェイルセーフ）する実装

---

## 主な機能一覧

- 環境セットアップウィザード（python -m kabusys.config_setup）
- 設定検証 CLI（python -m kabusys.validate_config）
- ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - KABUSYS_ENV=paper_trading 時は MockBrokerClient を用い、data/paper_trading.db に記録
- Monitoring 起動スクリプト（python -m kabusys.run_monitoring）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
- MonitoringDB（SQLite ベース）: system_status / trade_logs / positions / risk_logs / dashboard
- RiskMonitor / TradeMonitor / SystemMonitor と KillSwitch、AlertManager の統合
- research モジュール: モメンタム / ボラティリティ / バリュー等のファクター計算
- ai モジュール: ニュースセンチメント評価（OpenAI）と市場レジーム判定
- tools.paper_verification_report: ペーパートレードの検証レポート生成

---

## 必要な依存パッケージ（例）

最低限想定されるパッケージ（環境に合わせてバージョン指定してください）:

- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（config/*.yaml の検証を行う場合、任意）
- （SQLite は標準ライブラリで利用）

インストール例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

※ requirements.txt が用意されている場合はそちらを利用してください。

---

## セットアップ手順

1. リポジトリをクローン
2. 仮想環境作成・依存インストール（上記参照）
3. 初期 .env を作成
   - 対話式ウィザードを使う:
     ```
     python -m kabusys.config_setup
     ```
   - もしくは `.env.example` を参考に `.env` を作成して環境変数を設定
4. 設定検証:
   ```
   python -m kabusys.validate_config
   ```
   - `--strict` を付けると警告も失敗（exit 1）扱いになります
5. データディレクトリやログディレクトリを作成（自動で作られることが多いが、権限等に注意）
   - デフォルト: `data/`（SQLite 等）, `logs/`（ログ）

---

## 環境変数（主なもの）

Settings クラスで参照される主要環境変数と既定値（必要に応じて .env に設定）:

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用
- KABU_API_PASSWORD — kabuステーション API パスワード

任意 / デフォルト:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト `development`
  - paper_trading: 発注は MockBrokerClient を使用し、別 DB（data/paper_trading.db）に記録
- DUCKDB_PATH — デフォルト `data/kabusys.duckdb`
- SQLITE_PATH — デフォルト `data/monitoring.db`
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 DB（default `data/paper_trading.db`）
- LOG_LEVEL — `INFO`（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR — ログ格納ディレクトリ（デフォルト `logs/`）
- PID_FILE_PATH — ExecutionEngine の pid ファイル（デフォルト `data/execution.pid`）
- KILL_FLAG_PATH — Kill Switch の flag ファイルパス（デフォルト `data/kill.flag`）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（`0`/`1`、デフォルト `0`）
- PAPER_FILL_MODE — ペーパートレードの約定モード（`instant` | `partial` | `never` | `reject`）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring で使用、デフォルト 60）

OpenAI 関連:
- OPENAI_API_KEY — ニュースNLP / regime_detector で使用（必要に応じて）

その他の補助:
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 本番のアラート通知用（任意）

設定は .env（git 管理しない）に保存して利用してください。config_setup は .env の生成を対話的に支援します。

---

## 使い方（よく使うコマンド）

- 環境設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine を起動
  - 通常（ローカル開発）
    ```
    python -m kabusys.run_execution
    ```
  - ペーパートレード（MockBroker を使用、paper DB に記録）
    ```
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```

- Monitoring を起動
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を変更したい場合:
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB 指定:
    ```
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
    ```

補足:
- 実行中の停止は実行スクリプトが見るフラグファイルで制御されます。
  - 停止要求（ランタイム側）: `data/stop_requested.flag` を作成すると run_monitoring / run_execution は検知して停止します（run_execution は起動時に既に存在すれば起動しない）。
  - Kill Switch（監視側から ExecutionEngine に対する安全停止）: `data/kill.flag` が書き込まれると ExecutionEngine は停止対象になります（KillSwitch が評価・書き込み）。

---

## 実装上の注意点 / 運用メモ

- データ分離:
  - paper_trading 環境では `paper_sqlite_path`（デフォルト `data/paper_trading.db`）を使用し、本番用 SQLite と分離されます。
- ロギング:
  - 共通ユーティリティ `kabusys.utils.logging_setup.setup_logging` を起動スクリプトから呼び出します。ログは stdout と日次ローテーションファイル（logs/<app_name>.log）へ出力されます。
- プロセス優先度:
  - 起動時にプロセス優先度を `high` に設定しようとします（psutil を使用）。権限不足時は警告が出ますが継続します。
- OpenAI 利用:
  - API 呼び出しでの失敗はリトライ／フェイルセーフ実装有り。API キーが未設定ならエラー（明示的に必要な関数呼び出しでは ValueError）。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は存在しないテーブルとカラムを追加する冪等処理を行います。既存 DB に対してカラム追加のマイグレーションを内包しています。
- テストしやすさ:
  - 多くの外部依存呼び出し（OpenAI 呼び出し等）はモックしやすい設計となっています（内部呼び出しラッパー関数経由）。

---

## ディレクトリ構成（抜粋）

以下は主要ファイル／ディレクトリと役割です。

- src/kabusys/
  - __init__.py — パッケージ定義（version 等）
  - config.py — 環境変数 / Settings の読み込み・検証ロジック
  - config_setup.py — .env を対話式に生成するウィザード
  - validate_config.py — 起動前の設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py — SQLite を用いた永続化層（テーブル定義・CRUD）
    - monitoring_engine.py — 各モニタを束ねるエンジン
    - system_monitor.py — システム状態・データ鮮度監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — Kill Switch 制御（flag ファイル）
    - (その他: trade_monitor, alert_manager 等)
  - execution/
    - execution_engine.py, order_manager.py, order_repository.py, risk_manager.py, reconciler.py, broker_factory.py
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数計算
    - risk_adjustment.py — セクター制限・レジーム係数
  - research/
    - factor_research.py — モメンタム/ボラティリティ/バリュー等
    - feature_exploration.py — 将来リターン・IC 計算など
  - ai/
    - news_nlp.py — ニュースセンチメント（OpenAI）
    - regime_detector.py — 市場レジーム判定
  - data/ (実行時生成想定)
    - monitoring.db / paper_trading.db / execution.pid / kill.flag / stop_requested.flag
  - logs/ (実行時生成想定)
    - execution.log, monitoring.log 等

---

## 開発・デバッグヒント

- 設定に不安がある場合はまず：
  ```
  python -m kabusys.config_setup
  python -m kabusys.validate_config
  ```
- DuckDB を使った研究処理は DB スキーマ（prices_daily / raw_financials / raw_news 等）に依存します。テスト用データで関数を動作確認してください。
- OpenAI 呼び出しをユニットテストする場合、該当モジュールの内部 API 呼び出し（_call_openai_api など）を patch してモックする設計になっています。
- ログ出力は stdout とファイルの両方に出ます。デバッグ時は LOG_LEVEL=DEBUG を設定してください。

---

## ライセンス / 貢献

本プロジェクトのライセンス情報や貢献ガイドラインがある場合は別途 LICENSE / CONTRIBUTING を参照してください。

---

README は実装済みコードを基にした概要と操作手順のまとめです。実行環境や追加の運用ルール（運用時の監視・バックアップ・シークレット管理等）は別途整備してください。質問や、README に追記して欲しい項目があれば教えてください。