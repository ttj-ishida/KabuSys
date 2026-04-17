KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤です。  
主要コンポーネントは実行エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築ロジック、リサーチ／ファクター計算、AI ベースのニュース評価（OpenAI）などで構成されています。  
設計方針として、環境変数ベースの設定、SQLite / DuckDB を用いた永続化、ペーパートレードと本番の分離、安全な Kill Switch（停止フラグ）などを備えています。

主な機能
--------
- ExecutionEngine（発注処理、リスク管理、order 管理、reconciler 等） — 本番 / ペーパートレード対応
- Monitoring（SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine） — システム稼働性・データ鮮度・注文滞留・約定異常・ドローダウン監視
- Kill Switch（kill.flag） — 致命的条件で Execution を停止する仕組み
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ算出・セクター制約）
- リサーチ（ファクター計算：モメンタム / ボラティリティ / バリュー、将来リターン・IC 等の解析）
- ニュース NLP（OpenAI を使った銘柄別センチメントスコア算出）
- レジーム判定（ETF MA とマクロニュースの LLM 評価を組み合わせた市場レジーム判定）
- ユーティリティ：プロセス優先度設定、.env 対話ウィザード、設定検証 CLI、ペーパートレード検証レポート生成

必須・推奨依存ライブラリ
-----------------------
（プロジェクトに requirements.txt がない場合の代表例）
- Python 3.10+
- duckdb
- psutil
- openai
- PyYAML（config YAML の検証を行う場合）
- sqlite3（標準ライブラリ）

セットアップ手順
----------------
1. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML

3. プロジェクトルートに移動（本リポジトリのルート。.git か pyproject.toml を含む階層）
   - この場所に .env ファイルを配置する想定です。

4. .env を生成（対話式ウィザード）
   - python -m kabusys.config_setup
   - ウィザードで J-Quants / kabuステーション パスワード等を入力してください。
   - 重要: .env は絶対に Git にコミットしないでください。

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります。

6. DB ファイル／data ディレクトリ
   - Settings のデフォルト:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
   - これらの親ディレクトリは起動時に自動作成されることもありますが、権限等に注意してください。

環境変数（主要）
----------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
  - paper_trading の場合は MockBroker を使い、paper_trading DB に記録します
- OPENAI_API_KEY: OpenAI を使う機能（ニュース NLP / レジーム判定）で必要
- DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH: 各 DB ファイルのパス
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: paper_trading 時のモック約定モード（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）

使い方（主要コマンド）
--------------------
- 実行エンジンを起動
  - python -m kabusys.run_execution
  - 停止方法: 管理用フラグファイル（data/stop_requested.flag）を作成すると起動中の run_execution は停止処理を開始します（コード中の STOP フラグを参照）。
  - KABUSYS_ENV=paper_trading を設定するとペーパートレード専用 DB（PAPER_TRADING_SQLITE_PATH）を使用します。

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位でオーバーライド可能（デフォルト 60 秒）。
  - run_monitoring も data/stop_requested.flag の存在でループを終了します。

- .env 対話ウィザード（設定作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗（exit 1）になります。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは --db オプションまたは環境変数 PAPER_TRADING_SQLITE_PATH で指定可能。

- AI / リサーチ関数（ライブラリ呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 両方とも OpenAI API キー（api_key 引数または OPENAI_API_KEY 環境変数）が必要です。

停止・Kill Switch 操作
---------------------
- 手動停止（run_execution / run_monitoring）
  - data/stop_requested.flag を作成するとループが検知して終了します。
- 自動 Kill（危険検出時）
  - Monitoring の KillSwitch は data/kill.flag を書き込み、ExecutionEngine に停止を促します（設定により Execution 起動時に kill.flag を自動クリアするか制御可能）。
- Execution の PID ファイル
  - data/execution.pid 等に PID が書き込まれています。system monitor は stale PID を検知した場合に削除・アラートを行います。

ディレクトリ構成（主要ファイル）
-------------------------------
以下は src/kabusys 以下の主な構成（抜粋）です：

