# KabuSys

日本株向け自動売買プラットフォームの一部をまとめたコードベースです。本 README はコード内の主要コンポーネント・使い方・セットアップ手順・ディレクトリ構成の要約を日本語でまとめたものです。

注意: 実行スクリプトはモジュールとして起動することを想定しています（例: `python -m kabusys.run_execution`）。パッケージ化していない場合はリポジトリルートで `PYTHONPATH=src` を設定して実行してください。

## プロジェクト概要

KabuSys は以下の主な機能群を備えた自動売買システムのコア実装例です：

- Execution: 発注エンジン（本番 / ペーパートレード対応）
- Monitoring: システム稼働監視、トレードログ・リスク監視、Kill Switch
- Portfolio: 銘柄選定 / ウェイト計算 / ポジションサイジング
- Research: ファクター計算・特徴量探索
- AI: ニュースセンチメント評価（OpenAI）・レジーム判定
- Tools: ペーパートレード検証レポート等のユーティリティ

設計上のポイント：
- 環境変数（.env / .env.local）で設定を管理（自動読み込みあり）
- DuckDB（分析） + SQLite（監視 / 発注履歴）を併用
- OpenAI クライアントを使った NLP モジュール（API キー必須）
- ログは共通ロギングユーティリティで stdout + ローテートファイル出力

---

## 主な機能一覧

- 実行エンジン起動スクリプト
  - run_execution: ExecutionEngine を起動。`KABUSYS_ENV=paper_trading` 時は MockBrokerClient を使用し専用 DB に記録
- 監視（ポーリング）起動スクリプト
  - run_monitoring: SystemMonitor のポーリングループを起動。ポーリング間隔は環境変数で上書き可能
