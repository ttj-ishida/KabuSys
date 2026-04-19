KabuSys — 日本株自動売買システム
=================================

本ドキュメントはリポジトリ内の主要スクリプト・モジュールをもとに作成した README です。
起動スクリプトや設定ウィザード、監視・検証ツールの使い方を日本語でまとめています。

プロジェクト概要
---------------
KabuSys は日本株自動売買を想定したモジュール群です。主な責務は以下のとおりです。

- 発注エンジン（ExecutionEngine）: ブローカーとのやり取り、注文管理、リスク管理、約定監視
- 監視（Monitoring）: システム状態・注文状況・リスク（ドローダウン等）を定期ポーリングしてログ・アラートを管理
- ポートフォリオ構築（portfolio）: 候補選定、重み付け、ポジションサイズ計算、セクター制約、レジーム調整
- リサーチ（research）: DuckDB 上の価格・財務データからファクター計算や特徴量解析
- AI 補助（ai）: OpenAI を用いたニュースセンチメントスコアリング・市場レジーム判定
- 設定管理: .env の自動読み込み、対話式生成、静的検証ツール・ウィザード
- ツール: ペーパートレード検証レポート等のユーティリティ

主な機能一覧
-------------
- 環境設定ウィザード（python -m kabusys.config_setup）による .env 生成・更新
- 起動前チェック（python -m kabusys.validate_config）で環境変数・設定ファイルの問題検出
- ExecutionEngine の起動 / 停止（run_execution.py）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading DB に分離して記録
- Monitoring のポーリング実行（run_monitoring.py）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
  - 監視は常に本番 sqlite_path を用いる設計
- Kill Switch（data/kill.flag）による ExecutionEngine の強制停止
- RiskMonitor によるドローダウン・ポジション上限検出と永続化（SQLite）
- AI モジュールでニュースをスコア化し ai_scores に永続化（OpenAI API 利用）
- Paper Trading 検証レポート生成ツール（python -m kabusys.tools.paper_verification_report）
- DuckDB を利用したファクター計算・リサーチ機能（prices_daily / raw_financials 参照）
- ロギングセットアップ（コンソール + 日次ローテートファイル）

前提条件 / 依存（概略）
---------------------
（リポジトリに requirements.txt がある場合はそちらを利用してください）
主に以下のパッケージが必要になります（バージョンは適宜調整してください）:

- duckdb
- psutil
- openai
- PyYAML（validate_config の YAML 検証を行う場合）
- （標準ライブラリ: sqlite3, logging, threading など）

セットアップ手順
----------------

1. Python 環境準備
   - 推奨: 仮想環境を作成してアクティベート
     - python -m venv .venv
     - source .venv/bin/activate  (Linux/macOS)
     - .venv\Scripts\activate     (Windows)

2. 依存パッケージのインストール
   - 例:
     - pip install duckdb psutil openai pyyaml
   - もし requirements.txt があれば:
     - pip install -r requirements.txt

3. .env の作成（対話式推奨）
   - python -m kabusys.config_setup
   - もしくは .env を手動作成（.env.example を参考に）
   - 自動読み込み:
     - config.py はプロジェクトルート（.git または pyproject.toml を基準）にある .env / .env.local を自動で読み込みます
     - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

4. 設定検証（起動前）
   - python -m kabusys.validate_config
   - --strict オプションを付けると警告も失敗として扱う

5. DB / ディレクトリの準備
   - デフォルトのパス:
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - ログディレクトリ: logs/
   - 必要なら directories を作る（多くはコード側で存在確認・作成を行います）

環境変数（主なもの）
-------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: 実行環境。development | paper_trading | live（デフォルト: development）
  - KABUSYS_ENV=paper_trading の場合、発注はモックに切り替わりデータは PAPER_TRADING_SQLITE_PATH に記録されます
- DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
- LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）
- OPENAI_API_KEY（ai.news_nlp / ai.regime_detector を使う場合）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔 [秒]、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START（本番での Kill Flag 自動クリアを制御）

使い方（起動・ツール）
---------------------

- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine 起動（発注エンジン）
  - python -m kabusys.run_execution
  - 補足
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使いデータを data/paper_trading.db に記録
    - 起動時、data/stop_requested.flag が存在すると起動を中止
    - エンジンは PID ファイル（data/execution.pid など）を作成する
    - 停止は CTRL+C、もしくは monitoring の KillSwitch により data/kill.flag を作成して通知

