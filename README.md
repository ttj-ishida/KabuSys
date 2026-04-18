# KabuSys

日本株向け自動売買システムのサブモジュール群（ライブラリ + 起動スクリプト群）。

この README はリポジトリ内の主要コンポーネントの概要、セットアップ手順、よく使うコマンド例、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は以下のような責務を持つモジュール群で構成されています。

- 注文実行エンジン（ExecutionEngine）
- 監視（Monitoring）・アラート・Kill Switch
- ポートフォリオ構築（銘柄選定・配分・ポジションサイズ）
- リサーチ（ファクター計算・特徴量探索）
- AI 支援（ニュース NLP によるセンチメント・レジーム判定）
- 開発用ユーティリティ（.env ウィザード、設定検証、検証レポート）

設計方針の例：
- 本番 / ペーパートレードを環境変数 `KABUSYS_ENV` で切替可能（`development` / `paper_trading` / `live`）
- Paper trading 時は MockBroker を使用し、監視 DB と分離した専用 SQLite を使う
- DuckDB を分析用 DB として使用
- OpenAI を用いた NLP 処理をサポート（API キー必須）

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py — ExecutionEngine 起動。`KABUSYS_ENV=paper_trading` の場合は MockBroker を使用。
  - run_monitoring.py — SystemMonitor を定期ポーリングして状態を記録、KillSwitch の評価等を行う。
