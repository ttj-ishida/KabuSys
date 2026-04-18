# KabuSys — 日本株自動売買システム

このリポジトリは日本株の自動売買（発注・モニタリング・リサーチ・Paper Trading 環境等）を目的としたモジュール群を収めています。各コンポーネントは疎結合に設計され、運用用スクリプト・設定ウィザード・検証ツール・解析ツールを含みます。

---

## 概要

- 実運用（live）、ペーパートレード（paper_trading）、開発（development）向けに環境分離された設計。
- ExecutionEngine（発注エンジン）と Monitoring（監視）を分離して実行可能。
- DuckDB / SQLite をデータストアとして利用。Paper Trading は本番 DB と分離して専用 SQLite を利用可能。
- AI（OpenAI）を用いたニュースセンチメントや市場レジーム判定機能を搭載（OpenAI API キー必須）。
- ポートフォリオ構築、ポジションサイジング、リスク調整など純粋関数群を提供（テスト容易）。

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py — ExecutionEngine の起動（KABUSYS_ENV により本番 / ペーパーを切替）
  - run_monitoring.py — SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔指定可）
- 設定関連
  - config_setup.py — .env を対話式に作成・更新するウィザード
  - validate_config.py — .env と config/*.yaml の起動前検証 CLI
  - config.Settings — 環境変数/設定管理
- 監視（Monitoring）
  - monitoring_engine.py — 各モニタを束ねるエンジン
  - system_monitor.py — システムリソース・データ鮮度・実行プロセス状態監視
  - trade_monitor.py（実装あり） — 注文ログ/約定監視（ソース参照）
  - risk_monitor.py — ドローダウン / ポジション上限監視
  - kill_switch.py — kill.flag による ExecutionEngine 停止シグナル
  - monitoring_db.py — SQLite を用いた永続化層（テーブル初期化 / 読み書き）
- Execution（発注）
  - execution_engine / order_manager / risk_manager / reconciler / broker_factory など（発注ワークフロー）
  - Paper Trading 用 MockBrokerClient をサポート（KABUSYS_ENV=paper_trading）
- 研究・解析（Research / Tools）
  - research.factor_research, research.feature_exploration — ファクター計算・IC 等
  - tools.paper_verification_report — Paper Trading 検証レポート生成スクリプト
- AI 関連
  - ai.news_nlp — ニュースを OpenAI で評価し ai_scores に書き込む
  - ai.regime_detector — マクロ + ETF 指標を組合せた市場レジーム判定

---

## セットアップ手順

前提: Python 3.9+（プロジェクトの pyproject.toml 等に合わせてください）

1. リポジトリをクローン
   ```
   git clone <this-repo>
   cd <this-repo>
   ```

2. 仮想環境を作成・有効化（例）
   - Unix / macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 依存ライブラリをインストール
   必要なパッケージの一例:
   - duckdb
   - psutil
   - openai
   - PyYAML（config ファイル検証に任意で必要）
   インストール例:
   ```
   pip install duckdb psutil openai PyYAML
   ```
   （開発モードでパッケージ化されていれば `pip install -e .`）

4. 初期設定 (.env) の作成
   対話式ウィザードを使う:
   ```
   python -m kabusys.config_setup
   ```
   完了後、`.env` が生成されます。重要な必須環境変数:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   （AI 機能利用時）OPENAI_API_KEY も設定してください。

5. 設定検証（任意）
   ```
   python -m kabusys.validate_config
   ```
   警告もエラーにしたい場合:
   ```
   python -m kabusys.validate_config --strict
   ```

6. データディレクトリ準備
   ログや DB のデフォルトパスは `data/` / `logs/`。必要に応じて作成してください（setup_logging は自動作成を試みますが、権限等で失敗する場合があります）：
   ```
   mkdir -p data logs
   ```

---

## 使い方

- ExecutionEngine（発注エンジン）を起動
  - 本番/ペーパーの切り替えは KABUSYS_ENV 環境変数で指定（.env で設定）。
    - development / paper_trading / live
  - 起動:
    ```
    python -m kabusys.run_execution
    ```
  - Paper Trading（DB を分離）:
    - KABUSYS_ENV=paper_trading を設定すると、MockBrokerClient が使用され、デフォルトで `data/paper_trading.db` に記録します。

  - 停止方法:
    - ExecutionEngine はプロセス内で `data/stop_requested.flag` の存在を監視しています。停止を要求するにはこのファイルを作成します（`run_execution.py` のループは stop flag を検出するとエンジン停止処理を行います）。

- Monitoring（監視ループ）を起動
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書きできます（デフォルト 60 秒）。
  - Monitoring は設定にかかわらず本番用の sqlite_path を使用して監視ログを残します（監視用 DB は Settings.sqlite_path）。
  - 監視ループも `data/stop_requested.flag` を検出すると終了します。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB: `data/paper_trading.db`。`--db` オプション、または環境変数 `PAPER_TRADING_SQLITE_PATH` で変更可。

- AI 関連（ニュース NLP / レジーム判定）
  - OpenAI API キーを環境変数 `OPENAI_API_KEY` に設定してから利用してください。
  - 機能は duckdb 接続と target_date を渡す関数 API として実装されています（スクリプトから呼び出す、または Engine 内でスケジュール実行される想定）。

- Kill Switch / Kill Flag
  - KillSwitch はリスク条件（ドローダウンやポジション上限等）に基づき `data/kill.flag` を生成して ExecutionEngine 停止を促します。
  - ExecutionEngine は `KILL_FLAG_CLEAR_ON_START` 設定を参照します（起動時に kill.flag を自動クリアするか、デフォルトは 0 = クリアしない）。

---

## よく使う環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- OPENAI_API_KEY — OpenAI API（ニュース NLP / レジーム判定で使用）
- KABUSYS_ENV — 実行環境（development / paper_trading / live）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR）
- MONITOR_POLL_INTERVAL — Monitoring ポーリング間隔（秒）

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数/設定管理
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度・CPU affinity 設定
  - monitoring/
    - monitoring_db.py — SQLite テーブル初期化 / 永続化 API
    - system_monitor.py — システム監視
    - trade_monitor.py — 注文／約定監視（実装あり）
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — Kill Switch 実装
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - alert_manager.py — アラート送信（LINE 等）（実装参照）
  - execution/  — ExecutionEngine, OrderManager, RiskManager, BrokerFactory 等
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

## 運用上の注意点

- 本番環境（KABUSYS_ENV=live）では kill.flag / stop flag の取り扱いに十分注意してください。`KILL_FLAG_CLEAR_ON_START` は本番で 0（自動クリアしない）を推奨します。
- Paper Trading は本番 DB と分離されますが、設定ミスで DB が上書きされないよう .env の `SQLITE_PATH` / `PAPER_TRADING_SQLITE_PATH` を確認してください。
- ログはデフォルトで `logs/<app_name>.log` に日次ローテートで保存されます。ログディレクトリ作成に失敗した場合は標準出力のみになります。
- OpenAI API を利用するパーツは外部 API 呼び出しに依存するため、API エラーやレート制限に対するフェイルセーフが組み込まれていますが、運用時にはキー管理とコストに注意してください。

---

## トラブルシューティング

- .env の自動読み込みを無効化したい（テスト時など）場合:
  ```
  KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- 設定検証で警告やエラーが出る場合は `python -m kabusys.validate_config` の出力に従って修正してください。
- Monitoring / Execution の即時停止が必要な場合は `data/stop_requested.flag` を作成してください。KillSwitch が検出した際は `data/kill.flag` が生成されます（自動クリア設定に注意）。

---

この README はリポジトリ内の主要なモジュール群（設定管理、起動スクリプト、監視、Execution、研究、AI）を基に作成しました。各モジュールの詳細な使用方法や API（関数シグネチャ、返り値）についてはソースコード内のドキュメント文字列（docstring）を参照してください。必要であれば、さらに導入ガイドや運用手順書（Runbook）を作成します。