# KabuSys

KabuSys は日本株自動売買システムのコアライブラリ群です。本リポジトリには取引実行、監視、ポートフォリオ構築、ファクター算出、ニュース NLP（OpenAI 経由）などの主要コンポーネントが含まれます。

以下はこのコードベースを使い始めるための README です。

---

## プロジェクト概要

- 目的：日本株を対象とした自動売買システムのコアロジックと運用ツール群を提供する。
- 主な機能：
  - 発注・注文管理（ExecutionEngine / OrderManager / Reconciler）
  - リスク管理（RiskManager / RiskMonitor）
  - 監視（SystemMonitor / TradeMonitor / MonitoringEngine）
  - ポートフォリオ構築（候補選定、重み計算、ポジションサイズ算出）
  - ファクター計算・研究（momentum / value / volatility 等）
  - ニュースの LLM（OpenAI）によるセンチメント評価（news_nlp）
  - 市場レジーム判定（regime_detector）
  - 管理用ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）

---

## 機能一覧（抜粋）

- 実行（run_execution.py）
  - KABUSYS_ENV によるモード切替（`development` / `paper_trading` / `live`）
  - `paper_trading` では MockBrokerClient を使用し、本番 DB と分離（デフォルト DB: `data/paper_trading.db`）
  - ExecutionEngine 起動、リスク設定、Reconciler による起動時同期
- 監視（run_monitoring.py / monitoring.Engine）
  - システム負荷、データ鮮度、注文滞留、約定異常、ドローダウン等の監視
  - LINE によるアラート送信（AlertManager）
  - kill.flag による ExecutionEngine 停止シグナル発行
  - Streamlit ベースのダッシュボード（read-only 接続）
- ポートフォリオ（portfolio）
  - 候補選定（select_candidates）
  - 重み計算（等分配 / スコア加重）
  - セクター制限・レジーム乗数（apply_sector_cap / calc_regime_multiplier）
  - 発注株数計算（position sizing, lot 単位丸め、aggregate cap）
- リサーチ（research）
  - Momentum / Volatility / Value ファクター算出（DuckDB 経由の SQL + Python）
  - 将来リターン計算・IC（Spearman）の算出・統計サマリー
- AI（ai）
  - news_nlp.score_news: raw_news を集約して OpenAI へ投げ、銘柄別センチメントを ai_scores テーブルに書き込み
  - regime_detector.score_regime: ETF (1321) の MA200 とマクロニュースの LLM センチメントを合成してレジーム判定
- ツール
  - Paper Trading 検証レポート生成（tools/paper_verification_report.py）
  - Streamlit ダッシュボード（monitoring/streamlit_dashboard.py）
- 設定管理（config）
  - .env / .env.local の自動読み込み（OS 環境変数が優先）
  - 重要な環境変数の取得と検証を提供する Settings クラス

---

## セットアップ手順

1. Python 環境（3.9+ 推奨）を用意する。
2. 必要パッケージをインストール（例）:

   ```bash
   pip install duckdb psutil requests openai streamlit
   ```

   - 実行環境により追加の依存が必要になる場合があります（例: Windows の一部ビルド依存など）。
   - requirements.txt がない場合は上記パッケージを参考にしてください。

3. リポジトリのルートに `.env` / `.env.local` を用意（必要に応じて）。自動読み込みはデフォルトで有効です。無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

4. 主要な環境変数（例）:

   - KABUSYS_ENV = development | paper_trading | live
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
   - OPENAI_API_KEY (AI機能を使う場合)
   - PAPER_FILL_MODE = instant | partial | never | reject (paper_trading 用、デフォルト: instant)
   - PAPER_TRADING_SQLITE_PATH (paper_trading 用 SQLite。デフォルト: data/paper_trading.db)
   - SQLITE_PATH (監視 DB。デフォルト: data/monitoring.db)
   - DUCKDB_PATH (DuckDB ファイル。デフォルト: data/kabusys.duckdb)
   - PID_FILE_PATH (デフォルト: data/execution.pid)
   - KILL_FLAG_PATH (デフォルト: data/kill.flag)
   - MONITOR_POLL_INTERVAL (監視ポーリング間隔秒、デフォルト 60)
   - LOG_LEVEL (DEBUG/INFO/...)
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート用）

   簡易的な .env サンプル:

   ```
   KABUSYS_ENV=development
   JQUANTS_REFRESH_TOKEN=xxxxxxxx
   KABU_API_PASSWORD=secret
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   MONITOR_POLL_INTERVAL=60
   ```

5. データディレクトリ（`data/`）を準備。SQLite / DuckDB のファイルは自動作成されますが、適切なパーミッションが必要です。

