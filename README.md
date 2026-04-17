# KabuSys

KabuSys は日本株向けの自動売買システム（研究・ポートフォリオ構築・発注エンジン・監視・レポート・AI 補助）を目的としたコードベースです。本リポジトリはモジュール単位で機能が分離されており、ローカルの SQLite / DuckDB を使ってデータ永続化・解析を行います。

バージョン: 0.1.0

---

## 概要

主なコンポーネント：

- Execution（発注エンジン）: Broker クライアント経由で注文を作成・管理し、リスク制御やリコンシリエーションを行います。
- Monitoring（監視）: システム状態・注文状態・リスク指標の定期ポーリングとログ保存、LINE 通知や kill flag によるエンジン停止を扱います。
- Research / Factors: DuckDB 上の株価・財務データからファクター（モメンタム・ボラティリティ・バリュー等）を計算します。
- Portfolio Construction: 候補選定、重み付け、ポジションサイズ決定、セクター制限やレジーム補正など。
- AI (OpenAI): ニュースの NLP スコアリング（センチメント）や市場レジーム判定のラッパー。
- Tools: Paper Trading の検証レポート生成や Streamlit ダッシュボード等のユーティリティ。

設計方針の抜粋：

- 本番と paper_trading を分離（paper_trading は専用 SQLite DB を使用）
- DuckDB を分析用 DB として使用（prices_daily / raw_financials 等を前提）
- 外部 API 呼び出し（OpenAI 等）は明示的にキーを渡すか環境変数で管理
- 重要処理はフェイルセーフ（API失敗時はフォールバック）を採用

---

## 機能一覧

- 発注管理（OrderManager、OrderRepository、ExecutionEngine）
- 起動時リコンシリエーション（Reconciler）
- リスク管理（RiskManager、RiskMonitor）
- 監視（SystemMonitor、TradeMonitor、MonitoringEngine）
- LINE によるアラート通知（AlertManager）
- kill.flag による外部停止シグナル書き込み（KillSwitch）
- Paper Trading モード（MockBrokerClient を利用、DB は data/paper_trading.db に分離）
- Paper Trading 検証レポート生成ツール（kabusys.tools.paper_verification_report）
- Streamlit ダッシュボード（監視データ表示）
- ニュース NLP（OpenAI を使った銘柄別センチメント → ai_scores に保存）
- 市場レジーム判定（ETF MA とマクロニュースを組み合わせた判定）
- ポートフォリオ構築ユーティリティ（候補選定、重み・株数計算、セクター上限など）
- process priority / CPU affinity 設定ユーティリティ（psutil ベース）

---

## セットアップ手順

1. Python 環境

   - Python 3.9+（コード中の typing 構文などを想定）
   - 仮想環境を推奨（venv, pyenv など）

2. 依存ライブラリをインストール

   requirements.txt は含まれていないため、主要な依存を個別インストールします（バージョンは適宜指定してください）:

   ```
   pip install duckdb psutil requests openai streamlit
   ```

   - 標準ライブラリ: sqlite3 などは Python に同梱
   - 実際の運用では必要なパッケージを requirements.txt にまとめて管理してください。

3. プロジェクトルートに `data/` ディレクトリを作成

   ```
   mkdir -p data
   ```

   - デフォルトの DB パス:
     - DuckDB: data/kabusys.duckdb
     - Monitoring SQLite: data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db

4. 環境変数 / .env

   - プロジェクトは自動的にプロジェクトルート（.git または pyproject.toml があるディレクトリ）から `.env` / `.env.local` を読み込みます（OS 環境変数が優先されます）。
   - 自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   必須または主要な環境変数（例）:

   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - OPENAI_API_KEY (AI 機能を使う場合に必要)
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 用、デフォルト: instant）
   - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
   - DUCKDB_PATH: data/kabusys.duckdb
   - SQLITE_PATH: data/monitoring.db
   - PID_FILE_PATH, KILL_FLAG_PATH, LOG_LEVEL 等

   サンプル `.env`（最小）:

   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_token
   KABU_API_PASSWORD=your_kabu_password
   OPENAI_API_KEY=sk-...
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

---

## 使い方

以下は主要な起動・ユーティリティコマンド例です。コードはパッケージとして動作するように `if __name__ == "__main__":` が書かれているため、モジュール実行が可能です。

- ExecutionEngine（発注エンジン）起動

  - 通常起動（production/paper の切替は KABUSYS_ENV に依存）:

    Linux/macOS（環境変数設定例）:

    ```
    export KABUSYS_ENV=paper_trading   # または live / development
    python -m kabusys.run_execution
    ```

  - 停止するにはプロジェクトルート `data/stop_requested.flag` を作成するか、KillSwitch を使って `data/kill.flag` を書き込む（監視側や operator が作成する想定）。

