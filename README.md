KabuSys — README
=================

概要
----
KabuSys は日本株の自動売買 / リサーチ / 監視を目的とした軽量な Python コードベースです。
主なコンポーネントは以下の通りです。

- ExecutionEngine（発注・注文管理・リスク管理・リコンシリエーション）
- Monitoring（システム稼働・注文滞留・ドローダウン監視・アラート）
- Portfolio（銘柄選定・重み計算・ポジションサイズ決定）
- Research（ファクター計算・将来リターン・IC 計算）
- AI（ニュースセンチメント、レジーム判定）
- ツール（Paper Trading 用検証レポート、Streamlit ダッシュボード）

主な設計方針：
- DB は SQLite / DuckDB を使用。Paper Trading（検証）は本番 DB と分離可能。
- LLM（OpenAI）連携はフェイルセーフ（API 失敗時に継続）で設計。
- datetime.today()/date.today() の安易な参照を避け、ルックアヘッドバイアスを抑制。

機能一覧
-------
- 発注管理（OrderManager、OrderRepository、BrokerClientFactory）
- 起動時リコンシリエーション（Reconciler）
- リスク管理（RiskManager / RiskMonitor）
- システム監視（CPU・メモリ・ディスク・データ鮮度・PID チェック）
- 注文監視（滞留注文、約定異常検出）
- Kill Switch（条件に応じて data/kill.flag を書き込み Execution を停止）
- LINE を用いたアラート送信（AlertManager）
- Streamlit ベースの監視ダッシュボード
- Paper Trading 用検証レポート生成スクリプト
- ファクター計算 / 特徴量解析ユーティリティ（DuckDB ベース）
- ニュース NLP（OpenAI を使った銘柄ごとのセンチメント算出）
- 市場レジーム判定（ETF MA + マクロニュースの LLM スコア合成）

必要条件
-------
- Python 3.10+
- SQLite（標準ライブラリ）
- 以下の主要な Python パッケージ（抜粋）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード利用時)

セットアップ手順
---------------
1. リポジトリをクローン / 展開
   - プロジェクトルートには pyproject.toml または .git が存在する想定

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - Windows: .venv\Scripts\activate
   - macOS/Linux: source .venv/bin/activate

3. 依存パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   - （必要に応じて他のパッケージも追加）

4. 環境変数設定
   - プロジェクトルートに .env または .env.local を配置すると自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可）。
   - 必須（実行コンポーネントに応じて）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を使う場合:
     - OPENAI_API_KEY
   - サンプル（.env の最小例）:
     JQUANTS_REFRESH_TOKEN=your_jquants_token
     KABU_API_PASSWORD=your_kabu_password
     OPENAI_API_KEY=sk-...
     KABUSYS_ENV=development
     LINE_CHANNEL_ACCESS_TOKEN=xxxxx
     LINE_USER_ID=Uxxxxxx

主要な環境変数（抜粋）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading の場合、Execution は MockBrokerClient を使い data/paper_trading.db に書き込みます。
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 DB（デフォルト: data/paper_trading.db）
- PID_FILE_PATH, KILL_FLAG_PATH, MONITOR_POLL_INTERVAL（秒）など
- OPENAI_API_KEY: OpenAI 呼び出しに必要（AI 機能）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager 用

使い方
-----

実行（Monitoring）
- 監視ループを起動（ポーリング・DB 書き込み・KillSwitch 判定等）
- 実行:
  - プロジェクトルートから:
    python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で上書き:
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 注意:
  - monitoring は KABUSYS_ENV の値に関わらず settings.sqlite_path（本番パス）を使用します。
  - 停止は data/stop_requested.flag を作成するか、Ctrl+C。

実行（ExecutionEngine）
- エンジンを起動して注文処理を行う
- 実行:
  - python -m kabusys.run_execution
- KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、データは paper_trading 用 DB に記録され完全分離されます。
- PID ファイル（data/execution.pid）を生成し、プロセス優先度を "high" に設定します。
- 停止:
  - data/stop_requested.flag を作成することで安全停止を行います。
  - KillSwitch（監視により data/kill.flag が書かれた場合、Execution は停止します）。

Streamlit ダッシュボード
- 監視 DB を読み取り専用で表示します。
- 起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

Paper Trading 検証レポート
- data/paper_trading.db を読み取ってレポートを出力
- 実行例:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

AI 機能（ニュース NLP / レジーム判定）
- OpenAI API キーが必須（OPENAI_API_KEY または引数で指定）
- 直接 Python から呼び出す（DuckDB 接続を渡す必要があります）。
  例（概念）:
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, date(2026, 4, 1), api_key="sk-...")

停止・Kill
- data/stop_requested.flag:
  - run_monitoring / run_execution のメインループはこのフラグファイルを監視し、存在すると安全に終了します。
- data/kill.flag:
  - KillSwitch（監視コンポーネント）が条件を満たした場合に作成され、ExecutionEngine に停止シグナルとして利用されます。
  - KillSwitch を手動でクリアしたい場合はファイルを削除するか KillSwitch.clear() を実行。

実装上の重要な挙動（備考）
- run_monitoring は Monitoring 用の DB を環境にかかわらず settings.sqlite_path を使います（監視は常に本番対象を扱う想定）。
- run_execution は KABUSYS_ENV が paper_trading の場合、paper_sqlite_path を使用して本番 DB と分離します。
- 起動直後にプロセス優先度を "high" に設定（set_process_priority）。
- .env の読み込みは自動（プロジェクトルートが検出できる場合）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

ディレクトリ構成（主要ファイル）
--------------------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数 / 設定管理
- run_monitoring.py        — Monitoring ポーリングループ起動スクリプト
- run_execution.py         — ExecutionEngine 起動スクリプト

モジュール群:
- ai/
  - news_nlp.py            — ニュースセンチメント（OpenAI）
  - regime_detector.py     — 市場レジーム判定
- monitoring/
  - monitoring_db.py       — SQLite テーブル初期化 / 永続化層
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
  - (その他 broker / order_repository 等)
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- tools/
  - paper_verification_report.py
- utils/
  - process_priority.py

プロジェクトルート（想定）
- pyproject.toml
- .env, .env.local
- data/
  - monitoring.db (default)
  - kabusys.duckdb (default)
  - paper_trading.db (paper_trading 用)
  - execution.pid
  - stop_requested.flag
  - kill.flag

開発・運用上のヒント
------------------
- Paper Trading 検証は本番データや口座に影響を与えないよう設計されています。KABUSYS_ENV=paper_trading を活用してください。
- OpenAI を呼ぶ箇所は外部 API に依存するため、API キーとレート制限対策（リトライ・バッチ処理）に注意してください。
- SQLite / DuckDB のファイルは適切にバックアップしておくことを推奨します。
- モニタリングのアラートは LINE を用いた push で行えます。クールダウン（デフォルト 30 分）が組み込まれています。

ライセンス・貢献
----------------
- 本 README はコードベースの説明用です。ライセンス情報・コントリビューションガイドはリポジトリのルートを参照してください。

お問い合わせ
------------
- 実行や設定で不明点があれば、対象モジュール（例: config.py, monitoring/*, execution/*）の docstring を参照してください。
- 小さなユーティリティやテスト用フックはモジュール内に記載されています（例: news_nlp._call_openai_api はテストで差し替え可能）。

以上。必要であれば README に含めるコマンド例や .env.example のテンプレートを追記します。どの部分を詳細化しますか？