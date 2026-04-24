# KabuSys

日本株向け自動売買システム（ライブラリ／実行スクリプト群）

このリポジトリは、シグナル生成 → ポートフォリオ構築 → 発注（ExecutionEngine） → 監視（Monitoring）までを含む自動売買プラットフォームのコア部分です。研究用ファクター計算、ペーパートレード検証、ニュースNLP（OpenAI）連携などのコンポーネントを備えています。

バージョン: 0.1.0

---

## 主な機能

- ExecutionEngine
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - ブローカークライアントファクトリ（MockBroker を含む）
  - 注文管理、リスク制御、約定/再照合ロジック（Engine、OrderManager、RiskManager 等）

- Monitoring（監視）
  - システムリソース監視（CPU / メモリ / ディスク）
  - データ鮮度チェック（DuckDB prices_daily 参照）
  - 注文滞留・約定異常・リスク（ドローダウン / ポジション上限）監視
  - Kill Switch（条件成立時に data/kill.flag を書き出し ExecutionEngine を停止）
  - ログ永続化（SQLite: monitoring.db）

- Portfolio / Position Sizing
  - 候補選定（スコア順 / 上位N）
  - 等分配・スコア加重配分
  - リスクベースの株数計算（lot rounding、aggregate cap 処理）
  - セクターキャップ、レジーム乗数

- Research
  - ファクター計算（Momentum / Value / Volatility 等）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ

- AI（OpenAI）連携
  - ニュース記事のセンチメントスコアリング（ai_scores テーブルへの書き込み）
  - 市場レジーム判定（ma200 とマクロセンチメントの合成）
  - 再試行・JSON バリデーション等の堅牢化された実装

- ユーティリティ
  - 設定ウィザード（.env 生成 / 更新）
  - 設定検証 CLI（.env と config/*.yaml のチェック）
  - ペーパートレード検証レポート生成スクリプト

---

## 要件（例）

- Python 3.10+
- 推奨パッケージ（一例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で必要）
- 実行環境により追加の依存が必要になる場合があります。requirements.txt が用意されていればそれを使用してください。

（リポジトリに requirements.txt がない場合は上記パッケージを pip でインストールしてください）

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化する。

2. 必要パッケージをインストールする（上記参照）。

3. .env を作成する
   - 対話式ウィザード:
     ```
     python -m kabusys.config_setup
     ```
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - OpenAI を使う場合:
     - OPENAI_API_KEY（必要）

4. 設定検証:
   ```
   python -m kabusys.validate_config
   ```
   - --strict を付けると警告もエラー扱いになります。

5. 必要に応じて data/ ディレクトリを作成（DB ファイルやフラグファイルを格納）:
   - デフォルト DB / ファイル:
     - DuckDB: data/kabusys.duckdb
     - SQLite（監視）: data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - PID/flag: data/execution.pid, data/kill.flag, data/stop_requested.flag

---

## 環境変数（主要なもの）

- KABUSYS_ENV: 実行環境（development | paper_trading | live）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視 DB）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードのフィルモード（instant|partial|never|reject）
- LOG_LEVEL: ログレベル（DEBUG|INFO|...）
- LOG_DIR: ログ出力先ディレクトリ（デフォルト: logs/）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、run_monitoring の挙動を上書き）

監視・停止関連:
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START などは Settings 経由で取得されます。

---

## 使い方

- ExecutionEngine を起動（本番 / ペーパーは KABUSYS_ENV で切り替え）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録して本番 DB と分離します。
  - 起動前に data/stop_requested.flag が存在すると起動をスキップします（停止フラグ）。

- Monitoring を起動（ポーリング監視）
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト: 60 秒）。
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（監査用途のため）。

- 設定ウィザード（.env 生成 / 更新）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証 CLI
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パスは --db で上書き可能。また環境変数 PAPER_TRADING_SQLITE_PATH を使用できます。

- AI ニューススコアリング（プログラム的に）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続と対象日を渡して呼び出します。api_key が None の場合は環境変数 OPENAI_API_KEY を参照します。

- 市場レジーム判定（プログラム的に）
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

- テスト用に各モジュールをインポートして個別実行（ex. MonitoringEngine.run_once など）できます。

---

## ログとデータ

- ログ: デフォルトで logs/<app_name>.log に日次ローテートで保存されます（LOG_DIR で変更可）。
- 監視データ（永続化）: SQLite（monitoring.db）に system_status / trade_logs / positions / risk_logs / dashboard 等のテーブルを作成します。
- DuckDB: 研究・ファクター計算用データ（prices_daily, raw_financials, raw_news 等）を格納します。

---

## 停止・Kill Switch の動作

- Stop（運用停止）:
  - data/stop_requested.flag を作成すると run_execution / run_monitoring のループが停止・起動防止を行います。
- Kill Switch（自動停止トリガ）:
  - RiskMonitor 等が条件を満たすと KillSwitch が data/kill.flag を作成します。ExecutionEngine はこのファイルの存在を検出して安全停止処理を行います。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag をクリアします（本番環境では推奨されません）。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py — 環境変数 / 設定取得ロジック
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — Monitoring 起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py — ニュース NLP（OpenAI）によるスコアリング
  - regime_detector.py — 市場レジーム判定
- monitoring/
  - monitoring_db.py — SQLite 永続化層（schema と CRUD）
  - system_monitor.py — システム状態・データ鮮度監視
  - trade_monitor.py — (滞留注文・約定異常の検出) ※実装参照
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - monitoring_engine.py — 各 Monitor を束ねるオーケストレータ
  - kill_switch.py — kill.flag の読み書きユーティリティ
  - alert_manager.py — (LINE 等への通知管理) ※実装参照
- execution/
  - execution_engine.py — ExecutionEngine 本体
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
- research/
  - factor_research.py, feature_exploration.py
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート
- utils/
  - logging_setup.py — 共通ログ設定
  - process_priority.py — プロセス優先度 / CPU affinity 設定

トップレベル（プロジェクトルート）:
- data/ (DB、PID、flag 等を配置する実行時用ディレクトリ)
- logs/ (ログファイル)
- config/ (yaml 設定雛形: system_config.yaml 等、generate スクリプトで生成されることを想定)

---

## 開発 / トラブルシュートのヒント

- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml を基準）を探索して行われます。テストで自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- run_monitoring は MONITOR_POLL_INTERVAL 環境変数で間隔を上書きできます（秒）。不正な値が与えられるとデフォルト 60 秒にフォールバックします。
- process priority / CPU affinity の設定は psutil を使用します。権限不足や OS 非対応の場合は警告が出てスキップされます。
- OpenAI API 連携部分はリトライやレスポンスバリデーションを備えていますが、API キーや利用制限に注意してください。
- DB スキーマは init_monitoring_db() によって冪等に作成・マイグレーションされます。

---

必要であれば、README にインストール用の requirements.txt の雛形、より詳細な実行例、各設定ファイル（config/*.yaml）の説明、単体テストの実行方法などを追記できます。どの情報を優先して追加しますか？