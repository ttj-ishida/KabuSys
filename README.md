# KabuSys

日本株向けの自動売買 / 研究基盤ライブラリ。  
ポートフォリオ構築、ポジションサイジング、監視・アラート、ペーパートレードの検証、LLM を用いたニュースセンチメント評価などのコンポーネントを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は次のような機能を備えたモジュール群です。

- 実運用向け ExecutionEngine（発注・注文管理・リスク管理・照合）
- 監視サブシステム（System / Trade / Risk の監視、Kill Switch）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制限、レジーム乗数）
- 研究用機能（DuckDB を用いたファクター計算、将来リターン、IC 計算、特徴量要約）
- AI（OpenAI）を使ったニュースセンチメント評価・市場レジーム判定
- ペーパートレード検証レポート生成ツール
- 環境設定ウィザード、設定検証 CLI、ログ設定ユーティリティなど運用支援ツール

設計上のポイント:
- 本番とペーパートレードで DB を分離（KABUSYS_ENV による切り替え）
- .env / 環境変数で設定を管理（自動読み込みあり、無効化可能）
- DuckDB（分析向け）と SQLite（監視・履歴向け）の併用
- ロギングは Stream と日次ローテートファイルに対応
- LLM 呼び出しは失敗耐性（リトライ・フォールバック）を実装

---

## 主な機能一覧

- run_execution: ExecutionEngine を起動（実発注 or ペーパートレード）
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を用い、data/paper_trading.db に記録
- run_monitoring: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔変更可）
- Monitoring:
  - system_monitor: CPU/メモリ/ディスク/プロセス・データ鮮度の監視
  - trade_monitor: 注文の滞留・約定異常などの検出（trade_logs を参照）
  - risk_monitor: ドローダウン・ポジション上限などの監視とリスクログ記録
  - monitoring_engine: 上記を束ね、KillSwitch/AlertManager と連携して通知・停止制御
