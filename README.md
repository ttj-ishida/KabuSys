# KabuSys

日本株向け自動売買システムの軽量実装（ライブラリ + 起動スクリプト群）。

このリポジトリは、戦略研究・ファクター計算、ポートフォリオ構築、発注エンジン（ExecutionEngine）、監視/アラート、AI を使ったニュースセンチメント評価などのコンポーネントを含むモジュール群で構成されています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的としたコンポーネント群を提供します。

- ファクター計算・リサーチ（DuckDB を用いた prices_daily / raw_financials 参照）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- ExecutionEngine（発注ロジック、リスク管理、オーダー管理、リコンシリエーション等）
- 監視（System / Trade / Risk のポーリング、Kill Switch）
- AI モジュール（OpenAI を用いたニュースセンチメント、レジーム検知）
- ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード/検証等）
- 開発用ツール（Paper Trading の検証レポート生成等）

設計上の特徴:
- 設定は環境変数（.env）を基本とする。`.env` の対話式生成ウィザードあり。
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と分離された SQLite を使用。
- DuckDB を分析用途に利用（prices_daily 等のテーブルを想定）。
- OpenAI（gpt-4o-mini）呼び出しは冗長処理・リトライ・バリデーション対応。

---

## 主な機能一覧

- config
  - .env 自動読み込み（プロジェクトルート検出）
  - 設定ウィザード: `python -m kabusys.config_setup`
  - 設定検証: `python -m kabusys.validate_config`
- Execution
  - 起動スクリプト: `python -m kabusys.run_execution`
  - Paper Trading 時は MockBrokerClient を利用し `data/paper_trading.db` に保存
  - PID / stop フラグにより外部制御可能
- Monitoring
  - 起動スクリプト: `python -m kabusys.run_monitoring`
  - System / Trade / Risk を定期ポーリングし監視ログ（SQLite）へ蓄積
  - Kill Switch（`data/kill.flag`）で ExecutionEngine を停止可能
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
- AI
  - ニュースセンチメント評価（raw_news → ai_scores）: kabusys.ai.news_nlp.score_news
  - 市場レジーム判定（ETF 1321 + マクロニュース LLM）: kabusys.ai.regime_detector.score_regime
  - OpenAI API キーは環境変数 `OPENAI_API_KEY` を使用
- Tools
  - Paper Trading 検証レポート生成: `python -m kabusys.tools.paper_verification_report`
- Utilities
  - ロギング設定: kabusys.utils.logging_setup.setup_logging
  - プロセス優先度設定 / CPU affinity: kabusys.utils.process_priority

---

## 必須依存パッケージ（代表）
※プロジェクトに requirements.txt がある前提でインストールしてください。主な依存は下記です。

- python >= 3.9（型アノテーション等を利用）
- duckdb
- psutil
- openai
- PyYAML（config 検証で任意）

インストール例（仮）
```
python -m venv .venv
source .venv/bin/activate
pip install -e .
# または個別に
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows (PowerShell/Command Prompt)
   ```

3. 依存パッケージをインストール
   ```
   pip install -r requirements.txt
   # requirements.txt がない場合は主要パッケージを個別に
   pip install duckdb psutil openai pyyaml
   ```

4. 環境変数設定（.env）
   - 対話式ウィザードで `.env` を生成できます:
     ```
     python -m kabusys.config_setup
     ```
   - 生成後、設定の検証:
     ```
     python -m kabusys.validate_config
     ```
   - 主な環境変数（例）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LOG_LEVEL（デフォルト: INFO）

5. ディレクトリ
   - `data/` と `logs/` は実行時に自動作成されますが、権限等に注意してください。

---

## 使い方

- 実行エンジン（ExecutionEngine）を起動
  - Paper Trading モードで起動する場合:
    ```
    export KABUSYS_ENV=paper_trading        # Unix
    set KABUSYS_ENV=paper_trading           # Windows
    python -m kabusys.run_execution
    ```
  - 本番モード（KABUSYS_ENV=live）は実際に発注が行われます。十分注意して使用してください。

