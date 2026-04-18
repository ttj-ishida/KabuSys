# KabuSys

日本株自動売買システムの実装（ライブラリ / 起動スクリプト / ツール群）。  
このリポジトリはトレーディングロジック、ポートフォリオ構築、監視、AI を使ったニュース解析などを含むモジュール群で構成されています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の主要機能を持つ自動売買基盤です。

- シグナル → ポートフォリオ構築 → 注文生成 → 実行（ExecutionEngine）
- ExecutionEngine の監視（System / Trade / Risk モニタ）と自動 Stop（Kill Switch）
- ペーパートレード用分離 DB（実運用 DB と切り離し可能）
- DuckDB を用いた研究用ファクター計算・特徴量解析
- OpenAI を用いたニュース NLP（センチメント）および市場レジーム判定
- 対話式 `.env` 作成ウィザード、設定検証ツール、レポート生成ツール
- ログはコンソール＋日次ローテートファイル（logs/*）に出力

設計方針として「ランタイムでのルックアヘッドを避ける」「DB 書き込みは冪等に」「外部 API 失敗時はフェイルセーフ」の考え方が随所に反映されています。

---

## 主な機能一覧

- Execution
  - run_execution.py: ExecutionEngine をデーモン的に起動（`python -m kabusys.run_execution`）
  - BrokerClientFactory により本番/ペーパーを切替
  - Paper Trading は `data/paper_trading.db`（デフォルト）に記録

- Monitoring
  - run_monitoring.py: SystemMonitor のポーリングループ起動（`python -m kabusys.run_monitoring`）
  - System / Trade / Risk モニタ、KillSwitch 評価、アラート発行
  - MonitoringDB（SQLite）による永続化（system_status / trade_logs / positions / risk_logs / dashboard）

- Portfolio（純粋関数群）
  - 候補選定、等配分/スコア加重、ポジションサイズ計算、セクター上限・レジーム調整

- Research
  - DuckDB を使ったファクター計算（momentum / volatility / value）
  - 将来リターン、IC 計算、統計サマリ等

- AI
  - news_nlp.score_news: OpenAI（gpt-4o-mini 等）でニュースをスコアリングし ai_scores に書込
  - regime_detector.score_regime: ETF (1321) MA + マクロニュースの LLM センチメントで市場レジーム判定

- ツール
  - config_setup.py: 対話式 `.env` 作成ウィザード
  - validate_config.py: .env / config/*.yaml 等の起動前検証
  - tools/paper_verification_report.py: ペーパートレード検証レポート生成

---

## セットアップ手順

1. Python 環境を作成（推奨: venv）
   - Python 3.9+ を想定
   - 例:
     ```
     python -m venv .venv
     source .venv/bin/activate   # macOS/Linux
     .venv\Scripts\activate      # Windows
     ```

2. 依存ライブラリをインストール
   - 必要な主要パッケージ:
     - duckdb
     - psutil
     - openai
     - pyyaml（config 検証で使用する場合）
   - 例:
     ```
     pip install duckdb psutil openai pyyaml
     ```
   - （任意）ログ出力先をファイルにするには書き込み権限のある `logs/` ディレクトリを作成

3. 初期設定（.env）
   - 対話式ウィザードで `.env` を作成:
     ```
     python -m kabusys.config_setup
     ```
   - あるいはリポジトリルートの `.env.example` を参考に `.env` を作成して配置

4. 設定検証
   - 作成した `.env` と config/*.yaml をチェック:
     ```
     python -m kabusys.validate_config
     python -m kabusys.validate_config --strict   # 警告も FAIL とする
     ```

5. DB 初期化は起動スクリプトが必要に応じて行います（monitoring / execution 起動時に自動でテーブル作成）

注意:
- 自動で .env をロードする仕組みがあり（プロジェクトルートを .git / pyproject.toml で検出）、環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動読み込みを無効化できます。

---

## 重要な環境変数とデフォルト値

- KABUSYS_ENV: 実行環境（development / paper_trading / live） デフォルト: development
- JQUANTS_REFRESH_TOKEN: （必須）J-Quants API トークン
- KABU_API_PASSWORD: （必須）kabuステーション API パスワード
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）デフォルト: INFO
- LOG_DIR: ログディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 使用時に必要）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START: 実行制御・Kill Switch 関連（Settings 参照）

---

## 使い方（主なコマンド）

- 環境設定ウィザード（.env 生成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン起動（ExecutionEngine）
  - デフォルトでは KABUSYS_ENV に応じて本番/ペーパーの BrokerClient を選択
  - 起動:
    ```
    python -m kabusys.run_execution
    ```
  - 停止:
    - Kill Switch による停止は `data/kill.flag` を書き込むことで行われます（KillSwitch が自動評価して書くこともあります）。
    - 外部から強制停止したい場合は `data/stop_requested.flag` を作成すると run_execution の監視ループが検知して停止します（スクリプトによりファイル名が参照されます）。

- 監視モード起動（SystemMonitor ポーリング）
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（秒、デフォルト 60）
  ```
  python -m kabusys.run_monitoring
  ```
  - 監視は常に本番の sqlite_path を使用（監視 DB は環境に依らず同一）

- Paper Trading 検証レポート作成
  ```
  python -m kabusys.tools.paper_verification_report
  # 期間指定:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB 指定:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 系（プログラム的に使用）
  - ニューススコア生成:
    - 関数: `kabusys.ai.score_news(conn, target_date, api_key=None)`
    - OpenAI API キーは引数で渡すか `OPENAI_API_KEY` 環境変数を設定
  - レジーム判定:
    - 関数: `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)`

- ログ設定（共通）
  - 全起動スクリプトは `kabusys.utils.logging_setup.setup_logging(app_name="...")` を呼び出します
  - ログは stdout と `logs/<app_name>.log`（日次ローテート、30世代）に出力

---

## 運用上の注意 / ベストプラクティス

- 本番環境（KABUSYS_ENV=live）では特に `LINE_*` の通知設定、`KILL_FLAG_CLEAR_ON_START=0` などの値を慎重に確認してください。`validate_config` の `--strict` モードで警告も FAIL 扱いにできます。
- Paper Trading と Live の DB は明確に分離してください（PAPER_TRADING_SQLITE_PATH を利用）。
- OpenAI を用いる機能は API キーとコスト管理に注意。API の失敗時はフェイルセーフ（スコア 0.0 等）で動作するよう設計されていますが、運用時はレートや費用を監視してください。
- ログディレクトリに十分なディスク容量を確保してください。monitoring は disk usage を監視しますが、ログの肥大化は別途管理してください。

---

## ディレクトリ構成

リポジトリの主要ファイル/フォルダ（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - config_setup.py          — 対話式 .env ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP スコアリング
    - regime_detector.py     — 市場レジーム判定
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py       — （trade 関連監視）
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py       — （アラート送信ラッパー）
  - execution/
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
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

- data/                      — デフォルトの DB / pid / フラグ等を格納する想定ディレクトリ
  - monitoring.db (SQLITE_PATH)
  - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
  - kabusys.duckdb (DUCKDB_PATH)
  - execution.pid
  - kill.flag
  - stop_requested.flag

- logs/                      — ログファイル（LOG_DIR。デフォルト: logs/）

---

## 最低限の .env の例

（config_setup により自動生成可能）

例:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
```

- 注意: `.env` は絶対にリポジトリにコミットしないでください（機密情報が含まれます）。

---

## 開発者向け補足

- 各モジュールはできるだけ副作用を避ける設計（例: research, portfolio は純粋関数中心）になっています。
- MonitoringDB の初期化・マイグレーションは `init_monitoring_db` が担います（起動時に自動的にテーブルやカラムを作成）。
- 複数の外部 API 呼び出し（OpenAI など）はリトライとバックオフ、レスポンスバリデーションを備えています。
- `kabusys.utils.process_priority` はプラットフォーム差を吸収してプロセス優先度を設定します（起動スクリプトの冒頭で呼び出されています）。

---

必要に応じて README を拡張します。特定の起動例、設定項目の詳細説明、デプロイ手順（systemd / supervisor / container）など追記希望があれば教えてください。