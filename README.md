KabuSys — 日本株自動売買システム（README）
=====================================

概要
---
KabuSys は日本株向けの自動売買・リサーチ・監視を目的とした Python パッケージ群です。本コードベースは以下の主要機能を持ち、実運用・ペーパートレード・リサーチ用途に対応するよう設計されています。

- 注文エンジン（ExecutionEngine）と注文管理（OrderManager / Reconciler）
- モニタリング（System / Trade / Risk）とアラート送信（LINE）
- AI を用いたニュースセンチメント（OpenAI）とレジーム検出
- ポートフォリオ構築（候補選定、配分、ポジションサイジング、リスク調整）
- DuckDB / SQLite を用いた時系列データ・監視ログ保存
- Streamlit ダッシュボード、ペーパートレード検証レポート生成ツール

主な特徴・設計方針
- 本番・ペーパートレードを分離（KABUSYS_ENV による切替）
- ルックアヘッドバイアス防止（date/time の扱いに注意）
- フェイルセーフ：API エラー時はフォールバックして継続（例: OpenAI 呼び出し失敗時）
- モジュールは純粋関数／副作用を最小化する設計（テスト容易性を重視）

機能一覧
---
- Execution（起動スクリプト: run_execution.py）
  - Broker クライアント切替（KABUSYS_ENV=paper_trading の場合は Mock）
  - OrderManager / RiskManager / Reconciler を組み合わせた実行セッション
  - 停止フラグ（data/stop_requested.flag / data/kill.flag）で安全停止
- Monitoring（起動スクリプト: run_monitoring.py）
  - SystemMonitor（CPU/Memory/Disk、プロセス、データ鮮度）
  - TradeMonitor（滞留注文、約定異常価格）
  - RiskMonitor（ドローダウン、ポジション上限）
  - KillSwitch（一定条件で Execution に停止命令を発行）
  - AlertManager（LINE Push による通知）
  - Streamlit ダッシュボード（監視用 UI）
- AI
  - news_nlp.score_news: ニュースを集約して OpenAI で銘柄ごとのセンチメントを算出・ai_scores に書き込み
  - regime_detector.score_regime: ETF（1321）MA200 とマクロニュースを合成して市場レジーム判定
- Research
  - ファクター計算（momentum / volatility / value）
  - 将来リターン、IC 計算、統計サマリー
- Portfolio
  - 候補選定（select_candidates）
  - 重み計算（等配分 / スコア加重）
  - ポジションサイジング（単元株丸め、リスクベース等）
  - セクターキャップ、レジーム乗数適用
- Tools
  - paper_verification_report: Paper Trading の検証レポートを生成

セットアップ手順
---
前提: Python 3.9+（ソースは typing の新構文を利用）、git ワークツリー内で動かすことを想定しています。

1. リポジトリをクローン（またはソースを取得）
   - git clone ... またはローカルに配置

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージのインストール（最低限）
   - pip install duckdb psutil openai requests streamlit

   ※ 実際の requirements.txt があればそれを使用してください。

4. 環境変数 / .env の設定
   - プロジェクトルートに .env または .env.local を配置可能（config.py が自動で読み込みます）
   - 主要な環境変数:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須な箇所で参照）
     - KABU_API_PASSWORD: kabu API パスワード
     - OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
     - SQLITE_PATH: 監視 DB パス（デフォルト: data/monitoring.db）
     - DUCKDB_PATH: DuckDB パス（デフォルト: data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 DB（デフォルト: data/paper_trading.db）
     - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動 .env ロードを無効化できます

5. データディレクトリ作成（必要に応じて）
   - mkdir -p data

使い方（起動 / よく使うコマンド）
---

基本的にパッケージのモジュールをモジュール実行（-m）で起動します。

- 監視ループの起動（Monitoring）
  - MONITOR_POLL_INTERVAL を必要に応じて設定できます（秒、1 以上）。
  - python -m kabusys.run_monitoring
  - 監視は常に settings.sqlite_path（デフォルト data/monitoring.db）を使用します（環境に関係なく監視 DB は本番 DB を参照する設計）。

- 注文エンジンの起動（Execution）
  - KABUSYS_ENV=paper_trading の場合、ペーパートレード専用 DB（PAPER_TRADING_SQLITE_PATH）と MockBroker を使用します。
  - python -m kabusys.run_execution
  - Execution は data/execution.pid（既定）を作成し、data/stop_requested.flag または data/kill.flag を検知すると停止します。

- Streamlit ダッシュボード（監視用）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ブラウザで監視指標・最近のイベント・ポジション等を確認できます（読み取り専用で DB を開きます）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH  （PAPER_TRADING_SQLITE_PATH を上書き）
  - 例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- AI 機能（ニューススコア / レジーム判定）
  - OpenAI API キー（OPENAI_API_KEY）が必須です。
  - Python から呼び出して利用する例:
    - from datetime import date
      from duckdb import connect
      from kabusys.ai.news_nlp import score_news
      conn = connect('data/kabusys.duckdb')
      score_news(conn, date(2026, 4, 1), api_key='sk-xxxx')
    - 同様に regime_detector.score_regime(conn, target_date, api_key=...)

運用上の注意
- 停止フラグ:
  - data/stop_requested.flag: run_monitoring / run_execution で参照される停止フラグ（外部から停止要求を出す際に使用）
  - data/kill.flag: KillSwitch（監視側）から Execution 停止要求を出す際に作成されます
- PID ファイル:
  - data/execution.pid（デフォルト）は Execution 起動時に作成され、SystemMonitor はこの PID を参照してプロセスの生存チェックを行います
- DB マイグレーション:
  - init_monitoring_db() は冪等的にテーブルを作成し、既存 DB に欠けているカラムを追加するマイグレーションロジックを持っています
- Logging / 権限:
  - set_process_priority() はプラットフォームによっては権限不足で失敗する場合があります（警告ログのみ出力）

ディレクトリ構成（主要ファイル）
---
以下は src/kabusys 以下の主要モジュール・ファイル一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env ロード・Settings 管理
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
- src/kabusys/execution/
  - order_manager.py
  - order_repository.py
  - order_record.py
  - reconciliation.py
  - reconciler.py
  - broker_factory.py
  - execution_engine.py
  - risk_manager.py
- src/kabusys/monitoring/
  - monitoring_db.py
  - monitoring_engine.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - alert_manager.py
  - kill_switch.py
  - streamlit_dashboard.py
- src/kabusys/ai/
  - news_nlp.py
  - regime_detector.py
- src/kabusys/research/
  - factor_research.py
  - feature_exploration.py
- src/kabusys/portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- src/kabusys/tools/
  - paper_verification_report.py
- src/kabusys/utils/
  - process_priority.py

（上記はソース内で参照されている主要コンポーネントを抜粋したものです。）

開発・テストに関する補足
---
- config.py の自動 .env ロードはプロジェクトルート（.git か pyproject.toml を起点）を探索して行います。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 関連の内部呼び出し関数はテスト時にモックしやすいように分離されています（例: _call_openai_api を patch）。
- DuckDB / SQLite 接続は外部の DB ファイルパスを受け取り、read-only URI でダッシュボードから安全に開くことができます。

ライセンス・貢献
---
（ここにライセンス情報・貢献方法を追記してください）

最後に
---
本 README はコードベースに含まれる docstring / コメントを基に作成しています。実運用の前に各環境変数やパス、Broker クライアントの実装（kabu API 連携や Mock 実装）を確認し、テスト環境で十分な検証を行ってください。質問や追記したい項目があればお知らせください。