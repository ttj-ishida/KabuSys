# KabuSys

日本株自動売買システムのコアライブラリ（ドキュメント版）。  
この README は提供されたコードベースに基づく簡易ガイドです。

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（起動／ツール）
- 環境変数（主要設定）
- 運用上の注意（監視 / 停止フラグ 等）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを構成するモジュール群です。主な役割は以下の通りです。

- シグナル → 注文発行 → ブローカー送信 の Execution 層
- 注文・約定・ポジションの管理とリコンシリエーション
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ算出）
- リスク監視（ドローダウン監視、ポジション上限）
- システム監視（CPU/メモリ/ディスク、データ鮮度、プロセス生存）
- AI（ニュースセンチメント・レジーム判定）連携（OpenAI）
- モニタリングダッシュボード（Streamlit）と検証レポート生成ツール

設計上のポイント：
- DuckDB / SQLite を使ったデータ層（prices_daily 等は DuckDB）
- Paper Trading（検証）と Live（本番）で DB を分離可能
- 環境変数 / .env を使用した設定管理（自動ロード機能あり）
- フェイルセーフ（APIエラー時のフォールバックやログ保護）

---

## 主な機能一覧

- 実行エンジン起動: run_execution.py
  - 本番 / Paper trading 切替（KABUSYS_ENV=paper_trading）
  - Broker クライアントの切り替え（MockBroker を利用）
  - 起動時に Reconciler による同期処理を実行
- 監視ループ起動: run_monitoring.py
  - SystemMonitor / TradeMonitor / RiskMonitor 等を定期実行
  - MONITOR_POLL_INTERVAL で間隔変更可能（デフォルト 60 秒）
  - 監視ログは SQLite に永続化
- ポートフォリオ構築
  - 候補選定（score 等）・等配分・スコア配分
  - ポジションサイズ算出（リスクベース等）
  - セクター制約・レジーム乗数の適用
- AI 機能
  - news_nlp: LLM を使ったニュースセンチメント算出（ai_scores テーブルへ書込）
  - regime_detector: MA200 とマクロニュースセンチメントを合成してレジーム判定
- 監視・アラート
  - AlertManager: LINE Messaging API 経由でプッシュ通知
  - KillSwitch: 条件（例: ドローダウン）で data/kill.flag を作成し実行エンジン停止を指示
- ツール
  - paper_verification_report: Paper Trading DB を集計して PASS/FAIL 形式の検証レポート出力
  - Streamlit ベースの監視ダッシュボード（streamlit_dashboard.py）

---

## セットアップ手順

前提:
- Python 3.10+（型ヒントの union 表記等を使用）
- Git リポジトリのルートが存在する（.env 自動ロードのため）

1. リポジトリをクローン（省略）

2. 必要パッケージをインストール
   pip を利用する例:
   ```
   python -m pip install duckdb psutil requests openai streamlit
   ```
   （プロジェクトに requirements.txt があればそちらを利用してください）

3. 環境変数 / .env を準備
   - プロジェクトルートに `.env`（および `.env.local`）を置くと自動で読み込まれます。
   - 自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
   - 必須項目の例は後述の「環境変数」セクションを参照してください。

4. データディレクトリの作成（任意）
   ```
   mkdir -p data
   ```
   デフォルトで使用されるファイル:
   - data/monitoring.db（監視ログ）
   - data/paper_trading.db（Paper Trading 用 SQLite）
   - data/kabusys.duckdb（DuckDB）
   - data/execution.pid（ExecutionEngine PID）
   - data/kill.flag / data/stop_requested.flag（停止フラグ）

---

## 使い方

以下はローカル開発環境（プロジェクトが `src/` にある構成）を想定したコマンド例です。

- Python モジュールとして実行する（PYTHONPATH を通す）
  ```
  # 監視ループ起動（デフォルト 60 秒間隔。MONITOR_POLL_INTERVAL で変更可）
  PYTHONPATH=src python -m kabusys.run_monitoring

  # 実行エンジン起動
  PYTHONPATH=src python -m kabusys.run_execution
  ```

- Paper Trading（検証）モードで実行
  ```
  KABUSYS_ENV=paper_trading PYTHONPATH=src python -m kabusys.run_execution
  ```
  Paper Trading の場合は MockBrokerClient を使い、デフォルトで `data/paper_trading.db` に記録します（本番 DB と完全分離）。

