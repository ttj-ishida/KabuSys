# KabuSys

日本株向け自動売買システムの軽量モジュール群（ライブラリ＋起動スクリプト群）。

このリポジトリには以下の主要機能を提供するコンポーネントが含まれます：
- 注文執行エンジン（ExecutionEngine 起動スクリプト）
- 監視（MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- リサーチ（ファクター計算・特徴量探索）
- ニュース NLP / レジーム判定（OpenAI を利用したスコアリング）
- ユーティリティ（プロセス優先度設定等）
- 各種ツール（Paper Trading 検証レポート等）

以下にプロジェクト概要、機能一覧、セットアップ手順、基本的な使い方、ディレクトリ構成を示します。

---

## プロジェクト概要

KabuSys は日本株の自動売買および運用監視を想定したモジュール群です。  
設計上の特徴：
- 実行系（Execution）と監視系（Monitoring）を分離。監視は環境に依らず本番用 monitoring DB を参照。
- Paper Trading 環境をサポートし、本番 DB と完全分離してテスト可能。
- DuckDB を使った時系列・ファクタ計算（リサーチ）と、SQLite による監視ログ/取引ログの永続化。
- OpenAI（gpt-4o-mini 等）を使ったニュースセンチメント評価やマクロセンチメントを用いたレジーム判定機能。
- フェイルセーフ設計（API リトライ、部分失敗時の書き込み保護、kill flag による停止など）。

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（paper_trading モードではモックブローカーを使用）
  - run_monitoring.py: SystemMonitor のポーリングループを起動
- 監視
  - SystemMonitor: CPU/メモリ/Disk/プロセス生存・データ鮮度の監視
  - TradeMonitor: 注文の滞留検出・約定価格異常検出
  - RiskMonitor: ドローダウン / ポジション上限監視とアラート記録
  - KillSwitch: 条件に応じた停止フラグ（data/kill.flag）書き込み
  - AlertManager: LINE Push による通知（クールダウン管理）
  - Streamlit ダッシュボード: 監視結果の可視化
- Execution（発注系）
  - OrderManager / OrderRepository / Reconciler 等（注文作成・同期・再起動時のリコンシリエーション）
  - Paper Trading モード（KABUSYS_ENV=paper_trading）でモックブローカーと別 DB を使用
- ポートフォリオ構築
  - 候補選定（score / rank によるソート）
  - 重み計算（等金額 / スコア加重）
  - リスク適用（セクターキャップ、レジーム乗数）
  - ポジションサイズ決定（ロット丸め、利用可能資金に応じたスケーリング）
- リサーチ
  - ファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン・IC 計算・統計サマリー
- AI (OpenAI)
  - news_nlp.score_news: ニュースを集約して銘柄ごとにセンチメントスコアを ai_scores テーブルへ書き込み
  - regime_detector.score_regime: ma200 距離とマクロセンチメントを合成して market_regime を算出
- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成（稼働率 / 注文成功率 / レイテンシ 等）

---

## セットアップ手順

※ 以下は一般的なセットアップ手順です。環境や配布物によって細部は調整してください。

1. 必要条件
   - Python 3.10 以上
   - SQLite（標準で同梱）
   - DuckDB（Python パッケージ）
   - 外部 API: OpenAI（news/regime 機能を使用する場合）
   - ネットワークアクセス（LINE API を使う場合）

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージのインストール（requirements ファイルがない場合は手動で）
   - pip install duckdb psutil openai requests streamlit
   - （必要に応じて他ライブラリを追加）

4. プロジェクトルートの data ディレクトリ作成
   - mkdir -p data

5. 環境変数設定
   - .env もしくは環境変数で設定します。自動でプロジェクトルートの `.env` / `.env.local` がロードされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 重要な環境変数:
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - JQUANTS_REFRESH_TOKEN: J-Quants 用（必須な API を使う場合）
     - KABU_API_PASSWORD: kabuステーション API のパスワード（本番/接続時）
     - OPENAI_API_KEY: OpenAI を使う機能で必要
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager 使用時
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（監視DB: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB: data/paper_trading.db）
     - PAPER_FILL_MODE（paper_trading の約定挙動: instant|partial|never|reject）
     - MONITOR_POLL_INTERVAL（監視ループのポーリング間隔秒、デフォルト 60）
   - 例（.env の一部）:
     ```
     KABUSYS_ENV=development
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=your_pw
     JQUANTS_REFRESH_TOKEN=...
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     ```

6. DB 初期化
   - run_monitoring.py / run_execution.py は起動時に monitoring DB を自動で初期化します（init_monitoring_db を実行）。
   - 手動で監視 DB を初期化したい場合は Python から init_monitoring_db(sqlite3.connect("data/monitoring.db")) を呼ぶことも可能。

---

## 使い方（よく使うコマンド例）

- 監視ループを起動（本番/開発問わず monitoring DB を使用）
  - MONITOR_POLL_INTERVAL を指定してポーリング間隔を変更できます（秒）。
  - 例:
    ```
    export MONITOR_POLL_INTERVAL=30
    python -m kabusys.run_monitoring
    ```
  - 停止: Ctrl+C、もしくはプロジェクトルートの data/stop_requested.flag を作成すると安全にループが終了します。