- 監視プロセスを起動
  - デフォルトポーリング間隔は 60 秒。環境変数で上書き可:
    ```
    export MONITOR_POLL_INTERVAL=30
    python -m kabusys.run_monitoring
    ```
  - 監視は常に本番の sqlite_path を使用します（monitoring は KABUSYS_ENV に依存しません）。

- 停止 / Kill Switch / フラグ操作
  - ExecutionEngine の停止要求（Kill Switch）は `data/kill.flag` に理由文字列を書き込むことで実行されます（KillSwitch クラス）。
  - 監視ループ等の外部停止要求には `data/stop_requested.flag`（run_monitoring/run_execution が確認）を使用します。
  - Execution 起動時に `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に kill.flag を自動でクリアします（本番では推奨されません）。

- AI 機能
  - news_nlp（ニュースセンチメント）を実行するには `OPENAI_API_KEY` を設定し、DuckDB 接続を用いて `kabusys.ai.news_nlp.score_news(conn, target_date)` を呼び出します（スクリプト版は提供していませんが、モジュール関数として利用可能）。
  - regime_detector は同様に `kabusys.ai.regime_detector.score_regime(conn, target_date)` で使えます。

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを指定する場合
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- ログ
  - デフォルトログディレクトリ: `logs/`
  - ログファイル名はアプリ名別（例: `logs/execution.log`, `logs/monitoring.log`）
  - ログ設定は `kabusys.utils.logging_setup.setup_logging(app_name="...")` で統一的に設定されます。

---

## 監視 DB スキーマ（概要）

monitoring 用 SQLite（初期化は init_monitoring_db）に以下のテーブルが含まれます:

- system_status: CPU / メモリ / ディスク / プロセス稼働情報 等
- trade_logs: 発注イベントログ（Created / Sent / Filled 等）、latency_ms カラム含む
- positions: 保有ポジション
- risk_logs: リスク関連イベント（DRAWDOWN_ALERT / POSITION_LIMIT 等）
- dashboard: ダッシュボード集計（portfolio_value, cash, drawdown_pct 等）

（テーブル作成・マイグレーションは kabusys.monitoring.monitoring_db.init_monitoring_db に実装済み）

---

## ディレクトリ構成

以下は主要なファイル・モジュールの概観（`src/` 配下）:

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理（.env 自動ロード）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py            — ニュースセンチメント（OpenAI 呼び出し）
    - regime_detector.py     — レジーム判定（ETF MA + マクロセンチメント）
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py       # アラートマネージャ（コード内参照）
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
    - __init__.py
  - data/                   — デフォルトで使われる DB / フラグファイル等（実行時作成）
  - logs/                   — ログ出力先（実行時作成）

---

## 注意事項 / ベストプラクティス

- 本番（KABUSYS_ENV=live）での運用は高リスクです。API キー・パスワード・Kill Switch の設定を必ず確認してください。
- `.env` は機密情報を含むため Git 管理しないでください（README 内の config_setup.py でも注意喚起あり）。
- Paper Trading は本番 DB と分離されていますが、DuckDB / その他リソースの取り扱いは慎重に行ってください。
- OpenAI の呼び出しはコストがかかるため、開発・テスト時はモック化することを推奨します（コード上で関数を patch できる設計があります）。
- 権限のない環境で `psutil` によるプロセス優先度・affinity 設定が失敗する場合がありますが、警告ログを出してスキップするよう設計されています。

---

## 参考コマンドまとめ

- 環境ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン起動
  ```
  python -m kabusys.run_execution
  ```

- 監視起動
  ```
  MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
  ```

- Paper Trading レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

必要であれば、README にサンプル `.env`（テンプレート）や、ExecutionEngine / Broker の設定詳細（MockBroker の挙動やリスクパラメータの説明）、監視・アラートの具体的な閾値設定の例を追加できます。どの情報を追加したいか教えてください。