KabuSys — 日本株自動売買システム
=============================

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤の一部を実装した Python パッケージです。  
主な機能は以下の通りです：

- 実行エンジン（ExecutionEngine）：発注・リスク管理・約定管理（paper_trading ではモックブローカー）
- 監視（Monitoring）：プロセス死活、データ鮮度、注文状況、リスク（ドローダウン・ポジション上限）をポーリングしてログ／アラートを出す
- ポートフォリオ構築：候補選定、重み計算、株数決定、セクター制限などの純粋関数群
- 研究（Research）：ファクター計算、将来リターン、IC 等の統計解析
- AI モジュール：ニュースセンチメント（OpenAI）を用いたスコアリングや市場レジーム判定
- ツール類：.env ウィザード、設定検証、Paper Trading 検証レポート生成 等
- 永続化：SQLite（監視 / paper trading DB）・DuckDB（時系列・研究用データ）

特徴
----
- 環境変数 / .env ベースで柔軟に設定（config.Settings）
- 実行 / 監視プロセスに共通のログ設定（ログローテーション対応）
- Paper Trading（完全に本番 DB と分離）モードをサポート
- OpenAI を用いたニュース解析・レジーム判定のサポート（API キー必須）
- フェイルセーフ設計（API エラーやデータ不足時は安全なフォールバック）

主な機能一覧
--------------
- run_execution.py: ExecutionEngine の起動スクリプト（KABUSYS_ENV により実際発注 or モック）
  - paper_trading の場合は MockBrokerClient を用い、データベースは data/paper_trading.db を使用
  - 起動前に data/stop_requested.flag が存在すると起動しない
  - プロセス優先度を high に設定
- run_monitoring.py: SystemMonitor のポーリング起動スクリプト
  - 環境変数 MONITOR_POLL_INTERVAL で間隔上書き可（デフォルト 60 秒）
  - 監視は本番の sqlite_path を使用（環境に依らず）
