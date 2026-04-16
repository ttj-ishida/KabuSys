# KabuSys

日本株自動売買システムのサブセット実装ドキュメント（README）。

このリポジトリには、監視（Monitoring）、実行エンジン（Execution）、ポートフォリオ構築（Portfolio）、リサーチ（Research）、AI ベースのニュース NLP、ユーティリティ等の主要コンポーネントが含まれています。

---

## プロジェクト概要

KabuSys は日本株の自動売買パイプラインを構成するモジュール群です。主要な役割は以下の通りです。

- Execution: ブローカーとの発注・注文状態管理・再同期（Reconciliation）を担う。
- Monitoring: システム状態・注文滞留・リスク（ドローダウン、ポジション上限）を監視し、アラートや停止シグナルを発行。
- Portfolio: 銘柄選定、重み付け、株数計算（ポジションサイズ）などの純粋関数群。
- Research: ファクター計算、将来リターン、IC 計算、特徴量探索。
- AI: ニュースのセンチメント評価（OpenAI API を利用）と市場レジーム判定。
- Tools: Paper Trading 検証レポート生成や Streamlit ダッシュボードなど。

設計上の特徴：
- DuckDB（履歴・時系列データ）と SQLite（監視ログ / 注文DB）を併用。
- Paper trading では本番 DB と分離された SQLite を利用可能。
- OpenAI を用いた NLP はフェイルセーフやリトライ実装あり。

---

## 機能一覧

主要機能（抜粋）:

- 監視 (monitoring)
  - SystemMonitor: CPU/メモリ/ディスク・データ鮮度・実行プロセス存在チェック
  - TradeMonitor: 注文滞留・約定異常検出
  - RiskMonitor: ドローダウン検出、ポジション上限監視
  - KillSwitch / AlertManager: 条件による停止フラグ書き込み、LINE 送信による通知
  - MonitoringEngine: 各 Monitor を束ねてポーリング

- 実行 (execution)
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - BrokerFactory / BrokerClient（本番 or Mock）
  - OrderManager / OrderRepository / Reconciler による状態管理と再同期

- ポートフォリオ構築 (portfolio)
  - 銘柄候補選定、等配分 / スコア配分、リスク調整（セクター上限、レジーム乗数）
  - 株数決定（単元株丸め、aggregate cap）

- リサーチ (research)
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリー

- AI モジュール (ai)
  - ニュースのセンチメント評価（OpenAI, gpt-4o-mini）
  - 市場レジーム判定（ETF MA200 乖離 + マクロセンチメント）

- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）
  - Streamlit 監視ダッシュボード（monitoring/streamlit_dashboard.py）

---

## セットアップ手順

1. Python 環境
   - 推奨: Python 3.10+
   - 仮想環境を作成・有効化:
     ```
     python -m venv .venv
     source .venv/bin/activate  # Unix/macOS
     .venv\Scripts\activate     # Windows
     ```

2. 依存パッケージのインストール（代表例）
   - 本リポジトリに requirements.txt は含まれていませんが、以下をインストールしてください:
     ```
     pip install duckdb psutil requests openai streamlit
     ```
   - 実行やテストに応じて追加ライブラリが必要になる場合があります。

3. プロジェクトルートの .env 設定
   - プロジェクトは自動で `.env` / `.env.local` をロードします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動無効化可能）。
   - 必須環境変数例:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - オプション・重要変数:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - OPENAI_API_KEY: AI モジュールを利用する場合に必要
     - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading時のモック約定モード）
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading用DB）
     - SQLITE_PATH: data/monitoring.db（監視 DB）
     - DUCKDB_PATH: data/kabusys.duckdb
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（アラート送信）

4. データディレクトリ
   - デフォルトの DB / PID / フラグ等は `data/` 配下に作成されます。必要に応じて作成権限を確認してください。

---

## 使い方

主要な起動・実行方法を紹介します。

- モニタリング（永続ポーリング）
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き（デフォルト 60 秒）
  - 起動:
    ```
    python -m kabusys.run_monitoring
    ```
  - 監視は常に本番用の sqlite_path を使用します（Settings.sqlite_path）。

- 実行エンジン（ExecutionEngine）
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使用され、paper_trading 用 SQLite に記録されます。
  - 起動:
    ```
    python -m kabusys.run_execution
    ```
  - 実行中に `data/stop_requested.flag` が存在すると停止します。Execution はデフォルトで `data/execution.pid` を書きます。

