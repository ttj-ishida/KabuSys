# KabuSys

日本株向け自動売買システムのコンポーネント群（ライブラリ・監視・実行エンジン・研究用ツール等）。  
このリポジトリは戦略構築（ファクター計算・特徴量探索）、ポートフォリオ構築、発注実行、監視・アラート、AI を用いたニュース解析などのモジュールで構成されています。

---

## プロジェクト概要

KabuSys は以下の目的を持つモジュール群です。

- DuckDB / SQLite を使ったデータ処理・履歴管理
- 発注エンジン（ExecutionEngine）とブローカー抽象化
- 監視（System / Trade / Risk）とアラート（LINE）機能
- Paper Trading 用の切替（本番 DB と分離）
- ニュースの LLM（OpenAI）を用いたセンチメント評価・レジーム判定
- 研究用ファクター計算・特徴量探索ユーティリティ
- Streamlit ベースの監視ダッシュボード
- 検証レポート生成ツール（Paper Trading 向け）

設計方針として、ルックアヘッドバイアス対策（date.today() の直接参照を避ける等）、冪等性・クラッシュ耐性（DB 操作、2相永続化、一貫したマイグレーション）、フェイルセーフ（API失敗時のフォールバック）を重視しています。

---

## 主な機能一覧

- execution/
  - 発注管理（OrderManager, Reconciler）と再起動時の自動リコンシリエーション
  - Paper Trading モード（モックブローカー、専用 SQLite）
  - リスク管理（RiskManager）
- monitoring/
  - SystemMonitor: CPU/メモリ/ディスク/プロセス死活、データ鮮度チェック
  - TradeMonitor: 滞留注文、約定価格異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視 + kill flag 書き込み
  - AlertManager: LINE Push による通知（クールダウン管理）
  - Streamlit ダッシュボード（監視 DB を読み取り専用で可視化）
- ai/
  - news_nlp: ニュースを LLM で集約評価して ai_scores テーブルへ書き込み
  - regime_detector: ma200 とマクロニュースで市場レジーム判定（market_regime）
- research/
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ等
- portfolio/
  - 候補選定、重み計算、セクター制約適用、ポジションサイズ算出（単元丸め等）
- tools/
  - paper_verification_report: Paper Trading DB から検証レポートを生成
- config と utils
  - Settings: 環境変数 / .env 読み込みロジック（自動読み込みの挙動あり）
  - process_priority: プロセス優先度・CPU affinity 設定ユーティリティ

---

## 要件

- Python >= 3.10（型注釈に PEP 604 の `X | Y` 構文を使用）
- 必要パッケージ（例）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード利用時)
- SQLite（標準ライブラリで利用可）

インストール例（仮想環境推奨）:

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install duckdb psutil requests openai streamlit
```

（必要に応じてプロジェクト専用の requirements.txt を作成してください）

---

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリへ移動。

2. Python 仮想環境を作成・有効化し、依存パッケージをインストール（上記参照）。

3. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くことで自動読み込みされます（既存 OS 環境 > .env.local > .env の優先順位）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
   - 必須（運用に応じて）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を使う機能を利用する場合:
     - OPENAI_API_KEY
   - 監視・DB 関連（デフォルトあり）:
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, default: data/paper_trading.db)
     - KABUSYS_ENV (development | paper_trading | live) — default: development
     - PAPER_FILL_MODE (instant | partial | never | reject) — paper_trading の約定動作
     - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
   - LINE 通知を使う場合:
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID

   簡単な .env 例:

   ```env
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   OPENAI_API_KEY=sk-...
   JQUANTS_REFRESH_TOKEN=...
   KABU_API_PASSWORD=...
   LINE_CHANNEL_ACCESS_TOKEN=...
   LINE_USER_ID=Uxxxxxxxxxxxx
   ```

4. 必要なデータベースファイルやデータフォルダ（`data/`）を作成して権限を調整する。

---

## 使い方（主要スクリプト）

※各コマンドはプロジェクトルートから実行することを想定しています。

- 実行エンジン（ExecutionEngine）を起動

  - 本番（live）または開発（development）の場合は通常の DB を使用:
    ```bash
    export KABUSYS_ENV=live   # または development
    python -m kabusys.run_execution
    ```

  - Paper Trading（モックブローカー、データを data/paper_trading.db に分離）:
    ```bash
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```

  run_execution は起動時にプロセス優先度を "high" に設定し、必要な DB 初期化やコンポーネントの組み立てを行ってセッションを実行します。

- 監視ループ（SystemMonitor を単体でポーリング）

  - デフォルトのポーリング間隔は 60 秒。環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（正の整数）。
    ```bash
    python -m kabusys.run_monitoring
    ```

  - 監視は常に本番用の sqlite_path を使って記録します（KABUSYS_ENV にかかわらず）。

- Streamlit ダッシュボード（監視データ閲覧）

  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

  readonly モードで SQLite DB を開き、Overview / Positions / Orders / System タブを表示します。

- Paper Trading 検証レポートの生成（tools）

  SQLite（paper_trading）DB から集計して標準出力にレポートを出力します。

  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # or 指定 DB の場合
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- ライブラリ的な利用（Python REPL やスクリプトから）
  - 研究用 API（DuckDB 接続を渡して呼ぶ）:
    ```py
    import duckdb
    from datetime import date
    from kabusys.research import calc_momentum, calc_volatility, calc_value

    conn = duckdb.connect("data/kabusys.duckdb")
    res = calc_momentum(conn, date(2026, 4, 10))
    ```
  - AI スコアリング / レジーム判定:
    ```py
    from kabusys.ai.news_nlp import score_news
    from kabusys.ai.regime_detector import score_regime
    # duckdb_conn: duckdb connection, target_date: date object
    score_news(duckdb_conn, target_date, api_key="sk-...")
    score_regime(duckdb_conn, target_date, api_key="sk-...")
    ```

---

## 重要な挙動・運用メモ

- .env 自動読み込み
  - プロジェクトルート（.git または pyproject.toml を基準）を探索して `.env` と `.env.local` を自動ロードします。
  - OS 環境変数が優先され、`.env.local` は `.env` を上書きします。
  - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- Paper Trading 分離
  - `KABUSYS_ENV=paper_trading` のとき、MockBrokerClient を使い、DB は `PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）を使って本番 DB と分離されます。

