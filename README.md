KabuSys — 日本株自動売買システム
================================

本リポジトリは日本株向けの自動売買 / 研究ツール群を含む小規模なシステムです。
主要機能にはエンジン実行（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、
ファクター計算・リサーチ、ニュース NLP を用いた AI スコアリング等があります。

以下は本コードベースの利用に必要な概要、セットアップ手順、使い方、ディレクトリ構成の説明です。

プロジェクト概要
----------------
- ExecutionEngine: 発注処理・注文管理・リスク管理を行う実行コンポーネント（run_execution.py）。
  - KABUSYS_ENV が `paper_trading` の場合は MockBroker を使い、本番 DB と分離して data/paper_trading.db に記録します。
- Monitoring: システム状態、注文・約定ログ、リスク監視をポーリングし、Kill Switch の判定やアラート発行を行う（run_monitoring.py）。
- Portfolio: 候補選定、重み計算、ポジションサイズ計算、セクター制約など純粋関数群（kabusys.portfolio）。
- Research: DuckDB 上の時系列データを使ったファクター計算・特徴量探索（kabusys.research）。
- AI: OpenAI を利用したニュースセンチメント（news_nlp）や市場レジーム判定（regime_detector）。
- Tools: ペーパートレード検証レポート生成スクリプト（kabusys.tools.paper_verification_report）。
- 設定 / ユーティリティ:
  - 環境設定読み込み・管理（kabusys.config）
  - 対話式 .env 作成ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
  - ログ設定・プロセス優先度ユーティリティ等（kabusys.utils）

主な機能一覧
------------
- 環境設定の自動読み込み（.env / .env.local、OS env 優先）
- 対話式 .env 作成ウィザード（config_setup）
- 設定検証ツール（validate_config、--strict オプションあり）
- 実行エンジン起動スクリプト（run_execution.py）
  - Paper trading と Live を分離
  - PID / stop フラグ制御（data/execution.pid, data/stop_requested.flag）
- 監視エンジン起動スクリプト（run_monitoring.py）
  - MONITOR_POLL_INTERVAL でポーリング間隔を指定可能（デフォルト 60 秒）
  - monitoring DB（SQLite）へ system/trade/risk/dashbord ログを永続化
  - Kill Switch 判定（kill.flag 書き込み）
- DuckDB を利用したファクター計算・研究関数群（momentum / volatility / value 等）
- OpenAI を用いたニュースセンチメント・レジーム判定（リトライ、レスポンスバリデーションを備える）
- Paper Trading 検証レポート生成（期間指定可能）

前提条件（動作環境）
-------------------
- Python 3.10+
  - 型記法（X | Y）を使用しているため 3.10 以上を要求します。
- 必要パッケージ（一例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（validate_config の YAML 検証を行う場合に必要）
- SQLite（標準ライブラリ sqlite3 を使用）
- ネットワーク接続（OpenAI API を使う機能を利用する場合）

セットアップ手順
----------------
1. リポジトリをクローンして作業ディレクトリをプロジェクトルートに移動:
   - プロジェクトルートの判定は .git または pyproject.toml に依存します。
2. 仮想環境を作成して有効化（推奨）:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール:
   - pip install duckdb psutil openai PyYAML
   - 実際の requirements.txt があればそれを使ってください。
4. 環境変数 / .env ファイルの準備:
   - 対話式ウィザードを使う: python -m kabusys.config_setup
   - もしくは .env を手動で作成（下記「主要な環境変数」を参照）
5. 設定の検証（必須項目が埋まっているか確認）:
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります
6. データディレクトリ:
   - デフォルトで data/ 以下に DB やフラグファイルを作成します。必要に応じて .env でパスを上書きしてください。

主要な環境変数（.env 例）
------------------------
以下は主な環境変数の例（.env に保存）:

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
KABUSYS_ENV=development      # development | paper_trading | live
LOG_LEVEL=INFO
PAPER_FILL_MODE=instant     # paper_trading 用: instant | partial | never | reject
KILL_FLAG_CLEAR_ON_START=0

- 注意: .env は絶対にソース管理にコミットしないでください（config_setup でも警告あり）。
- Settings クラス（kabusys.config）で多くのプロパティが参照されます。必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD。