- Streamlit ダッシュボード
  - 監視 DB を読み取りモードで表示します。
    ```
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    ```

- Paper Trading 検証レポート
  - Paper Trading 用 SQLite を対象に期間指定でレポートを生成します。
    ```
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    ```
  - データベースを明示する場合:
    ```
    python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
    ```

- AI モジュール（ニューススコア / レジーム判定）
  - どちらも DuckDB 接続を受け取り、OPENAI_API_KEY が必要です（引数でも渡せます）。
  - 例: score_news / score_regime はライブラリ関数として呼び出して使用します（CLI ではありません）。
  - API 呼び出し回数や失敗時の挙動は実装内でリトライ・フェイルセーフが組み込まれています。

環境変数（主要）
- KABUSYS_ENV: development | paper_trading | live
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）
- OPENAI_API_KEY: OpenAI API キー（ai モジュールで必須）
- PAPER_FILL_MODE: paper_trading 時のモック約定挙動（instant, partial, never, reject）
- PAPER_TRADING_SQLITE_PATH / SQLITE_PATH / DUCKDB_PATH
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID

停止制御・フラグ
- data/stop_requested.flag: run_monitoring / run_execution が監視する停止フラグ
- data/kill.flag: KillSwitch が書き込む実行停止フラグ（ExecutionEngine に通知）
- PID ファイル: data/execution.pid（ExecutionEngine が書き込み）

ログ・通知
- ログは標準の logging を使用。AlertManager により LINE へプッシュ可能（トークン設定必要）。
- MonitoringEngine は重要イベントで AlertManager を使って通知できます。

---

## ディレクトリ構成

リポジトリ内の主要ファイル／ディレクトリ構成（抜粋）:

```
src/
  kabusys/
    __init__.py
    config.py
    run_monitoring.py
    run_execution.py

    ai/
      __init__.py
      news_nlp.py
      regime_detector.py

    monitoring/
      __init__.py
      monitoring_db.py
      system_monitor.py
      trade_monitor.py
      risk_monitor.py
      kill_switch.py
      alert_manager.py
      monitoring_engine.py
      streamlit_dashboard.py

    execution/
      order_manager.py
      order_repository.py
      reconciler.py
      execution_engine.py
      broker_factory.py
      broker_api.py
      order_record.py
      ... (その他 execution 関連)

    portfolio/
      __init__.py
      portfolio_builder.py
      risk_adjustment.py
      position_sizing.py

    research/
      __init__.py
      factor_research.py
      feature_exploration.py

    tools/
      __init__.py
      paper_verification_report.py

    data/                 # 実行時に使用する DB / PID / フラグを置く（git には含めない）
```

主要なモジュールの役割は前節「機能一覧」を参照してください。

---

## 注意事項 / トラブルシューティング

- SQLite / DuckDB のパスは Settings で指定可能。デフォルトは data/*. 必要なら .env で上書きしてください。
- Paper trading を行う際は KABUSYS_ENV を `paper_trading` に設定することで本番 DB との分離が行われます（PAPER_TRADING_SQLITE_PATH）。
- OpenAI API を使う機能を実行する場合は OPENAI_API_KEY を設定してください。API の失敗時は一部機能が 0 やスキップで安全にフォールバックする実装になっていますが、意図した動作を得るには正しいキーが必要です。
- psutil によるプロセス優先度設定は権限不足や一部プラットフォームで失敗する可能性があります。失敗時は警告ログが出力され、処理は継続されます。
- `MONITOR_POLL_INTERVAL` に 0 や負値を設定すると無効な値としてデフォルト（60 秒）にフォールバックします。
- `kill.flag` / `stop_requested.flag` はファイルベースの制御フラグです。テストや運用で手動作成・削除することでプロセスを制御できます。

---

## 開発者向け補足

- 設定ロードは config.py に実装され、自動で .env / .env.local をプロジェクトルートから読み込みます（必要に応じて自動読み込みを無効化できます）。
- モジュールは可能な限り副作用を避ける設計（DB 書き込みは明示的に行う等）になっています。
- AI 呼び出し部分はテスト容易性を意識し、API 呼び出し箇所を差し替え可能に実装しています（ユニットテストでモック可能）。

---

この README はコードベースに含まれる実装と docstring を元に作成しました。実行環境や運用ルールに合わせて .env の設定、DB パス、監視間隔等を調整してご利用ください。質問や追加で欲しいドキュメント（API リファレンス、設定例、運用手順など）があれば教えてください。