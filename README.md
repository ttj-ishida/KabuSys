# KabuSys

日本株向け自動売買 / リサーチ基盤（KabuSys）のリポジトリ（README 日本語版）

以下はこのコードベースの要約ドキュメントです。プロジェクトの概要、機能、セットアップ方法、使い方、ディレクトリ構成を日本語でまとめています。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムおよびリサーチ用ユーティリティの集合です。  
主な目的は以下：

- 戦略に基づく銘柄選定・ポジション管理（ポートフォリオ構築）
- 発注・約定管理（ExecutionEngine）およびペーパートレーディング対応
- システム稼働監視（Monitoring）：リスク監視、Kill Switch、アラート連携
- DuckDB を用いたファクター計算・リサーチ機能
- OpenAI を用いたニュース NLP（センチメント）やレジーム判定の補助
- 各種ツール（.env ウィザード、設定検証、ペーパートレード検証レポート等）

設計方針として、
- 本番とペーパートレードは DB を分離して運用可能
- ルックアヘッドバイアスを避ける設計（日時参照の扱いに注意）
- フェイルセーフ（API 失敗時は安全側で継続）を重視

---

## 機能一覧（ハイレベル）

- 環境設定管理
  - .env 自動読み込み（プロジェクトルートが検出される場合）
  - 対話式ウィザードで .env を生成（`kabusys.config_setup`）
  - 設定検証 CLI（必須環境変数・YAML 等の検査）：`kabusys.validate_config`
- 実行コンポーネント
  - ExecutionEngine 起動スクリプト（`run_execution.py`） — 本番 / ペーパートレード対応
  - Monitoring 起動スクリプト（`run_monitoring.py`） — ポーリング監視・Kill Switch 判定
- データベース
  - DuckDB（分析用）
  - SQLite（監視・発注ログ等）
- モニタリング
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine
  - kill.flag による外部停止シグナル、stop_requested.flag によるループ停止
- ポートフォリオ構築（純粋関数群）
  - 銘柄選定、重み付け（等金額・スコア加重）、ポジションサイズ計算、セクター制約、レジーム乗数
- リサーチ
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン、IC 計算、統計サマリ
- AI（OpenAI）
  - ニュースセンチメント（`ai.news_nlp.score_news`）
  - 市場レジーム判定（`ai.regime_detector.score_regime`）
- ツール
  - Paper Trading 検証レポート（`kabusys.tools.paper_verification_report`）

---

## 必要要件・依存ライブラリ（代表例）

推奨 Python バージョン: 3.10+

主要依存（一部オプション）:
- duckdb
- psutil
- openai
- PyYAML（config 検証時に YAML の内容をチェックする場合）
- sqlite3（標準ライブラリ）

（実行環境に合わせて requirements.txt を用意して pip でインストールしてください）
例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリを取得して、Python 仮想環境を作成・アクティベートします。

2. 必要パッケージをインストールします（上記参照）。

3. 環境変数の準備
   - `.env` をプロジェクトルートに置くか、環境変数を直接設定します。
   - 対話式で .env を作る場合:
     ```
     python -m kabusys.config_setup
     ```
     ウィザードに従って入力すると `.env` が生成されます。

4. 設定検証（推奨）
   ```
   python -m kabusys.validate_config
   ```
   true/false ではなく exit code と標準出力で結果を出します。`--strict` を付けると警告も失敗扱いになります。

5. データディレクトリ
   - デフォルトでは `data/` 以下に SQLite / PID / フラグファイル等が置かれます。
   - 必要に応じて `.env` の `SQLITE_PATH`, `DUCKDB_PATH`, `PAPER_TRADING_SQLITE_PATH` を設定してください。

---

## 実行方法（使い方）

### 1) 監視プロセス起動（Monitoring）
- 起動:
  ```
  python -m kabusys.run_monitoring
  ```
- ポーリング間隔の上書き:
  - 環境変数 `MONITOR_POLL_INTERVAL`（秒、デフォルト 60）で変更できます。
  - 例: `MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring`
- 注意:
  - Monitoring は実装上「環境（KABUSYS_ENV）にかかわらず」`Settings.sqlite_path`（本番用）を使用して監視 DB を開きます（run_monitoring の挙動）。
  - 監視ループを外部から停止するには `data/stop_requested.flag` を作成します。

### 2) 実行エンジン起動（Execution）
- 起動:
  ```
  python -m kabusys.run_execution
  ```
- ペーパートレード:
  - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を使い、デフォルトで `data/paper_trading.db` を使用します（本番 DB とは分離）。
  - `PAPER_TRADING_SQLITE_PATH` を `.env` で上書き可能。
- 停止方法:
  - `data/stop_requested.flag` を作成するとエンジンが停止します。
  - Execution 側の PID ファイルはデフォルト `data/execution.pid`（`Settings.pid_file_path`）に保存されます。

### 3) .env 管理と検証
- 対話式作成:
  ```
  python -m kabusys.config_setup
  ```
- 検証:
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