- kill_switch: 条件に応じて data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送る
- portfolio: 候補選定、等重・スコア重み、ポジションサイズ計算、セクターキャップ、レジーム乗数
- research: DuckDB を用いたファクター計算（Momentum / Volatility / Value）・IC / 統計サマリ
- ai.news_nlp: raw_news を LLM（gpt-4o-mini）でスコア化して ai_scores に保存
- ai.regime_detector: ETF + マクロニュースで市場レジーム判定・保存
- tools.paper_verification_report: ペーパートレード DB から検証レポート生成
- config_setup: .env を対話式で作成・更新するウィザード
- validate_config: .env と config/*.yaml の基本チェックを行う CLI
- utils: logging_setup（共通ログ設定）、process_priority（プロセス優先度設定）等

---

## セットアップ手順

1. Python 環境
   - 推奨: Python 3.10+
   - 仮想環境を作成して有効化してください（venv / pyenv / conda 等）

2. 依存ライブラリをインストール
   - 必要な主要パッケージ（例）:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML（validate_config が YAML パースを行う際に任意）
   - 例:
     ```
     pip install duckdb psutil openai PyYAML
     ```
   - 実プロジェクトでは requirements.txt / poetry 等で管理してください。

3. ディレクトリ準備（手動で作るか起動時に自動生成されますが、権限等で問題がある場合は事前作成を推奨）
   ```
   mkdir -p data logs
   ```

4. .env の作成
   - 対話式ウィザードを使う:
     ```
     python -m kabusys.config_setup
     ```
   - もしくは `.env.example` を参考に `.env` を作成してください。
   - 注意: `.env` は Git にコミットしないでください。

5. 設定の検証
   ```
   python -m kabusys.validate_config
   ```
   - --strict を付けると警告も失敗扱いになります。

6. DB 初期化
   - 実行スクリプトが起動時に必要なテーブルを作成します（init_monitoring_db など）。手動で作る必要は通常ありません。

---

## 主要な環境変数（概要）

- 必須（実行前に設定）
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用
  - KABU_API_PASSWORD — kabuステーション API パスワード

- 主要なオプション / 推奨
  - KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード DB（デフォルト: data/paper_trading.db）
  - PAPER_FILL_MODE — ペーパートレードの約定挙動: instant | partial | never | reject（デフォルト: instant）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/…、デフォルト: INFO）
  - LOG_DIR — ログ出力先ディレクトリ（デフォルト: logs）
  - OPENAI_API_KEY — OpenAI を使う場合の API キー
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）

- 自動ロードの挙動
  - プロジェクトルート（.git または pyproject.toml 基準）にある `.env`/`.env.local` を自動ロードします。
  - 自動ロードを無効化する場合:
    ```
    export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    ```

---

## 使い方（実行例）

- ExecutionEngine を起動（デフォルトは KABUSYS_ENV に従う）
  - 実行:
    ```
    python -m kabusys.run_execution
    ```
  - ペーパートレードで起動する場合:
    ```
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```
  - 注意: ペーパートレード時は MockBrokerClient を使い、記録先 DB は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）になります。

- Monitoring を起動（ポーリングで system_monitor.check_once を実行）
  - 実行:
    ```
    python -m kabusys.run_monitoring
    ```
  - ポーリング間隔を変更:
    ```
    export MONITOR_POLL_INTERVAL=30
    python -m kabusys.run_monitoring
    ```

- 設定ウィザード:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Paper Trading 検証レポート生成:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを指定する場合:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI スコアリング / レジーム判定（Python から呼び出す）
  - ニューススコアを生成（DuckDB 接続を渡す）
    ```py
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    n_written = score_news(conn, target_date=date(2026,4,10), api_key="sk-...")
    ```
  - レジーム判定:
    ```py
    from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime

    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026,4,10), api_key="sk-...")
    ```

- ログ
  - デフォルトは console (stdout) とファイル: logs/<app_name>.log（日次ローテーション、30 日保持）
  - ログ設定は kabusys.utils.logging_setup.setup_logging で共通管理。環境変数 LOG_DIR / LOG_LEVEL で調整可能。

---

## 運用上の注意・補足

- Kill Switch / Stop フラグ
  - 実行プロセスは data/stop_requested.flag や data/kill.flag を監視します。これらのファイルを作成することで外部から停止シグナルを送れます。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動でクリアします（本番では 0 を推奨）。

- DB マイグレーション
  - monitoring_db.init_monitoring_db は冪等でテーブル作成および軽微な列追加（マイグレーション）を行います。
  - DuckDB 側のスキーマ変更は手動または別スクリプトで管理してください。

- 権限 / 優先度
  - process_priority.set_process_priority はプラットフォームにより権限が必要な場合があります（`psutil.AccessDenied` で警告になるだけで継続します）。

- LLM（OpenAI）利用
  - OPENAI_API_KEY が必要。API 呼び出しはレート制限や一時エラーに対してリトライ処理を行いますが、費用やレートに留意してください。
  - ニュース評価・レジーム判定は外部 API を呼ぶため、API キーの管理とコスト管理を行ってください。

---

## ディレクトリ構成（主要ファイル）

（プロジェクトルートの `src/kabusys/` を基準）

- __init__.py
- config.py — 環境変数 / Settings 管理（.env 自動ロードロジック含む）
- config_setup.py — .env 対話ウィザード
- validate_config.py — 設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — Monitoring ポーリング起動スクリプト

- execution/  (発注関連)
  - broker_factory.py
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
  - …（実装に依存するファイル群）

- monitoring/
  - monitoring_db.py — SQLite 永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - monitoring_engine.py
  - kill_switch.py
  - alert_manager.py
  - …（監視関連）

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
  - news_nlp.py
  - regime_detector.py
  - __init__.py

- tools/
  - paper_verification_report.py

- utils/
  - logging_setup.py
  - process_priority.py
  - __init__.py

- data/ （実行時に使用/作成）
  - monitoring.db（SQLite, デフォルト）
  - paper_trading.db（ペーパートレード用、設定で変更可）
  - kill.flag / stop_requested.flag / execution.pid など

- logs/
  - execution.log, monitoring.log, …（ログ出力先）

---

## 参考コマンドまとめ

- .env 作成:
  ```
  python -m kabusys.config_setup
  ```
- 設定検証:
  ```
  python -m kabusys.validate_config
  ```
- Execution 起動:
  ```
  python -m kabusys.run_execution
  ```
- Monitoring 起動:
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
- Paper 検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

README はここまでです。運用上の細かな挙動（DB スキーマ、プロセス停止ロジック、AI の挙動など）はソース内ドキュメント（各モジュールの docstring）を参照してください。必要であれば各コンポーネントの詳しい利用例や設定例（.env のテンプレート）を追加で作成します。