- Execution エンジンを起動
  - Paper Trading モード:
    ```
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```
    paper_trading 時は MockBrokerClient を使用し、デフォルトで data/paper_trading.db に記録します（PAPER_TRADING_SQLITE_PATH で変更可）。
  - Live/Development モード:
    ```
    export KABUSYS_ENV=live
    python -m kabusys.run_execution
    ```
  - 実行中の停止: data/stop_requested.flag を作ると Engine が検知して停止します。KillSwitch（data/kill.flag）は監視側が生成して Execution 停止を促します。

- Streamlit ダッシュボード（監視結果の可視化）
  - 監視 DB を読み込み表示（読み取り専用推奨）
    ```
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    ```

- Paper Trading 検証レポート生成
  - ツールを使って指定期間のレポートを出力します:
    ```
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    ```
  - DB パスを指定したい場合:
    ```
    python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
    ```

- AI 機能（ニュース / レジーム判定）
  - ニューススコア算出（例）:
    ```py
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026,4,10), api_key="sk-...")
    ```
  - レジーム判定（例）:
    ```py
    from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime

    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026,4,10), api_key="sk-...")
    ```
  - 注意: API キー未設定時は ValueError が送出されます（API キーを引数で渡すか環境変数 OPENAI_API_KEY を設定）。

---

## 重要な実装/挙動のメモ

- Monitoring は KABUSYS_ENV に依らず常に本番用 sqlite_path（Settings.sqlite_path）を使用します。
- Execution は KABUSYS_ENV=paper_trading のとき paper_sqlite_path を使用して本番 DB とは完全に分離されます。
- run_monitoring.py / run_execution.py 起動時にプロセス優先度を set_process_priority("high") で試みます（プラットフォーム依存で失敗した場合は警告を出してスキップ）。
- Kill / Stop 信号:
  - data/stop_requested.flag: run_*.py が監視している停止フラグ（起動中に作成するとループが終了）
  - data/kill.flag: KillSwitch が発行する ExecutionEngine 停止用フラグ（監視ロジックから書き込む）
- .env の自動ロード:
  - プロジェクトルート（.git または pyproject.toml で検出）にある .env/.env.local を自動読み込みします。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py — パッケージ定義
- config.py — 環境変数 / 設定読み込みロジック（Settings クラス）
- run_monitoring.py — SystemMonitor ポーリング起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト

subpackages:
- monitoring/
  - monitoring_db.py — SQLite ベースの永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py — CPU/MEM/DISK/process/data鮮度の監視
  - trade_monitor.py — 注文滞留・約定異常検出
  - risk_monitor.py — ドローダウン / ポジション上限監視
  - kill_switch.py — kill.flag 書き込みユーティリティ
  - alert_manager.py — LINE Push 通知（クールダウン付き）
  - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - streamlit_dashboard.py — Streamlit ベースのダッシュボード表示
- execution/
  - order_manager.py — 注文管理の外向き API（OrderManager）
  - reconciler.py — 起動時リコンシリエーション（ブローカー再照合）
  - （その他: broker_factory, execution_engine, order_repository などが存在）
- portfolio/
  - portfolio_builder.py — 候補選定・重み付け
  - position_sizing.py — 株数決定・スケーリング・ロット丸め
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- research/
  - factor_research.py — モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン・IC・統計サマリー
- ai/
  - news_nlp.py — raw_news を OpenAI でセンチメントして ai_scores へ書き込み
  - regime_detector.py — ma200 + マクロセンチメントで市場レジームを判定
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ラッパー
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト

その他:
- data/ — データファイル置き場（デフォルト）
  - monitoring.db（Settings.sqlite_path）
  - paper_trading.db（PAPER_TRADING_SQLITE_PATH）
  - kabusys.duckdb（DuckDB）
  - execution.pid / stop_requested.flag / kill.flag など

---

## 開発・テストについて

- 設定テスト: Settings クラスは .env の自動ロードを行いますが、テスト実行時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して外部環境に依存しないようにできます。
- OpenAI 呼び出し部（news_nlp._call_openai_api や regime_detector._call_openai_api）はテスト時にモックしやすいように分離されています（unittest.mock.patch で差し替え）。
- DuckDB を使ったリサーチは外部 API に依存せず、prices_daily / raw_financials テーブルのみを参照する方針です。テスト時は小さな DuckDB ファイルを用意すると良いです。

---

## 付記（運用上の注意）

- Live 環境で ExecutionEngine を動かす際は設定値（KABU_API_PASSWORD、LOG_LEVEL、閾値など）を慎重に確認してください。
- paper_trading モードは本番資金にアクセスしないよう分離設計されていますが、設定ミス（パス指定ミスなど）によって本番 DB を上書きする可能性があるため環境変数の確認を行ってください。
- KillSwitch / RiskMonitor は冪等性とデデュープ機能を備えていますが、ログやフラグファイルの管理は運用ルールを設けてください。

---

必要であれば README にサンプル .env.example や systemd / supervisor 用のサービスユニット、CI 用のテスト手順（pytest 設定例）なども追加できます。どの情報を優先して追記しましょうか？