- Monitoring 起動（監視ポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL で間隔を秒単位で指定可能（例: MONITOR_POLL_INTERVAL=120）
  - 監視は常に Settings.sqlite_path を使用（監視 DB は本番 DB に記録）
  - data/stop_requested.flag を作成するとポーリングループが終了する（外部停止用）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH  （PAPER_TRADING_SQLITE_PATH 環境変数より優先）

- AI 系（ニューススコア / レジーム判定）
  - ai.news_nlp.score_news(conn, target_date, api_key=None)  # OPENAI_API_KEY を利用
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 実行には OPENAI_API_KEY が必要（未設定だと ValueError）

停止・Kill Switch の仕組み
------------------------
- 停止フラグ: data/stop_requested.flag
  - run_monitoring と run_execution はこのファイルを参照して安全に終了します
- Kill Switch: data/kill.flag
  - KillSwitch.evaluate() が書き込み、ExecutionEngine に対して停止を促す仕組み
  - 設定により起動時に自動クリアされる場合があります（KILL_FLAG_CLEAR_ON_START=1）

ログ
----
- ログはデフォルトで stdout と logs/<app_name>.log（日次ローテーション）に出力されます
- ログレベルは LOG_LEVEL 環境変数で制御可能

ディレクトリ構成（主要ファイル）
------------------------------
下記は src/kabusys 以下の主要モジュールと簡単な説明です。

- kabusys/
  - __init__.py  — パッケージ初期化、バージョン
  - config.py  — 環境変数・.env 自動ロードと Settings クラス
  - config_setup.py — 対話式 .env ウィザード
  - validate_config.py — 起動前検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
  - utils/
    - logging_setup.py — ログ設定ユーティリティ（stdout + 日次ローテーション）
    - process_priority.py — プロセス優先度設定 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py — SQLite を使った監視ログ永続化層
    - system_monitor.py — CPU/メモリ/ディスク / データ鮮度 / プロセス生存監視
    - trade_monitor.py — （注文監視ロジック: 滞留注文・約定異常等）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 書き込みユーティリティ
    - monitoring_engine.py — 各 Monitor を束ねる実行エンジン
    - alert_manager.py — （通知管理：LINE 等へ送る実装を想定）
  - execution/
    - execution_engine.py — 実行ロジック（セッション管理）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py ...
      （発注・リスク制御・リポジトリ等）
  - portfolio/
    - portfolio_builder.py — 候補選定・スコアソート
    - position_sizing.py — 株数決定・単元丸め・集約キャップ処理
    - risk_adjustment.py — セクター制約・レジーム乗数
  - research/
    - factor_research.py — momentum / volatility / value 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン計算、IC、統計サマリ
  - ai/
    - news_nlp.py — ニュースセンチメント（OpenAI呼出し）と ai_scores への反映
    - regime_detector.py — マクロニュース + MA200 で市場レジーム判定
  - data/ — デフォルトで利用する DB / フラグ / PID ファイル置き場（例: data/monitoring.db）
  - config/ — YAML 設定ファイル（system_config.yaml など）

補足・運用上の注意
-----------------
- KABUSYS_ENV を正しく設定してください。live を指定する際は本番設定（LINE 通知や Kill Switch 設定等）に注意が必要です（validate_config の live ガード参照）。
- .env は機密情報を含むため Git にコミットしないでください（config_setup.py のヘッダにも注意書きあり）。
- OpenAI を利用するモジュールは API 利用料が発生します。APIキーの取り扱いに注意してください。
- DuckDB / SQLite のパスは環境変数で上書きできます。paper_trading の場合は paper_trading DB を使って本番 DB と分離されます。
- 長期運用する場合はログローテーション、ディスク容量、DB バックアップポリシーを検討してください。

トラブルシュート
-----------------
- validate_config で警告・エラーが出たら指摘に従って .env や config/*.yaml を修正してください。
- psutil 関連で権限エラーが出る場合はプロセスの実行権限や OS のポリシー（nice, affinity）を確認してください。
- OpenAI 呼び出しのエラーは一時的な場合があるため、retry ロジックが入っています。継続的に失敗する場合は API キーやネットワーク、料金プランを確認してください。

最後に
------
この README はコードベースから主要な設計意図と操作手順を抜粋・要約したものです。各モジュール内部に詳細な docstring／コメントがありますので、実装を利用または変更する際は該当ファイルを参照してください。質問や補足が必要であれば教えてください。