- config_setup.py: 対話式 .env 作成ウィザード
- validate_config.py: .env と config/*.yaml の起動前チェック CLI（--strict で警告も FAIL）
- tools/paper_verification_report.py: Paper Trading の検証レポート生成（稼働率・成立率・レイテンシ等）
- ai/news_nlp.py, ai/regime_detector.py: OpenAI を用いたニュースセンチメント / レジーム判定（API キー必須）
- portfolio/*: 候補選定、重み、ポジションサイズ、セクターキャップ等の純粋関数
- monitoring/*: MonitoringDB（SQLite 永続化）、SystemMonitor、RiskMonitor、KillSwitch、MonitoringEngine など

セットアップ手順
----------------
1. Python 環境を用意（推奨: 3.10+）
2. 必要パッケージをインストール
   - 最低限の依存例:
     pip install duckdb psutil openai
   - 以下は機能に応じて必要:
     - PyYAML（config/*.yaml の検証に必要）
   - 実環境では requirements.txt を用意して pip install -r requirements.txt を推奨

3. プロジェクトルートで .env を作成
   - 対話式ウィザード:
     python -m kabusys.config_setup
   - あるいは .env.example を参考に作成
   - 重要な環境変数:
     - JQUANTS_REFRESH_TOKEN （必須）
     - KABU_API_PASSWORD （必須）
     - OPENAI_API_KEY （AI 機能を使う場合必須）
     - KABUSYS_ENV: development / paper_trading / live （デフォルト: development）
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用、デフォルト data/paper_trading.db）
     - LOG_LEVEL（デフォルト INFO）
     - MONITOR_POLL_INTERVAL（run_monitoring 用、秒。デフォルト 60）

4. ディレクトリ作成（必要に応じて）
   - data/ （データベース・フラグ用）
   - logs/ （ログ出力用。setup_logging が自動作成を試みますが権限等で失敗することがあります）

5. 設定検証（任意）
   python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになる

使い方（主要スクリプト）
-----------------------

- ExecutionEngine を起動（通常はサービスや systemd、nohup 等でデーモン化）
  - 通常起動:
    python -m kabusys.run_execution
  - paper_trading モードで起動する場合:
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 実行が開始されると data/execution.pid（デフォルト）に PID が書かれ、停止は data/stop_requested.flag を作成して行います

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL を指定してポーリング間隔を変更可:
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- .env を対話式で作る
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - 環境変数 PAPER_TRADING_SQLITE_PATH で DB 指定可（デフォルト data/paper_trading.db）

- AI 機能
  - OpenAI を使う機能（ニューススコアリング、レジーム判定）は OPENAI_API_KEY が必要
  - 直接呼び出す場合は関数に api_key 引数を渡すか環境変数 OPENAI_API_KEY を設定

運用に関する注意点
------------------
- kill.flag / stop flag:
  - KillSwitch により条件を満たすと data/kill.flag が書かれ、ExecutionEngine に停止指示を送ることができます
  - 実行停止用の flag: data/stop_requested.flag（run_*.py はこのファイルを検知して終了）
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番では 0 推奨）

- ロギング:
  - 共通の setup_logging を使い logs/<app_name>.log に日次ローテーションで出力（30 日保持）
  - コンソールは stdout に出力されます（cron 等でリダイレクトしやすくするため）

- DB:
  - monitoring（SQLite）はデフォルト data/monitoring.db に永続化されます
  - research/価格データ等は DuckDB（data/kabusys.duckdb）を使用
  - paper_trading モードは paper_trading 用 SQLite（data/paper_trading.db）を使用し、本番 DB と完全分離

- プロセス優先度:
  - 起動スクリプトは set_process_priority("high") を呼びます。psutil の権限により実行環境では失敗する場合があります（警告ログのみ）

ディレクトリ構成（主なファイル）
-------------------------------
以下は src/kabusys 配下の主要ファイル群（省略あり）：

- kabusys/
  - __init__.py
  - config.py                  — 環境変数/Settings 管理（.env 自動読み込みロジック含む）
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor ポーリング起動スクリプト
  - monitoring/
    - monitoring_db.py         — SQLite スキーマ作成 / DB 操作ラッパー
    - system_monitor.py        — システム状態・データ鮮度監視
    - risk_monitor.py          — ドローダウン・ポジション上限監視
    - trade_monitor.py         — 注文滞留・約定異常監視（監視系）
    - monitoring_engine.py     — 複数モニタ束ねるランナー
    - kill_switch.py           — kill.flag 発行ロジック
    - alert_manager.py         — アラート通知管理（LINE 等）
  - execution/
    - execution_engine.py      — ExecutionEngine（発注ループのコア）
    - broker_factory.py        — Broker クライアント生成（実口座 / モック）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py              — ニュースセンチメント（OpenAI）
    - regime_detector.py       — 市場レジーム判定（OpenAI + MA）
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py         — 共通ログ設定
    - process_priority.py      — プロセス優先度 / CPU affinity ユーティリティ

依存関係（主なもの）
-------------------
- duckdb
- psutil
- openai
- PyYAML（任意、validate_config の YAML 検証に使用）

よくある質問 / トラブルシューティング
------------------------------------
- Q: モデルにアクセスできない（OpenAI）／API キーが無い
  - A: NEWS / REGIME 機能は API キーが必須。テスト時は呼び出し先をモックできます。

- Q: logs ディレクトリが作れない／ファイルハンドラが作れない
  - A: 権限等で失敗した場合は標準出力のみで継続します（警告が出ます）。logs/ を手動で作成して権限を確認してください。

- Q: MONITOR_POLL_INTERVAL を小さくするとエラーになる
  - A: 環境変数は正の整数で指定してください。0 や負の値は無視されデフォルト 60 秒が使われます。

- Q: 本番環境での kill.flag の扱い
  - A: KILL_FLAG_CLEAR_ON_START=1 は本番では危険です（起動時に自動で Kill Switch をクリアしてしまうため）。live 環境では 0 を推奨します。

開発・拡張に関して
------------------
- 研究用・AI 用の処理は DuckDB 接続を受け取り、look-ahead をしない設計になっています（再現性重視）。
- broker クライアントは Factory 経由で切り替えられ、paper_trading では完全に本番 DB から分離されます。
- 追加のアラートチャネル（Slack, Email 等）は AlertManager を拡張して実装してください。

ライセンス・バージョン
---------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（例: 0.1.0）。
- ライセンスはリポジトリのルートに従ってください（ここでは明示していません）。

以上がこのコードベースの概観・導入手順です。具体的な実行手順や環境依存の調整（systemd ユニット、コンテナ化、監視設定等）が必要であれば、目的に合わせた起動例や systemd / Dockerfile のサンプルを作成します。必要なら教えてください。