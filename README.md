# KabuSys

日本株自動売買システムの簡易実装（ライブラリ / 実行スクリプト群）。  
このリポジトリは、シグナル生成・ポートフォリオ構築・発注実行・監視・研究ツール・AI を組み合わせたサンプル実装を含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の主要コンポーネントで構成されます。

- Execution: 発注エンジン（実際のブローカークライアントまたは Paper Trading のモックを使用）
- Monitoring: システム稼働状況／取引状況／リスクを定期チェックしてログやアラート、Kill Switch を管理
- Portfolio: 候補選定・重み計算・ポジションサイズ決定・セクター制限等の純粋関数群
- Research: DuckDB を用いたファクター計算・特徴量分析ツール
- AI: ニュースセンチメント（OpenAI）を用いたスコアリング・市場レジーム判定
- Tools: ペーパートレード検証レポート等のユーティリティスクリプト
- 設定ユーティリティ: 対話的 .env 作成 (`config_setup`)、起動前検証 (`validate_config`)

設計方針の一部:
- 本番／ペーパーは DB を分離（paper_trading モードでは専用 SQLite を使用）
- ルックアヘッドバイアス回避（内部で date.today() 等を不用意に参照しない）
- フェイルセーフ（API 失敗時は妥当なフォールバックを使って継続）
- ログは統一的に設定（stdout + 日次ローテーション）

---

## 主な機能一覧

- 実行エンジン起動スクリプト: `python -m kabusys.run_execution`
  - KABUSYS_ENV=paper_trading 時は MockBroker を使用し `data/paper_trading.db` を使用
  - 停止は `data/stop_requested.flag` または監視側の Kill Switch による `data/kill.flag`
- 監視ループ起動スクリプト: `python -m kabusys.run_monitoring`
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を変更可能（デフォルト 60）
  - 監視は本番用 sqlite_path を常に使用
- 設定ウィザード: `python -m kabusys.config_setup`（対話式で .env を生成）
- 設定検証 CLI: `python -m kabusys.validate_config`（--strict で警告も FAIL に）
- Paper Trading 検証レポート: `python -m kabusys.tools.paper_verification_report`
- AI:
  - `kabusys.ai.score_news` — raw_news を集約して OpenAI に投げ、ai_scores に書き込む
  - `kabusys.ai.regime_detector.score_regime` — ma200 とマクロニュースで市場レジーム判定
- Portfolio ユーティリティ:
  - 候補選定、等重／スコア重み、ポジションサイズ計算、セクターキャップ、レジーム乗数など
- MonitoringDB（SQLite）: system_status / trade_logs / positions / risk_logs / dashboard を管理

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   ```
   git clone <repo_url>
   cd <repo>
   ```

2. 仮想環境を作成・有効化（推奨）
   ```
   python -m venv .venv
   # macOS / Linux
   source .venv/bin/activate
   # Windows
   .venv\Scripts\activate
   ```

3. 依存パッケージをインストール  
   （requirements.txt が無い場合は最低限次をインストールしてください）
   ```
   pip install duckdb psutil openai
   # YAML のパースを使う場合（config ファイル検証）:
   pip install pyyaml
   ```

4. 環境変数 / .env の用意  
   対話式ウィザードで作成:
   ```
   python -m kabusys.config_setup
   ```
   もしくは `.env` を手動で作成。必須の環境変数:
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   オプション / 推奨:
   - KABUSYS_ENV (development / paper_trading / live) — デフォルト `development`
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH（paper_trading 用、デフォルト: data/paper_trading.db）
   - LOG_LEVEL（DEBUG/INFO/...）, LOG_DIR
   - OPENAI_API_KEY（AI 機能を使う場合）
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（本番アラート用、任意）

5. 設定検証（起動前に実行推奨）
   ```
   python -m kabusys.validate_config
   # --strict をつけると警告も FAIL 扱い
   python -m kabusys.validate_config --strict
   ```

6. データ / ログ ディレクトリの確認  
   デフォルトで `data/` と `logs/` が使われます。必要に応じて手動で作成してください（セットアップ処理でも自動作成されます）。