---

## 使い方

- 実行エンジン起動（プロセスの優先度を上げて起動）:

  ```bash
  python -m kabusys.run_execution
  ```

  - KABUSYS_ENV に `paper_trading` を指定すると MockBrokerClient を使い、データは `PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）に書き込まれ、本番 DB と分離されます。

- 監視ポーリング起動:

  ```bash
  python -m kabusys.run_monitoring
  ```

  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書きできます（最小 1 秒、デフォルト 60）。
  - 監視は常に本番の `SQLITE_PATH` を使用します（モードにかかわらず）。

- Streamlit ダッシュボード（ローカルで監視 DB を参照）:

  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

  - Dashboard は DB を read-only モードで開きます。監視プロセスを先に起動してデータを作成してください。

- Paper Trading 検証レポート生成:

  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
  ```

  - `--db` を省略すると `PAPER_TRADING_SQLITE_PATH` または `data/paper_trading.db` が使われます。

- AI（ニューススコアリング / レジーム判定）
  - news_nlp.score_news / regime_detector.score_regime を Python から呼び出して利用できます（OpenAI API key が必要）。
  - 例（スクリプト内から）:

    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, date(2026,4,10), api_key="sk-...")
    ```

  - API 呼び出しはリトライやパースの堅牢処理が実装されていますが、キー未設定時は ValueError を送出します。

---

## 重要な運用注意点

- .env の自動読み込み順序: OS 環境 > .env.local > .env。OS 環境のキーは保護され上書きされません。自動読み込みは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
- Paper Trading は本番 DB と完全分離する設計（`PAPER_TRADING_SQLITE_PATH` を使用）。
- 監視（Monitoring）は KABUSYS_ENV にかかわらず本番の `SQLITE_PATH` を使います（監視ログは本番 DB に集約）。
- PID / kill.flag
  - ExecutionEngine は PID ファイル（デフォルト `data/execution.pid`）を作成します。SystemMonitor は PID 存在・生存を検査し、stale PID を検出したらファイルを削除してリスクイベントを記録します。
  - KillSwitch は `data/kill.flag` を書き込むことで ExecutionEngine に停止シグナルを送ります（ExecutionEngine 側がフラグを監視する実装を持つことを前提）。
- DB マイグレーション
  - monitoring_db.init_monitoring_db() は冪等でテーブルを作成し、既存 DB にカラム（例: `peak_value`, `latency_ms`）が無ければ追加する簡易マイグレーション処理を行います。

---

## ディレクトリ構成

以下は主要ファイル／ディレクトリの抜粋です（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py  — 環境変数 / .env ロードと Settings
  - run_execution.py  — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring 起動スクリプト
  - ai/
    - __init__.py
    - news_nlp.py       — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py— 市場レジーム判定（OpenAI）
  - monitoring/
    - __init__.py
    - monitoring_db.py  — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py  — システム状態・データ鮮度チェック
    - trade_monitor.py   — 注文滞留・約定異常チェック
    - risk_monitor.py    — ドローダウン／ポジション上限チェック
    - kill_switch.py     — kill.flag 管理
    - alert_manager.py   — LINE 通知
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py
    - reconciler.py
    - order_repository.py
    - order_record.py
    - execution_engine.py
    - broker_factory.py
    - broker_api.py
    - risk_manager.py
    - ...（発注関連の実装）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - data/
    - pipeline.py (prices / DuckDB 関連ユーティリティなど)
    - stats.py (zscore 等)
  - tools/
    - __init__.py
    - paper_verification_report.py
  - utils/
    - __init__.py
    - process_priority.py — psutil を使ったプロセス優先度 / affinity ユーティリティ

（実際のツリーはリポジトリの全ファイルに依存します。上は主要モジュールの一覧です。）

---

## 開発時のヒント

- テストやローカル実行時に .env の自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセット。
- DuckDB は SQL を直接投げられるため、research や ai モジュールはローカルでのデータ実験に便利です。
- OpenAI API を使う処理（news_nlp / regime_detector）は外部 API 呼び出しを行うため、ユニットテストでは API 呼び出し箇所をモックしてください（コード中にモックしやすい箇所が用意されています）。
- process priority / cpu affinity を設定するユーティリティはプラットフォーム依存の例外を安全に無視する設計です（権限不足などは警告ログに落ちます）。

---

必要であれば、README に含めるコマンド実行例や .env.example の完全版、依存関係ファイル（requirements.txt）生成のサンプル、よくある運用 FAQ（データ更新 / ログ確認 / 障害時の対処）を追加できます。どれを追加しましょうか？