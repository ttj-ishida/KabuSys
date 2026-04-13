# KabuSys — README

このリポジトリは日本株向けの自動売買／リサーチ基盤（KabuSys）の一部実装です。本ドキュメントはコードベース（src/kabusys 以下）に基づく簡易 README です。

注意: 実行はプロジェクトルート（pyproject.toml または .git がある場所）から行うことを想定しています。

---

## プロジェクト概要

KabuSys は日本株の自動売買・リサーチ・監視を目的としたモジュール群です。本実装には以下の主要機能が含まれます。

- 注文管理（OrderManager / ExecutionEngine）
- 発注・リコンシリエーション（Reconciler）
- リスク管理（RiskManager / RiskMonitor）
- システム監視（SystemMonitor / MonitoringEngine）
- 監視 DB（SQLite）への永続化層（MonitoringDB）
- ポートフォリオ構築ロジック（候補選定・重み・ポジションサイズ）
- ファクター計算・リサーチユーティリティ（DuckDB を利用）
- ニュース NLP / レジーム判定（OpenAI API を利用する LLM ベース処理）
- 運用支援ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）

設計方針として、データ計算系（research / portfolio）は副作用を持たない純粋関数として実装され、監視や実行系は SQLite / DuckDB をデータ永続化に使用します。

---

## 主な機能一覧

- SystemMonitor: CPU / メモリ / ディスク使用率、実行プロセスの生存確認、価格データ鮮度チェック
- TradeMonitor: 注文滞留（stale order）、約定価格の異常検知
- RiskMonitor: ドローダウン検出、保有銘柄数上限チェック、ダッシュボード更新
- KillSwitch: 条件（ドローダウン等）で flag ファイルを書き、ExecutionEngine に停止シグナルを送付
- AlertManager: LINE Messaging API 経由でアラート通知（クールダウン管理あり）
- MonitoringDB: system_status / trade_logs / positions / risk_logs / dashboard テーブルの作成・読み書き・簡易マイグレーション
- ExecutionEngine（起動スクリプト含む）: ブローカークライアントと連携して発注・リスクチェック・リコンシリエーション
- Paper Trading: KABUSYS_ENV=paper_trading 時に mock ブローカーを使用し、本番 DB とは別の data/paper_trading.db に記録
- Research: momentum / volatility / value 等のファクター計算、forward returns、IC（情報係数）計算
- AI: ニュース記事のセンチメントスコアリング（OpenAI）および市場レジーム判定
- 運用ツール: Streamlit ダッシュボード、paper trading 検証レポート作成スクリプト

---

## セットアップ手順

1. Python 環境を用意（推奨: 3.10+）
2. 依存パッケージをインストール（代表的なもの）
   - duckdb
   - psutil
   - requests
   - openai
   - streamlit
   - その他プロジェクト側で必要なライブラリ

   例（pip）:
   ```
   pip install duckdb psutil requests openai streamlit
   ```

3. リポジトリをクローンし、プロジェクトルートへ移動
4. （任意）開発用にパッケージを editable install
   ```
   pip install -e .
   ```
   もしくは実行時に `PYTHONPATH=src` を通す/プロジェクトルートから実行する

5. 環境変数の設定
   - .env/.env.local をプロジェクトルートに配置することで自動読み込みされます（自動読み込みはデフォルトで有効）。
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（使用機能に応じて）
   - OpenAI を使う場合は OPENAI_API_KEY を設定

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV: 起動環境（development / paper_trading / live）。デフォルト: development
- SQLITE_PATH: 監視 DB（SQLite）のパス。デフォルト: data/monitoring.db
  - 監視（run_monitoring）は環境に関わらずこの sqlite_path を使用します（監視は本番 DB を参照する仕様）。