---

## 使い方（実行例）

- 監視プロセスを起動
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を変更する:
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```

- 発注エンジンを起動
  ```
  python -m kabusys.run_execution
  ```
  - Paper Trading モードで起動するには `.env` で `KABUSYS_ENV=paper_trading` を設定するか、環境変数を指定:
    ```
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```

- 停止フラグ（実行中のプロセスに停止シグナルを送る）:
  - 監視 / 実行スクリプトはプロジェクトルートの `data/stop_requested.flag` を検出して終了します。手動で停止したい場合はそのファイルを作成してください。
  - Kill Switch（自動停止基準）: `data/kill.flag` を生成して ExecutionEngine 停止を促します（Monitoring 側が書き込み）。

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  DB の指定:
  ```
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 機能（プログラムから呼ぶ例）
  ```py
  import duckdb
  from kabusys.ai import score_news
  conn = duckdb.connect("data/kabusys.duckdb")
  # target_date は datetime.date オブジェクト
  score_news(conn, target_date, api_key="sk-...")
  ```

- ログ
  - デフォルト: `logs/<app_name>.log`（app_name は `execution` / `monitoring` 等）
  - コンソール出力は stdout（`kabusys.utils.logging_setup.setup_logging` による統一設定）

---

## 重要なファイル・フラグ（概略）

- データ / フラグ
  - data/stop_requested.flag — 手動停止フラグ（run_monitoring / run_execution が監視）
  - data/kill.flag — Kill Switch（監視が書き込むと execution 側で停止）
  - data/execution.pid — ExecutionEngine の PID ファイル（`run_execution` が利用）
  - data/monitoring.db — 監視用 SQLite（デフォルト）
  - data/paper_trading.db — Paper Trading 用 SQLite（paper_trading 時）

- ログ
  - logs/execution.log, logs/monitoring.log, ...（日次ローテーション）

- 設定
  - .env, .env.local（プロジェクトルート）。自動ロード機能あり（Settings モジュール）

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                 — 環境変数読み込み / Settings
- config_setup.py           — .env 対話ウィザード
- validate_config.py        — 起動前設定検証 CLI
- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py         — SystemMonitor 起動スクリプト
- tools/
  - paper_verification_report.py
- ai/
  - news_nlp.py             — ニュース→LLMセンチメント処理
  - regime_detector.py      — レジーム判定
- monitoring/
  - monitoring_db.py
  - system_monitor.py
  - trade_monitor.py        — (ファイルは省略されているがモニタ類が配置)
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py        — (アラート送信ロジックが入る想定)
- execution/
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - broker_factory.py
  - reconciler.py
  - risk_manager.py
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
  - ... その他ユーティリティ

（上記はリポジトリ内の主要モジュール一覧。実際のファイルは src/kabusys 以下を参照してください）

---

## 開発・拡張メモ

- DuckDB を用いて価格・財務データの高速な分析を行います。prices_daily / raw_financials 等のテーブル構造に依存します。
- OpenAI（gpt-4o-mini）を使う箇所は API キーが必要です。API 呼び出しはリトライやパース耐性を備えていますが、キーのレート制限に注意してください。
- 本番運用時は `KABUSYS_ENV=live` を設定し、LINE 通知等を設定してください。validate_config によるガードもあります。
- ログや DB のパスは環境変数で自由に上書き可能です。`.env` で管理してください。
- テストでは外部 API 呼び出し（OpenAI など）をモックすることを推奨します（score_news 等は呼び出し箇所を差し替え可能な設計）。

---

## ライセンス・注意事項

このリポジトリはサンプル実装であり、本番対応の安全性／完全性は保証されません。実際の資金を扱う前に十分なテスト・レビューを行ってください。API キーやシークレットは `.env` に保存しますが、決してリポジトリにコミットしないでください。

---

何か README に追加したい内容（例: 依存関係の完全な一覧、実行時のログサンプル、DB スキーマ詳細など）があれば教えてください。必要に応じて追記します。