- 設定関連
  - config_setup.py — 対話式ウィザードで `.env` を作成・更新
  - validate_config.py — 環境設定と config/*.yaml の事前検証
- 監視
  - monitoring/monitoring_db.py — SQLite による監視ログ永続化（table 作成・マイグレーション含む）
  - monitoring/system_monitor.py / trade_monitor.py / risk_monitor.py / monitoring_engine.py 等
  - KillSwitch（kill.flag）による ExecutionEngine 停止
- ポートフォリオ構築
  - portfolio/*.py — 候補選定、重み付け、セクター制約、ポジションサイズ計算（純粋関数）
- リサーチ
  - research/factor_research.py / feature_exploration.py — DuckDB を参照して各種ファクター・統計を計算
- AI（OpenAI）
  - ai/news_nlp.py — ニュースをまとめて OpenAI に投げセンチメントスコアを ai_scores テーブルへ書込
  - ai/regime_detector.py — ETF の MA200 とマクロニュースの LLM 結果を合成して市場レジーム判定
- ツール
  - tools/paper_verification_report.py — ペーパートレード DB を解析し検証レポートを生成
- 共通ユーティリティ
  - utils/logging_setup.py — 一貫したログ設定（stdout + 日次ローテーション）
  - utils/process_priority.py — プロセス優先度設定（Windows / POSIX 対応）
  - config.py — 環境変数 / .env の読み込みと Settings クラス

---

## セットアップ手順（ローカル向け）

1. Python 環境を準備（推奨: 3.10+）
2. 必要パッケージをインストール
   - 必須（主要）：duckdb, psutil, openai
   - 任意だが推奨：PyYAML（`validate_config.py` が config YAML を検証する場合）
   - 例（pip）:
     ```
     pip install duckdb psutil openai pyyaml
     ```
   - requirements.txt がある場合はそれを使ってください。

3. プロジェクトルートに `.env` を作成
   - 対話式ウィザード:
     ```
     python -m kabusys.config_setup
     ```
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - 主要なオプション:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - LOG_LEVEL（デフォルト: INFO）
     - OPENAI_API_KEY（AI 機能を使う場合に必須）
     - PAPER_FILL_MODE（paper_trading の注文約定挙動: instant|partial|never|reject、デフォルト: instant）
     - KILL_FLAG_CLEAR_ON_START（0/1、本番で 1 は危険）

4. 設定の妥当性を検証
   ```
   python -m kabusys.validate_config
   ```
   - `--strict` を付けると警告も失敗扱い（exit 1）になります。

5. データディレクトリの準備（必要なら）
   - デフォルトでは `data/`、`logs/` が使用されます。`setup_logging` が自動作成しますが権限等で失敗する環境では事前に作成しておくと安全です。

---

## 使い方（実行例）

- ExecutionEngine を起動（本番 / ペーパーは KABUSYS_ENV で切替）
  ```
  # 例: ペーパートレードで起動
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```

  動作のポイント:
  - `paper_trading` の場合、MockBroker を使用し、データは `PAPER_TRADING_SQLITE_PATH` に記録され本番 SQLite と分離されます。
  - 起動時に `data/stop_requested.flag` があると起動せず終了します。
  - 実行中は `data/execution.pid`（デフォルト）に PID を書くようになっています（Engine に渡される）。

- Monitoring を起動（SystemMonitor のポーリング）
  ```
  # デフォルトポーリング間隔 60 秒。環境変数で上書き可
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```

  動作のポイント:
  - `MONITOR_POLL_INTERVAL`（秒）でポーリング間隔を指定（デフォルト 60）。
  - 監視は Settings が示す sqlite_path（監視 DB）を使って永続化します（環境にかかわらず本番 sqlite_path を使用）。
  - 監視中に `data/stop_requested.flag` を検知するとループを終了します。

- Paper Trading 検証レポート生成（ツール）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を指定する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 機能
  - ニュース NLP / レジーム判定は OpenAI API を利用します。環境変数 `OPENAI_API_KEY` を設定してください。
  - プログラム的に呼ぶ場合:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

- Kill Switch / 手動停止フロー
  - KillSwitch は `Settings.kill_flag_path`（デフォルト: `data/kill.flag`）へ文字列を書き、ExecutionEngine に停止を促します。
  - `run_execution` / `run_monitoring` は `data/stop_requested.flag`（監視用スクリプト内で参照）を見て自ら終了する挙動を持ちます（運用上、stop フラグと kill.flag の使い分けを行ってください）。

---

## 重要な環境変数（抜粋）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

運用・挙動制御:
- KABUSYS_ENV: development | paper_trading | live
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
- DUCKDB_PATH: data/kabusys.duckdb（分析 DB）
- SQLITE_PATH: data/monitoring.db（監視 DB）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用 DB）
- PAPER_FILL_MODE: instant | partial | never | reject
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（デフォルト 60）
- OPENAI_API_KEY: OpenAI を使う機能で必須
- KILL_FLAG_CLEAR_ON_START: 0/1（本番で 1 は慎重に）

---

## ディレクトリ構成（主要ファイル）

リポジトリの `src/kabusys` に相当する主要モジュールを抜粋しています。

- kabusys/
  - __init__.py
  - config.py                      — 環境変数読み込みと Settings
  - config_setup.py                — .env 対話式ウィザード
  - validate_config.py             — 起動前設定検証
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート
  - ai/
    - news_nlp.py                   — ニュースを LLM でスコアリング
    - regime_detector.py            — 市場レジーム判定
  - monitoring/
    - monitoring_db.py              — SQLite 永続化層
    - monitoring_engine.py
    - system_monitor.py
    - risk_monitor.py
    - trade_monitor.py
    - kill_switch.py
    - alert_manager.py (※実装参照)
  - execution/                      — ExecutionEngine 関連（broker_factory, execution_engine, order_manager, risk_manager, reconciler, order_repository 等）
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
  - data/ (ランタイムで生成される / DB ファイルやフラグファイル置き場)
  - logs/ (ログファイル出力先)

（注）上記は抜粋です。実際のリポジトリには data / config / その他ユーティリティが含まれます。

---

## 運用上の注意・ベストプラクティス

- 本番環境（KABUSYS_ENV=live）では `KILL_FLAG_CLEAR_ON_START=0` を推奨します。自動クリアは危険です。
- `.env` は絶対に Git にコミットしないでください（config_setup が注意文を出力します）。
- OpenAI など外部 API 呼び出し周りはフェイルセーフ実装（失敗時のフォールバック）になっていますが、API キーやレート制限は運用で管理してください。
- ログはデフォルトで `logs/<app_name>.log` に出力され、日次ローテートされます。ディスク容量に注意してください。
- Paper trading は本番 DB と完全に分離された専用 SQLite を使用するため、検証に適しています。

---

## トラブルシュートのヒント

- 起動時に config の警告・エラーが出る場合:
  - `python -m kabusys.validate_config` を実行して指示に従って修正してください。
- DuckDB / SQLite ファイルの場所を変えたい場合は `.env` の `DUCKDB_PATH` / `SQLITE_PATH` を更新してください。
- 監視・実行プロセスの強制停止やデバッグ時は `data/stop_requested.flag` を作成すると run_execution/run_monitoring が検知して終了します（環境により運用ルールを定義してください）。
- OpenAI 関連で API の失敗が頻発する場合は API キー、ネットワーク、またはレート制限の再確認を。

---

この README はコードベースの主要点をまとめたものです。より詳細な設計方針やアルゴリズム仕様は各モジュール内の docstring やプロジェクト内ドキュメント（例: PortfolioConstruction.md, StrategyModel.md 等）を参照してください。必要であれば特定モジュールの利用例や API 使用方法のサンプルを追加で作成します。