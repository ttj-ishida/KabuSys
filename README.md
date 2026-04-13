# KabuSys

KabuSys は日本株向けの自動売買／リサーチ基盤です。本リポジトリは取引実行（Execution）、監視（Monitoring）、ポートフォリオ構築、ファクター計算、ニュースNLP（OpenAI を使用）などの主要コンポーネントを提供します。

以下は、このコードベースの概要・セットアップ・使い方・ディレクトリ構成の README です。

---

## プロジェクト概要

- 目的: 日本株自動売買システムのコアロジックおよび監視・検証ツール群を提供する。
- 主な機能:
  - 注文管理・発注エンジン（ExecutionEngine, OrderManager, Reconciler 等）
  - 取引監視・システム監視（MonitoringEngine, SystemMonitor, TradeMonitor, RiskMonitor 等）
  - ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
  - ファクター計算・リサーチ（モメンタム、ボラティリティ、バリュー等）
  - ニュースの NLP によるセンチメントスコアリング（OpenAI）
  - Paper Trading 用の分離データベースと検証レポート生成ツール
  - Streamlit による監視ダッシュボード

---

## 機能一覧（抜粋）

- 実行関連
  - OrderManager: 注文生成・送信・状態管理
  - Reconciler: 再起動後の注文/ポジション突合
  - BrokerFactory: 環境に応じて実ブローカー／モックを選択（`KABUSYS_ENV=paper_trading` でモック）

- 監視関連
  - SystemMonitor: CPU / メモリ / ディスク / プロセス PID / データ鮮度の監視
  - TradeMonitor: 滞留注文チェック・約定価格異常チェック
  - RiskMonitor: ドローダウン・ポジション数上限チェック
  - MonitoringDB: SQLite を利用した永続化（system_status, trade_logs, positions, risk_logs, dashboard 等）
  - KillSwitch: 条件により ExecutionEngine 停止フラグを書き込む仕組み
  - AlertManager: LINE Push による通知（クールダウン付き）

- リサーチ / ポートフォリオ
  - research.calc_momentum / calc_volatility / calc_value: DuckDB 上でファクター計算
  - research.calc_forward_returns / calc_ic / factor_summary: 特徴量評価・IC 計算
  - portfolio.select_candidates / calc_equal_weights / calc_score_weights
  - portfolio.calc_position_sizes: 発注株数計算（リスクベース・等配分等）
  - portfolio.apply_sector_cap / calc_regime_multiplier: セクター集中制限・レジーム乗数

- AI（OpenAI）
  - ai.news_nlp.score_news: raw_news を集約して OpenAI で銘柄毎にセンチメントを算出し ai_scores に保存
  - ai.regime_detector.score_regime: ETF (1321) の MA とマクロニュースから市場レジーム判定

- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成（稼働率・注文成功率・レイテンシ等）
  - monitoring/streamlit_dashboard.py: Streamlit ダッシュボード（監視情報可視化）

---

## セットアップ手順

1. Python 環境を用意（推奨: Python 3.10+）
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   - （SQLite は標準ライブラリに含まれています）
   - 必要に応じて他の依存ライブラリを追加してください（プロジェクトの requirements.txt がある場合はそれを使用）

4. 環境変数（最低限）
   - KABUSYS_ENV: 起動環境（"development" / "paper_trading" / "live"。デフォルトは development）
   - OPENAI_API_KEY: OpenAI を利用する場合に必要
   - JQUANTS_REFRESH_TOKEN: （必要な場合）
   - KABU_API_PASSWORD: kabu ステーション API を使う場合
   - 省略した場合は Settings クラスのデフォルトが使用されます（例: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"）

5. .env の自動読み込み
   - プロジェクトルートに `.env` や `.env.local` があると自動で読み込まれます（OS 環境変数が優先）。
   - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

6. データベース初期化
   - 監視 DB（SQLite）は起動時に `init_monitoring_db()` によりテーブル作成・マイグレーションが自動実行されます。

---

## 使い方（主要コマンド）

- Execution エンジン起動
  - デフォルト（実口座/開発環境）:
    - python -m kabusys.run_execution
  - Paper Trading（モックブローカーを使用し DB を分離）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - Paper Trading の DB はデフォルト `data/paper_trading.db`（環境変数 `PAPER_TRADING_SQLITE_PATH` で変更可）
  - 注意: 起動時にプロセス優先度が "high" に設定されます（実行環境で権限不足の場合は警告が出ます）。

- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能。デフォルトは 60 秒。
  - 監視は production の sqlite_path を常に使用します（環境にかかわらず本番監視 DB を参照）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db オプション または 環境変数 `PAPER_TRADING_SQLITE_PATH`

- Streamlit ダッシュボード起動
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは監視 DB を読み取り専用で開きます。MonitoringEngine を先に起動してください。

- AI 関連（プログラムから呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API キーが必要。`api_key` を渡すか環境変数 `OPENAI_API_KEY` を設定。

---

## 主要な環境変数とデフォルト値

- KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト: development）
- LOG_LEVEL: "DEBUG"|"INFO"|"WARNING"|"ERROR"|"CRITICAL"（デフォルト: INFO）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- PAPER_FILL_MODE: instant | partial | never | reject（paper trading の注文約定挙動、デフォルト: instant）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- MONITOR_POLL_INTERVAL: 監視ループの秒数（デフォルト 60）
- PID_FILE_PATH: data/execution.pid（ExecutionEngine が PID を書く場所）
- KILL_FLAG_PATH: data/kill.flag（KillSwitch が停止フラグを書き込む）
- KILL_FLAG_CLEAR_ON_START: "1" にすると ExecutionEngine 起動時に kill.flag を削除

---

## 注意点 / 実装の重要な仕様

- Paper Trading は本番 DB と完全に分離する（`KABUSYS_ENV=paper_trading` の場合は `paper_sqlite_path` を使用）。
- Monitoring の DB 初期化は `init_monitoring_db()` が冪等に行う（既存カラムのマイグレーション含む）。
- news_nlp / regime_detector は OpenAI を使うが、API エラー時はフォールバックや部分的スキップを行いシステムを停止しない設計（フェイルセーフ）。
- Process 優先度設定は start-up 時に行われる（`set_process_priority("high")`）。権限不足時は警告。
- Streamlit ダッシュボードは監視 DB を読み取り専用で開くよう推奨（起動時に `?mode=ro` を付与）。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理（.env 自動読み込み）
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — SystemMonitor ポーリング起動スクリプト
  - utils/
    - __init__.py
    - process_priority.py          — プロセス優先度 / CPU affinity ユーティリティ
  - execution/
    - order_manager.py
    - order_repository.py
    - execution_engine.py
    - reconciler.py
    - broker_factory.py
    - broker_api.py
    - ... (OrderRecord, OrderState など)
  - monitoring/
    - monitoring_db.py             — SQLite テーブル定義 + MonitoringDB
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
    - streamlit_dashboard.py
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
    - __init__.py
    - paper_verification_report.py
  - data/ (想定されるデータ格納先、実行時に生成/使用)
    - kabusys.duckdb
    - monitoring.db
    - paper_trading.db

---

## 監視 DB（monitoring_db.py）の概要

- テーブル:
  - system_status: CPU/メモリ/ディスク/プロセス状態の時系列ログ
  - trade_logs: 発注イベントログ（event_type: Created/Sent/Filled 等）
  - positions: 保有ポジション（code を主キー）
  - risk_logs: リスク関連イベント（DRAWDOWN_ALERT/STALE_ORDER 等）
  - dashboard: 集計（1 行 固定 id=1） — portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value

- MonitoringDB クラスは読み書きメソッドを提供（log_system_status / log_trade_event / upsert_position / log_risk_event / upsert_dashboard / get_dashboard 等）。

---

## よく使うコマンド例

- Execution 起動（paper trading）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Monitoring 起動（ポーリング間隔 30 秒）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading レポート（2026-04-01 〜 2026-04-11）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

## 開発メモ / 拡張ポイント

- position_sizing では将来的に銘柄別 lot_size を導入することを想定した拡張余地あり（現在は全銘柄共通単元）。
- news_nlp と regime_detector は OpenAI 呼び出しを内部で行うため、単体テストでは該当関数をモックすること。
- データ鮮度チェックは DuckDB 上の prices_daily テーブルに依存。prices の取り込みパイプラインと連携すること。

---

もし README に追加したい情報（CI / デプロイ手順・サンプル設定ファイル .env.example・requirements.txt など）があれば、教えてください。必要に応じて追記・整備します。