- 設定管理
  - config_setup: 対話式 .env 作成ウィザード
  - validate_config: .env および config/*.yaml の検証 CLI
- 監視コンポーネント
  - system_monitor, trade_monitor, risk_monitor, monitoring_engine, kill_switch, alert_manager
- ポートフォリオ構築
  - 候補選定、等配分/スコア配分、セクター制限、レジーム乗数、株数計算（単元丸め、aggregate cap）
- リサーチ
  - ファクター（モメンタム / ボラティリティ / バリュー）計算、将来リターン、IC 計算、統計要約
- AI（OpenAI）
  - news_nlp: ニュース記事から銘柄別センチメントスコアを生成し ai_scores テーブルへ書込み
  - regime_detector: マクロ記事 + ETF MA200 を使って市場レジーム判定
- ツール
  - paper_verification_report: ペーパートレード DB を解析し PASS/FAIL レポート生成

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローンし、作業ディレクトリをプロジェクトルートにする。
2. Python 環境を作成し依存パッケージをインストール（必要に応じて）：

   必須パッケージ例:
   - duckdb
   - psutil
   - openai
   - （開発時）PyYAML（`validate_config` の YAML 検証に使用）

   例:
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb psutil openai pyyaml
   ```

3. 実行方法（開発時、パッケージ未インストールの場合）:
   - Python のモジュール検索パスに `src` を追加して実行:
     ```
     PYTHONPATH=src python -m kabusys.config_setup
     PYTHONPATH=src python -m kabusys.validate_config
     PYTHONPATH=src python -m kabusys.run_execution
     PYTHONPATH=src python -m kabusys.run_monitoring
     PYTHONPATH=src python -m kabusys.tools.paper_verification_report
     ```
   - パッケージ化した場合は `pip install -e .` などでインストール後に `python -m kabusys.run_execution` 等で実行できます。

4. 初期設定:
   - `.env` ファイルをプロジェクトルートに作成。簡易作成はウィザードを実行:
     ```
     PYTHONPATH=src python -m kabusys.config_setup
     ```
   - `.env` の自動読み込みはデフォルトで有効（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - （OpenAI を使う場合）OPENAI_API_KEY

5. デフォルトのファイルパス（.env 未設定時のデフォルト）:
   - DuckDB: data/kabusys.duckdb
   - SQLite（監視）: data/monitoring.db
   - Paper trading SQLite: data/paper_trading.db
   - ログディレクトリ: logs/
   - PID / Kill flag: data/execution.pid, data/kill.flag, data/stop_requested.flag

---

## 使い方（主なコマンド）

- 環境ウィザード（.env 作成）
  ```
  PYTHONPATH=src python -m kabusys.config_setup
  ```

- 設定検証
  ```
  PYTHONPATH=src python -m kabusys.validate_config
  PYTHONPATH=src python -m kabusys.validate_config --strict
  ```

- ExecutionEngine 起動（本番 or paper_trading に応じて挙動が変わる）
  ```
  PYTHONPATH=src python -m kabusys.run_execution
  ```
  挙動:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 用 SQLite に記録（本番 DB と完全分離）
  - 起動時に data/stop_requested.flag の有無を確認。存在する場合は起動せず終了。
  - 実行中に data/stop_requested.flag が作成されるとエンジンを停止する。
  - PID ファイル: data/execution.pid

- Monitoring のポーリング起動
  ```
  PYTHONPATH=src python -m kabusys.run_monitoring
  ```
  オプション・挙動:
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可（デフォルト 60 秒）
  - Monitoring は KABUSYS_ENV にかかわらず production の sqlite_path を使用（監視 DB は共通）
  - 監視ループの停止は data/stop_requested.flag の作成で行う

- Paper Trading 検証レポート
  ```
  PYTHONPATH=src python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  デフォルト DB: data/paper_trading.db（環境変数 `PAPER_TRADING_SQLITE_PATH` または `--db` で指定可）

- AI / レジームスコア、ニューススコアの呼び出し
  - モジュール関数を直接呼ぶ形が基本（DuckDB 接続 + target_date + api_key を引数で渡す）
  - 例（コード内 API）:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

---

## 主要設定項目（代表）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）

注意: Settings クラスは必須環境変数が未設定だと起動時に例外を投げます。validate_config を事前に実行することを推奨します。

---

## ログ・運用関係

- ロギング: kabusys.utils.logging_setup.setup_logging で統一管理
  - stdout（StreamHandler）と日次ローテーションファイル（logs/<app_name>.log）を設定
  - デフォルトログディレクトリ: logs/
- プロセス優先度: kabusys.utils.process_priority.set_process_priority("high"|"normal"|"low") を使用
- 停止フラグ:
  - data/stop_requested.flag: run_execution/run_monitoring のループ停止用（運用側で作成）
  - data/kill.flag: KillSwitch が書き込むことで ExecutionEngine 停止を指示（リスク発動時）
- PID ファイル:
  - data/execution.pid に ExecutionEngine の PID を出力（起動スクリプトで使用）

---

## ディレクトリ構成（概要）
以下はリポジトリ内の主要モジュールとファイルの階層（抜粋）です。

- src/kabusys/
  - __init__.py
  - __version__ 定義
  - config.py                — 環境変数 / .env ロードと Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity
  - execution/               — 発注関連（Engine, OrderManager 等）
  - monitoring/
    - monitoring_db.py       — 監視 DB 層（SQLite）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
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
  - tools/
    - paper_verification_report.py

---

## 開発者向けメモ / 注意点

- .env の自動読み込みは、プロジェクトルート（.git または pyproject.toml を基準）を探索して行われます。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- Monitoring の DB 初期化（テーブル作成 / マイグレーション）は `init_monitoring_db` で行われ、冪等に設計されています。
- OpenAI を使う AI モジュールは API リトライ、レスポンスバリデーション、スコアのクリッピング等のフェイルセーフを含みますが、API キーの漏洩防止に注意してください。
- Production（KABUSYS_ENV=live）では kill flag の自動クリア設定（KILL_FLAG_CLEAR_ON_START）を 0 にすることを推奨します（安全策）。
- DuckDB / SQLite のパスはデフォルトで `data/` 下に置かれます。バックアップ・権限に注意してください。

---

もし README の内容を CI 実行例、サンプル .env、より詳細な API ドキュメント（個別モジュールの public 関数一覧やシーケンス図）に拡張したい場合は、どの領域を優先して拡張するか教えてください。