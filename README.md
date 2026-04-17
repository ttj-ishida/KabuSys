# KabuSys

日本株自動売買システム（KabuSys）のコードベース README。  
このドキュメントはプロジェクト概要、機能一覧、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

注意：このリポジトリは実際のブローカー API や市場データ等と連携するためのコンポーネントを含みます。実運用前に十分なテストと安全対策（APIキーの管理、資金制御、リスク設定など）を行ってください。

---

## プロジェクト概要

KabuSys は日本株の自動売買／リサーチ／監視を行うためのモジュール群です。主な目的は以下の通りです。

- 戦略に基づくシグナル生成 → 注文作成 → ブローカーへの発注（ExecutionEngine）
- 注文およびポジションの整合性確保（Reconciler）
- 監視機能（System / Trade / Risk）とアラート送信（LINE）
- Paper Trading（模擬売買）用の分離された DB と振る舞い
- リサーチ用ファクター計算、特徴量解析モジュール
- ニュースを LLM（OpenAI）でスコアリングして投資判断に取り込む AI モジュール
- 検証レポート生成および Streamlit ダッシュボード

設計上、多くの関数は副作用を持たず純粋関数として実装され、DuckDB/SQLite を用いたデータ層を区別しています。環境変数・.env を利用して挙動を切り替えます。

---

## 主な機能一覧

- Execution
  - ExecutionEngine（エンジン起動スクリプト: run_execution.py）
  - Broker クライアントの切替（本番 / paper_trading の Mock）
  - OrderManager / OrderRepository / Reconciler（自動復旧）
  - RiskManager（発注前リスクチェック、レートリミット等）
- Monitoring
  - SystemMonitor（CPU/メモリ/ディスク・プロセス・データ鮮度監視）
  - TradeMonitor（滞留注文・約定異常検出）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - KillSwitch（条件で Execution を停止する flag ファイル生成）
  - AlertManager（LINE へプッシュ通知）
  - MonitoringEngine（複数 Monitor のポーリング）
  - Streamlit ベースの監視ダッシュボード
- Research / Portfolio
  - factor_research（モメンタム、ボラティリティ、バリュー等の計算）
  - feature_exploration（将来リターン、IC、統計サマリー）
  - portfolio（候補選定、重み計算、ポジションサイズ算出、セクター制限、レジーム乗数）
- AI
  - news_nlp（ニュースを LLM でセンチメント化し ai_scores に書き込み）
  - regime_detector（MA とマクロニュースを組み合わせて市場レジーム判定）
- Tools
  - paper_verification_report（Paper Trading 検証レポート生成スクリプト）
- ユーティリティ
  - process_priority（プロセス優先度 / CPU affinity 設定）
  - config（環境変数・.env 自動ロード、Settings クラス）

---

## セットアップ手順

1. リポジトリをクローン／配置

2. Python 仮想環境を作成して有効化（例）
   - python3 -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール  
   このコードベースでは以下のパッケージを使用します（代表例）。requirements.txt がない場合は手動でインストールしてください。
   - duckdb
   - psutil
   - requests
   - openai
   - streamlit
   - （必要に応じて）その他のテスト用パッケージ

   例:
   pip install duckdb psutil requests openai streamlit

4. data ディレクトリ作成
   - mkdir -p data

5. 環境変数設定（.env または .env.local）
   プロジェクトルートに .env を置くと自動で読み込まれます（OS 環境変数が優先）。自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須（実運用時）:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD

   推奨設定例（.env）:
   ```
   KABUSYS_ENV=development            # development | paper_trading | live
   LOG_LEVEL=INFO
   OPENAI_API_KEY=sk-...
   JQUANTS_REFRESH_TOKEN=...
   KABU_API_PASSWORD=...
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   PAPER_FILL_MODE=instant           # instant | partial | never | reject
   LINE_CHANNEL_ACCESS_TOKEN=...
   LINE_USER_ID=...
   PID_FILE_PATH=data/execution.pid
   KILL_FLAG_PATH=data/kill.flag
   ```

6. DB 初期化
   - Monitoring や Execution の起動スクリプトは起動時に必要テーブルを自動作成します（init_monitoring_db を利用）。特別なマイグレーションは起動時に自動適用されます。

---

## 使い方

以下は代表的な起動・実行方法です。