- DUCKDB_PATH: DuckDB ファイルのパス。デフォルト: data/kabusys.duckdb
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（paper_trading 時に使用）。デフォルト: data/paper_trading.db
- PAPER_FILL_MODE: paper_trading の約定モード（instant / partial / never / reject）デフォルト: instant
- PID_FILE_PATH: 実行プロセスの PID を書くファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: SystemMonitor のポーリング間隔（秒）。デフォルト: 60（0以下は無効でデフォルトフォールバック）
- OPENAI_API_KEY: OpenAI API キー（ai.news_nlp / ai.regime_detector で使用）

---

## 使い方（実行例）

以下はプロジェクトルートからの実行例です。パッケージとしてインストール済みであれば `python -m kabusys.<module>` でも可。

- 監視ループを起動（SystemMonitor 単体）
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能
  - 起動時にプロセス優先度を "high" に設定しようとします（OS・権限により失敗する場合があります）
  - 監視 DB 初期化（テーブル作成・簡易マイグレーション）を行います

- 実取引 / ExecutionEngine を起動
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合はモックブローカーを使用し、Paper Trading 専用 DB（PAPER_TRADING_SQLITE_PATH）に記録されます
  - 通常は本番用 sqlite_path / duckdb_path を使用します
  - 起動時にプロセス優先度を "high" に設定します

- Streamlit ダッシュボード（監視用）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - 読み取り専用で SQLite DB を開きダッシュボードを表示

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - --db オプションで SQLite ファイルを指定可能（省略時は PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）

- AI モジュール（ニューススコア・レジーム判定）
  - OpenAI API キーを設定して、関数を呼び出す（ライブラリ API を通じて使用）
  - 例: kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を呼び出す（スクリプト化は任意）

---

## 実装上の注意点 / 挙動

- Monitoring は常に Settings.sqlite_path（production 想定）を使う仕様です。Paper Trading と監視を完全に分離したい場合は設定を調整してください。
- MonitoringDB.init_monitoring_db は冪等（存在チェック）でテーブルを作成し、既存 DB に対する簡易マイグレーション（カラム追加）を行います。
- OpenAI 関連は API 呼び出しに対して指数バックオフやトリミング、バリデーションを行う実装です。API キー未設定時には ValueError を送出するケースがあります。
- Process Priority / CPU Affinity 設定は psutil を使用。権限不足や未サポート OS では警告を出してスキップします。
- Paper Trading では mock ブローカー動作が実装され、記録先 DB を分離しています（PAPER_TRADING_SQLITE_PATH）。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py — 環境変数 / 設定管理（.env の自動読み込み機能含む）
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト
- tools/
  - __init__.py
  - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト
- monitoring/
  - __init__.py
  - monitoring_db.py — SQLite テーブル定義・MonitoringDB クラス
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py
  - monitoring_engine.py
  - streamlit_dashboard.py
- execution/
  - order_manager.py
  - reconciler.py
  - (その他: broker_factory, execution_engine, order_repository 等 — 実装の一部が省略されているファイルもあり)
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
  - news_nlp.py — ニュースの LLM スコアリング
  - regime_detector.py — マクロ + ETF MA を合成した市場レジーム判定
  - __init__.py
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - __init__.py

データディレクトリ（デフォルト）
- data/kabusys.duckdb (DuckDB ファイル)
- data/monitoring.db (監視 SQLite)
- data/paper_trading.db (Paper Trading 用 SQLite)
- data/execution.pid (PID ファイル)
- data/kill.flag (kill スイッチ用フラグファイル)

---

## 参考・デバッグ

- ログレベルは Settings.log_level（環境変数 LOG_LEVEL）で制御します（デフォルト INFO）。
- monitor / engine 系は KeyboardInterrupt を受けると安全に終了します。
- Streamlit ダッシュボードは読み取り専用 URI を使って DB を開くため、監視プロセスと同時に表示しても安全です（read-only モード推奨）。

---

必要に応じて README に追記します。特にセットアップの OS 固有注意点（psutil の権限、OpenAI SDK バージョン）、および実行時の systemd / supervisor のサービス定義例などが必要であれば指示ください。