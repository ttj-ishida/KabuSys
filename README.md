# KabuSys

日本株向け自動売買システムのリポジトリ（簡易説明版）。この README ではプロジェクトの概要、主な機能、セットアップ手順、利用方法、ディレクトリ構成を日本語でまとめます。

---

プロジェクト内の主要な CLI / スクリプトはモジュールとして実装されており、`python -m kabusys.<module>` の形式で起動できます。

## プロジェクト概要

KabuSys は日本株の自動売買（ExecutionEngine）とそれを補助する各種コンポーネント（監視、ポートフォリオ構築、リスク管理、リサーチ、AI ベースのニュース解析等）を含む Python ベースのシステムです。

主な設計方針:
- DuckDB を分析用 DB、SQLite を監視／ペーパートレード用に利用
- 環境変数 / .env による設定管理（.env の対話式ウィザードあり）
- Paper Trading と Live を分離（paper_trading 用 DB は別ファイル）
- OpenAI（gpt-4o-mini 等）を用いたニュース NLP / レジーム判定機能を実装
- 監視コンポーネントが ExecutionEngine の安全停止（Kill Switch）を担う

## 機能一覧

- ExecutionEngine（発注エンジン）
  - 本番（live）／ペーパートレード（paper_trading）モード対応
  - ブローカークライアントの切り替え（Mock / 実ブローカー）
  - リスク管理（最大ポジション割合・利用率・ドローダウン等）
- Monitoring（システム監視）
  - CPU/メモリ/ディスク・プロセス生存確認・データ鮮度チェック
  - トレード監視（滞留注文 / 約定異常等）
  - リスク監視（ドローダウン・ポジション数上限）
  - Kill Switch による ExecutionEngine 停止
- ポートフォリオ構築（純粋関数群）
  - 候補選定、重み付け（等金額 / スコア加重）
  - ポジションサイズ計算（リスクベース・等配分）
  - セクターキャップ、レジーム乗数
- 研究モジュール（research）
  - ファクター計算（Momentum / Volatility / Value）
  - Forward returns, IC（情報係数）, 統計サマリー
- AI モジュール（news_nlp / regime_detector）
  - ニュースを LLM でセンチメント解析 → ai_scores テーブルへ書き込み
  - マクロ記事 + ETF ma200 乖離 による市場レジーム判定
- ツール
  - .env 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading の検証レポート生成（tools.paper_verification_report）
- ログ設定ユーティリティ（統一的なログ出力・日次ローテート）
- プロセス優先度 / CPU affinity 設定ユーティリティ

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境を作成・有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   （requirements.txt が無い場合は以下の主要パッケージをインストールしてください）
   ```
   pip install duckdb psutil openai
   # YAML 検証を行いたい場合:
   pip install PyYAML
   ```
   注: sqlite3 は標準ライブラリです。

4. 環境変数設定
   - 対話式ウィザードで .env を作成:
     ```
     python -m kabusys.config_setup
     ```
   - 作成後、設定検証:
     ```
     python -m kabusys.validate_config
     ```
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
   - 重要: `.env` をリポジトリにコミットしないこと

5. データディレクトリの作成（必要に応じて）
   ```
   mkdir -p data logs
   ```

## 使い方（起動/実行コマンド）

- 環境設定ウィザード（.env 作成／更新）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証（起動前チェック）
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict   # 警告を FAIL 扱いにする
  ```

- 監視ループ（monitoring）
  - 起動:
    ```
    python -m kabusys.run_monitoring
    ```
  - 補足:
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（秒、デフォルト 60）
    - 停止フラグファイル: `data/stop_requested.flag` を作成するとループが終了します
    - 監視は KABUSYS_ENV に関わらず本番用 sqlite_path を使用して監視テーブルを永続化します

- ExecutionEngine（発注エンジン）
  - 起動:
    ```
    python -m kabusys.run_execution
    ```
  - 補足:
    - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を使用し、データは `data/paper_trading.db`（既定）に分離して記録されます
    - 起動時に `data/stop_requested.flag` が存在すると起動せず終了します
    - 実行中の PID は `data/execution.pid` に書き込まれる（設定で変更可）

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- プログラム的にモジュールを利用する例（Python REPL / スクリプト）
  - 研究関数を呼ぶ:
    ```py
    import duckdb, datetime
    from kabusys.research import calc_momentum
    conn = duckdb.connect("data/kabusys.duckdb")
    recs = calc_momentum(conn, datetime.date(2026,4,1))
    ```
  - AI スコアリング:
    ```py
    from kabusys.ai.news_nlp import score_news
    # conn: duckdb connection, target_date: datetime.date, api_key: str
    score_news(conn, target_date, api_key="sk-...")
    ```

## 重要な環境変数（主要なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- OPENAI_API_KEY (AI 機能使用時に必要)
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — 監視 DB。デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 DB。デフォルト: data/paper_trading.db
- LOG_LEVEL — デフォルト: INFO
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）

## ログとデータ

- ログ: デフォルトは logs/ ディレクトリに日次ローテートで保存（`kabusys.utils.logging_setup`）
- 監視 DB: SQLite（`data/monitoring.db` デフォルト）
- DuckDB: 分析用（`data/kabusys.duckdb` デフォルト）
- PID / フラグ:
  - data/execution.pid — ExecutionEngine の PID（設定で変更可）
  - data/stop_requested.flag — 存在すると run_execution / run_monitoring のループを停止
  - data/kill.flag — Kill Switch による ExecutionEngine 停止シグナル（存在時は Engine 停止）

## ディレクトリ構成（主要ファイル・モジュール）

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数 / .env の自動ロード、Settings クラス
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity の設定
  - monitoring/
    - monitoring_db.py — SQLite による監視用永続層
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — （トレード監視モジュール）
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — kill.flag の作成・管理
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - alert_manager.py — アラート送信（LINE 等、実装あり）
  - execution/ — ExecutionEngine, OrderManager, Reconciler, BrokerFactory 等（発注関連）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・スケーリング
    - risk_adjustment.py — セクター上限 / レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value 計算
    - feature_exploration.py — forward returns / IC / summary
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI）
    - regime_detector.py — マクロ + ma200 によるレジーム判定
  - data/ — 実行時に生成される DB / フラグ等（git 管理対象外推奨）
  - logs/ — ログ出力（デフォルト）

（注）上記はリポジトリの主要ファイル群の抜粋です。細かいモジュールは実際のリポジトリを参照してください。

## 運用上の注意 / 備考

- .env の管理
  - `.env` には機密情報（APIキー等）が含まれるため、絶対に Git にコミットしないでください。
  - `python -m kabusys.config_setup` で安全に作成できます。
- 本番（live）運用時は設定を慎重に確認してください（validate_config は live 時に注意喚起を出力します）。
- AI 機能（news_nlp / regime_detector）は OpenAI API に依存します。API キーやコストに注意してください。
- Monitoring は KABUSYS_ENV にかかわらず監視用 sqlite_path を使用します（監視データは一元管理）。
- Paper Trading は本番 DB と分離されるため、安全に検証可能です。
- 長時間稼働させる場合はログローテーション、ディスク容量、PSUtil の権限制約（nice / cpu_affinity の設定で PermissionError が出る可能性）に注意してください。

---

更に詳細な使い方・開発者向けドキュメントはリポジトリ内の各モジュールの docstring とコメントを参照してください。README に抜けている点や、補足して欲しい部分があれば教えてください。