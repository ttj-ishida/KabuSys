# KabuSys

日本株自動売買システムの主要モジュール群を収めたリポジトリの README です。  
この README はプロジェクトの概要、機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買 / リサーチ基盤です。主要コンポーネントは以下を含みます。

- ExecutionEngine：発注・注文管理・リスク管理を担う実行系
- Monitoring（監視）：システム状態・注文ログ・リスクの監視、Kill Switch による安全停止
- Portfolio モジュール：候補選定・重み付け・ポジションサイズ計算等のポートフォリオ構築ロジック
- Research：ファクター計算・特徴量探索・IC 計算などの研究用ツール
- AI モジュール：OpenAI を用いたニュースセンチメントや市場レジーム判定
- ツール群：ペーパートレード検証レポート生成、設定ウィザード、設定検証 CLI など

設計方針として、DB（DuckDB / SQLite）を用いたオフライン計算やログ永続化、外部 API 呼び出しは明示的に扱いフェイルセーフにすることを重視しています。

---

## 主な機能一覧

- システム監視（CPU / メモリ / ディスク / プロセス健全性）
- 注文ログの収集・監査（trade_logs）
- リスク監視（ドローダウン、ポジション上限など）と Kill Switch（フラグファイルで ExecutionEngine 停止）
- 発注フロー（Broker クライアントは本番/ペーパートレードで切替）
- ポートフォリオ構築：候補選定、等加重/スコア加重、リスクベースのポジションサイズ計算
- リサーチ：Momentum/Volatility/Value ファクター計算、将来リターン・IC 計算
- OpenAI を用いたニュースのセンチメントスコアリング（ai.news_nlp）および市場レジーム判定（ai.regime_detector）
- ペーパートレード用の検証レポート生成ツール
- 設定ウィザード（.env 作成支援）と設定検証 CLI

---

## 前提条件 / 必要パッケージ

- Python 3.8+（ソースは型ヒントに | 演算子を使っていますが、future annotations により 3.8 以降で動作します。実運用では 3.10 以上を推奨します）
- 必須パッケージ（少なくともプロダクションで使う場合）:
  - duckdb
  - psutil
  - openai
- 開発・追加機能で便利なもの:
  - PyYAML（config/*.yaml の内容検証に使用）
- 例（pip でインストール）:
  - pip install duckdb psutil openai PyYAML

※ 実運用で必要な Broker クライアント実装や外部 API 資格情報は別途用意してください。

---

## セットアップ手順

1. リポジトリをクローンして Python 環境を用意します。
   - python -m venv .venv
   - source .venv/bin/activate（Windows は .venv\Scripts\activate）

2. 必要パッケージをインストールします（例）:
   - pip install duckdb psutil openai PyYAML

3. 環境変数の初期化（.env 作成）:
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - 手動で .env を作る場合はルートに `.env` を作成し、`.env.example` を参考に必要なキーを設定します。

4. 設定検証（起動前チェック）:
   - python -m kabusys.validate_config
     - --strict を付けると警告も FAIL 扱いになります。

5. データディレクトリとログディレクトリの確認（必要に応じて作成）:
   - デフォルトの SQLite / DuckDB / logs は `data/` / `logs/` 配下です。`LOG_DIR` 環境変数でログ先を変更できます。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuステーション API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時に必須）
- KABUSYS_ENV: 実行環境（development | paper_trading | live、デフォルト: development）
  - paper_trading を選ぶと ExecutionEngine は専用の paper DB を使用します
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードの整定（instant|partial|never|reject、デフォルト: instant）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- LOG_DIR: ログ保存ディレクトリ（デフォルト: logs）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: Kill Switch のフラグファイル（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト: 60）

---

## 使い方（主要コマンド）

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- ExecutionEngine（取引実行）起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に書き込み
    - 起動時に data/stop_requested.flag が存在すると起動しません
    - 実行中に stop フラグが作成されるとエンジンを停止します
    - PID ファイルは data/execution.pid（デフォルト）に書き込まれます

- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - 挙動:
    - モニタリング用の SQLite DB（設定の sqlite_path）にイベントを記録
    - ポーリング間隔は MONITOR_POLL_INTERVAL（秒、デフォルト 60）
    - data/stop_requested.flag を検知するとループを終了します
    - 監視は本番 sqlite_path を環境にかかわらず使用します（監視は本番 DB を参照）

- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI スコアリング / レジーム判定（プログラムから呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API を利用するため OPENAI_API_KEY を設定してください

- ログ出力
  - setup_logging により stdout と 日次ローテートされたログファイル (`logs/<app_name>.log`) に出力されます

---

## 停止・Kill スイッチの仕様

- stop のためのフラグ:
  - data/stop_requested.flag: run_monitoring / run_execution が検知して安全に停止
  - data/kill.flag: ExecutionEngine に対して停止を指示する Kill Switch（監視側が書き込む）
- kill.flag はゼロサイズでなく理由文字列を格納します。既に存在すれば再書き込みしません（冪等）。
- kill.flag をクリアする（起動時に自動クリアさせる設定は危険）:
  - 手動でファイルを削除するか、KillSwitch.clear() を呼ぶ処理で削除できます
- 注意: 本番環境で KILL_FLAG_CLEAR_ON_START=1 を設定することは推奨されません（安全性低下）

---

## 推奨ワークフロー（初回起動例）

1. .env を作成（python -m kabusys.config_setup）
2. 設定検証（python -m kabusys.validate_config）
3. DuckDB / SQLite の初期データを用意（データロード処理は別途実行）
4. 監視プロセスを起動（推奨順）
   - python -m kabusys.run_monitoring &
5. ExecutionEngine を起動
   - python -m kabusys.run_execution &
6. 運用中は logs/ 以下のログと data/monitoring.db のテーブル（system_status, trade_logs, risk_logs, positions, dashboard）を監視

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / Settings
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py (存在する場合)
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/                       — 実行時に利用するファイル（.pid, .flag, DB 等、リポジトリに含めないこと）

（注）上記はプロジェクトの主要モジュールを抜粋したツリーです。実際のリポジトリにはさらに補助モジュールやテスト、スクリプトが含まれる可能性があります。

---

## 開発・運用上の注意

- .env は機密情報を含むため、絶対に Git 等にコミットしないでください。
- 本番運用（KABUSYS_ENV=live）の場合、外部 API キーや通知設定（LINE 等）を必ず確認してください。validate_config の live 向けチェックが警告を出します。
- AI (OpenAI) を使う機能は API 利用料とレイテンシ、失敗時のフォールバックを考慮して運用してください（score_news / score_regime はフェイルセーフ化されています）。
- 監視 / 発注ロジックはファイルフラグと PID ベースで制御されます。運用スクリプトや Cron / Systemd 等と組み合わせる際はこれらの動作を理解した上で導入してください。

---

もし README に追加したいコマンドや具体的な設定例（.env のテンプレート、systemd ユニットサンプル等）があれば教えてください。必要に応じて追記・例示します。