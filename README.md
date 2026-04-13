KabuSys — README
=================

概要
----
KabuSys は日本株の自動売買および研究用ユーティリティ群を含む Python ベースのプロジェクトです。  
主な機能は、ExecutionEngine（発注実行）・Monitoring（監視・アラート）・研究用ファクター計算・AI ベースのニュース評価などです。  
設計方針の一例として「ルックアヘッドバイアスを避ける」「DB 周りは冪等・クラッシュ耐性」「本番と paper_trading を明確に分離」などが採用されています。

主な機能一覧
--------------
- 発注実行
  - ExecutionEngine / OrderManager による発注フロー、ブローカ API 抽象化（BrokerClientFactory）
  - Reconciler による再起動時の状態同期（ブローカーとの照合）
  - paper_trading モード（MockBrokerClient）を用いた完全分離された検証
- 監視（Monitoring）
  - SystemMonitor: プロセス生存確認、CPU/メモリ/ディスク使用率、データ鮮度チェック
  - TradeMonitor: 注文滞留や約定価格異常の検出
  - RiskMonitor: ドローダウン・ポジション上限監視、dashboard の更新
  - KillSwitch: 条件に応じた停止フラグ（data/kill.flag）書き込み
  - AlertManager: LINE によるプッシュ通知（クールダウン付き）
  - Streamlit ダッシュボード（監視情報の可視化）
- 研究（Research）
  - ファクター計算（momentum/value/volatility 等）
  - 将来リターン計算、IC（Information Coefficient）等の統計ユーティリティ
- ポートフォリオ構築
  - 候補選定、等分配/スコア重み付け、セクター制約適用、ポジションサイズ算出（単元丸め・aggregate cap）
- AI（OpenAI）連携
  - news_nlp: ニュース記事をまとめて OpenAI（gpt-4o-mini）でセンチメント評価し ai_scores に保存
  - regime_detector: ETF の MA 乖離 + マクロニュースセンチメントを合成して市場レジーム判定
- ユーティリティ
  - process_priority: OS に依存せずプロセス優先度 / CPU affinity を設定
  - .env 読み込みユーティリティ（Settings）

セットアップ手順
----------------

1. リポジトリをクローン
   - 例: git clone <repo-url>

2. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - 必要な主なライブラリ:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit (ダッシュボード用)
   - 例:
     - pip install duckdb psutil requests openai streamlit

   （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt を使用）

4. データディレクトリ作成
   - デフォルトの DB / ファイルパスは data/ 配下に置かれます。必要なら作成してください:
     - mkdir -p data

5. 環境変数 / .env の準備
   - ルート（pyproject.toml または .git があるディレクトリ）に .env/.env.local を置くと自動読み込みされます。
   - 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

必須（または重要）な環境変数
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- OPENAI_API_KEY — OpenAI を使う機能（news_nlp, regime_detector）で必要
- KABUSYS_ENV — 実行モード: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL — ログレベル（例: INFO、DEBUG）
- PAPER_FILL_MODE — Paper Trading の約定動作（instant|partial|never|reject、デフォルト: instant）
- Optional:
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — AlertManager（LINE 通知）
  - SQLITE_PATH / DUCKDB_PATH / PAPER_TRADING_SQLITE_PATH / PID_FILE_PATH / KILL_FLAG_PATH など（デフォルト値は次節参照）

使い方（主なコマンド）
--------------------

- 実行優先度設定や DB 初期化を含む監視ループ起動
  - python -m kabusys.run_monitoring
  - 実行前に必要なら MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定可能（デフォルト 60）。
  - 監視は常に本番 sqlite_path を使用（KABUSYS_ENV に依らず）。

- Execution エンジン起動（発注実行）
  - 通常運用:
    - python -m kabusys.run_execution
  - Paper Trading（ブローカーはモック、DB を完全に分離）
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - この場合、デフォルトで data/paper_trading.db が使われます。

- Streamlit ダッシュボード（監視 UI）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - もしくは python -m streamlit run ... として実行

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db /path/to/paper_trading.db
    - 環境変数 PAPER_TRADING_SQLITE_PATH でも指定可能