- kabusys/
  - __init__.py
  - config.py              — 環境変数読み込み / Settings クラス
  - config_setup.py        — .env 対話ウィザード
  - validate_config.py     — 起動前設定検証 CLI
  - run_execution.py       — ExecutionEngine 起動スクリプト
  - run_monitoring.py      — SystemMonitor ポーリング起動スクリプト

  - ai/
    - news_nlp.py          — ニュースを OpenAI でスコアリングする処理
    - regime_detector.py   — マクロ + ETF MA から市場レジーム判定
  - monitoring/
    - monitoring_db.py     — SQLite のテーブル初期化 / MonitoringDB クラス
    - system_monitor.py    — CPU/メモリ/ディスク／データ鮮度監視
    - trade_monitor.py     — 注文滞留・約定価格異常の監視
    - risk_monitor.py      — ドローダウン・ポジション上限監視
    - kill_switch.py       — kill.flag 書き込みロジック
    - monitoring_engine.py — 各モニタを束ねるループ
    - alert_manager.py     — （アラート送信管理: 実装ファイルあり）
  - portfolio/
    - portfolio_builder.py — 候補選定・スコアソート
    - position_sizing.py   — 株数算出・ロット丸め・キャップ処理
    - risk_adjustment.py   — セクター上限・レジーム乗数等
  - research/
    - factor_research.py   — モメンタム / ボラティリティ / バリュー等の計算（DuckDB）
    - feature_exploration.py — 将来リターン計算・IC・統計要約
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成スクリプト
  - utils/
    - process_priority.py  — プロセス優先度 / CPU affinity 設定ユーティリティ

主要モジュールの簡単説明
-----------------------
- config.py: .env 自動読み込み（.env / .env.local）・Settings による安全な環境値の取得
- config_setup.py: .env を対話的に作るウィザード
- validate_config.py: 起動前に環境変数や config/*.yaml の整合性をチェック
- monitoring/monitoring_db.py: monitoring 用の SQLite テーブルを作成し、CRUD 操作を提供
- monitoring/system_monitor.py: 実行プロセスの有無、データ鮮度、システム負荷を定期ログ
- ai/news_nlp.py: raw_news → OpenAI で銘柄ごとのセンチメントを生成し ai_scores に書く
- ai/regime_detector.py: ETF 1321 の MA200 とマクロニュースの組合せで daily レジームを算出
- portfolio/*: 候補選定・重み計算・数量決定・セクターキャップ・レジーム乗数などの実際のポジション設計ロジック
- utils/process_priority.py: プロセス優先度を OS に依存せず設定するヘルパー（psutil を利用）

運用上の注意
-------------
- .env を絶対にリポジトリにコミットしないこと（機密情報が含まれる）。
- 本番（KABUSYS_ENV=live）では LINE 通知等の設定を必ず確認してください（validate_config がチェック）。
- OpenAI API を使う処理は API コストとレイテンシの観点で注意が必要です。API キーの権限管理を厳格に行ってください。
- モニタリングはデータベースパスの親ディレクトリが存在しない場合に警告を出します。ディスクパス・権限を事前に確認してください。
- ペーパートレードは本番 DB と完全に分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH を利用）。

トラブルシューティング（よくある事象）
---------------------------------
- 起動時に設定不足エラーが出る:
  - python -m kabusys.validate_config で原因を確認し、.env を作り直す（python -m kabusys.config_setup）。
- OpenAI 呼び出しで失敗する:
  - OPENAI_API_KEY を設定済みか確認。API の一時エラーや RateLimit は内部でリトライ処理がありますが、ログとレート上限に注意してください。
- DB 周りのエラー:
  - ファイルの権限やパスを確認。DuckDB / SQLite のファイルはデフォルトで data/ 下に作られます。

ライセンス・バージョン
---------------------
- パッケージバージョンは kabusys.__version__ で管理（例: 0.1.0）

最後に
------
この README はソースコードの現状（主要モジュール）に基づく概要ドキュメントです。実運用時は config/*.yaml や追加ドキュメント（PortfolioConstruction.md、StrategyModel.md 等）を合わせて参照してください。質問や特定モジュールの詳細説明が必要であればお知らせください。