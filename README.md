KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買システム「KabuSys」のコアユーティリティ群を集めたコードベースです。  
本 README はローカルでのセットアップ、主要スクリプトの実行方法、ディレクトリ構成の説明を日本語でまとめています。

概要
----
KabuSys は以下のような責務を持つモジュール群で構成されます：

- 環境設定管理 (.env 読み込み / ウィザード)
- 実行エンジン起動スクリプト（ExecutionEngine）
- 監視 (Monitoring) — システム状態、注文状況、リスク監視、Kill Switch
- ポートフォリオ構築（銘柄選定、重み付け、ポジションサイズ）
- 研究用機能（ファクター計算、IC 計算など）
- AI 補助（ニュースセンチメント / レジーム判定 via OpenAI）
- 解析用ツール（Paper Trading 検証レポート生成 など）
- ロギング・プロセス優先度ユーティリティ

主な機能一覧
--------------
- config_setup: 対話式 .env 作成ウィザード（python -m kabusys.config_setup）
- validate_config: .env や config/*.yaml の事前検証 CLI（python -m kabusys.validate_config）
- run_execution: 実際の ExecutionEngine 起動用スクリプト（本番または paper_trading に対応）
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使い、paper_trading 用 DB に分離
  - 起動時にプロセス優先度を「high」に設定
  - 停止フラグ（data/stop_requested.flag）を検知して安全に停止
- run_monitoring: SystemMonitor ポーリングループ起動（MONITOR_POLL_INTERVAL で間隔変更可）
  - 監視データは monitoring 用 SQLite を使用（環境に依らず本番 sqlite_path）
  - 停止フラグ検知でループ終了
- monitoring モジュール群:
  - SystemMonitor: CPU/メモリ/Disk、プロセス生存・データ鮮度チェック
  - TradeMonitor: 注文の滞留 / 約定異常検出（trade_logs を参照）
  - RiskMonitor: ドローダウンやポジション上限の監視、risk_logs/dashboad 更新
  - KillSwitch: 条件到達時に data/kill.flag を書き込み ExecutionEngine を停止させる
  - MonitoringDB: SQLite のテーブル準備 / CRUD を担当
- portfolio モジュール群:
  - 候補選定 / 等重・スコア重み / リスク調整（セクター制限、レジーム乗数） / 発注株数計算（単元丸め、aggregate cap）
- research:
  - ファクター計算（momentum/value/volatility 等）、将来リターン、IC、統計サマリ
- ai:
  - news_nlp.score_news: ニュースを LLM でセンチメント評価して ai_scores に保存
  - regime_detector.score_regime: マクロニュース + ETF MA による日次レジーム判定
- tools:
  - paper_verification_report: Paper Trading 用の検証レポート生成（成功率・レイテンシ等の判定）

セットアップ手順
-----------------
1. Python 環境（3.10+ 推奨）を用意
2. 依存パッケージをインストール（例）
   - duckdb
   - psutil
   - openai
   - （オプション）PyYAML（config 検証で使う）
   例:
   - pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt がある場合はそれを使用してください）

3. プロジェクトルートで .env を用意
   - 対話式ウィザードを推奨:
     - python -m kabusys.config_setup
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要な環境変数（抜粋）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH: 分析用 DuckDB ファイル（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: ペーパー取引専用 DB（paper_trading 時）
     - OPENAI_API_KEY: OpenAI を使う場合に設定
     - LOG_LEVEL, LOG_DIR, PID_FILE_PATH, KILL_FLAG_CLEAR_ON_START など

4. DB ディレクトリ / data ディレクトリ作成
   - 通常は初回起動処理で必要なら自動作成されますが、手動作成して権限を確認しておくと安全です。
   - data/stop_requested.flag, data/kill.flag, data/execution.pid が使用されます。

5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

使い方（主要スクリプト）
------------------------

- 実行エンジン起動（ExecutionEngine）
  - 開発 / 本番 / ペーパートレードに応じて KABUSYS_ENV を設定して起動します。
  - 例 (本番/開発):
    - export KABUSYS_ENV=development
    - python -m kabusys.run_execution
  - 例 (ペーパートレード):
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
    - PAPER_TRADING_SQLITE_PATH が指定されていればその DB に記録され、本番 DB と分離されます。
  - 動作のポイント:
    - 起動時にプロセス優先度を High に設定しようとします（権限により失敗することがあります）。
    - 実行中に data/stop_requested.flag を作成するとスレッドが停止します。
    - 実行中は data/execution.pid に PID を書きます。

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒指定（デフォルト 60）
    - 例: export MONITOR_POLL_INTERVAL=30
  - 監視は monitoring 用の SQLite（Settings.sqlite_path）に書き込みます。Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使います。
  - 停止: data/stop_requested.flag を作成するか Ctrl+C

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- .env ウィザード
  - python -m kabusys.config_setup

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI 関連（ニュース / レジーム）
  - OpenAI API を利用します。OPENAI_API_KEY を設定してください。
  - ニューススコアリング: kabusys.ai.news_nlp.score_news (コード内 API)
  - レジーム判定: kabusys.ai.regime_detector.score_regime

主要ファイル・ディレクトリ構成
------------------------------
（src/kabusys 配下を抜粋）

- kabusys/
  - __init__.py
  - config.py                — 環境変数読み込み / Settings クラス（.env 自動ロード機能含む）
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - monitoring/
    - monitoring_db.py       — SQLite テーブル作成 / 永続化操作
    - system_monitor.py      — CPU/メモリ/ディスク/データ鮮度監視
    - trade_monitor.py       — 注文ログ監視（ファイル内に実装あり）
    - risk_monitor.py        — ドローダウン・ポジション数監視
    - kill_switch.py         — kill.flag 書き込みロジック
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - alert_manager.py       — （通知ラッパー、LINE などを想定）
  - execution/
    - execution_engine.py    — ExecutionEngine（起動 / run_session 等）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 発注株数計算・aggregate cap
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py     — momentum/value/volatility 等
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — マクロ+MA によるレジーム判定（OpenAI）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - utils/
    - logging_setup.py       — 統一的なロギング設定
    - process_priority.py    — プロセス優先度 / CPU affinity 設定

運用上の注意
--------------
- 環境変数と .env:
  - .env は絶対にリポジトリにコミットしないでください（機密情報が含まれます）。
  - .env 作成は config_setup.py を使うと安全です。
- DB 分離:
  - paper_trading モードでは PAPER_TRADING_SQLITE_PATH を使い、本番データと分離されます。
- Kill Switch / Stop Flag:
  - KillSwitch は条件に応じて data/kill.flag を書き込み、ExecutionEngine に安全停止を要求します。
  - run_monitoring / run_execution は data/stop_requested.flag を見て自己終了できます（手動停止用）。
- ログ:
  - ログは logs/<app_name>.log に日次ローテーションで保存されます（logs ディレクトリを作成できる必要あり）。
- OpenAI:
  - ai/news_nlp と ai/regime_detector は OpenAI API を使用します。OPENAI_API_KEY を設定してください。
  - API 呼び出しはリトライ / フェイルセーフを備えていますが、レート制限やコストに注意してください。
- 権限:
  - プロセス優先度変更や CPU affinity の設定は管理者権限が必要なことがあります。失敗した場合は警告が出て継続します。

トラブルシューティング
-----------------------
- 設定検証でエラーが出る:
  - 必須環境変数の未設定や不正値がないか確認してください。
  - config/*.yaml の不足や PyYAML 未インストールの場合は警告やスキップが出ます。
- ログファイルが作成されない:
  - ログディレクトリに書き込み権限があるか、環境変数 LOG_DIR の設定を確認してください。
- OpenAI 呼び出しで失敗する:
  - OPENAI_API_KEY を確認、ネットワーク、レート制限をチェックしてください。モジュールはリトライ処理を行いますが、API 権限や料金に注意。

開発者向けメモ
----------------
- DuckDB を分析用に使用。prices_daily / raw_financials 等のテーブルを前提にファクター計算を行います。
- 多くのモジュールは「DB 接続を引数で受け取る」設計で、テスト時はモック接続で容易に差し替え可能です。
- 自動ロードされる .env はプロジェクトルート（.git または pyproject.toml）を基準に探索します。テスト時に自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ライセンス / 貢献
-----------------
（ここにプロジェクトのライセンスや貢献方法を記載してください。現状 README にライセンス情報は含まれていません）

以上がこのコードベースの簡潔な概要と使い方です。必要であれば各モジュール（ExecutionEngine、Monitoring の詳細 API 仕様や db スキーマなど）を別途ドキュメント化します。どの部分をより詳しく知りたいか教えてください。