- Monitoring 起動（SystemMonitor 単体のポーリングループ）

  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で秒数を指定（デフォルト 60 秒）

    ```
    export MONITOR_POLL_INTERVAL=30
    python -m kabusys.run_monitoring
    ```

  - 停止は `data/stop_requested.flag` を作成します（スクリプトが検知して終了します）。

- Paper Trading 検証レポート（コマンドラインツール）

  - 使い方（ヘッダに記載されているとおり）:

    ```
    python -m kabusys.tools.paper_verification_report
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
    ```

- Streamlit ダッシュボード（監視 UI）

  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

  - ブラウザでダッシュボードが開き、ポートフォリオ集計・ポジション・注文・最新システム状態・最新リスクログを確認できます。

- AI モジュール（プログラムから呼び出し）

  - ニュース NLP（銘柄別スコア取得）:

    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    # target_date を指定（例: 2026-04-01）
    score_news(conn, date(2026, 4, 1), api_key="sk-...")
    ```

  - 市場レジーム判定:

    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime

    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, date(2026, 4, 1), api_key="sk-...")
    ```

  - OpenAI API の呼び出しはリトライ・バックオフ等に対応しています。API キーは引数で渡すか環境変数 `OPENAI_API_KEY` を利用します。

---

## 停止 / 管理（フラグファイル）

- run_execution/run_monitoring はプロジェクトルート `data/stop_requested.flag` の存在を見て終了・停止します。停止を要求するにはファイルを作成してください：

  ```
  touch data/stop_requested.flag
  ```

- Execution 側を強制停止する（KillSwitch）には `data/kill.flag` を書き込みます。KillSwitch は reason をファイルに書き込み、存在確認で停止を促します。

- PID ファイルはデフォルト `data/execution.pid`。SystemMonitor は PID ファイルの stale 判定・削除を行います。

---

## 主な設定と注意点

- KABUSYS_ENV: "development" | "paper_trading" | "live"
  - paper_trading の場合、発注は MockBrokerClient を使い、DB は `PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）へ記録され、本番 DB と分離されます。

- PAPER_FILL_MODE: paper_trading 時の約定モード
  - 有効値: "instant" | "partial" | "never" | "reject"

- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）

- 自動 .env 読み込み:
  - プロジェクトルート（.git または pyproject.toml がある階層）から `.env`（優先度低）と `.env.local`（優先度高）を読み込む仕組みがあります。
  - OS 環境変数は上書きされません（ただし .env.local は override=True なので既存キーを上書きできますが、protected ロジックで OS 環境変数は保護されます）。
  - 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。

- データベースマイグレーション:
  - monitoring DB 初期化関数は必要なテーブルと列（例: latency_ms, peak_value）の存在チェックと追加を行います（冪等処理あり）。

- プロセス優先度:
  - 起動スクリプトは最初に `set_process_priority("high")` を呼んで優先度設定を試みます（psutil が必要）。
  - 権限不足 / 未対応 OS の場合は警告を出してスキップします。

---

## ディレクトリ構成（主要ファイル）

簡易ツリー（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定管理（Settings）
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — SystemMonitor 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポートツール
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュース NLP（OpenAI 経由）
    - regime_detector.py           — 市場レジーム判定
  - monitoring/
    - __init__.py
    - monitoring_db.py             — SQLite 永続化層（監視テーブル）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - execution_engine.py
    - broker_factory.py
    - broker_api.py
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
  - utils/
    - process_priority.py
    - __init__.py
  - data/ (実行時に作成されることを想定)
    - monitoring.db (デフォルト)
    - kabusys.duckdb (デフォルト)
    - paper_trading.db (paper_trading 用)

---

## 開発・運用上の補足

- ログレベルは環境変数 `LOG_LEVEL` で制御できます（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
- DuckDB 側のデータスキーマ（prices_daily / raw_financials / raw_news 等）は本リポジトリの分析・AI 機能が前提としています。データ投入は別途パイプラインを用意してください（kabusys.data.pipeline を参照する関数が利用されています）。
- OpenAI 呼び出しはコストとレート制限に注意してください。モジュールはリトライ・バックオフ処理を備えていますが、呼び出し頻度やバッチサイズに注意してください。
- Paper Trading の検証は tools/paper_verification_report を使用すると、稼働率・注文成功率・レイテンシ等の指標を出力できます。

---

この README はコードベースの主要ポイントをまとめたものです。詳細は各モジュールの docstring や関数注釈を参照してください。必要であればデプロイ手順、CI / テスト方法、requirements.txt の整備なども追記します。