### 4) Paper Trading 検証レポート
- 期間指定（例）:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
- DB 指定:
  ```
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```
- デフォルトは `PAPER_TRADING_SQLITE_PATH` 環境変数、なければ `data/paper_trading.db`。

### 5) AI 関連ユーティリティ（ライブラリ関数）
- ニューススコアリング:
  - 関数: `kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)`
  - DuckDB 接続 (`duckdb.connect(...)`) を渡して使います。
  - `api_key` が None の場合は環境変数 `OPENAI_API_KEY` を参照します。
- レジーム判定:
  - 関数: `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)`
  - 同様に DuckDB 接続と API キーを渡します。

（OpenAI API を使うため、`OPENAI_API_KEY` の設定が必要です）

---

## 重要な環境変数（主なもの）

- KABUSYS_ENV: execution の振る舞いを決める（`development` / `paper_trading` / `live`）。デフォルト `development`
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API 用（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
- SQLITE_PATH: SQLite（監視 DB）パス（デフォルト `data/monitoring.db`）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト `data/paper_trading.db`）
- LOG_LEVEL: ログレベル（`DEBUG`/`INFO`/...）
- LOG_DIR: ログの保存先（デフォルト `logs/`）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- MONITOR_POLL_INTERVAL: Monitoring ポーリング間隔（秒、run_monitoring 用）

その他、PAPER_FILL_MODE（`instant`/`partial`/`never`/`reject`）などもあります（Settings 参照）。

---

## ログ・ファイル・フラグ

- ログ: `kabusys.utils.logging_setup.setup_logging` により `stdout` と `logs/<app_name>.log`（日次ローテーション）へ出力
- PID ファイル: デフォルト `data/execution.pid`（Execution 起動時に使用）
- 停止フラグ:
  - `data/stop_requested.flag` — 起動スクリプト（monitoring / execution）はこのファイルが存在するとループを終了・停止する
  - `data/kill.flag` — Kill Switch（条件により作成） → Execution に対する停止シグナルとして使用
- DB マイグレーション: 起動時に monitoring DB の必要なカラム追加等を自動的に行う処理があります（`monitoring_db.init_monitoring_db`）

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                — 環境設定読み込み・Settings
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — Monitoring ループ起動スクリプト

monitoring/
- monitoring_db.py         — SQLite テーブル定義・永続化層
- system_monitor.py        — システム / データ鮮度監視
- trade_monitor.py         — （コードベースにある）発注/約定監視ロジック
- risk_monitor.py          — ドローダウン・ポジション上限監視
- kill_switch.py           — kill.flag を作成するロジック
- monitoring_engine.py     — 各 Monitor を束ねる

execution/
- broker_factory.py        — ブローカークライアント生成ファクトリ（Mock/実ブローカ切替）
- execution_engine.py      — ExecutionEngine 本体
- order_manager.py
- order_repository.py
- reconciler.py
- risk_manager.py

portfolio/
- portfolio_builder.py     — 銘柄選定・重み付け
- position_sizing.py       — 株数決定・スケーリング
- risk_adjustment.py       — セクターキャップ・レジーム乗数

research/
- factor_research.py       — モメンタム / ボラティリティ / バリュー等
- feature_exploration.py   — 将来リターン / IC / 統計サマリ

ai/
- news_nlp.py              — ニュース NLP（OpenAI）による銘柄センチメント
- regime_detector.py       — マクロ + ETF MA を組み合わせたレジーム判定

utils/
- logging_setup.py         — ログ設定ユーティリティ
- process_priority.py      — プロセス優先度 / CPU affinity 設定ユーティリティ

tools/
- paper_verification_report.py — ペーパートレード検証レポート生成スクリプト

data/（実行時に生成される想定）
- monitoring.db, paper_trading.db, kabusys.duckdb, execution.pid, kill.flag, stop_requested.flag など

---

## 開発上の注意点 / 運用上の注意

- KABUSYS_ENV が `live` の場合は本番運用になります。`validate_config` は本番に危険な設定（Kill Flag の自動クリア等）を警告します。必ず設定を確認してください。
- Monitoring と Execution の DB の取り扱いに注意：
  - Monitoring（`run_monitoring.py`）は Settings.sqlite_path（本番監視 DB）を使用します（環境に無関係）。
  - Execution（`run_execution.py`）は `KABUSYS_ENV=paper_trading` の場合ペーパー用 DB を使用します（分離）。
- OpenAI API 呼び出しはレート制限やネットワークエラーに対してエクスポネンシャルバックオフでリトライする実装ですが、API キーやコストには注意してください。
- ログディレクトリの作成に失敗した場合、コンソール出力のみになるようフェールバックします。

---

この README はコードベースの主要部を要約したものです。各モジュールの詳細や追加の運用手順はコード内の docstring / コメントと合わせて参照してください。必要であれば、特定モジュール（例: ExecutionEngine の起動オプション、broker の実装、TradeMonitor 詳細など）に関する追加ドキュメントを作成できます。