使い方（CLI）
--------------
- .env 作成（対話式）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン起動
  - python -m kabusys.run_execution
  - 動作中は data/execution.pid を作成し、data/stop_requested.flag により外部から停止できます。
  - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を用い、PAPER_TRADING_SQLITE_PATH に記録します。
- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL（秒）でポーリング間隔を上書き可能。デフォルト 60 秒。
- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report
  - 期間を指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB を明示する場合: --db PATH
- AI スコアリング / レジーム判定（ライブラリ関数）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API キーが必要（api_key 引数または OPENAI_API_KEY 環境変数）

ログ / PID / フラグファイル
-------------------------
- ログ: デフォルト logs/ ディレクトリ。setup_logging が logs/<app_name>.log を日次ローテーションで出力します。
- PID: data/execution.pid（ExecutionEngine が使用）
- 停止フラグ: data/stop_requested.flag — 起動スクリプトはこのファイル存在を見てループを終了します。
- Kill Switch: data/kill.flag — Monitoring 側がリスクトリガーで書き込み、ExecutionEngine 停止の合図として使います。

注意事項 / 実運用上のポイント
----------------------------
- KABUSYS_ENV を `live` にした場合は本番発注が有効になります。設定値やキーの取り扱いに十分注意してください。
- validate_config の警告・メッセージを確認し、特に本番時の LINE 通知設定や KILL_FLAG_CLEAR_ON_START の値を確認してください。
- OpenAI を使う機能は API 呼び出しの失敗耐性（リトライ、フォールバック）を備えていますが、API コストやレイテンシに注意してください。
- DuckDB / SQLite ファイルのバックアップとアクセス制御を実施してください（個人情報 / トレード履歴が含まれ得ます）。
- psutil を使用してプロセス優先度や CPU affinity を設定します。権限不足により設定が失敗する場合は警告で続行されます。

ディレクトリ構成（抜粋）
-----------------------
以下は src/kabusys 配下の主要ファイル / ディレクトリ（今回提供されたコードに基づく抜粋）:

- src/kabusys/
  - __init__.py
  - run_execution.py                — ExecutionEngine 起動スクリプト
  - run_monitoring.py               — Monitoring 起動スクリプト
  - config.py                       — 環境変数 / Settings 管理
  - config_setup.py                 — .env を対話式で作るウィザード
  - validate_config.py              — 設定検証 CLI
  - utils/
    - logging_setup.py              — ログ設定ユーティリティ
    - process_priority.py           — 優先度 / affinity 設定
  - monitoring/
    - monitoring_db.py              — SQLite 永続化層（テーブル作成・アクセス）
    - system_monitor.py             — システム状態・データ鮮度チェック
    - trade_monitor.py              — 注文 / 約定の監視（参照されるが今回省略）
    - risk_monitor.py               — ドローダウン / ポジション上限監視
    - kill_switch.py                 — kill.flag 書き込みロジック
    - monitoring_engine.py          — 各 Monitor を束ねる
    - alert_manager.py              — アラート送信（参照されるが今回省略）
  - execution/                       — Execution 関連コンポーネント（Engine 等、参照される）
  - portfolio/
    - portfolio_builder.py          — 候補選定・重み計算
    - position_sizing.py            — 発注株数決定
    - risk_adjustment.py            — セクター制約 / レジーム乗数
  - research/
    - factor_research.py            — ファクター計算（momentum/volatility/value）
    - feature_exploration.py        — 将来リターン / IC / 統計サマリー
  - ai/
    - news_nlp.py                   — ニュース NLP / OpenAI 呼び出し・検証
    - regime_detector.py            — 市場レジーム判定
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート生成ツール

ライセンス・貢献
----------------
- 本 README ではライセンスファイルを含めていません。実際の配布時は LICENSE を追加してください。
- 貢献は Issue / Pull Request を通じて受け付けてください。

よくあるコマンドまとめ
---------------------
- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- Execution 起動: python -m kabusys.run_execution
- Monitoring 起動: python -m kabusys.run_monitoring
- Paper レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

最後に
------
この README はリポジトリ内の主要スクリプト・モジュールの概要と運用に必要な手順をまとめたものです。
実際の運用では設定ファイル（.env、config/*.yaml）および DB の権限・バックアップ方針、監視（外部）の設計を適切に行ってください。質問や補足があれば教えてください。