KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤を想定した Python パッケージです。  
主な機能は以下の通りです:

- 発注エンジン（ExecutionEngine） — live / paper_trading / development を切り替え可能
- 監視（Monitoring） — システム状態・注文ログ・リスク監視、Kill Switch（フラグファイル）連携
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ算出）
- ファクター計算・リサーチ（Momentum / Volatility / Value 等）
- ニュース NLP（OpenAI を用いたセンチメント評価 / 市場レジーム判定）
- 各種ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード、設定検証、レポート生成）

特徴
----
- モジュール化された設計（monitoring / execution / ai / portfolio / research / utils）
- SQLite（監視・ペーパートレード） + DuckDB（時系列/分析データ）を併用
- .env による環境変数管理／対話式ウィザードと検証ツールを提供
- OpenAI 統合（ニュースセンチメント、レジーム判定）を想定した堅牢なリトライ・バリデーション
- ログは標準出力と日次ローテーションされたファイル出力（logs/*.log）

必要条件（推奨）
----------------
下記は本リポジトリのコードで参照される主要パッケージ例です。環境によってバージョン調整してください。

- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（config 検証で任意）
- その他（必要に応じて）: sqlite3（標準）、logging など標準ライブラリ

セットアップ手順
---------------
1. リポジトリをクローン:
   - git clone <repo-url>

2. 仮想環境作成（例）:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール（requirements.txt が無い場合は個別に）:
   - pip install duckdb psutil openai PyYAML

4. データディレクトリを作成（初期ファイルの保存先）:
   - mkdir -p data logs

5. 環境変数ファイルを作成:
   - python -m kabusys.config_setup
     （対話式ウィザードで .env を生成／更新します）

6. 設定検証:
   - python -m kabusys.validate_config
   - 必要なら --strict を付けて警告も失敗扱いにする

主要コマンド・使い方
------------------

1. ExecutionEngine（取引エンジン）起動
   - 本番・ペーパートレードを .env の KABUSYS_ENV で切り替えます。
   - 起動:
     - python -m kabusys.run_execution
   - 補足:
     - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、デフォルトで data/paper_trading.db を使用（本番 DB と分離）。
     - 起動後は data/execution.pid に PID が書き込まれます。停止は kill.flag を作るかスクリプトを停止してください。
     - 停止フラグ: data/stop_requested.flag / data/kill.flag（Kill Switch）

2. Monitoring（監視ループ）起動
   - 起動:
     - python -m kabusys.run_monitoring
   - 環境変数:
     - MONITOR_POLL_INTERVAL: ポーリング間隔（秒）。デフォルト 60
   - 補足:
     - 監視は本番 sqlite_path を参照（KABUSYS_ENV に依らず同一 monitoring DB を使用）
     - stop フラグファイル data/stop_requested.flag を置くとループを終了します

3. 設定ウィザード・検証
   - .env 生成／更新:
     - python -m kabusys.config_setup
   - 設定検証:
     - python -m kabusys.validate_config [--strict]

4. Paper Trading 検証レポート生成
   - レポート:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - オプション:
     - --db で SQLite ファイルを指定（環境変数 PAPER_TRADING_SQLITE_PATH を優先）

5. AI / リサーチ機能（ライブラリ API）
   - ニュースセンチメント（ai）:
     - kabusys.ai.score_news(conn, target_date, api_key=None)
   - レジーム判定:
     - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
   - これらは DuckDB 接続を受け取り、内部で OpenAI API を呼び出します（OPENAI_API_KEY 指定が必要）。

主要な環境変数（抜粋）
---------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV  (development | paper_trading | live) — デフォルト development
- LOG_LEVEL (DEBUG/INFO/...)
- DUCKDB_PATH — デフォルト data/kabusys.duckdb
- SQLITE_PATH — デフォルト data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — デフォルト data/paper_trading.db
- PAPER_FILL_MODE — paper_trading のフィル処理（instant/partial/never/reject）
- OPENAI_API_KEY — AI 機能を使う場合に必要
- MONITOR_POLL_INTERVAL — 監視ループの秒間隔（run_monitoring 用）

ログ
----
- ログ出力は kabusys.utils.logging_setup.setup_logging により統一管理されます。
- stdout（StreamHandler）に加え、日次ローテーションのファイルハンドラ（logs/<app_name>.log）を生成します（既定で logs ディレクトリ、30日保持）。

Kill Switch / 停止フラグ
-----------------------
- data/kill.flag: Kill Switch が発動した旨を保存するファイル。ExecutionEngine は起動時にこのフラグを確認します。
- data/stop_requested.flag: run_monitoring/run_execution によるループ停止のためのファイル。存在すると各ループは安全に終了します。
- KillSwitch はリスク監視（ドローダウン・ポジション上限等）により kill.flag を書き込みます（冪等）。

ディレクトリ構成（主なファイル）
------------------------------
以下は本リポジトリの主要なモジュール構成（抜粋）です:

- src/
  - kabusys/
    - __init__.py
    - config.py                 — 環境変数 / Settings
    - config_setup.py           — .env 対話ウィザード
    - validate_config.py        — 設定検証 CLI
    - run_execution.py          — ExecutionEngine 起動スクリプト
    - run_monitoring.py         — Monitoring 起動スクリプト
    - utils/
      - logging_setup.py        — ログ設定ユーティリティ
      - process_priority.py     — プロセス優先度・CPU affinity 設定
    - monitoring/
      - monitoring_db.py        — SQLite 永続化レイヤ
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py        — （アラート送信ロジック等; 実装参照）
    - execution/
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
      - broker_factory.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - ai/
      - news_nlp.py
      - regime_detector.py
    - monitoring/
      - monitoring_db.py
    - tools/
      - paper_verification_report.py

（上記はリポジトリ内の主要ソースの抜粋です。実際のファイル一覧はプロジェクトルートの src/kabusys ディレクトリを参照してください。）

開発上の注意点 / 運用上の注意
--------------------------
- 本システムは「自動発注」を行う設計を含みます。KABUSYS_ENV=live を運用する場合は .env の値や Kill Switch の設定を十分に確認してください。
- .env は機密情報（API トークン等）を含むため、絶対にリポジトリにコミットしないでください。
- OpenAI を使う処理は API Key を外部に送信するため、使用・課金に関するポリシーを確認してください。
- DuckDB / SQLite のパスは .env で適切に分離しておく（特に本番とペーパーは別 DB を推奨）。
- 監視 / エンジンの起動順序や PID / フラグファイルの取り扱いに注意してください（run_execution は起動時に stop flag を確認します）。

拡張 / 貢献
------------
- 新しい戦略・ファクターの追加、ブローカーインターフェースの実装、アラートチャネル（LINE）の拡張などが想定拡張です。
- PR の前に lint / unit test を整備してください（現在のコードベースは主要ロジックを関数化・純粋関数化しているためユニットテストが書きやすい構造です）。

参考コマンドまとめ
------------------
- .env 作成（対話式）:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- Execution 起動:
  - python -m kabusys.run_execution
- Monitoring 起動:
  - python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD

以上。README の内容やサンプルコマンドを実環境に合わせて調整してご利用ください。必要であればより詳しい運用手順書（デプロイ手順、systemd サービス定義、ログローテーション確認等）も作成できます。