- Streamlit 監視ダッシュボード起動
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- Paper Trading 検証レポート生成
  ```
  PYTHONPATH=src python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または
  PYTHONPATH=src python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI 機能（ニューススコア / レジーム判定）
  - これらは関数として呼び出します（Python スクリプト内から）。
  - 実行時に OpenAI API キーが必要（環境変数 `OPENAI_API_KEY` か、関数引数で渡す）。
  - 例: Python REPL から
    ```
    from kabusys.ai.news_nlp import score_news
    import duckdb, datetime
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, datetime.date(2026,4,1))
    ```

---

## 環境変数（主要設定）

Settings クラスが参照する主な環境変数（デフォルト値など）：

- 必須（未設定時は ValueError）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- OpenAI
  - OPENAI_API_KEY（AI 機能を使う場合に必須）

- 実行環境
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）

- ログレベル
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

- DB パス
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db

- Paper Trading
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）

- 監視 / PID / フラグ
  - PID_FILE_PATH: data/execution.pid
  - KILL_FLAG_PATH: data/kill.flag
  - KILL_FLAG_CLEAR_ON_START: "1" なら起動時に kill.flag をクリア

- 監視閾値（デフォルト値を Settings が参照）
  - CPU_THRESHOLD_PCT（デフォルト: 90.0）
  - MEMORY_THRESHOLD_PCT（デフォルト: 85.0）
  - DISK_THRESHOLD_PCT（デフォルト: 90.0）

- 監視ループ間隔（run_monitoring.py で使用）
  - MONITOR_POLL_INTERVAL（秒。デフォルト 60。0 以下や不正はデフォルトにフォールバック）

例: .env（最小の例）
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-...
LOG_LEVEL=INFO
```

自動ロードの仕様:
- プロジェクトルート（.git か pyproject.toml を含むディレクトリ）を起点に `.env`（上書き不可）→ `.env.local`（上書き可）の順で読み込みます。
- OS 環境変数は保護され、.env.local でも上書きされません（ただし自動ロードを無効化可能）。

---

## 運用上の注意

- 監視データは SQLite（monitoring.db）に永続化されます。monitoring モジュールの `init_monitoring_db` がテーブル作成と簡単なマイグレーションを行います。
- run_monitoring は常に Settings.sqlite_path（本番）を使って監視DBに接続します（KABUSYS_ENV に依存せず本番パスを参照）。
- run_execution は KABUSYS_ENV=paper_trading の場合に専用 paper_sqlite_path を使用します（本番 DB と分離）。
- 停止フラグ:
  - `data/stop_requested.flag` はスクリプト（run_monitoring/run_execution）がループを抜けるために利用する内部フラグ。
  - `data/kill.flag` は KillSwitch によって作成され、ExecutionEngine に外部停止シグナルを伝えます（存在すれば engine 側で検出して停止）。
  - KillSwitch の evaluate はドローダウンやポジション上限超過を検出した際に作成します。
- PID ファイル（data/execution.pid）は ExecutionEngine が自分の PID を書き込み、SystemMonitor が存在チェックするために使います。スタレ PID 検出時は削除され、リスクイベントがログに残ります。
- LINE 通知（AlertManager）を使用するには `LINE_CHANNEL_ACCESS_TOKEN` と `LINE_USER_ID` を設定してください。未設定の場合は送信せずログに出ます。
- OpenAI 呼び出しはレート制限や一時エラーに対して指数バックオフでリトライする実装ですが、API キーの管理とコストに注意してください。

---

## ディレクトリ構成（抜粋）

以下は主要ファイル／モジュールの構成（src/kabusys 以下）です。実際のプロジェクトルートは src/ を含む想定です。

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / Settings 管理（.env 自動ロード）
  - run_monitoring.py             — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - utils/
    - __init__.py
    - process_priority.py         — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py            — SQLite 監視DB 層（init / MonitoringDB クラス）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他: broker_factory, execution_engine, order_repository 等)
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
  - data/ (実行時に使用されるデータディレクトリ、ソース管理外)
    - monitoring.db
    - paper_trading.db
    - kabusys.duckdb
    - execution.pid
    - kill.flag
    - stop_requested.flag
  - tools/
    - __init__.py
    - paper_verification_report.py

---

## 開発・拡張のヒント

- DB スキーマ変更は monitoring_db.init_monitoring_db を通じて行う。簡単なマイグレーション処理（カラム追加）あり。
- AI 呼び出し周りは外部 API（OpenAI）依存のため、テストでは _call_openai_api をモックして検証してください（実装にもそのための分離が意識されています）。
- Execution / Broker 関連は BrokerAPIProtocol による抽象化がなされているため、実ブローカー実装と Mock を差し替えてテスト可能です。
- Streamlit ダッシュボードは監視 DB を読み取り専用で開くため、MonitoringEngine を稼働させてログを貯めてから確認してください。

---

この README はコードベースの要点をまとめたものです。詳細な API ドキュメント（関数仕様、データスキーマ、設計ドキュメント）は別途参照してください。必要であれば、特定モジュールの使用例や API 仕様の追記を作成します。