- AI 機能（ニューススコア・レジーム判定）
  - ニューススコア付与:
    - Python から kabusys.ai.score_news(conn, target_date, api_key=None) を呼ぶ（api_key を渡すか OPENAI_API_KEY を設定）
  - レジームスコア:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

Settings / .env の挙動
----------------------
- 自動ロード順序: OS 環境 > .env.local > .env
- プロジェクトルートは __file__ の親ディレクトリ列を上って .git または pyproject.toml を検出して決定します。
- 複雑な .env の構文（export プレフィックス、クォート、インラインコメント）に対応した自前パーサを使用しています。
- 自動ロードを無効化する場合は:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

重要な既定値（Settings）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- PID_FILE_PATH: data/execution.pid
- KILL_FLAG_PATH: data/kill.flag
- CPU / メモリ / ディスクの閾値は Settings 経由で調整可能（例: CPU_THRESHOLD_PCT）

監視・アラートの振る舞い（概略）
--------------------------------
- SystemMonitor は PID ファイルの存在とプロセス存続をチェックし、stale PID を検出すると削除してリスクログに残します。
- TradeMonitor は滞留注文（既定 30 分）や約定価格の大きな乖離（既定 20%）を検出し、risk_logs に記録します。
- RiskMonitor はダッシュボードのハイウォーターマークを保持し、ドローダウン閾値超過やポジション数超過を検出すると risk_logs に追記します。
- KillSwitch はドローダウンやポジション上限超過などの条件時に data/kill.flag を書き込み、ExecutionEngine 側が検出して安全停止できるようにします。
- AlertManager は LINE の Push API を使って通知します（トークン未設定時はログのみ）。同一レベル・カテゴリでクールダウンを行います。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数 / Settings
- run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
- run_execution.py         — ExecutionEngine 起動スクリプト

subpackages:
- ai/
  - news_nlp.py            — ニュースからの AI スコアリング（OpenAI 呼出し）
  - regime_detector.py     — 市場レジーム判定（MA + マクロセンチメント合成）
- execution/
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - execution_engine.py    — (主要実装: 起動時リコン・セッション管理など)
  - broker_factory.py
  - broker_api.py
  - order_record.py
- monitoring/
  - monitoring_db.py       — SQLite 永続化（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py
  - monitoring_engine.py
  - streamlit_dashboard.py
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
  - process_priority.py    — プロセス優先度 / CPU affinity

注意・運用上のポイント
----------------------
- DB のマイグレーションは init_monitoring_db() の内部で最小限の ALTER を行います（冪等）。本番運用ではバックアップを推奨します。
- Execution と Monitoring は異なる SQLite ファイル（本番用・paper_trading 用）を使う設計です。paper_trading では data/paper_trading.db に記録されます。
- OpenAI API 呼び出しはリトライ・エラーハンドリングを実装していますが、API キーや利用料・レート制限には注意してください。
- process_priority の設定はプラットフォーム差異を吸収しますが、権限不足で設定できないことがあります（警告ログで通知されます）。
- KillSwitch のフラグファイルは存在するだけで停止トリガー扱いになります。必要に応じて起動時に clear してください（Settings.kill_flag_clear_on_start を使う設定もあります）。

トラブルシューティングのヒント
------------------------------
- DB に接続できない / 存在しない場合:
  - monitoring の起動前に data/monitoring.db を init_monitoring_db() で初期化またはディレクトリと適切な権限を確認してください。
- OpenAI 呼び出し周りでのエラー:
  - OPENAI_API_KEY の設定を確認。接続エラー・429 等はライブラリ内でリトライされますが、継続的な失敗ならログを確認してください。
- PID ファイル関連:
  - run_execution は起動時に pid_file を書く想定です。SystemMonitor はその PID を見てプロセス生存を判定します。stale PID は自動的に削除されます。

ライセンス / バージョン
-----------------------
- パッケージバージョンは kabusys.__version__ = "0.1.0"（初期値）
- ライセンス情報はプロジェクトルートの LICENSE（存在する場合）を参照してください。

最後に
------
この README はコードベースの主要な使い方・構成をまとめたものです。詳細な API や内部仕様（EngineConfig, RiskConfig のパラメータなど）はソースドキュメント・各モジュールの docstring を参照してください。必要なら運用手順（systemd ユニット、Dockerfile、CI 設定）などの追加ドキュメント作成もサポートします。