- モニタ・キルスイッチ
  - RiskMonitor が閾値超過を検出すると kill.flag を書き込み、ExecutionEngine に停止シグナルを伝えます（kill.flag のパスは Settings.kill_flag_path）。
  - ExecutionEngine 起動時に `kill_flag_clear_on_start` が設定されているとフラグをクリアします。

- プロセス優先度
  - run_monitoring / run_execution 起動時に process priority を "high" に設定しようとします（プラットフォームによる制約あり、失敗してもワーニングで継続）。

- データ鮮度チェック
  - SystemMonitor は DuckDB の prices_daily テーブルから最終日を取得して、データ更新が 3 日以内かどうかを確認します（休日調整用の許容値あり）。

- OpenAI API の利用
  - `OPENAI_API_KEY` が必要。API 呼び出しはリトライ、フォールバック設計（429 / ネットワーク / 5xx は指数バックオフ）がありますが、失敗時はスコアをゼロ等で安全に継続する実装です。
  - LLM レスポンスは JSON モードで期待していますが、パース不能時のリカバリ処理も含まれます。

---

## ディレクトリ構成

主要ファイル・モジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / .env 読み込みと Settings
  - run_monitoring.py              — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - utils/
    - __init__.py
    - process_priority.py          — プロセス優先度・CPU affinity
  - monitoring/
    - __init__.py
    - monitoring_db.py             — SQLite スキーマ / 永続化層
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
    - order_repository.py
    - order_record.py
    - broker_factory.py
    - execution_engine.py
    - (その他ブローカー関連)
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - tools/
    - __init__.py
    - paper_verification_report.py

補足: データファイルはプロジェクト外の `data/` 等に配置する想定。デフォルトパスは Settings で定義されています（duckdb, sqlite など）。

---

## 開発者向けメモ

- 型・テスト
  - コアロジックは純粋関数（DB 参照なし）で記述している箇所が多く、ユニットテストが書きやすい設計です（例: portfolio/*.py）。
- DB マイグレーション
  - monitoring_db.init_monitoring_db は冪等で実行可能です。既存スキーマにカラムがない場合は ALTER TABLE で追記する簡易マイグレーションを行います。
- ロギング
  - run_* スクリプトでは logging.basicConfig(level=logging.INFO) を呼んでいます。詳細デバッグを見たい場合は環境変数 LOG_LEVEL を設定してください（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
- テスト用フラグ
  - Settings.kill_flag_clear_on_start 等のオプションで起動時のクリンナップ挙動を制御できます。
- API 呼び出しのモック
  - OpenAI 呼び出しや外部ブローカー API はテストでモック可能なよう関数分離されています（テスト用に patch しやすい実装）。

---

もし README に追加したい内容（例: CI 設定、requirements.txt、起動 Dockerfile、詳細な環境変数の一覧や推奨値、サンプル .env.example）や、特定のコンポーネントのドキュメント化（ExecutionEngine のフロー図など）があれば教えてください。必要に応じて追記・整形します。