- 監視ループの起動（Monitoring）
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定可能（デフォルト 60）
  - 実行:
    python -m kabusys.run_monitoring
  - 停止:
    - Ctrl+C で終了
    - またはプロジェクトルートの data/stop_requested.flag を作成すると安全にループが抜けます

- エンジン（ExecutionEngine）起動
  - KABUSYS_ENV 環境によって paper_trading（MockBrokerClient）か本番ブローカーを選択します
  - Paper Trading の場合データは PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）に格納され、本番 DB と完全に分離されます
  - 実行:
    python -m kabusys.run_execution
  - 停止:
    - Ctrl+C
    - または data/stop_requested.flag を作成するとエンジンに停止シグナルが送られます
  - PID ファイル:
    - 実行時に data/execution.pid（デフォルト）に PID を書きます。SystemMonitor はこの PID を監視します

- Streamlit ダッシュボード
  - 実行方法例:
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - DB を読み取り専用で開くため、MonitoringEngine 実行中に閲覧するのが推奨

- Paper Trading 検証レポート
  - 使い方:
    python -m kabusys.tools.paper_verification_report
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション:
    --db で PAPER_TRADING_SQLITE_PATH を上書き可能（例: --db data/paper_trading.db）

- AI / リサーチ機能（ライブラリ API）
  - ニューススコア付与:
    from kabusys.ai import score_news
    score_news(conn: duckdb.DuckDBPyConnection, target_date: datetime.date, api_key: Optional[str])
  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key=None)
  - ファクター計算:
    from kabusys.research import calc_momentum, calc_volatility, calc_value
    calc_momentum(duckdb_conn, target_date)
  - ポートフォリオ系ユーティリティ:
    from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier

- Kill Switch / Stop フラグ
  - kill.flag (Settings.kill_flag_path、デフォルト data/kill.flag) は ExecutionEngine を停止させるための「致命的」フラグです。KillSwitch が検出して書き込みます。
  - stop_requested.flag（data/stop_requested.flag）は run_monitoring/run_execution 側のローカル停止用フラグとして使われています（起動スクリプト内で参照）。

- 環境読み込みの挙動
  - 自動でプロジェクトルート（.git または pyproject.toml を基準）を探索し `.env`（優先度低）・`.env.local`（優先度高）を読み込みます。
  - OS 環境変数は保護され、.env で上書きされません（ただし .env.local は override=True で上書き可）。
  - 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します（主にテスト用）。

---

## 重要な環境変数（抜粋）

- KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring）パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite パス（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant|partial|never|reject）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH, KILL_FLAG_PATH: 実行中プロセスの PID ファイル／kill flag のパス
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動読み込みを無効化

---

## ディレクトリ構成（抜粋）

リポジトリの主なファイル／モジュール構成（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数/.env 読み込み、Settings クラス
  - run_monitoring.py              — SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成ツール
  - monitoring/
    - __init__.py
    - monitoring_db.py             — SQLite テーブル定義・簡易永続化 API
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
    - (その他 broker_factory, execution_engine, order_repository 等)
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
  - utils/
    - process_priority.py

- data/ (推奨、実行時に使用するファイル置き場)
  - monitoring.db (デフォルト)
  - paper_trading.db (paper_trading 用)
  - kabusys.duckdb
  - execution.pid
  - kill.flag
  - stop_requested.flag

---

## 運用上の注意事項

- Paper Trading は本番 DB と完全に分離されていますが、API キーや秘密情報の管理は慎重に行ってください。
- OpenAI を利用する機能はネットワーク/課金/レート制限の影響を受けます。API 呼び出しはリトライ・バックオフや失敗時のフォールバックが組み込まれていますが、運用時の監視が必要です。
- Process 優先度や CPU affinity の変更は OS に依存し、権限不足で失敗する場合があります（ログに警告が出ます）。
- データ鮮度チェックや KillSwitch は安全のための仕組みです。設定値（閾値など）は環境に応じて調整してください。
- DB スキーマのマイグレーションは一部自動化されていますが、重要な変更を加える際はバックアップを推奨します。

---

README はここまでです。必要であれば、次の内容を追加できます：

- より詳しい起動例（systemd / Supervisor / Dockerfile）
- テスト実行方法（ユニットテスト／モックの例）
- 設定ファイル（.env.example）のテンプレート
- API/データベーススキーマの詳細ドキュメント

どれを追加しましょうか？